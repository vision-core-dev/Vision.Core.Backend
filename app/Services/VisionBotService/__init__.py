from datetime import datetime, timezone

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.Objects.VisionBot import GuildSettings, Module, UniversalStore, ModuleLog


class VisionBotService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------
    # 🔹 1. СЕРВЕРИ / GUILD SETTINGS
    # ------------------------------------------------------------

    async def get_all_servers(self):
        """
        Повертає всі сервери з налаштуваннями.
        (GuildSettings = список усіх серверів, де бот хоч раз працював)
        """
        stmt = select(GuildSettings)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_guild(self, guild_id: int):
        """
        Повертає налаштування сервера.
        """
        stmt = select(GuildSettings).where(GuildSettings.guild_id == guild_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_guild_settings(self, guild_id: int, **kwargs):
        """
        Оновлює налаштування сервера:
        language, logs_channel_id, on_member_added_roles
        """
        stmt = (
            update(GuildSettings)
            .where(GuildSettings.guild_id == guild_id)
            .values(**kwargs)
            .returning(GuildSettings)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    # ------------------------------------------------------------
    # 🔹 2. МОДУЛІ
    # ------------------------------------------------------------

    async def get_modules(self, guild_id: int):
        """
        Повертає всі модулі, привʼязані до сервера.
        """
        stmt = (
            select(Module)
            .where(Module.server_id == guild_id)
            .order_by(Module.id.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_module(self, module_id: int):
        """
        Повертає один модуль.
        """
        stmt = select(Module).where(Module.id == module_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_module(self, module_id: int, **kwargs):
        """
        Оновлює модуль (name, code, status, meta, updated_at).
        """
        kwargs["updated_at"] = int(datetime.now(timezone.utc).timestamp())

        stmt = (
            update(Module)
            .where(Module.id == module_id)
            .values(**kwargs)
            .returning(Module)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def delete_module(self, module_id: int):
        """
        Видаляє модуль.
        """
        stmt = delete(Module).where(Module.id == module_id)
        await self.db.execute(stmt)
        await self.db.commit()
        return True

    # ------------------------------------------------------------
    # 🔹 3. ЛОГИ
    # ------------------------------------------------------------

    async def get_logs(self, guild_id: int, module_id: int | None = None, level: str | None = None):
        """
        Повертає логи сервера з фільтрами.
        """
        stmt = select(ModuleLog).where(ModuleLog.server_id == guild_id)

        if module_id:
            stmt = stmt.where(ModuleLog.module_id == module_id)
        if level:
            stmt = stmt.where(ModuleLog.level == level)

        stmt = stmt.order_by(ModuleLog.timestamp.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    # ------------------------------------------------------------
    # 🔹 4. UNIVERSAL STORE
    # ------------------------------------------------------------

    async def get_store_items(self, guild_id: int):
        """
        Повертає всі значення UniversalStore для сервера.
        """
        stmt = (
            select(UniversalStore)
            .where(UniversalStore.server_id == guild_id)
            .order_by(UniversalStore.id.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_store_item(self, item_id: int):
        """
        Повертає 1 запис UniversalStore.
        """
        stmt = select(UniversalStore).where(UniversalStore.id == item_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def set_store_item(self, **kwargs):
        """
        Додає або оновлює UniversalStore item (upsert по унікальному індексу).
        Поля:
        - server_id
        - scope
        - module_id
        - name
        - key
        - data_type
        - value_type
        - value
        """
        # Перевіряємо чи є запис
        stmt = select(UniversalStore).where(
            UniversalStore.server_id == kwargs["server_id"],
            UniversalStore.scope == kwargs["scope"],
            UniversalStore.module_id == kwargs.get("module_id"),
            UniversalStore.key == kwargs["key"],
        )

        existing = (await self.db.execute(stmt)).scalar_one_or_none()

        if existing:
            # оновлення
            for k, v in kwargs.items():
                setattr(existing, k, v)
            await self.db.commit()
            return existing

        # створення нового
        item = UniversalStore(**kwargs)
        self.db.add(item)
        await self.db.commit()
        return item

    async def delete_store_item(self, item_id: int):
        """
        Видаляє запис UniversalStore.
        """
        stmt = delete(UniversalStore).where(UniversalStore.id == item_id)
        await self.db.execute(stmt)
        await self.db.commit()
        return True
