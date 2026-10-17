"""Tear the demo down: stop delivery, remove the runner, close demo PRs, destroy, verify."""

import argparse

import boto3

from scripts.aws.run import REGION
from scripts.demo import gh, runner
from scripts.demo.attack import PREFIX
from scripts.demo.github_api import request
from scripts.demo.ops import activate, ok, step, terraform, tf_vars


def github_cleanup(repo: dict):
    step("GitHub: stop deployments, remove runner, close demo PRs")
    gh.set_var(repo, "DEPLOY_ENABLED", "false")
    gh.delete_var(repo, "D2_DEMO_ROLE_ARN")
    runner.remove(repo)
    for pr in request("GET", f"{repo['path']}/pulls?state=open&per_page=50"):
        if pr["head"]["ref"].startswith(PREFIX):
            request("PATCH", f"{repo['path']}/pulls/{pr['number']}", {"state": "closed"})
            request("DELETE", f"{repo['path']}/git/refs/heads/{pr['head']['ref']}")
            ok(f"closed demo PR #{pr['number']} without merging")


def verify():
    step("Verify nothing billable remains")
    ec2 = boto3.client("ec2", region_name=REGION)
    checks = {
        "EKS clusters": boto3.client("eks", region_name=REGION).list_clusters()["clusters"],
        "running instances": [i["InstanceId"] for r in ec2.describe_instances(Filters=[
            {"Name": "tag:Name", "Values": ["mybank-sandbox*"]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping"]},
        ])["Reservations"] for i in r["Instances"]],
        "NAT gateways": [n["NatGatewayId"] for n in ec2.describe_nat_gateways(Filters=[
            {"Name": "state", "Values": ["pending", "available"]}])["NatGateways"]],
        "elastic IPs": [a["AllocationId"] for a in ec2.describe_addresses()["Addresses"]],
    }
    for name, items in checks.items():
        print(f"    {name}: {items or 'none'}")
    if any(checks.values()):
        raise SystemExit("Resources remain; re-run `python -m scripts.demo.down`")
    ok("teardown verified; state bucket, bootstrap role and budget are kept by design")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="Destroy without prompting")
    args = parser.parse_args()
    activate()
    repo = gh.repository()
    github_cleanup(repo)
    step("Terraform destroy")
    if not args.yes and input("    Destroy the whole lab? [y/N] ").strip().lower() != "y":
        raise SystemExit("Stopped before destroy")
    terraform("destroy", "-auto-approve", "-input=false", *tf_vars(repo))
    verify()


if __name__ == "__main__":
    main()
