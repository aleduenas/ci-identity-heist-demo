"""Generate an ignored realm import containing operator-selected lab passwords."""
import argparse
import json
import os
import re
from pathlib import Path

from identity.keycloak.client import aws_client


def build_realm(configuration, passwords):
    provider = configuration["saml_provider_arn"]
    if not re.fullmatch(r"arn:aws:iam::\d{12}:saml-provider/[\w+=,.@-]+", provider):
        raise ValueError("Expected a commercial AWS SAML provider ARN")
    realm = json.loads(Path(__file__).with_name("keycloak").joinpath("realm.json").read_text())
    realm["clients"] = [aws_client()]
    realm["groups"] = []
    realm["users"] = []
    for role in ("engineer", "support"):
        arn = configuration[f"{role}_role_arn"]
        if not re.fullmatch(r"arn:aws:iam::\d{12}:role/[\w+=,.@/-]+", arn):
            raise ValueError("Expected an IAM role ARN")
        if arn.split(":")[4] != provider.split(":")[4]:
            raise ValueError("Role and provider must belong to the same account")
        if len(passwords[role]) < 16:
            raise ValueError(f"{role} lab password must contain at least 16 characters")
        group = role + "s"
        realm["groups"].append({
            "name": group, "attributes": {"aws_roles": [f"{arn},{provider}"]},
        })
        realm["users"].append({
            "username": "lab-" + role, "enabled": True,
            "firstName": "Lab", "lastName": role.capitalize(),
            "email": f"lab-{role}@mybank.example.invalid", "emailVerified": True,
            "groups": ["/" + group],
            "credentials": [{"type": "password", "value": passwords[role], "temporary": False}],
        })
    return realm


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("identity/generated/mybank-realm.json"))
    args = parser.parse_args()
    outputs = json.loads(args.outputs.read_text(encoding="utf-8-sig"))
    passwords = {
        role: os.environ[f"LAB_{role.upper()}_PASSWORD"] for role in ("engineer", "support")
    }
    realm = build_realm(outputs["identity_configuration"]["value"], passwords)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(realm, indent=2) + "\n", encoding="utf-8")
    args.output.chmod(0o600)
    print("Realm generated. Contains lab passwords; keep the generated directory out of Git.")


if __name__ == "__main__":
    main()
