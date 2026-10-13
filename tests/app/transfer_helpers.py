"""Shared transfer request construction and deliberate fixture mutations."""

from app.repository.codec import encode
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


def update_account(repository, account_id, **values):
    item = {**repository.account(account_id), **values}
    repository.client.put_item(TableName=repository.settings.accounts_table, Item=encode(item))
