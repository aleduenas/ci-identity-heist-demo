"""Business rules and typed failure vocabulary independent of HTTP."""

from dataclasses import dataclass

MAX_AMOUNT_CENTS = 1_000_000_000
MAX_BALANCE_CENTS = 1_000_000_000_000


@dataclass
class DomainError(Exception):
    code: str
    message: str
    status: int = 409


def validate_accounts(source: dict | None, destination: dict | None, amount: int) -> None:
    if source is None or destination is None:
        raise DomainError("account_not_found", "Both accounts must exist", 404)
    if source.get("currency") != "CAD" or destination.get("currency") != "CAD":
        raise DomainError("unsupported_currency", "Both accounts must use CAD", 422)
    if source["balance_cents"] < amount:
        raise DomainError("insufficient_funds", "Source account has insufficient funds")
    if destination["balance_cents"] > MAX_BALANCE_CENTS - amount:
        raise DomainError("balance_limit", "Destination account would exceed its balance limit")
