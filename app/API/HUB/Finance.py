from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Objects.finance.TransactionModel import Transaction
from app.Objects.finance.WithdrawalLimitModel import WithdrawalLimitModel
from app.Objects.finance.WithdrawalRequestModel import WithdrawalRequest, WithdrawalRequestStatus
from app.Services.Hub.AuthService.depends import getuser

finance_router = APIRouter(prefix="/Finance", tags=["Hub > Finance"])

@finance_router.get("/GetSalaryInfo")
async def get_salary_info(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    # 🧮 Баланс користувача
    current_balance = user.balance or 0.0
    withdrawn_amount = user.withdrawn_amount or 0.0

    # 💰 Трансакції
    transactions_result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user.id, Transaction.is_removed == False)
        .order_by(Transaction.created_at.desc())
    )
    transactions = [
        {
            "id": str(t.id),
            "name": t.name,
            "type": _map_transaction_type(t.type),
            "amount": float(t.amount),
            "created_at": t.created_at.isoformat(),
        }
        for t in transactions_result.scalars().all()
    ]

    # 💳 Ліміти виводу
    limit_result = await db.execute(
        select(WithdrawalLimitModel)
        .where(WithdrawalLimitModel.user_id == user.id)
        .order_by(WithdrawalLimitModel.created_at.desc())
        .limit(1)
    )
    limit = limit_result.scalar_one_or_none()

    monthly_limit = float(limit.limit_amount) if limit else 10000.0

    # Розрахунок залишку ліміту
    withdraw_sum_result = await db.execute(
        select(func.sum(WithdrawalRequest.amount))
        .where(
            WithdrawalRequest.user_id == user.id,
            WithdrawalRequest.status.in_(
                [WithdrawalRequestStatus.PAID.value, WithdrawalRequestStatus.APPROVED.value]
            ),
            func.date_trunc("month", WithdrawalRequest.requested_at)
            == func.date_trunc("month", datetime.utcnow())
        )
    )
    used_withdraw = withdraw_sum_result.scalar() or 0.0
    remaining_limit = monthly_limit - used_withdraw

    # 🧾 Запити на вивід
    requests_result = await db.execute(
        select(WithdrawalRequest)
        .where(WithdrawalRequest.user_id == user.id)
        .order_by(WithdrawalRequest.requested_at.desc())
    )
    withdrawal_requests = [
        {
            "id": str(r.id),
            "amount": float(r.amount),
            "status": _map_withdraw_status(r.status),
            "reason": getattr(r, "description", None),
            "created_at": r.requested_at.isoformat(),
        }
        for r in requests_result.scalars().all()
    ]

    # 📦 Формуємо фінальну відповідь
    return {
        "balance": current_balance,
        "withdrawable": remaining_limit,
        "withdrawn_total": withdrawn_amount,
        "transactions": transactions,
        "withdraw_requests": withdrawal_requests,
    }


# 🔧 Мапінги типів для фронту
def _map_transaction_type(db_type: str) -> str:
    mapping = {
        "income": "credit",
        "withdrawal": "withdraw",
        "deduction": "deduction",
        "expense": "deduction",
    }
    return mapping.get(db_type, "credit")


def _map_withdraw_status(db_status: str) -> str:
    mapping = {
        "pending": "pending",
        "approved": "approved",
        "rejected": "rejected",
        "paid": "paid",
        "completed": "paid",
    }
    return mapping.get(db_status, "pending")


# @finance_router.get("/GetFinanceStats")