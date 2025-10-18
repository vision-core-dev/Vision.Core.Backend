from fastapi import APIRouter

user_me_router = APIRouter(prefix="/UserMe", tags=["Hub > UserMe"])

from .Notifies import notifies_router
user_me_router.include_router(notifies_router)