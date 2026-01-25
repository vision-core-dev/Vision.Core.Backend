"""
API для роботи з логами системи.
Дозволяє переглядати історію дій користувачів та системи.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.LogModel import LogListResponse, ActionType
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser
from app.Services.LogService import LogService

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("/", response_model=LogListResponse)
async def get_logs(
    entity_type: Optional[str] = Query(None, description="Тип сутності (Task, Board, User, etc.)"),
    entity_id: Optional[uuid.UUID] = Query(None, description="ID сутності"),
    actor_id: Optional[uuid.UUID] = Query(None, description="ID користувача, який виконав дію"),
    action: Optional[ActionType] = Query(None, description="Тип дії"),
    start_date: Optional[datetime] = Query(None, description="Початкова дата"),
    end_date: Optional[datetime] = Query(None, description="Кінцева дата"),
    page: int = Query(1, ge=1, description="Номер сторінки"),
    page_size: int = Query(50, ge=1, le=100, description="Розмір сторінки"),
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """
    Отримати список логів з фільтрацією.
    
    Доступні фільтри:
    - entity_type: Тип сутності (Task, Board, User, etc.)
    - entity_id: ID конкретної сутності
    - actor_id: ID користувача, який виконав дію
    - action: Тип дії (CREATE, UPDATE, DELETE, etc.)
    - start_date: Початкова дата
    - end_date: Кінцева дата
    """
    return await LogService.get_logs(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get("/entity/{entity_type}/{entity_id}", response_model=LogListResponse)
async def get_entity_logs(
    entity_type: str,
    entity_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Номер сторінки"),
    page_size: int = Query(50, ge=1, le=100, description="Розмір сторінки"),
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """
    Отримати всі логи для конкретної сутності.
    
    Наприклад:
    - /logs/entity/Task/123e4567-e89b-12d3-a456-426614174000
    - /logs/entity/Board/123e4567-e89b-12d3-a456-426614174000
    """
    return await LogService.get_entity_logs(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        page=page,
        page_size=page_size,
    )


@router.get("/user/{user_id}", response_model=LogListResponse)
async def get_user_activity(
    user_id: uuid.UUID,
    page: int = Query(1, ge=1, description="Номер сторінки"),
    page_size: int = Query(50, ge=1, le=100, description="Розмір сторінки"),
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """
    Отримати всю активність користувача.
    
    Показує всі дії, які виконав конкретний користувач.
    """
    return await LogService.get_user_activity(
        db=db,
        user_id=user_id,
        page=page,
        page_size=page_size,
    )


@router.get("/my-activity", response_model=LogListResponse)
async def get_my_activity(
    page: int = Query(1, ge=1, description="Номер сторінки"),
    page_size: int = Query(50, ge=1, le=100, description="Розмір сторінки"),
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """
    Отримати мою активність.
    
    Показує всі дії, які виконав поточний користувач.
    """
    return await LogService.get_user_activity(
        db=db,
        user_id=user.id,
        page=page,
        page_size=page_size,
    )
