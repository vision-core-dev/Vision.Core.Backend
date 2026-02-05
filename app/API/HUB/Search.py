from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.Infrastructure.Database import getdb
from app.Services.Hub.AuthService.depends import getuser
from app.Objects.UserModel import User
from app.Services.Hub.SearchService import SearchService

search_router = APIRouter(prefix="/Search", tags=["Search"])

@search_router.get("/")
async def global_search(
    q: str = Query(..., min_length=1),
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    service = SearchService(db)
    results = await service.global_search(query=q, user_id=str(user.id), role_id=str(user.role_id))
    return results
