"""Stand up the whole demo: infrastructure, GitHub wiring, image, runner, app, data, release.

Every stage is idempotent, so re-running after a failure resumes safely.
"""

import argparse
import re

from scripts.demo import gh, kube, runner
from scripts.demo.ops import CACHE, activate, ok, save_outputs, step, terraform, tf_vars


def infrastructure(repo: dict, assume_yes: bool) -> dict:
    step("1/7 Infrastructure: Terraform plan and apply (private EKS, DynamoDB, roles)")
    terraform("init", "-input=false", "-backend-config=backend.hcl")
    plan = str(CACHE / "sandbox.tfplan")
    output = terraform("plan", "-input=false", "-no-color", *tf_vars(repo), f"-out={plan}",
                       capture=True)
    summary = re.search(r"Plan: .*|No changes\..*", output)
    print("    " + (summary.group(0) if summary else "plan produced"), flush=True)
    if "No changes" not in output:
        if not assume_yes and input("    Apply this plan? [y/N] ").strip().lower() != "y":
            raise SystemExit("Stopped before apply")
        terraform("apply", "-input=false", plan)
    values = save_outputs()
    ok(f"cluster {values['cluster_name']} in {values['aws_region']}; saved .cache/outputs.json")
    return values


def github(repo: dict, values: dict):
    step("2/7 GitHub: OIDC subject template and repository variables (no secrets)")
    gh.set_oidc_template(repo)
    variables = {
        "AWS_REGION": values["aws_region"], "AWS_BUILD_ROLE_ARN": values["build_role_arn"],
        "ECR_REPOSITORY_URL": values["ecr_repository_url"],
        "AWS_DEPLOY_ROLE_ARN": values["deploy_role_arn"],
        "EKS_CLUSTER_NAME": values["cluster_name"],
        "MYBANK_OIDC_RUN_CONTEXT": "true",
        "DETECTION_DEMO_ROLE_ARN": values["detection_demo_role_arn"],
    }
    for name, value in variables.items():
        gh.set_var(repo, name, value)
    ok(f"{len(variables)} variables set; OIDC subject prefix {repo['prefix']}")


def publish(repo: dict, values: dict) -> str:
    step("3/7 Image: trusted main release builds and pushes to private ECR")
    image = kube.main_image(repo, values)
    if not image:
        gh.set_var(repo, "DEPLOY_ENABLED", "false")
        run = gh.dispatch(repo, "release.yml")
        if run["jobs"].get("publish") != "success":
            raise SystemExit(f"Release publish failed: {run['jobs']}")
        image = kube.main_image(repo, values)
    ok(image)
    return image


def release(repo: dict):
    step("7/7 Trusted release: main -> deploy role -> private runner -> rollout")
    gh.set_var(repo, "DEPLOY_ENABLED", "true")
    run = gh.dispatch(repo, "release.yml")
    if run["jobs"].get("deploy") != "success":
        raise SystemExit(f"Release deploy failed: {run['jobs']}")
    ok("main release deployed through the deploy role on the private runner")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="Apply the Terraform plan unprompted")
    args = parser.parse_args()
    activate()
    repo = gh.repository()
    print(f"Repository {repo['full']} ({repo['prefix']})")
    values = infrastructure(repo, args.yes)
    github(repo, values)
    image = publish(repo, values)
    step("4/7 Runner: main-only release runner on the private operations host")
    runner.wait_host_ready(values["operations_instance_id"])
    runner.register(repo, values)
    step("5/7 Kubernetes: bootstrap the app privately with a fresh lab API key")
    kube.bootstrap(values, image)
    step("6/7 Data: seed synthetic records")
    kube.seed()
    release(repo)
    print("\nDemo environment is up. Next: python -m scripts.demo.app  (see DEMO.md)")


if __name__ == "__main__":
    main()
