"""Kubernetes steps over the private SSM tunnel, using the short-lived bootstrap-admin role."""

import os
import sys
from contextlib import contextmanager

import boto3

from scripts.aws.run import REGION, ROOT
from scripts.demo.github_api import request
from scripts.demo.ops import OUTPUTS, api_key, bootstrap_env, eks_tunnel, ok, run

sys.path.insert(0, str(ROOT / "scripts/deploy"))
from common import kubeconfig  # noqa: E402


def main_image(repo: dict, values: dict) -> str | None:
    """Digest of the image the trusted release published for the current main commit."""
    sha = request("GET", f"{repo['path']}/commits/main")["sha"]
    name = values["ecr_repository_url"].split("/", 1)[1]
    ecr = boto3.client("ecr", region_name=REGION)
    try:
        detail = ecr.describe_images(repositoryName=name, imageIds=[{"imageTag": sha}])
    except ecr.exceptions.ImageNotFoundException:
        return None
    return f"{values['ecr_repository_url']}@{detail['imageDetails'][0]['imageDigest']}"


@contextmanager
def admin_kubectl(values: dict):
    """Yield a kubectl command bound to a temporary kubeconfig through the tunnel."""
    saved = dict(os.environ)
    with eks_tunnel(values) as tunnel:
        os.environ.update({**bootstrap_env(), **tunnel})
        os.environ.pop("AWS_PROFILE", None)
        try:
            with kubeconfig(values["cluster_name"], values["aws_region"]) as command:
                yield command
        finally:
            os.environ.clear()
            os.environ.update(saved)


def bootstrap(values: dict, image: str):
    """First apply: namespace, RBAC, network policy, API-key Secret (stdin), Deployment."""
    with eks_tunnel(values) as tunnel:
        env = {**bootstrap_env(), **tunnel, "APP_API_KEY": api_key()}
        run([sys.executable, str(ROOT / "scripts/deploy/bootstrap.py"),
             "--outputs", str(OUTPUTS), "--image", image], env=env)
    ok("mybank namespace bootstrapped; mybank-api rolled out and Ready")


def seed():
    run([sys.executable, "-m", "scripts.data.seed_aws", "--outputs", str(OUTPUTS)])
    ok("synthetic customers/accounts present in DynamoDB")
