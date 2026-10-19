"""Release identity checks must preserve main-only boundaries during subject migration."""
import pytest

from scripts.checks.oidc_claims import checked_claims, expected_subject

EVENT = {"repository": {"id": 1416500552, "owner": {"id": 54992507}}}
PREFIX = "repo:aleduenas@54992507/mybank-eks-sandbox@1416500552"


def environment(**changes):
    return {
        "GITHUB_REPOSITORY": "aleduenas/mybank-eks-sandbox",
        "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "push",
        "GITHUB_RUN_ID": "12345", "GITHUB_RUN_ATTEMPT": "2",
        **changes,
    }


def claims(subject):
    return {
        "sub": subject, "aud": "sts.amazonaws.com",
        "repository_id": "1416500552", "repository_owner_id": "54992507",
    }


def test_default_subject_is_unchanged():
    expected = f"{PREFIX}:ref:refs/heads/main"
    assert checked_claims(claims(expected), EVENT, environment())["sub"] == expected


@pytest.mark.parametrize("event_name", ["push", "workflow_dispatch"])
def test_custom_subject_binds_exact_run_attempt(event_name):
    env = environment(MYBANK_OIDC_RUN_CONTEXT="true", GITHUB_EVENT_NAME=event_name)
    expected = f"{PREFIX}:ref:refs/heads/main:event_name:{event_name}:run_id:12345:run_attempt:2"
    assert checked_claims(claims(expected), EVENT, env)["sub"] == expected


@pytest.mark.parametrize("event_name", ["pull_request", "pull_request_target"])
def test_pr_context_is_rejected_even_with_a_main_reference(event_name):
    env = environment(MYBANK_OIDC_RUN_CONTEXT="true", GITHUB_EVENT_NAME=event_name)
    with pytest.raises(ValueError, match="only main"):
        expected_subject(EVENT, env)


def test_feature_branch_manual_dispatch_is_rejected():
    env = environment(
        MYBANK_OIDC_RUN_CONTEXT="true", GITHUB_EVENT_NAME="workflow_dispatch",
        GITHUB_REF="refs/heads/feature",
    )
    with pytest.raises(ValueError, match="only main"):
        expected_subject(EVENT, env)


def test_custom_subject_rejects_another_attempt():
    env = environment(MYBANK_OIDC_RUN_CONTEXT="true")
    wrong = expected_subject(EVENT, env).replace("run_attempt:2", "run_attempt:1")
    with pytest.raises(ValueError, match="subject differs"):
        checked_claims(claims(wrong), EVENT, env)


@pytest.mark.parametrize("key,value", [("GITHUB_RUN_ID", "*"), ("GITHUB_RUN_ATTEMPT", "0")])
def test_run_context_requires_numeric_identifiers(key, value):
    env = environment(MYBANK_OIDC_RUN_CONTEXT="true", **{key: value})
    with pytest.raises(ValueError, match="positive numeric"):
        expected_subject(EVENT, env)


@pytest.mark.parametrize("key,value", [
    ("aud", "different-audience"), ("repository_id", "99"), ("repository_owner_id", "99"),
])
def test_audience_and_immutable_identity_mismatches_are_rejected(key, value):
    payload = claims(expected_subject(EVENT, environment()))
    payload[key] = value
    with pytest.raises(ValueError):
        checked_claims(payload, EVENT, environment())


def test_default_check_rejects_pr_subject():
    with pytest.raises(ValueError, match="subject differs"):
        checked_claims(claims(f"{PREFIX}:pull_request"), EVENT, environment())
