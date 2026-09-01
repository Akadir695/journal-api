from fastapi import APIRouter

from app.api.v1.routes import auth, entries, users, tags, stats, exports

api_router = APIRouter()
api_router.include_router(entries.router, tags=["entries"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(tags.router, tags=["tags"])
api_router.include_router(stats.router, prefix="/stats", tags=["stats"])
api_router.include_router(exports.router, tags=["exports"])
