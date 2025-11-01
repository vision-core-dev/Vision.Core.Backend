from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser

finance_router = APIRouter(prefix="/Finance", tags=["Hub > Finance"])

# Тут будуть ендпоінти, пов'язані з фінансами
# Наприклад, отримання балансу, створення транзакцій тощо.
@finance_router.get("/GetSalaryInfo")
async def get_salary_info(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return {
        "current_balance": user.balance,
        "withdrawn_amount": user.withdrawn_amount,
        "transactions": [
            {"date": "2024-01-15", "amount": 2000, "type": "deposit"},
            {"date": "2024-02-15", "amount": 2500, "type": "deposit"},
            {"date": "2024-03-01", "amount": 4500, "type": "withdrawal"},
        ],
        "withdrawal_limits": {
            "monthly_limit": 10000,
            "remaining_limit": 5500
        },
        "withdrawal_requests": [
            {"date": "2024-03-01", "amount": 4500, "status": "completed"},
        ]
    }
