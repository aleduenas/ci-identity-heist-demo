"""Security-as-code deployment: read the setting, constrain IAM trust, verify readback.

Run by security-control.yml on trusted main. No project helpers or local AWS login.
false deliberately permits the synthetic PR attack; true permits only main.
"""

import argparse
import json
import os
import re
import time
from pathlib import Path

import boto3

SUB = "token.actions.githubusercontent.com:sub"


def load_setting(path: Path) -> bool:
    config = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(config, dict) or set(config) != {"enforcement_enabled"}
            or type(config["enforcement_enabled"]) is not bool):
        raise ValueError("Expected exactly one boolean: enforcement_enabled")
    return config["enforcement_enabled"]


def trust_policy(account: str, prefix: str, enabled: bool) -> dict:
    if not re.fullmatch(r"repo:[A-Za-z0-9-]+@[0-9]+/[A-Za-z0-9_.-]+@[0-9]+", prefix):
        raise ValueError("Expected the exact immutable GitHub repository subject prefix")
    contexts = [("ref:refs/heads/main", "push"), ("ref:refs/heads/main", "workflow_dispatch")]
    if not enabled:
        contexts.append(("pull_request", "pull_request"))
    return {"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow", "Action": "sts:AssumeRoleWithWebIdentity",
        "Principal": {"Federated":
                      f"arn:aws:iam::{account}:oidc-provider/token.actions.githubusercontent.com"},
        "Condition": {
            "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
            "StringLike": {SUB: [f"{prefix}:{context}:event_name:{event}:run_id:*:run_attempt:*"
                                 for context, event in contexts]},
        },
    }]}


def same_policy(left: dict, right: dict) -> bool:
    # IAM may reorder JSON fields and subject values. Preserve all other constraints.
    def normalized(doc):
        doc = json.loads(json.dumps(doc))
        try:
            subjects = doc["Statement"][0]["Condition"]["StringLike"][SUB]
            if isinstance(subjects, list):
                subjects.sort()
        except (KeyError, IndexError, TypeError):
            pass
        return doc
    return normalized(left) == normalized(right)


def apply_control(iam, role_arn: str, prefix: str, enabled: bool) -> dict:
    target = re.fullmatch(r"arn:aws:iam::([0-9]{12}):role/([\w+=,.@-]+-detection-demo-deploy)",
                          role_arn)
    if not target:
        raise ValueError("Target must be the exact sandbox detection-demo-deploy role ARN")
    account, name = target.groups()
    desired = trust_policy(account, prefix, enabled)
    role = iam.get_role(RoleName=name)["Role"]
    if role["Arn"] != role_arn:
        raise ValueError("Live role ARN differs from the configured target")
    current = role["AssumeRolePolicyDocument"]
    # Fail closed on unexpected principals, statements, branches or conditions.
    if not any(same_policy(current, trust_policy(account, prefix, state))
               for state in (True, False)):
        raise ValueError("Unrecognized live trust policy; refusing to replace it")
    print("BEFORE:\n" + json.dumps(current, indent=2), flush=True)
    print(f"DESIRED enforcement_enabled={str(enabled).lower()}:\n"
          + json.dumps(desired, indent=2), flush=True)
    if not same_policy(current, desired):
        iam.update_assume_role_policy(RoleName=name, PolicyDocument=json.dumps(desired))
    for attempt in range(11):
        saved = iam.get_role(RoleName=name)["Role"]["AssumeRolePolicyDocument"]
        if same_policy(saved, desired):
            print("SAVED AND VERIFIED:\n" + json.dumps(saved, indent=2), flush=True)
            return saved
        if attempt < 10:
            time.sleep(3)
    raise RuntimeError("IAM readback did not match desired policy; deployment failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("security/control.json"))
    parser.add_argument("--role-arn", default=os.environ.get("DETECTION_DEMO_ROLE_ARN", ""))
    parser.add_argument("--subject-prefix",
                        default=os.environ.get("SECURITY_CONTROL_SUBJECT_PREFIX", ""))
    args = parser.parse_args()
    enabled = load_setting(args.config)
    iam = boto3.client("iam", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    saved = apply_control(iam, args.role_arn, args.subject_prefix, enabled)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as report:
            report.write(f"## Exercise IAM control\n\nEnforcement: **{enabled}**\n\n"
                         f"Target: `{args.role_arn}`\n\nSaved policy:\n```json\n"
                         + json.dumps(saved, indent=2) + "\n```\n\n"
                         "IAM readback verified. Test a fresh CI run after propagation.\n")


if __name__ == "__main__":
    main()
