"""Run an operator command with the ignored, temporary AWS login configuration."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[2]
    aws_dir = root / ".tools/aws-cli/portable/Amazon/AWSCLIV2"
    ssm_dir = root / ".tools/session-manager/portable/bin"
    cache = root / ".cache/aws"
    env = {
        **os.environ,
        "AWS_CONFIG_FILE": str(cache / "config"),
        "AWS_SHARED_CREDENTIALS_FILE": str(cache / "credentials"),
        "AWS_LOGIN_CACHE_DIRECTORY": str(cache / "login"),
        "AWS_PROFILE": "codex-builder",
        "AWS_REGION": "ca-central-1",
        "AWS_DEFAULT_REGION": "ca-central-1",
        "AWS_PAGER": "",
        "PATH": os.pathsep.join([str(aws_dir), str(ssm_dir), os.environ["PATH"]]),
    }
    if len(sys.argv) < 2:
        raise SystemExit("Supply an operator command, e.g. aws sts get-caller-identity")
    command = sys.argv[1:]
    command[0] = shutil.which(command[0], path=env["PATH"]) or command[0]
    raise SystemExit(subprocess.run(command, env=env, check=False).returncode)


if __name__ == "__main__":
    main()
