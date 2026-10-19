"""Verify independent lookups and evidence sanitization, including STS response tokens."""

import io
import json
import urllib.error
from unittest.mock import patch

import pytest

from scripts.detection.collect import lookup, timestamp
from scripts.detection.evidence import safe_event, safe_run
from scripts.detection.github import get_run
from scripts.detection.sample_data import REPOSITORY, sample


def test_allowlist_drops_every_nested_credential_and_raw_token():
    event, run = sample()
    secret = "SYNTHETIC-SECRET-DO-NOT-RETAIN"
    event["requestParameters"]["webIdentityToken"] = secret
    event["responseElements"]["credentials"] = {
        "accessKeyId": secret, "secretAccessKey": secret, "sessionToken": secret,
    }
    event["raw_jwt"] = secret
    run["token"] = secret
    serialized = json.dumps({"aws": safe_event(event), "github": safe_run(run)})
    assert secret not in serialized
    assert "credentials" not in serialized
    assert "webIdentityToken" not in serialized


def test_github_context_is_fetched_from_exact_independent_attempt_endpoint():
    _, run = sample()
    response = io.BytesIO(json.dumps(run).encode())
    with patch("urllib.request.urlopen", return_value=response) as request:
        collected = get_run(REPOSITORY, 1001, 1, "synthetic-read-token")
    assert request.call_args.args[0].full_url.endswith("/actions/runs/1001/attempts/1")
    assert collected["id"] == 1001
    assert collected["run_attempt"] == 1


def test_github_failure_does_not_echo_response_or_credential():
    error = urllib.error.HTTPError("https://api.github.com", 403, "secret", {}, None)
    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(RuntimeError, match="HTTP 403") as failure:
            get_run(REPOSITORY, 1001, 1, "synthetic-read-token")
    assert "synthetic-read-token" not in str(failure.value)
    assert "secret" not in str(failure.value)


def test_cloudtrail_pages_are_sanitized_before_leaving_lookup():
    event, _ = sample()
    event["responseElements"]["credentials"] = {"sessionToken": "synthetic-secret"}

    class Client:
        def __init__(self):
            self.calls = []

        def lookup_events(self, **parameters):
            self.calls.append(parameters.copy())
            return ({"Events": [{"CloudTrailEvent": json.dumps(event)}], "NextToken": "page2"}
                    if len(self.calls) == 1 else {"Events": []})

    client = Client()
    now = timestamp("2026-10-17T12:00:00Z")
    with patch("scripts.detection.collect.time.sleep"):
        evidence = list(lookup(client, now, now))
    assert client.calls[1]["NextToken"] == "page2"
    assert "synthetic-secret" not in json.dumps(evidence)


def test_unreadable_github_metadata_remains_a_sanitized_error():
    with patch("urllib.request.urlopen", return_value=io.BytesIO(b"invalid-json")):
        with pytest.raises(RuntimeError, match="invalid JSON"):
            get_run(REPOSITORY, 1001, 1, "synthetic-read-token")


def test_measurement_timestamps_require_timezone():
    with pytest.raises(ValueError, match="UTC offset"):
        timestamp("2026-10-17T12:00:00")
