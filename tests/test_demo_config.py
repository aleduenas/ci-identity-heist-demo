"""Stale local variable names must fail before Terraform can delete exercise resources."""

import json
from pathlib import Path

import pytest

from scripts.demo.config import settings

SANDBOX = Path(__file__).resolve().parents[1] / "infra/environments/sandbox"
BASE = {"aws_region": "us-east-1", "enable_detection": True,
        "github_oidc_include_run_context": True}


def test_current_settings_are_preserved(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(BASE))
    assert settings(path, SANDBOX) == BASE


def test_old_detection_flag_fails_instead_of_defaulting_to_disabled(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({**BASE, "enable_d2": True}))
    with pytest.raises(SystemExit, match="Unknown Terraform settings"):
        settings(path, SANDBOX)


def test_missing_local_setup_has_an_actionable_error(tmp_path):
    with pytest.raises(SystemExit, match="demo.tfvars.json.example"):
        settings(tmp_path / "missing.json", SANDBOX)
