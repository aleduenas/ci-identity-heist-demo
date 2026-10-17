"""Run an operator command with the ignored, repository-local AWS login configuration."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGION = "us-east-1"


def operator_user() -> str:
    """IAM user whose console login backs the CLI; demo-admin unless overridden."""
    return os.environ.get("MYBANK_AWS_USER", "demo-admin")


def operator_env() -> dict[str, str]:
    aws_dir = ROOT / ".tools/aws-cli/portable/Amazon/AWSCLIV2"
    ssm_dir = ROOT / ".tools/session-manager/portable/bin"
    cache = ROOT / ".cache/aws"
    return {
        **os.environ,
        "AWS_CONFIG_FILE": str(cache / "config"),
        "AWS_SHARED_CREDENTIALS_FILE": str(cache / "credentials"),
        "AWS_LOGIN_CACHE_DIRECTORY": str(cache / "login"),
        "AWS_PROFILE": operator_user(),
        "AWS_REGION": REGION,
        "AWS_DEFAULT_REGION": REGION,
        "AWS_PAGER": "",
        "PATH": os.pathsep.join([str(aws_dir), str(ssm_dir), os.environ["PATH"]]),
    }


def main():
    env = operator_env()
    if len(sys.argv) < 2:
        raise SystemExit("Supply an operator command, e.g. aws sts get-caller-identity")
    command = sys.argv[1:]
    command[0] = shutil.which(command[0], path=env["PATH"]) or command[0]
    raise SystemExit(subprocess.run(command, env=env, check=False).returncode)


if __name__ == "__main__":
    main()
