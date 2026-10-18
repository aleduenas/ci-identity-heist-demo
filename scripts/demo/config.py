"""Validate local operator settings before Terraform can change the lab."""

import json
import re
from pathlib import Path


def settings(path: Path, sandbox: Path) -> dict:
    if not path.exists():
        raise SystemExit("Copy infra/environments/sandbox/demo.tfvars.json.example to "
                         ".cache/sandbox.tfvars.json and fill in your account and admin role")
    values = json.loads(path.read_text(encoding="utf-8"))
    declared = set()
    for source in sandbox.glob("*.tf"):
        declared.update(re.findall(r'variable\s+"([^"]+)"', source.read_text()))
    unknown = set(values) - declared
    if unknown:
        raise SystemExit(f"Unknown Terraform settings (migrate before apply): {sorted(unknown)}")
    if values.get("enable_detection") is not True:
        raise SystemExit("Demo settings must explicitly set enable_detection=true")
    if values.get("github_oidc_include_run_context") is not True:
        raise SystemExit("Demo settings must set github_oidc_include_run_context=true")
    if values.get("aws_region") != "us-east-1":
        raise SystemExit("Demo operator commands use us-east-1; use that region in demo settings")
    return values
