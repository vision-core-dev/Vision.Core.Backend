from fastapi import APIRouter

rovision_router = APIRouter(prefix="/RoVision")

from .Hangout import hangout_router
rovision_router.include_router(hangout_router)