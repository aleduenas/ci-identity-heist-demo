"""Demonstration workflows keep external actors and fork PRs off the shipped jobs."""

from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github/workflows"


@pytest.mark.parametrize("path", sorted(WORKFLOWS.glob("*.yml")), ids=lambda p: p.name)
def test_all_jobs_require_the_owner(path):
    flow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
    for job in flow["jobs"].values():
        condition = job.get("if", "")
        # Require the owner restriction as a conjunct, so another allowed branch
        # or a nonempty AWS variable cannot bypass the actor check.
        assert condition.startswith("github.actor == github.repository_owner &&")
        assert "pull_request_target" not in flow["on"]
        assert "workflow_run" not in flow["on"]


@pytest.mark.parametrize("name", ["ci.yml", "checks.yml", "infrastructure.yml"])
def test_general_checks_require_an_owner_pr_from_the_same_repository(name):
    flow = yaml.load((WORKFLOWS / name).read_text(), Loader=yaml.BaseLoader)
    for job in flow["jobs"].values():
        assert " ".join(job["if"].split()) == (
            "github.actor == github.repository_owner && "
            "(github.event_name != 'pull_request' || "
            "(github.event.pull_request.user.login == github.repository_owner && "
            "github.event.pull_request.head.repo.full_name == github.repository))"
        )


def test_demo_keeps_oidc_and_private_runner_away_from_forks():
    flow = yaml.load((WORKFLOWS / "detection-demo.yml").read_text(), Loader=yaml.BaseLoader)
    job = flow["jobs"]["verify-boundary"]
    assert " ".join(job["if"].split()) == (
        "github.actor == github.repository_owner && "
        "vars.DETECTION_DEMO_ROLE_ARN != '' && "
        "(github.ref == 'refs/heads/main' || "
        "(github.event_name == 'pull_request' && "
        "github.event.pull_request.user.login == github.repository_owner && "
        "github.event.pull_request.head.repo.full_name == github.repository))"
    )
    assert job["runs-on"] == "ubuntu-24.04"
    assert job["permissions"] == {"contents": "read", "id-token": "write"}
