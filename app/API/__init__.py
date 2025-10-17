from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")

from .HUB import hub_router
api_router.include_router(hub_router)