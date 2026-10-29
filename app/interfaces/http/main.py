"""Fundação HTTP fechada para dados até a implementação do acesso na SPEC-0033."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from app.infrastructure.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings or Settings.from_environment(os.environ)
    application = FastAPI(
        title="LottoBrain",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        debug=False,
    )
    application.state.settings = configuration

    @application.middleware("http")
    async def private_response(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @application.get("/healthz")
    async def health() -> dict[str, str]:
        # Liveness apenas: não declara banco, autenticação ou dados prontos.
        return {"status": "ok"}

    @application.get("/readyz", status_code=503)
    async def readiness() -> dict[str, str]:
        return {"status": "not_ready", "code": "PLATFORM_NOT_READY"}

    @application.api_route(
        "/api/v1/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
    )
    async def unavailable(path: str) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={
                "code": "PLATFORM_NOT_READY",
                "message": "Acesso à plataforma ainda não habilitado.",
            },
        )

    return application


app = create_app()
