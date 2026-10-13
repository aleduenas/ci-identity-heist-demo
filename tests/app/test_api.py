from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

PAYLOAD = {
    "transfer_id": "api-transfer",
    "source_account_id": "acct-alice",
    "destination_account_id": "acct-bob",
    "amount_cents": 100,
}


def test_health_readiness_and_transfer_contract(api):
    assert api.get("/health").json() == {"status": "ok"}
    assert api.get("/ready").status_code == 200
    assert api.get("/accounts/acct-alice").json()["balance_cents"] == 100_000
    result = api.post("/transfers", json=PAYLOAD)
    assert result.status_code == 200
    assert result.json()["amount_cents"] == 100
    assert api.post("/transfers", json=PAYLOAD).json() == result.json()
    assert api.get("/transfers/api-transfer").json() == result.json()
    conflict = api.post("/transfers", json={**PAYLOAD, "amount_cents": 200})
    assert conflict.status_code == 409
    assert api.get("/accounts/missing").status_code == 404


@pytest.mark.parametrize("key", [None, "wrong"])
def test_business_routes_require_authentication(api, key):
    api.headers.pop("X-API-Key")
    if key is not None:
        api.headers["X-API-Key"] = key
    for method, path, kwargs in [
        ("GET", "/accounts/acct-alice", {}),
        ("GET", "/transfers/api-transfer", {}),
        ("POST", "/transfers", {"json": PAYLOAD}),
    ]:
        assert api.request(method, path, **kwargs).status_code == 401


def test_missing_configuration_fails_closed(repository, settings):
    with TestClient(create_app(replace(settings, api_key=""), repository)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
        assert (
            client.get("/accounts/acct-alice", headers={"X-API-Key": "anything"}).status_code == 401
        )


@pytest.mark.parametrize("amount", [0, -1, 1.5, "100", True, 1_000_000_001])
def test_strict_amount_validation(api, amount):
    assert api.post("/transfers", json={**PAYLOAD, "amount_cents": amount}).status_code == 422


def test_same_account_and_unknown_fields_rejected(api):
    same = {**PAYLOAD, "destination_account_id": "acct-alice"}
    assert api.post("/transfers", json=same).status_code == 422
    assert api.post("/transfers", json={**PAYLOAD, "actor": "admin"}).status_code == 422


def test_readiness_does_not_disclose_storage_failure(api, repository):
    repository.client.delete_table(TableName=repository.settings.accounts_table)
    response = api.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"detail": "Storage is unavailable"}
