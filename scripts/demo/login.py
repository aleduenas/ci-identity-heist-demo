"""Sign the repository-local AWS CLI in as your console IAM user (browser approval, no keys).

Creates two ignored profiles in .cache/aws/config: `<user>-login` (the console login session)
and `<user>` (exports those temporary credentials to boto3/Terraform), then runs `aws login`.
"""

import argparse
import configparser
import os
import subprocess

from scripts.aws.run import REGION, ROOT, operator_env, operator_user


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", action="store_true", help="Use a code instead of a browser")
    args = parser.parse_args()
    user = operator_user()
    env = operator_env()
    config_path = ROOT / ".cache/aws/config"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = configparser.RawConfigParser()
    config.read(config_path, encoding="utf-8")
    aws = ROOT / ".tools/aws-cli/portable/Amazon/AWSCLIV2/aws.exe"
    login, process = f"profile {user}-login", f"profile {user}"
    for section in (login, process):
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, "region", REGION)
        config.set(section, "output", "json")
    config.set(process, "credential_process",
               f"{aws} configure export-credentials --profile {user}-login --format process")
    with config_path.open("w", encoding="utf-8") as handle:
        config.write(handle)
    command = [str(aws), "login", "--profile", f"{user}-login", "--region", REGION]
    if args.remote:
        command.append("--remote")
    subprocess.run(command, env=env, check=True)
    identity = subprocess.run([str(aws), "sts", "get-caller-identity", "--query", "Arn",
                               "--output", "text"], env=env, check=True, capture_output=True,
                              text=True).stdout.strip()
    print(f"Signed in as {identity} (profile {user}, region {REGION})")
    if not identity.endswith(f":user/{user}"):
        raise SystemExit(f"Expected IAM user {user}; set MYBANK_AWS_USER if that is intended")
    os.environ.update(env)


if __name__ == "__main__":
    main()
