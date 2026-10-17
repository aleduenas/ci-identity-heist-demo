"""Verify D2 distinguishes authenticated context from attacker-controlled labels and gaps."""

import pytest

from scripts.d2.alert import render
from scripts.d2.detector import classify
from scripts.d2.sample_data import PREFIX, REPOSITORY, ROLE, sample


def decision(event, run):
    return classify(event, run, role_arn=ROLE, repository=REPOSITORY,
                    subject_prefix=PREFIX)["decision"]


@pytest.mark.parametrize("event_name", ["workflow_dispatch", "push"])
def test_expected_main_context_requires_independent_match(event_name):
    event, run = sample(event_name)
    assert decision(event, run) == "expected_release"


def test_release_looking_session_cannot_hide_pr_context():
    event, run = sample()
    event["requestParameters"]["roleSessionName"] = "trusted-release-1002"
    assert decision(event, run) == "pr_role_misuse"


def test_missing_run_is_visible_gap():
    event, _ = sample()
    assert decision(event, None) == "context_not_verified"


@pytest.mark.parametrize("field,value", [
    ("id", 999), ("run_attempt", 2), ("event", "workflow_dispatch"),
])
def test_wrong_run_attempt_or_event_cannot_be_correlated(field, value):
    event, run = sample()
    run[field] = value
    assert decision(event, run) == "context_not_verified"


def test_wrong_immutable_repository_id_cannot_be_trusted():
    event, run = sample()
    run["repository"]["id"] = 789
    assert decision(event, run) == "context_not_verified"


def test_wrong_immutable_owner_id_cannot_be_trusted():
    event, run = sample()
    run["repository"]["owner"]["id"] = 987
    assert decision(event, run) == "context_not_verified"


def test_unsupported_default_subject_is_not_guessed_from_session():
    event, run = sample()
    event["responseElements"]["subjectFromWebIdentityToken"] = PREFIX + ":pull_request"
    assert decision(event, run) == "context_not_verified"


def test_success_without_issued_role_is_unverified():
    event, run = sample()
    event["responseElements"].pop("assumedRoleUser")
    assert decision(event, run) == "context_not_verified"


def test_denial_is_boundary_not_successful_misuse():
    event, run = sample()
    event["errorCode"] = "AccessDenied"
    event["responseElements"] = None
    assert decision(event, run) == "assumption_denied"


@pytest.mark.parametrize("field,value", [
    ("audience", "wrong-audience"), ("provider", "attacker-controlled-provider"),
])
def test_wrong_provider_or_audience_is_not_trusted(field, value):
    event, run = sample()
    event["responseElements"][field] = value
    assert decision(event, run) == "context_not_verified"


def test_main_workflow_must_be_the_documented_comparison():
    event, run = sample("push")
    run["path"] = ".github/workflows/other.yml"
    assert decision(event, run) == "context_not_verified"


def test_other_role_is_out_of_scope():
    event, run = sample()
    event["requestParameters"]["roleArn"] += "-other"
    assert decision(event, run) == "out_of_scope"


def test_pr_misuse_alert_explains_what_why_and_where():
    event, run = sample()
    alert = render(classify(event, run, role_arn=ROLE, repository=REPOSITORY,
                            subject_prefix=PREFIX))
    assert alert["severity"] == "high"
    assert ROLE in alert["what_happened"] and "pull_request" in alert["what_happened"]
    assert alert["where_to_look"]["run_url"] == run["html_url"]
    assert alert["where_to_look"]["cloudtrail_event_id"] == event["eventID"]


def test_expected_release_raises_no_alert_and_gap_is_not_escalated():
    event, run = sample("workflow_dispatch", 1002)
    assert render(classify(event, run, role_arn=ROLE, repository=REPOSITORY,
                           subject_prefix=PREFIX)) is None
    pr, _ = sample()
    gap = render(classify(pr, None, role_arn=ROLE, repository=REPOSITORY, subject_prefix=PREFIX))
    assert gap["severity"] == "investigate"


def test_live_denial_shape_links_role_from_resources_and_subject_from_identity():
    """Observed 2026-10-17: denied events have null request/response; role is in resources."""
    event, _ = sample()
    subject = event["responseElements"]["subjectFromWebIdentityToken"]
    event.update(errorCode="AccessDenied", requestParameters=None, responseElements=None,
                 resources=[{"type": "AWS::IAM::OIDCProvider", "ARN": "provider"},
                            {"type": "AWS::IAM::Role", "ARN": ROLE}],
                 userIdentity={"type": "WebIdentityUser", "userName": subject})
    result = classify(event, None, role_arn=ROLE, repository=REPOSITORY, subject_prefix=PREFIX)
    assert result["decision"] == "assumption_denied"
    assert (result["github_event"], result["run_id"]) == ("pull_request", 1001)
    assert render(result) is None
