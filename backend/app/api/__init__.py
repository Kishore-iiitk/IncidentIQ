from fastapi import APIRouter
from .incidents import router as incidents_router

api_router = APIRouter(prefix="/api")
api_router.include_router(incidents_router)

__all__ = ["api_router"]
