"""Transaction invariants and preservation of existing fixture balances."""

import pytest
from transfer_helpers import request, update_account

from app.domain import MAX_BALANCE_CENTS, DomainError
from app.fixtures.seed import seed_existing_tables


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


def test_seed_does_not_reset_transferred_balances(repository):
    repository.create_transfer(request())
    seed_existing_tables(repository.client, repository.settings)
    assert repository.account("acct-alice")["balance_cents"] == 98_766
