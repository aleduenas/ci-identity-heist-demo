import pytest
from botocore.exceptions import ClientError, ReadTimeoutError

from app.domain import MAX_BALANCE_CENTS, DomainError
from app.fixtures.seed import seed_existing_tables
from app.repository.codec import encode
from app.repository.transaction import transaction_items
from app.schemas import TransferRequest


def request(**overrides):
    return TransferRequest(
        **{
            "transfer_id": "transfer-001",
            "source_account_id": "acct-alice",
            "destination_account_id": "acct-bob",
            "amount_cents": 1234,
            **overrides,
        }
    )


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


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"amount_cents": 100_001}, "insufficient_funds"),
        ({"destination_account_id": "missing"}, "account_not_found"),
    ],
)
def test_rejections_do_not_modify_balances(repository, changes, code):
    with pytest.raises(DomainError) as error:
        repository.create_transfer(request(**changes))
    assert error.value.code == code
    assert repository.account("acct-alice")["balance_cents"] == 100_000
    assert repository.account("acct-bob")["balance_cents"] == 25_000
    assert repository.transfer("transfer-001") is None


def update_account(repository, account_id, **values):
    item = {**repository.account(account_id), **values}
    repository.client.put_item(TableName=repository.settings.accounts_table, Item=encode(item))


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("currency", "USD", "unsupported_currency"),
        ("balance_cents", MAX_BALANCE_CENTS, "balance_limit"),
    ],
)
def test_currency_and_destination_limit(repository, field, value, code):
    update_account(repository, "acct-bob", **{field: value})
    with pytest.raises(DomainError) as error:
        repository.create_transfer(request())
    assert error.value.code == code
    assert repository.account("acct-alice")["balance_cents"] == 100_000
    assert repository.transfer("transfer-001") is None


def test_account_changes_between_read_and_transaction_roll_back(repository, monkeypatch):
    original = repository.client.transact_write_items

    def change_before_transaction(**kwargs):
        update_account(repository, "acct-bob", currency="USD")
        return original(**kwargs)

    monkeypatch.setattr(repository.client, "transact_write_items", change_before_transaction)
    with pytest.raises(DomainError) as error:
        repository.create_transfer(request())
    assert error.value.code == "unsupported_currency"
    assert repository.account("acct-alice")["balance_cents"] == 100_000
    assert repository.account("acct-bob")["balance_cents"] == 25_000
    assert repository.transfer("transfer-001") is None


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


def test_balance_drain_after_prevalidation_cannot_overdraft(repository, monkeypatch):
    original = repository.client.transact_write_items

    def drain_before_transaction(**kwargs):
        update_account(repository, "acct-alice", balance_cents=0)
        return original(**kwargs)

    monkeypatch.setattr(repository.client, "transact_write_items", drain_before_transaction)
    with pytest.raises(DomainError) as error:
        repository.create_transfer(request())
    assert error.value.code == "insufficient_funds"
    assert repository.account("acct-alice")["balance_cents"] == 0
    assert repository.account("acct-bob")["balance_cents"] == 25_000
    assert repository.transfer("transfer-001") is None


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


def test_seed_does_not_reset_transferred_balances(repository):
    repository.create_transfer(request())
    seed_existing_tables(repository.client, repository.settings)
    assert repository.account("acct-alice")["balance_cents"] == 98_766
