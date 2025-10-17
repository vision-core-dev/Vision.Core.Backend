from fastapi import APIRouter

hub_router = APIRouter(prefix="/Hub")

from .Auth import auth_router
hub_router.include_router(auth_router)

from .Users import users_router
hub_router.include_router(users_router)

from .Events import events_router
hub_router.include_router(events_router)