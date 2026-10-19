"""Application use cases shield routes from persistence details."""

from app.domain import DomainError
from app.repository.dynamodb import BankRepository
from app.schemas import TransferRequest


class BankService:
    def __init__(self, repository: BankRepository):
        self.repository = repository

    def account(self, account_id: str) -> dict:
        account = self.repository.account(account_id)
        if account is None:
            raise DomainError("account_not_found", "Account does not exist", 404)
        return account

    def transfer(self, transfer_id: str) -> dict:
        transfer = self.repository.transfer(transfer_id)
        if transfer is None:
            raise DomainError("transfer_not_found", "Transfer does not exist", 404)
        return transfer

    def create_transfer(self, request: TransferRequest) -> dict:
        return self.repository.create_transfer(request)
