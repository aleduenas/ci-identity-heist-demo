"""Publication checks must reject credential-bearing examples as well as internal files."""

import pytest

from scripts.checks.repository_hygiene import check


@pytest.mark.parametrize("path", [
    ".claude/settings.local.json", ".aws/credentials", "AGENTS.md",
    "docs/plan/take_home.md", "infra/backend.hcl", "infra/terraform.tfstate",
    ".env.production", "identity/generated/realm.json", "operator_credentials.csv",
])
def test_internal_files_are_rejected(path):
    assert "internal/generated path" in check(path, b"{}")


def test_safe_examples_and_generated_ignore_marker_are_allowed():
    for path in (".env.example", "infra/demo.tfvars.json.example", "deploy/generated/.gitignore"):
        assert check(path, b"placeholder") == []


def test_example_exception_never_suppresses_credentials():
    token = "ghp_" + "a" * 36
    assert "GitHub token" in check(".env.example", token.encode())


def test_transient_aws_credentials_are_rejected():
    key = "ASIA" + "A" * 16
    assert "AWS access key" in check("docs/example.md", key.encode())
