"""One transaction enforces balance and immutable ledger conditions together."""

from app.domain import MAX_BALANCE_CENTS
from app.repository.codec import encode
from app.settings import Settings


def transaction_items(settings: Settings, transfer: dict) -> list[dict]:
    amount = transfer["amount_cents"]
    common = {
        "TableName": settings.accounts_table,
        "ExpressionAttributeNames": {"#currency": "currency"},
    }
    return [
        {
            "Update": {
                **common,
                "Key": encode({"account_id": transfer["source_account_id"]}),
                "UpdateExpression": "SET balance_cents = balance_cents - :amount",
                "ConditionExpression": (
                    "attribute_exists(account_id) AND #currency = :cad AND balance_cents >= :amount"
                ),
                "ExpressionAttributeValues": encode({":amount": amount, ":cad": "CAD"}),
            }
        },
        {
            "Update": {
                **common,
                "Key": encode({"account_id": transfer["destination_account_id"]}),
                "UpdateExpression": "SET balance_cents = balance_cents + :amount",
                "ConditionExpression": (
                    "attribute_exists(account_id) AND #currency = :cad "
                    "AND balance_cents <= :ceiling"
                ),
                "ExpressionAttributeValues": encode(
                    {
                        ":amount": amount,
                        ":cad": "CAD",
                        ":ceiling": MAX_BALANCE_CENTS - amount,
                    }
                ),
            }
        },
        {
            "Put": {
                "TableName": settings.transfers_table,
                "Item": encode(transfer),
                "ConditionExpression": "attribute_not_exists(transfer_id)",
            }
        },
    ]
