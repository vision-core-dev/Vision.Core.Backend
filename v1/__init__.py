from fastapi import APIRouter

v1_api = APIRouter(prefix="/v1")

from .Document import docs_router
v1_api.include_router(docs_router)