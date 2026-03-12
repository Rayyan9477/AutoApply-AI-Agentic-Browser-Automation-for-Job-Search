"""FastAPI application factory and lifespan management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.api.v1.router import v1_router
from app.api.websocket.endpoint import router as ws_router
from app.config.constants import API_V1_PREFIX, APP_TITLE, APP_VERSION
from app.config.settings import Environment, get_settings
from app.core.exceptions import AutoApplyError, RecordNotFoundError
from app.db.redis import close_redis_pool, init_redis_pool
from app.db.session import engine
from app.models import Base
from app.observability.logging import configure_logging

logger = structlog.get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup and shutdown lifecycle."""
    # Startup
    configure_logging(settings.log_level, settings.environment.value)
    logger.info(
        "app_starting",
        version=APP_VERSION,
        environment=settings.environment.value,
    )

    # Create database tables (safe no-op if they already exist)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database_ready")

    await init_redis_pool(settings.redis_url)

    yield

    # Shutdown
    await close_redis_pool()
    await engine.dispose()
    logger.info("app_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=APP_TITLE,
        version=APP_VERSION,
        lifespan=lifespan,
        docs_url="/docs" if settings.environment != Environment.PRODUCTION else None,
        redoc_url="/redoc" if settings.environment != Environment.PRODUCTION else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Exception handlers
    @app.exception_handler(AutoApplyError)
    async def autoapply_error_handler(
        request: Request,
        exc: AutoApplyError,
    ) -> JSONResponse:
        """Convert domain exceptions to JSON error responses."""
        status_code = 500
        if isinstance(exc, RecordNotFoundError):
            status_code = 404
        elif exc.code.endswith("AUTH_ERROR"):
            status_code = 401
        elif exc.code.endswith("RATE_LIMIT"):
            status_code = 429
        elif exc.code.endswith("INTEGRITY_ERROR"):
            status_code = 409

        logger.warning(
            "domain_error",
            error_code=exc.code,
            message=exc.message,
            path=str(request.url),
        )

        return JSONResponse(
            status_code=status_code,
            content={"detail": exc.message, "code": exc.code},
        )

    # Routes
    app.include_router(v1_router, prefix=API_V1_PREFIX)
    app.include_router(ws_router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok", "version": APP_VERSION}

    return app


app = create_app()
