"""A fail-closed lab credential is required before any business reads."""

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, Request

from app.service import BankService


def require_api_key(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
) -> None:
    configured = request.app.state.settings.api_key
    if (
        not configured
        or not x_api_key
        or not secrets.compare_digest(
            configured.encode(),
            x_api_key.encode(),
        )
    ):
        raise HTTPException(status_code=401, detail="Valid X-API-Key required")


def bank_service(request: Request) -> BankService:
    return request.app.state.bank_service
