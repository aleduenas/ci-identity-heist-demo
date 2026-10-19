"""Exchange an operator's own SAML assertion for an ignored short-lived AWS profile."""
import argparse
import base64
import configparser
import json
from pathlib import Path

import boto3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs", required=True, type=Path)
    parser.add_argument("--assertion", required=True, type=Path)
    parser.add_argument("--role", choices=("engineer", "support"), required=True)
    parser.add_argument("--credentials", type=Path, default=Path("identity/generated/credentials"))
    args = parser.parse_args()
    outputs = json.loads(args.outputs.read_text(encoding="utf-8-sig"))
    configuration = outputs["identity_configuration"]["value"]
    assertion = args.assertion.read_text().strip()
    base64.b64decode(assertion, validate=True)
    region = outputs["aws_region"]["value"]
    response = boto3.client("sts", region_name=region).assume_role_with_saml(
        RoleArn=configuration[f"{args.role}_role_arn"],
        PrincipalArn=configuration["saml_provider_arn"], SAMLAssertion=assertion,
        DurationSeconds=3600,
    )
    credentials = response["Credentials"]
    profile = configparser.ConfigParser()
    if args.credentials.exists():
        profile.read(args.credentials)
    profile["mybank-" + args.role] = {
        "aws_access_key_id": credentials["AccessKeyId"],
        "aws_secret_access_key": credentials["SecretAccessKey"],
        "aws_session_token": credentials["SessionToken"], "region": region,
    }
    args.credentials.parent.mkdir(parents=True, exist_ok=True)
    with args.credentials.open("w", encoding="utf-8") as destination:
        profile.write(destination)
    args.credentials.chmod(0o600)
    print(f"Saved short-lived mybank-{args.role} profile; expires {credentials['Expiration']}")


if __name__ == "__main__":
    main()
