"""Minimal JSON request audit events without secrets, bodies, or record IDs."""

import json
import logging
import re
import sys
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("mybank.requests")
CORRELATION_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE", "CONNECT"}


def configure_request_logging() -> None:
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class RequestLoggingMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        supplied = next(
            (value.decode("latin-1") for key, value in scope["headers"] if key == b"x-request-id"),
            "",
        )
        request_id = supplied if CORRELATION_ID.fullmatch(supplied) else uuid.uuid4().hex
        started = time.perf_counter()
        status = 500

        async def send_response(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() != b"x-request-id"
                ]
                message = {**message, "headers": [*headers, (b"x-request-id", request_id.encode())]}
            await send(message)

        try:
            await self.app(scope, receive, send_response)
        finally:
            # Route templates keep account/transfer identifiers out of request logs.
            route = getattr(scope.get("route"), "path", "<unmatched>")
            method = scope.get("method", "")
            logger.info(
                json.dumps(
                    {
                        "event": "http_request",
                        "request_id": request_id,
                        "method": method if method in HTTP_METHODS else "OTHER",
                        "route": route,
                        "status": status,
                        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                    },
                    separators=(",", ":"),
                )
            )
