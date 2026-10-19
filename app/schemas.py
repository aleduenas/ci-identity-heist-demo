"""HTTP request and response shapes; strict integer amounts avoid float rounding."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain import MAX_AMOUNT_CENTS

Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_-]+$")]


class TransferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transfer_id: Identifier
    source_account_id: Identifier
    destination_account_id: Identifier
    amount_cents: Annotated[int, Field(strict=True, gt=0, le=MAX_AMOUNT_CENTS)]

    @model_validator(mode="after")
    def different_accounts(self):
        if self.source_account_id == self.destination_account_id:
            raise ValueError("Source and destination must be different accounts")
        return self


class AccountResponse(BaseModel):
    account_id: str
    customer_id: str
    currency: str
    balance_cents: int


class TransferResponse(BaseModel):
    transfer_id: str
    source_account_id: str
    destination_account_id: str
    amount_cents: int
    currency: Literal["CAD"]
    created_at: str
    actor: str
