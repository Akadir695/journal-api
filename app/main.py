from fastapi import FastAPI

app = FastAPI(
    title="journal api",
    description="this is journal api where people use to journal their ideas",
    version="0.1.0",
)


@app.get("/health")
async def root() -> dict[str, str]:
    return {"status": "ok"}
