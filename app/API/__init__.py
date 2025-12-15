from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")

from .HUB import hub_router
api_router.include_router(hub_router)

from .RoVision import rovision_router
api_router.include_router(rovision_router)

from .VisionSupport import vision_support_router
api_router.include_router(vision_support_router)