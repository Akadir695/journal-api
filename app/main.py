import asyncio
import time
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import uuid4

import structlog
from arq import create_pool
from arq.connections import RedisSettings
from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_redis
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.handlers import register_exception_handlers
from app.core.logging import configure_logging
from app.core.rate_limit import check_rate_limit
from app.db.session import get_db

PROBE_TIMEOUT = 2.0

logger = structlog.get_logger()

settings = get_settings()
configure_logging(settings.environment)

# Opens the export pipe to Application Insights. Without this, telemetry is
# produced but never leaves the process.
if settings.applicationinsights_connection_string:
    configure_azure_monitor(
        connection_string=settings.applicationinsights_connection_string,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
    await app.state.redis.ping()
    app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    yield
    await app.state.redis.aclose()
    await app.state.arq.aclose()


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
)

# The pipe alone does not produce request spans — auto-instrumentation did not
# pick up FastAPI, so hook it to the app explicitly.
if settings.applicationinsights_connection_string:
    FastAPIInstrumentor.instrument_app(app)


register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")


# creating middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    structlog.contextvars.bind_contextvars(request_id=request_id)

    # Tag logs with the trace id so a log line can be joined to its trace.
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        structlog.contextvars.bind_contextvars(
            trace_id=format(span_context.trace_id, "032x")
        )

    start = time.perf_counter()

    response = await call_next(request)

    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )

    response.headers["X-Request-ID"] = request_id
    return response
# rate limiter middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host
    if request.url.path.startswith("/api/v1/auth"):
        limit = 5
        key = f"ratelimit:auth:{ip}"
    else:
        limit = 100
        key = f"ratelimit:{ip}"
    allowed, remaining = await check_rate_limit(request.app.state.redis, key, limit, 60)
    if not allowed:
        return JSONResponse(
            status_code=429,
            media_type="application/problem+json",
            content={
                "type": "about:blank",
                "title": "Too many requests",
                "status": 429,
                "detail": "Rate limit exceeded. Try again shortly.",
                "instance": request.url.path,
            },
            headers={
                "Retry-After": "60",
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
MAX_BODY_BYTES = 1_000_000  # 1 MB


@app.middleware("http")
async def body_size_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            media_type="application/problem+json",
            content={
                "type": "about:blank",
                "title": "Payload too large",
                "status": 413,
                "detail": "Request body exceeds the maximum allowed size.",
                "instance": request.url.path,
            },
        )
    return await call_next(request)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.get("/health", summary="Liveness probe", tags=["health"])
async def health() -> dict[str, str]:
    """Returns 200 whenever the process is running. Checks no dependencies.

    Azure restarts the container if this fails, so it must never depend on
    Postgres or Redis — a database blip would cause a restart loop.
    """
    return {"status": "ok"}


@app.get("/health/ready", summary="Readiness probe", tags=["health"])
async def readiness(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> JSONResponse:
    """Returns 200 when this replica can serve requests, 503 when it cannot.

    Azure stops sending traffic here on failure but does not restart the
    container, so a dependency outage pauses this replica rather than
    destroying it.
    """
    checks: dict[str, str] = {}

    try:
        await asyncio.wait_for(db.execute(text("SELECT 1")), PROBE_TIMEOUT)
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"

    try:
        await asyncio.wait_for(redis.ping(), PROBE_TIMEOUT)
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unavailable"

    ready = all(status == "ok" for status in checks.values())
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"status": "ready" if ready else "not ready", "checks": checks},
    )
@app.get("/", summary="API information", tags=["health"])
async def root() -> dict[str, str]:
    """Name and version, so the root of the API is not a 404."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }