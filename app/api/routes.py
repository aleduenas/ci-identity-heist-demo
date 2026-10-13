"""Small route definitions; business logic lives in services and repository."""

from typing import Annotated

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.dependencies import bank_service, require_api_key
from app.schemas import AccountResponse, TransferRequest, TransferResponse
from app.service import BankService

probes = APIRouter()
business = APIRouter(dependencies=[Depends(require_api_key)])
Service = Annotated[BankService, Depends(bank_service)]


@probes.get("/health")
def health() -> dict:
    return {"status": "ok"}


@probes.get("/ready")
def ready(request: Request) -> dict:
    if not request.app.state.settings.api_key:
        raise HTTPException(503, "Service is not configured")
    try:
        request.app.state.bank_service.repository.ready()
    except (ClientError, BotoCoreError):
        raise HTTPException(503, "Storage is unavailable") from None
    return {"status": "ready"}


@business.get("/accounts/{account_id}", response_model=AccountResponse)
def account(account_id: str, service: Service) -> dict:
    return service.account(account_id)


@business.post("/transfers", response_model=TransferResponse)
def create_transfer(payload: TransferRequest, service: Service) -> dict:
    return service.create_transfer(payload)


@business.get("/transfers/{transfer_id}", response_model=TransferResponse)
def transfer(transfer_id: str, service: Service) -> dict:
    return service.transfer(transfer_id)
