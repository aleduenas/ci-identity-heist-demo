import json
import re

from app.observability import logger


def test_request_audit_uses_template_and_excludes_key_and_records(api, caplog):
    with caplog.at_level("INFO", logger=logger.name):
        response = api.get(
            "/accounts/acct-alice",
            headers={"X-Request-ID": "audit-correlation-01"},
        )
    assert response.headers["X-Request-ID"] == "audit-correlation-01"
    entries = [record.message for record in caplog.records if record.name == logger.name]
    assert len(entries) == 1
    entry = json.loads(entries[0])
    assert entry == {
        "event": "http_request",
        "request_id": "audit-correlation-01",
        "method": "GET",
        "route": "/accounts/{account_id}",
        "status": 200,
        "latency_ms": entry["latency_ms"],
    }
    assert entry["latency_ms"] >= 0
    for sensitive in ["unit-test-key", "acct-alice", "cust-alice", "100000", "X-API-Key"]:
        assert sensitive not in entries[0]


def test_body_values_and_unknown_paths_are_never_logged(api, caplog):
    payload = {
        "transfer_id": "private-transfer-id",
        "source_account_id": "acct-alice",
        "destination_account_id": "acct-bob",
        "amount_cents": 1234,
    }
    with caplog.at_level("INFO", logger=logger.name):
        assert api.post("/transfers", json=payload).status_code == 200
        response = api.get("/unknown-secret-customer-value")
    entries = [record.message for record in caplog.records if record.name == logger.name]
    assert len(entries) == 2
    assert json.loads(entries[1])["route"] == "<unmatched>"
    assert json.loads(entries[1])["status"] == 404
    assert response.headers["X-Request-ID"]
    for value in [*payload.values(), "unknown-secret-customer-value", "unit-test-key"]:
        assert str(value) not in "".join(entries)


def test_untrusted_correlation_id_is_replaced(api):
    for request_id in ["a" * 65, "unsafe/id", ""]:
        response = api.get("/health", headers={"X-Request-ID": request_id})
        assert re.fullmatch(r"[a-f0-9]{32}", response.headers["X-Request-ID"])
