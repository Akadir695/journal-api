from fastapi import APIRouter

from app.api.v1.routes import entries

api_router = APIRouter()
api_router.include_router(entries.router, tags=["entries"])
  
