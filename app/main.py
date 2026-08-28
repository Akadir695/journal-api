import time
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.handlers import register_exception_handlers
from app.core.logging import configure_logging

logger = structlog.get_logger()

settings = get_settings()
configure_logging(settings.environment)


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
)
register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")


# creating middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    structlog.contextvars.bind_contextvars(request_id=request_id)
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


@app.get("/health")
async def root() -> dict[str, str]:
    return {"status": "ok"}
