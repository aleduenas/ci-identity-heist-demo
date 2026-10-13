"""Verify federation claim isolation without a live IdP or AWS account."""
import pytest

from identity.generate_realm import build_realm

ACCOUNT = "123456789012"
CONFIG = {
    "saml_provider_arn": f"arn:aws:iam::{ACCOUNT}:saml-provider/mybank",
    "engineer_role_arn": f"arn:aws:iam::{ACCOUNT}:role/mybank-engineer",
    "support_role_arn": f"arn:aws:iam::{ACCOUNT}:role/mybank-support",
}
PASSWORDS = {"engineer": "fictional-engineer-password", "support": "fictional-support-password"}


def test_employee_roles_are_separate_group_claims():
    realm = build_realm(CONFIG, PASSWORDS)
    groups = {group["name"]: group["attributes"]["aws_roles"] for group in realm["groups"]}
    assert groups["engineers"] == [CONFIG["engineer_role_arn"] + "," + CONFIG["saml_provider_arn"]]
    assert groups["supports"] == [CONFIG["support_role_arn"] + "," + CONFIG["saml_provider_arn"]]
    users = {user["username"]: user for user in realm["users"]}
    assert users["lab-engineer"]["groups"] == ["/engineers"]
    assert users["lab-support"]["groups"] == ["/supports"]
    assert all(user["firstName"] and user["lastName"] for user in users.values())
    client = realm["clients"][0]
    assert client["attributes"]["saml.assertion.signature"] == "true"
    role_mapper = client["protocolMappers"][0]["config"]
    assert role_mapper["aggregate.attrs"] == "true"
    assert role_mapper["attribute.name"] == "https://aws.amazon.com/SAML/Attributes/Role"


def test_cross_account_role_is_rejected():
    configuration = {**CONFIG, "engineer_role_arn": "arn:aws:iam::999999999999:role/engineer"}
    with pytest.raises(ValueError, match="same account"):
        build_realm(configuration, PASSWORDS)


def test_short_password_is_rejected():
    with pytest.raises(ValueError, match="16 characters"):
        build_realm(CONFIG, {**PASSWORDS, "support": "short"})
