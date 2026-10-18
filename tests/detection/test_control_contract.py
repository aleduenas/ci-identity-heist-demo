"""The privileged workflow and Terraform must preserve the PR/main boundary."""

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def test_control_never_runs_on_pr_or_checks_out_a_pr():
    flow = yaml.load((ROOT / ".github/workflows/security-control.yml").read_text(),
                     Loader=yaml.BaseLoader)
    assert set(flow["on"]) == {"push", "workflow_dispatch"}
    assert flow["on"]["push"]["branches"] == ["main"]
    job = flow["jobs"]["deploy-control"]
    assert job["if"] == "github.ref == 'refs/heads/main'"
    checkout = next(s for s in job["steps"] if s.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"] == {"ref": "main", "persist-credentials": "false"}
    assert flow["concurrency"]["cancel-in-progress"] == "false"
    assert flow["jobs"]["verify-main-access"]["needs"] == "deploy-control"
    assert "terraform" not in json.dumps(flow).lower()


def test_terraform_and_workflow_share_the_setting_and_limit_the_target():
    config = json.loads((ROOT / "security/control.json").read_text())
    assert type(config["enforcement_enabled"]) is bool
    root = (ROOT / "infra/environments/sandbox/detection.tf").read_text()
    assert 'file("${path.module}/../../../security/control.json")' in root
    assert "allow_pr_demo               = !local.detection_control.enforcement_enabled" in root
    control = (ROOT / "infra/modules/detection/control.tf").read_text()
    assert '["iam:GetRole", "iam:UpdateAssumeRolePolicy"]' in control
    assert "Resource = aws_iam_role.demo_deploy.arn" in control
    assert '"ref:refs/heads/main"' in control
    assert "pull_request" not in control
