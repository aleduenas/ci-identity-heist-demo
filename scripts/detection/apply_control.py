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

# "sub" is GitHub's signed job identity: repository, branch/PR context and run IDs.
SUB = "token.actions.githubusercontent.com:sub"


def load_setting(path: Path) -> bool:
    # 1. Read the versioned switch. Require a real boolean so "false" or a typo
    # cannot accidentally select the deliberately vulnerable lab state.
    config = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(config, dict) or set(config) != {"enforcement_enabled"}
            or type(config["enforcement_enabled"]) is not bool):
        raise ValueError("Expected exactly one boolean: enforcement_enabled")
    return config["enforcement_enabled"]


def trust_policy(account: str, prefix: str, enabled: bool) -> dict:
    # 2. Build the complete trust policy. Numeric owner/repository IDs make the
    # allowed repository explicit; this is not a match on an editable session name.
    if not re.fullmatch(r"repo:[A-Za-z0-9-]+@[0-9]+/[A-Za-z0-9_.-]+@[0-9]+", prefix):
        raise ValueError("Expected the exact immutable GitHub repository subject prefix")
    # Keep legitimate main pushes and manual main runs in either control state.
    contexts = [("ref:refs/heads/main", "push"), ("ref:refs/heads/main", "workflow_dispatch")]
    if not enabled:
        # Only the OFF state allows unreviewed PR jobs to obtain this role.
        contexts.append(("pull_request", "pull_request"))
    # This policy decides who may obtain credentials, not which data they can read.
    # Version is the IAM policy syntax version, not the deployment date.
    return {"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow", "Action": "sts:AssumeRoleWithWebIdentity",
        # Accept tokens through this AWS account's GitHub OIDC provider only.
        "Principal": {"Federated":
                      f"arn:aws:iam::{account}:oidc-provider/token.actions.githubusercontent.com"},
        "Condition": {
            # The token must be intended for AWS STS, the credential-issuing service.
            "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
            # Wildcards allow different run numbers/attempts; repo and context stay exact.
            "StringLike": {SUB: [f"{prefix}:{context}:event_name:{event}:run_id:*:run_attempt:*"
                                 for context, event in contexts]},
        },
    }]}


def same_policy(left: dict, right: dict) -> bool:
    # IAM may reorder JSON fields and subject values. Preserve all other constraints.
    def normalized(doc):
        # Compare copies so sorting cannot alter the policy we will print or submit.
        doc = json.loads(json.dumps(doc))
        try:
            subjects = doc["Statement"][0]["Condition"]["StringLike"][SUB]
            if isinstance(subjects, list):
                subjects.sort()
        except (KeyError, IndexError, TypeError):
            # Leave unexpected shapes intact; they will fail the known-policy comparison.
            pass
        return doc
    return normalized(left) == normalized(right)


def apply_control(iam, role_arn: str, prefix: str, enabled: bool) -> dict:
    # 3. Limit the target to the exercise deployer, then check the returned account
    # and role ARN: IAM GetRole takes a name, so the name alone is insufficient.
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
    # Accept only our known ON/OFF policies. Stop on unfamiliar principals or
    # restrictions rather than silently replacing someone else's security changes.
    if not any(same_policy(current, trust_policy(account, prefix, state))
               for state in (True, False)):
        raise ValueError("Unrecognized live trust policy; refusing to replace it")
    # 4. Make the proposed change visible in the Actions log before writing it.
    print("BEFORE:\n" + json.dumps(current, indent=2), flush=True)
    print(f"DESIRED enforcement_enabled={str(enabled).lower()}:\n"
          + json.dumps(desired, indent=2), flush=True)
    if not same_policy(current, desired):
        # The enforcement change: AWS will evaluate this trust on new STS requests.
        # Skip the write when already correct, so rerunning safely reconciles state.
        iam.update_assume_role_policy(RoleName=name, PolicyDocument=json.dumps(desired))
    # 5. Read back from IAM, allowing time for its stored policy to become visible.
    # This verifies the saved policy; a fresh CI attempt proves actual STS enforcement.
    for attempt in range(11):
        saved = iam.get_role(RoleName=name)["Role"]["AssumeRolePolicyDocument"]
        if same_policy(saved, desired):
            print("SAVED AND VERIFIED:\n" + json.dumps(saved, indent=2), flush=True)
            return saved
        if attempt < 10:
            time.sleep(3)
    # A mismatch must turn the deployment job red instead of claiming success.
    raise RuntimeError("IAM readback did not match desired policy; deployment failed")


def main():
    # 6. Inputs come from the committed file and explicit GitHub workflow variables.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("security/control.json"))
    parser.add_argument("--role-arn", default=os.environ.get("DETECTION_DEMO_ROLE_ARN", ""))
    parser.add_argument("--subject-prefix",
                        default=os.environ.get("SECURITY_CONTROL_SUBJECT_PREFIX", ""))
    args = parser.parse_args()
    enabled = load_setting(args.config)
    # boto3 uses the short-lived security-role credentials acquired by the workflow.
    # The prepared workflow deploys this example using temporary AWS credentials.
    iam = boto3.client("iam", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    saved = apply_control(iam, args.role_arn, args.subject_prefix, enabled)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        # Retain the verified policy in the run summary, without tokens or credentials.
        with Path(summary).open("a", encoding="utf-8") as report:
            report.write(f"## Exercise IAM control\n\nEnforcement: **{enabled}**\n\n"
                         f"Target: `{args.role_arn}`\n\nSaved policy:\n```json\n"
                         + json.dumps(saved, indent=2) + "\n```\n\n"
                         "IAM readback verified. Test a fresh CI run after propagation.\n")


if __name__ == "__main__":
    main()
