"""Operator recovery helper: update AWS IAM trust to toggle whether the exercise
deploy role trusts pull-request jobs. This is the control as an operator would apply it in the
lab architecture — editing the role's trust policy through the IAM API.

  python -m scripts.detection.set_trust show        # print the role's current trust policy
  python -m scripts.detection.set_trust block-pr    # fix: trust only main (push/dispatch)
  python -m scripts.detection.set_trust allow-pr    # revert to the vulnerable PR-trusting state

Equivalent raw CLI for `show` is `aws iam get-role --role-name <role>
--query Role.AssumeRolePolicyDocument`; applying a change is `aws iam
update-assume-role-policy --role-name <role> --policy-document <json>`.
"""

import argparse
import json

SUB = "token.actions.githubusercontent.com:sub"


def toggle(doc: dict, mode: str) -> dict:
    """Return the trust policy with the pull_request subject removed (block) or added (allow)."""
    statement = doc["Statement"][0]
    like = statement["Condition"]["StringLike"]
    subjects = like[SUB]
    subjects = [subjects] if isinstance(subjects, str) else list(subjects)
    mains = [s for s in subjects if ":pull_request:" not in s]
    if not mains:
        raise SystemExit("No main-branch subject patterns found; refusing to rewrite trust")
    if mode == "block-pr":
        new = mains
    else:
        prefix = mains[0].split(":ref:refs/heads/main")[0]
        pull_request = f"{prefix}:pull_request:event_name:pull_request:run_id:*:run_attempt:*"
        new = list(dict.fromkeys([*mains, pull_request]))
    like[SUB] = new
    return doc


def main():
    import boto3

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["show", "block-pr", "allow-pr"])
    parser.add_argument("--role", default="mybank-sandbox-detection-demo-deploy")
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()
    iam = boto3.client("iam", region_name=args.region)
    doc = iam.get_role(RoleName=args.role)["Role"]["AssumeRolePolicyDocument"]
    if args.mode == "show":
        print(json.dumps(doc, indent=2))
        return
    doc = toggle(doc, args.mode)
    iam.update_assume_role_policy(RoleName=args.role, PolicyDocument=json.dumps(doc))
    print(f"{args.role} trust updated ({args.mode}); it now accepts:")
    for subject in doc["Statement"][0]["Condition"]["StringLike"][SUB]:
        context = subject.split("@")[-1].split(":", 1)[-1]
        print(f"  {context}")


if __name__ == "__main__":
    main()
