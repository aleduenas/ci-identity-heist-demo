"""Publication checks must reject credential-bearing examples as well as internal files."""

import pytest

from scripts.checks.repository_hygiene import check


@pytest.mark.parametrize("path", [
    ".claude/settings.local.json", ".aws/credentials", "AGENTS.md", "control-instructions.md",
    "docs/plan/draft.md", "infra/backend.hcl", "infra/terraform.tfstate",
    ".env.production", "identity/generated/realm.json", "operator_credentials.csv",
    "DEMO.md", "WALKTHROUGH.md", "docs/implementation-status.md",
    "docs/repository-access.md",
    "docs/presentation/slides/01-intro.tex", "docs/presentation/deck.pdf",
    "docs/d2/HANDOFF.md", "docs/d2/evidence.md", "docs/detection/HANDOFF.md",
    "docs/detection/evidence.md", "docs/detection/control-evidence.md",
])
def test_internal_files_are_rejected(path):
    assert "internal/generated path" in check(path, b"{}")


def test_safe_examples_and_generated_ignore_marker_are_allowed():
    for path in (".env.example", "infra/demo.tfvars.json.example", "deploy/generated/.gitignore"):
        assert check(path, b"placeholder") == []


def test_public_walkthrough_and_demo_evidence_are_allowed():
    for path in ("docs/demo.md", "docs/architecture.md", "docs/demo-evidence/control-on.log"):
        assert check(path, b"synthetic sandbox") == []


def test_example_exception_never_suppresses_credentials():
    token = "ghp_" + "a" * 36
    assert "GitHub token" in check(".env.example", token.encode())


def test_transient_aws_credentials_are_rejected():
    key = "ASIA" + "A" * 16
    assert "AWS access key" in check("docs/example.md", key.encode())
