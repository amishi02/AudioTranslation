"""Application factory — P2-BE-001 / P2-BE-003 / P2-BE-007 / P2-BE-008."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.capabilities import router as capabilities_router
from app.api.health import router as health_router
from app.api.metrics import router as metrics_router
from app.api.websocket import router as websocket_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Wires logging, CORS, routers, and global error handlers.
    Keeps api layer thin — no provider/model instantiation here.
    """
    configure_logging(settings.log_level)
    logger.info(
        "app_startup log_level=%s app_env=%s version=%s",
        settings.log_level,
        settings.app_env,
        settings.app_version,
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )

    # --- CORS (P2-BE-007) ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routers (P2-BE-008: versioned prefix for capabilities) ---
    # Health stays unversioned as alias per Risks/Notes
    app.include_router(health_router)
    app.include_router(capabilities_router)
    app.include_router(websocket_router)
    app.include_router(metrics_router)

    # --- Exception handlers (P2-BE-003) ---
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.warning(
            "validation_error path=%s code=VALIDATION_ERROR",
            request.url.path,
        )
        err = ErrorResponse(
            error="validation_error",
            code="INVALID_MESSAGE",
            message="Invalid request payload",
            details={"errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=err.model_dump())

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else f"HTTP_{exc.status_code}"
        # Avoid logging stack for 404
        if exc.status_code >= 500:
            logger.error(
                "http_error path=%s status=%s code=%s",
                request.url.path,
                exc.status_code,
                code,
            )
        else:
            logger.info(
                "http_error path=%s status=%s code=%s",
                request.url.path,
                exc.status_code,
                code,
            )
        err = ErrorResponse(
            error="http_error",
            code=code,
            message=str(exc.detail) if exc.detail else "Not found",
        )
        return JSONResponse(status_code=exc.status_code, content=err.model_dump())

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("unhandled_error path=%s", request.url.path)
        err = ErrorResponse(
            error="internal_error",
            code="INTERNAL_ERROR",
            message="Internal server error",
        )
        return JSONResponse(status_code=500, content=err.model_dump())

    return app


app = create_app()
