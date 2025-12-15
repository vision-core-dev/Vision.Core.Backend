from fastapi import APIRouter

hangout_router = APIRouter(prefix="/Hangout", tags=["RoVision > Hangout"])

from .data import hangout_data_router
hangout_router.include_router(hangout_data_router)