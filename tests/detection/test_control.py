"""Control deployment must reject unexpected trust and verify the actual IAM write."""

import copy
import fnmatch
import json

import boto3
import pytest
from botocore.stub import Stubber

from scripts.detection.apply_control import SUB, apply_control, load_setting, trust_policy

PREFIX = "repo:example@123/lab@456"
ACCOUNT = "123456789012"
NAME = "synthetic-detection-demo-deploy"
ROLE = f"arn:aws:iam::{ACCOUNT}:role/{NAME}"


def client():
    return boto3.client("iam", region_name="us-east-1", aws_access_key_id="testing",
                        aws_secret_access_key="testing")


def role_response(policy):
    from datetime import UTC, datetime

    return {"Role": {"Path": "/", "RoleName": NAME, "RoleId": "A" * 21,
                     "Arn": ROLE, "CreateDate": datetime(2026, 1, 1, tzinfo=UTC),
                     "AssumeRolePolicyDocument": policy}}


def add_get_role(stub, policy):
    # IAM's wire model is a string; boto3's response handler decodes it to a dict.
    stub.add_response("get_role", role_response(json.dumps(policy)), {"RoleName": NAME})


def test_enforcement_rejects_pr_but_keeps_both_main_contexts():
    suffixes = ["pull_request:event_name:pull_request:run_id:42:run_attempt:1",
                "ref:refs/heads/main:event_name:push:run_id:43:run_attempt:2",
                "ref:refs/heads/main:event_name:workflow_dispatch:run_id:44:run_attempt:1"]
    for enabled, expected in [(True, [False, True, True]), (False, [True, True, True])]:
        policy = trust_policy(ACCOUNT, PREFIX, enabled)
        subjects = policy["Statement"][0]["Condition"]["StringLike"][SUB]
        assert [any(fnmatch.fnmatchcase(f"{PREFIX}:{s}", p) for p in subjects)
                for s in suffixes] == expected
        assert not any(fnmatch.fnmatchcase(f"{PREFIX}:ref:refs/heads/evil:event_name:push:"
                                          "run_id:1:run_attempt:1", p) for p in subjects)


@pytest.mark.parametrize("enabled", [True, False])
def test_deploy_writes_exact_policy_then_reads_it_back(enabled):
    before = trust_policy(ACCOUNT, PREFIX, not enabled)
    after = trust_policy(ACCOUNT, PREFIX, enabled)
    iam = client()
    with Stubber(iam) as stub:
        add_get_role(stub, before)
        stub.add_response("update_assume_role_policy", {},
                          {"RoleName": NAME, "PolicyDocument": json.dumps(after)})
        add_get_role(stub, after)
        assert apply_control(iam, ROLE, PREFIX, enabled) == after
        stub.assert_no_pending_responses()


def test_idempotent_deploy_does_not_write():
    policy = trust_policy(ACCOUNT, PREFIX, True)
    policy["Statement"][0]["Condition"]["StringLike"][SUB].reverse()
    iam = client()
    with Stubber(iam) as stub:
        for _ in range(2):
            add_get_role(stub, policy)
        assert apply_control(iam, ROLE, PREFIX, True) == policy
        stub.assert_no_pending_responses()


@pytest.mark.parametrize("mutation", ["principal", "audience", "extra_statement", "branch"])
def test_unknown_live_policy_is_never_overwritten(mutation):
    policy = copy.deepcopy(trust_policy(ACCOUNT, PREFIX, False))
    statement = policy["Statement"][0]
    if mutation == "principal":
        statement["Principal"] = {"AWS": "*"}
    elif mutation == "audience":
        statement["Condition"]["StringEquals"]["token.actions.githubusercontent.com:aud"] = "bad"
    elif mutation == "extra_statement":
        policy["Statement"].append(copy.deepcopy(statement))
    else:
        statement["Condition"]["StringLike"][SUB].append(f"{PREFIX}:*")
    iam = client()
    with Stubber(iam) as stub:
        add_get_role(stub, policy)
        with pytest.raises(ValueError, match="Unrecognized"):
            apply_control(iam, ROLE, PREFIX, True)


def test_readback_mismatch_fails_instead_of_claiming_success(monkeypatch):
    before, after = [trust_policy(ACCOUNT, PREFIX, enabled) for enabled in (False, True)]
    monkeypatch.setattr("scripts.detection.apply_control.time.sleep", lambda _: None)
    iam = client()
    with Stubber(iam) as stub:
        add_get_role(stub, before)
        stub.add_response("update_assume_role_policy", {},
                          {"RoleName": NAME, "PolicyDocument": json.dumps(after)})
        for _ in range(11):
            add_get_role(stub, before)
        with pytest.raises(RuntimeError, match="readback"):
            apply_control(iam, ROLE, PREFIX, True)


@pytest.mark.parametrize("value", ["false", 0, None, [], {}])
def test_invalid_setting_cannot_silently_disable_enforcement(tmp_path, value):
    path = tmp_path / "control.json"
    path.write_text(json.dumps({"enforcement_enabled": value}))
    with pytest.raises(ValueError, match="boolean"):
        load_setting(path)


def test_cannot_target_a_release_role():
    with pytest.raises(ValueError, match="exact sandbox"):
        apply_control(client(), f"arn:aws:iam::{ACCOUNT}:role/github-deploy", PREFIX, True)
