"""ASGI entry point; initialization avoids contacting AWS at import time."""

from contextlib import asynccontextmanager

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import business, probes
from app.domain import DomainError
from app.observability import RequestLoggingMiddleware, configure_request_logging
from app.repository.dynamodb import BankRepository
from app.service import BankService
from app.settings import Settings


def create_app(
    settings: Settings | None = None, repository: BankRepository | None = None
) -> FastAPI:
    selected = settings or Settings.from_environment()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        storage = repository or BankRepository(selected.dynamodb_client(), selected)
        application.state.settings = selected
        application.state.bank_service = BankService(storage)
        yield
        if repository is None:
            storage.client.close()

    application = FastAPI(title="Mybank sandbox", lifespan=lifespan)
    configure_request_logging()
    application.add_middleware(RequestLoggingMiddleware)
    application.include_router(probes)
    application.include_router(business)

    @application.exception_handler(DomainError)
    async def domain_error(_request: Request, error: DomainError):
        return JSONResponse(
            status_code=error.status,
            content={"code": error.code, "detail": error.message},
        )

    @application.exception_handler(ClientError)
    @application.exception_handler(BotoCoreError)
    async def storage_error(_request: Request, _error: Exception):
        return JSONResponse(
            status_code=503,
            content={"code": "storage_unavailable", "detail": "Storage unavailable"},
        )

    return application


app = create_app()
