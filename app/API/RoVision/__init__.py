from fastapi import APIRouter

rovision_router = APIRouter(prefix="/RoVision")

from .Hangout import hangout_router
rovision_router.include_router(hangout_router)

from .Blog import blog_router
rovision_router.include_router(blog_router)

from .Jobs import jobs_router
rovision_router.include_router(jobs_router)

from .Contact import contact_router
rovision_router.include_router(contact_router)

from .Games import games_router
rovision_router.include_router(games_router)