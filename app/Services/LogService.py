"""
Сервіс для глобального логування всіх операцій в системі.
Надає централізований API для запису та читання логів.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import Request
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.Objects.LogModel import Log, ActionType, LogResponse, LogListResponse


class LogService:
    """Сервіс для роботи з логами"""

    @staticmethod
    async def create_log(
        db: AsyncSession,
        actor_id: Optional[uuid.UUID],
        entity_type: str,
        entity_id: uuid.UUID,
        action: ActionType,
        entity_name: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        changed_fields: Optional[list] = None,
        details: Optional[str] = None,
        extra_data: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> Log:
        """
        Створює новий лог запис.
        
        Args:
            db: Сесія бази даних
            actor_id: ID користувача, який виконав дію
            entity_type: Тип сутності (Task, Board, User, etc.)
            entity_id: ID сутності
            action: Тип дії (CREATE, UPDATE, DELETE, etc.)
            entity_name: Назва сутності
            old_values: Старі значення полів (для UPDATE)
            new_values: Нові значення полів (для CREATE/UPDATE)
            changed_fields: Список змінених полів
            details: Текстовий опис дії
            extra_data: Додаткові метадані
            ip_address: IP адреса користувача
            user_agent: User Agent браузера
            request_id: ID запиту для трейсингу
            
        Returns:
            Створений лог запис
        """
        log = Log(
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            action=action,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            details=details,
            extra_data=extra_data,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
        )
        
        db.add(log)
        await db.commit()
        await db.refresh(log)
        
        return log

    @staticmethod
    async def log_create(
        db: AsyncSession,
        actor_id: Optional[uuid.UUID],
        entity_type: str,
        entity_id: uuid.UUID,
        entity_name: Optional[str] = None,
        new_values: Optional[dict] = None,
        details: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> Log:
        """Логує створення сутності"""
        return await LogService.create_log(
            db=db,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            action=ActionType.CREATE,
            new_values=new_values,
            details=details or f"Створено {entity_type}: {entity_name or entity_id}",
            ip_address=LogService._get_client_ip(request) if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

    @staticmethod
    async def log_update(
        db: AsyncSession,
        actor_id: Optional[uuid.UUID],
        entity_type: str,
        entity_id: uuid.UUID,
        entity_name: Optional[str] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        changed_fields: Optional[list] = None,
        details: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> Log:
        """Логує оновлення сутності"""
        # Автоматично визначаємо змінені поля
        if old_values and new_values and not changed_fields:
            changed_fields = [
                field for field in new_values.keys()
                if field in old_values and old_values[field] != new_values[field]
            ]
        
        return await LogService.create_log(
            db=db,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            action=ActionType.UPDATE,
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            details=details or f"Оновлено {entity_type}: {entity_name or entity_id}",
            ip_address=LogService._get_client_ip(request) if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

    @staticmethod
    async def log_delete(
        db: AsyncSession,
        actor_id: Optional[uuid.UUID],
        entity_type: str,
        entity_id: uuid.UUID,
        entity_name: Optional[str] = None,
        old_values: Optional[dict] = None,
        details: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> Log:
        """Логує видалення сутності"""
        return await LogService.create_log(
            db=db,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            action=ActionType.DELETE,
            old_values=old_values,
            details=details or f"Видалено {entity_type}: {entity_name or entity_id}",
            ip_address=LogService._get_client_ip(request) if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

    @staticmethod
    async def log_action(
        db: AsyncSession,
        actor_id: Optional[uuid.UUID],
        entity_type: str,
        entity_id: uuid.UUID,
        action: ActionType,
        entity_name: Optional[str] = None,
        details: Optional[str] = None,
        extra_data: Optional[dict] = None,
        request: Optional[Request] = None,
    ) -> Log:
        """Логує довільну дію"""
        return await LogService.create_log(
            db=db,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            action=action,
            details=details,
            extra_data=extra_data,
            ip_address=LogService._get_client_ip(request) if request else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )

    @staticmethod
    async def get_logs(
        db: AsyncSession,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
        action: Optional[ActionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> LogListResponse:
        """
        Отримує список логів з фільтрацією.
        
        Args:
            db: Сесія бази даних
            entity_type: Фільтр по типу сутності
            entity_id: Фільтр по ID сутності
            actor_id: Фільтр по ID користувача
            action: Фільтр по типу дії
            start_date: Початкова дата
            end_date: Кінцева дата
            page: Номер сторінки
            page_size: Розмір сторінки
            
        Returns:
            Список логів з пагінацією
        """
        # Будуємо фільтри
        filters = []
        
        if entity_type:
            filters.append(Log.entity_type == entity_type)
        
        if entity_id:
            filters.append(Log.entity_id == entity_id)
        
        if actor_id:
            filters.append(Log.actor_id == actor_id)
        
        if action:
            filters.append(Log.action == action)
        
        if start_date:
            filters.append(Log.created_at >= start_date)
        
        if end_date:
            filters.append(Log.created_at <= end_date)
        
        # Запит для підрахунку загальної кількості
        count_query = select(func.count(Log.id))
        if filters:
            count_query = count_query.where(and_(*filters))
        
        result = await db.execute(count_query)
        total = result.scalar() or 0
        
        # Запит для отримання логів
        query = select(Log).order_by(desc(Log.created_at))
        
        if filters:
            query = query.where(and_(*filters))
        
        # Пагінація
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        result = await db.execute(query)
        logs = result.scalars().all()
        
        return LogListResponse(
            logs=[LogResponse.model_validate(log) for log in logs],
            total=total,
            page=page,
            page_size=page_size,
        )

    @staticmethod
    async def get_entity_logs(
        db: AsyncSession,
        entity_type: str,
        entity_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> LogListResponse:
        """Отримує всі логи для конкретної сутності"""
        return await LogService.get_logs(
            db=db,
            entity_type=entity_type,
            entity_id=entity_id,
            page=page,
            page_size=page_size,
        )

    @staticmethod
    async def get_user_activity(
        db: AsyncSession,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> LogListResponse:
        """Отримує всю активність користувача"""
        return await LogService.get_logs(
            db=db,
            actor_id=user_id,
            page=page,
            page_size=page_size,
        )

    @staticmethod
    def _get_client_ip(request: Request) -> Optional[str]:
        """Отримує IP адресу клієнта з урахуванням проксі"""
        # Перевіряємо заголовки проксі
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Якщо немає проксі, беремо прямий IP
        if request.client:
            return request.client.host
        
        return None

    @staticmethod
    def compare_values(old_obj: Any, new_obj: Any, fields: list[str]) -> tuple[dict, dict, list]:
        """
        Порівнює два об'єкти та повертає старі/нові значення та список змінених полів.
        
        Args:
            old_obj: Старий об'єкт
            new_obj: Новий об'єкт
            fields: Список полів для порівняння
            
        Returns:
            Tuple з (old_values, new_values, changed_fields)
        """
        old_values = {}
        new_values = {}
        changed_fields = []
        
        for field in fields:
            old_val = getattr(old_obj, field, None)
            new_val = getattr(new_obj, field, None)
            
            # Конвертуємо в JSON-сумісний формат
            if isinstance(old_val, datetime):
                old_val = old_val.isoformat()
            if isinstance(new_val, datetime):
                new_val = new_val.isoformat()
            if isinstance(old_val, uuid.UUID):
                old_val = str(old_val)
            if isinstance(new_val, uuid.UUID):
                new_val = str(new_val)
            
            if old_val != new_val:
                old_values[field] = old_val
                new_values[field] = new_val
                changed_fields.append(field)
        
        return old_values, new_values, changed_fields
