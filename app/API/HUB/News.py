import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Objects.NewsModel import News
from app.Objects.NewsSchemas import CreateNewsRequest, UpdateNewsRequest, NewsResponse, ListNewsResponse
from app.Services.Hub.AuthService.depends import getuser

news_router = APIRouter(prefix="/News", tags=["Hub > News"])

def check_permission(user: User):
    if not user.role or user.role.order not in [0, 1]:
        raise HTTPException(status_code=403, detail="Створення новин дозволено лише для CEO та COO")

@news_router.get("/List", response_model=ListNewsResponse)
async def list_news(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    result = await db.execute(
        select(News)
        .order_by(desc(News.created_at))
    )
    return {"items": result.scalars().all()}

@news_router.post("/Create", response_model=NewsResponse)
async def create_news(
    data: CreateNewsRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    check_permission(user)
    
    news = News(
        author_id=user.id,
        title=data.title,
        content=data.content,
        labels=data.labels,
        target_text=data.target_text,
        target_url=data.target_url
    )
    
    db.add(news)
    await db.commit()
    await db.refresh(news)
    return news

@news_router.patch("/{news_id}/Update", response_model=NewsResponse)
async def update_news(
    news_id: uuid.UUID,
    data: UpdateNewsRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    check_permission(user)
    
    news = await db.get(News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
        
    for key, value in data.dict(exclude_unset=True).items():
        setattr(news, key, value)
        
    await db.commit()
    await db.refresh(news)
    return news

@news_router.delete("/{news_id}/Delete")
async def delete_news(
    news_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    check_permission(user)
    
    news = await db.get(News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
        
    await db.delete(news)
    await db.commit()
    return {"status": "success"}
