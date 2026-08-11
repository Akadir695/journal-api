from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.handlers import register_exception_handlers

app = FastAPI(
    title="journal api",
    description="this is journal api where people use to journal their ideas",
    version="0.1.0",
)
register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def root() -> dict[str, str]:
    return {"status": "ok"}
