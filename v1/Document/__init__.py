from fastapi import APIRouter

docs_router = APIRouter(prefix="/Document", tags=["Document"])



from .Get import router as get
docs_router.include_router(get)