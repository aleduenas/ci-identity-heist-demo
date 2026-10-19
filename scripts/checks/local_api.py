"""Smoke-check the Docker API against real DynamoDB Local transactions."""
import json
import os
import urllib.error
import urllib.request
import uuid


def request(path, body=None, key=True):
    headers = {"Content-Type": "application/json"}
    if key:
        headers["X-API-Key"] = os.environ["APP_API_KEY"]
    req = urllib.request.Request(
        "http://localhost:8000" + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def main():
    assert request("/ready", key=False)[0] == 200
    assert request("/accounts/acct-alice", key=False)[0] == 401
    before_source = request("/accounts/acct-alice")[1]
    before_destination = request("/accounts/acct-bob")[1]
    transfer = {
        "transfer_id": "smoke-" + str(uuid.uuid4()),
        "source_account_id": "acct-alice", "destination_account_id": "acct-bob",
        "amount_cents": 500,
    }
    first_status, first = request("/transfers", transfer)
    assert first_status in (200, 201), (first_status, first)
    retry_status, retry = request("/transfers", transfer)
    assert retry_status in (200, 201) and first == retry
    assert request("/transfers", {**transfer, "amount_cents": 600})[0] == 409
    rejected = {**transfer, "transfer_id": "reject-" + str(uuid.uuid4()), "amount_cents": 99999999}
    assert request("/transfers", rejected)[0] == 409
    after_source = request("/accounts/acct-alice")[1]
    after_destination = request("/accounts/acct-bob")[1]
    assert after_source["balance_cents"] == before_source["balance_cents"] - 500
    assert after_destination["balance_cents"] == before_destination["balance_cents"] + 500
    assert request("/transfers/" + rejected["transfer_id"])[0] == 404
    print("PASS: readiness, auth, atomic transfer, retry, key conflict, overdraft rollback")


if __name__ == "__main__":
    main()
