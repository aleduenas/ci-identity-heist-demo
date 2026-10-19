"""Shared operator configuration and isolated kubeconfig handling."""

# The private release runner uses Amazon Linux 2023's system Python 3.9.
from __future__ import annotations

import json
import os
import re
import subprocess
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory


def terraform_outputs(path: Path) -> dict[str, str]:
    """Read native `terraform output -json`, including PowerShell UTF-8 BOM."""
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    return {name: entry["value"] for name, entry in document.items()}


def checked_image(image: str, repository: str | None = None) -> str:
    pattern = r"\d{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com/[a-z0-9._/-]+"
    pattern += r"(?::[a-f0-9]{40}|@sha256:[a-f0-9]{64})"
    if not re.fullmatch(pattern, image):
        raise ValueError("Image must be a private ECR image with commit SHA tag or digest")
    if repository and not image.startswith((repository + ":", repository + "@")):
        raise ValueError("Image repository differs from Terraform ecr_repository_url")
    return image


@contextmanager
def kubeconfig(cluster: str, region: str):
    """Do not modify an operator's default Kubernetes context or runner home."""
    server = os.environ.get("MYBANK_KUBE_API_SERVER")
    tls_name = os.environ.get("MYBANK_KUBE_TLS_SERVER_NAME")
    if bool(server) != bool(tls_name):
        raise ValueError(
            "MYBANK_KUBE_API_SERVER and MYBANK_KUBE_TLS_SERVER_NAME must be set together"
        )
    if server and not server.startswith("https://"):
        raise ValueError("MYBANK_KUBE_API_SERVER must use HTTPS")
    with TemporaryDirectory(prefix="mybank-kube-") as directory:
        path = Path(directory) / "config"
        subprocess.run(
            [
                "aws",
                "eks",
                "update-kubeconfig",
                "--name",
                cluster,
                "--region",
                region,
                "--kubeconfig",
                str(path),
            ],
            check=True,
        )
        os.chmod(path, 0o600)
        command = ["kubectl", "--kubeconfig", str(path)]
        if server:
            result = subprocess.run(
                command + ["config", "view", "-o", "json"],
                capture_output=True,
                text=True,
                check=True,
            )
            cluster_entry = json.loads(result.stdout)["clusters"][0]["name"]
            subprocess.run(
                command
                + [
                    "config",
                    "set-cluster",
                    cluster_entry,
                    f"--server={server}",
                    f"--tls-server-name={tls_name}",
                ],
                check=True,
            )
        yield command
