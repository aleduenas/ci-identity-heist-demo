"""Consistent reads and bounded transaction retries preserve idempotency."""

import time
from datetime import UTC, datetime

from botocore.exceptions import BotoCoreError, ClientError

from app.domain import DomainError, validate_accounts
from app.repository.codec import decode, encode
from app.repository.transaction import transaction_items
from app.schemas import TransferRequest
from app.settings import Settings


class BankRepository:
    def __init__(self, client, settings: Settings):
        self.client = client
        self.settings = settings

    def get(self, table: str, key: str, value: str) -> dict | None:
        result = self.client.get_item(
            TableName=table,
            Key=encode({key: value}),
            ConsistentRead=True,
        )
        return decode(result["Item"]) if "Item" in result else None

    def account(self, account_id: str) -> dict | None:
        return self.get(self.settings.accounts_table, "account_id", account_id)

    def transfer(self, transfer_id: str) -> dict | None:
        return self.get(self.settings.transfers_table, "transfer_id", transfer_id)

    def ready(self) -> bool:
        # Probes test the same read permission needed by the app, avoiding DescribeTable privileges.
        for table, key in [
            (self.settings.customers_table, "customer_id"),
            (self.settings.accounts_table, "account_id"),
            (self.settings.transfers_table, "transfer_id"),
        ]:
            self.get(table, key, "__readiness_probe__")
        return True

    def replay(self, request: TransferRequest) -> dict | None:
        previous = self.transfer(request.transfer_id)
        if previous is not None and any(
            previous[key] != value for key, value in request.model_dump().items()
        ):
            raise DomainError(
                "idempotency_conflict", "Transfer ID was used with different parameters"
            )
        return previous

    def validate(self, request: TransferRequest) -> None:
        validate_accounts(
            self.account(request.source_account_id),
            self.account(request.destination_account_id),
            request.amount_cents,
        )

    def validate_or_replay(self, request: TransferRequest) -> dict | None:
        try:
            self.validate(request)
        except DomainError:
            # A winning matching transfer may have changed balances between reads.
            previous = self.replay(request)
            if previous is not None:
                return previous
            raise
        return None

    def create_transfer(self, request: TransferRequest) -> dict:
        previous = self.replay(request)
        if previous is not None:
            return previous
        previous = self.validate_or_replay(request)
        if previous is not None:
            return previous
        transfer = {
            **request.model_dump(),
            "currency": "CAD",
            "actor": "lab-api",
            "created_at": datetime.now(UTC).isoformat(),
        }
        for attempt in range(3):
            try:
                self.client.transact_write_items(
                    TransactItems=transaction_items(self.settings, transfer),
                )
                return transfer
            except ClientError as error:
                code = error.response["Error"]["Code"]
                if code not in {
                    "TransactionCanceledException",
                    "TransactionConflictException",
                    "ProvisionedThroughputExceededException",
                    "ThrottlingException",
                    "RequestLimitExceeded",
                    "InternalServerError",
                }:
                    raise
                # A concurrent matching request or ambiguous response may have committed.
                previous = self.replay(request)
                if previous is not None:
                    return previous
                previous = self.validate_or_replay(request)
                if previous is not None:
                    return previous
            except BotoCoreError:
                # A lost response can hide a successful commit. Always check the durable ledger.
                previous = self.replay(request)
                if previous is not None:
                    return previous
            if attempt < 2:
                time.sleep(0.05 * 2**attempt)
        raise DomainError("temporarily_unavailable", "Retry with the same transfer ID", 503)
