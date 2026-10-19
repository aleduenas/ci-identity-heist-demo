"""Durable idempotency, competing writers, and ambiguous failure recovery."""

import pytest
from botocore.exceptions import ClientError, ReadTimeoutError
from transfer_helpers import request

from app.domain import DomainError
from app.repository.codec import encode
from app.repository.transaction import transaction_items


def test_atomic_transfer_and_durable_idempotency(repository):
    result = repository.create_transfer(request())
    assert result["currency"] == "CAD"
    assert repository.account("acct-alice")["balance_cents"] == 98_766
    assert repository.account("acct-bob")["balance_cents"] == 26_234
    assert repository.transfer("transfer-001") == result
    assert repository.create_transfer(request()) == result
    assert repository.account("acct-alice")["balance_cents"] == 98_766
    with pytest.raises(DomainError, match="different parameters"):
        repository.create_transfer(request(amount_cents=2000))


def test_concurrent_matching_request_returns_winner(repository, monkeypatch):
    original = repository.client.transact_write_items
    winner = {
        **request().model_dump(),
        "currency": "CAD",
        "actor": "lab-api",
        "created_at": "2026-10-13T12:00:00+00:00",
    }

    def commit_winner_first(**kwargs):
        # Emulates another writer winning after this writer's initial ledger read.
        kwargs["TransactItems"][2]["Put"]["Item"] = encode(winner)
        original(**kwargs)
        return original(**kwargs)

    monkeypatch.setattr(repository.client, "transact_write_items", commit_winner_first)
    assert repository.create_transfer(request()) == winner
    assert repository.account("acct-alice")["balance_cents"] == 98_766
    assert repository.account("acct-bob")["balance_cents"] == 26_234


def test_winner_committing_between_idempotency_read_and_validation(repository, monkeypatch):
    payload = request(amount_cents=100_000)
    winner = {
        **payload.model_dump(),
        "currency": "CAD",
        "actor": "lab-api",
        "created_at": "2026-10-13T12:00:00+00:00",
    }
    original = repository.account
    committed = False

    def account_after_competing_commit(account_id):
        nonlocal committed
        if not committed:
            committed = True
            repository.client.transact_write_items(
                TransactItems=transaction_items(repository.settings, winner),
            )
        return original(account_id)

    monkeypatch.setattr(repository, "account", account_after_competing_commit)
    assert repository.create_transfer(payload) == winner
    assert repository.account("acct-alice")["balance_cents"] == 0
    assert repository.account("acct-bob")["balance_cents"] == 125_000


def test_ambiguous_commit_response_checks_ledger(repository, monkeypatch):
    original = repository.client.transact_write_items

    def timeout_after_commit(**kwargs):
        original(**kwargs)
        raise ReadTimeoutError(endpoint_url="http://example.invalid")

    monkeypatch.setattr(repository.client, "transact_write_items", timeout_after_commit)
    result = repository.create_transfer(request())
    assert result == repository.transfer("transfer-001")
    assert repository.account("acct-alice")["balance_cents"] == 98_766


def test_transaction_conflict_retries_and_is_bounded(repository, monkeypatch):
    original = repository.client.transact_write_items
    calls = 0

    def one_conflict(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ClientError(
                {"Error": {"Code": "TransactionConflictException"}}, "TransactWriteItems"
            )
        return original(**kwargs)

    monkeypatch.setattr(repository.client, "transact_write_items", one_conflict)
    repository.create_transfer(request())
    assert calls == 2

    def always_conflict(**kwargs):
        nonlocal calls
        calls += 1
        raise ClientError({"Error": {"Code": "TransactionConflictException"}}, "TransactWriteItems")

    monkeypatch.setattr(repository.client, "transact_write_items", always_conflict)
    calls = 0
    with pytest.raises(DomainError) as error:
        repository.create_transfer(request(transfer_id="another"))
    assert error.value.status == 503
    assert calls == 3
    assert repository.account("acct-alice")["balance_cents"] == 98_766
