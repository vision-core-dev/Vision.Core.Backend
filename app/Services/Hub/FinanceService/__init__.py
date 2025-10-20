from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import client as RedisClient

class FinanceService:
    def __init__(self, db: AsyncSession, redis: RedisClient):
        self.db = db
        self.redis = redis

    async def GetUserBalance(self, user_id: str) -> float:
        """
        Отримати баланс користувача.
        """
        # Спробувати отримати баланс з Redis кешу
        cached_balance = await self.redis.get(f"user_balance:{user_id}")
        if cached_balance is not None:
            return float(cached_balance)

        # Якщо в кеші немає, отримати баланс з бази даних
        result = await self.db.execute(
            "SELECT balance FROM user_finances WHERE user_id = :user_id",
            {"user_id": user_id}
        )
        balance = result.scalar_one_or_none() or 0.0

        # Зберегти баланс у кеш Redis
        await self.redis.set(f"user_balance:{user_id}", balance, ex=300)  # Кеш на 5 хвилин

        return balance