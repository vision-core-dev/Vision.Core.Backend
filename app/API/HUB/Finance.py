import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Objects.finance.TransactionModel import Transaction, TransactionType
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
            "type": t.type.value,
            "amount": float(t.amount),
            "transaction_at": t.transaction_at.isoformat(),
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

    monthly_limit = float(limit.limit_amount) if limit else 0.00

    # Розрахунок залишку ліміту
    withdraw_sum_result = await db.execute(
        select(func.sum(WithdrawalRequest.amount))
        .where(
            WithdrawalRequest.user_id == user.id,
            WithdrawalRequest.status.in_(
                [WithdrawalRequestStatus.PAID, WithdrawalRequestStatus.APPROVED]
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
    withdrawal_requests = []
    for r in requests_result.scalars().all():
        status_value = getattr(r, "status", "pending")
        withdrawal_requests.append({
            "id": str(r.id),
            "amount": float(r.amount),
            "status": status_value,
            "comment": r.comment,
            "reason": r.reason,
            "created_at": r.requested_at.isoformat(),
        })

    # 📦 Формуємо фінальну відповідь
    return {
        "balance": current_balance,
        "withdrawable": remaining_limit,
        "withdrawn_total": withdrawn_amount,
        "transactions": transactions,
        "withdraw_requests": withdrawal_requests,
    }




class WithdrawalRequestDataModel(BaseModel):
    amount: float
    comment: str | None = None

@finance_router.post("/CreateWithdrawalRequest")
async def create_withdrawal_request(
    data: WithdrawalRequestDataModel,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    if data.amount <= 0:
        raise HTTPException(status_code=400, detail="invalid_amount")

    # 🔹 Поточний баланс користувача
    current_balance = user.balance or 0.0
    if data.amount > current_balance:
        raise HTTPException(status_code=400, detail="amount_exceeds_balance")

    # 🔹 Отримуємо ліміт
    limit_result = await db.execute(
        select(WithdrawalLimitModel)
        .where(WithdrawalLimitModel.user_id == user.id)
        .order_by(WithdrawalLimitModel.created_at.desc())
        .limit(1)
    )
    limit = limit_result.scalar_one_or_none()
    monthly_limit = float(limit.limit_amount) if limit else 10000.0

    # 🔹 Обчислюємо вже використаний ліміт цього місяця
    withdraw_sum_result = await db.execute(
        select(func.sum(WithdrawalRequest.amount))
        .where(
            WithdrawalRequest.user_id == user.id,
            WithdrawalRequest.status.in_(
                [WithdrawalRequestStatus.PAID, WithdrawalRequestStatus.APPROVED]
            ),
            func.date_trunc("month", WithdrawalRequest.requested_at)
            == func.date_trunc("month", datetime.utcnow())
        )
    )
    used_withdraw = withdraw_sum_result.scalar() or 0.0
    remaining_limit = monthly_limit - used_withdraw

    if data.amount > remaining_limit:
        raise HTTPException(status_code=400, detail="amount_exceeds_monthly_limit")

    # 🧾 Створюємо новий запит
    new_request = WithdrawalRequest(
        user_id=user.id,
        amount=data.amount,
        comment=data.comment,
        status=WithdrawalRequestStatus.PENDING,
        requested_at=datetime.utcnow(),
    )

    db.add(new_request)
    await db.commit()
    await db.refresh(new_request)

    # 🧮 Оновлюємо баланс користувача
    user.balance = current_balance - data.amount
    await db.commit()

    return {
        "id": str(new_request.id),
        "status": "pending",
        "amount": data.amount,
        "requested_at": new_request.requested_at.isoformat(),
        "message": "withdrawal_request_created",
    }


# @finance_router.get("/GetFinanceStats")

def _map_transaction_type(db_type: str) -> str:
    mapping = { "income": "credit", "withdrawal": "withdraw", "deduction": "deduction", "expense": "deduction", }
    return mapping.get(db_type, "credit")

@finance_router.get("/GetTransactionsList")
async def get_transactions_list(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    transactions_result = await db.execute(
        select(Transaction)
        .where(Transaction.is_removed == False)
        .order_by(Transaction.created_at.desc())
    )
    transactions = [
        {
            "id": str(t.id),
            "user_id": str(t.user_id),
            "name": t.name,
            "type": _map_transaction_type(t.type),
            "amount": float(t.amount),
            "transaction_at": t.transaction_at.isoformat(),
        }
        for t in transactions_result.scalars().all()
    ]

    users_result = await db.execute(select(User))
    users = [
        {
            "id": str(u.id),
            "avatar_url": u.avatar_url,
            "first_name": u.first_name,
            "last_name": u.last_name,
        }
        for u in users_result.scalars().all()
    ]

    return {"transactions": transactions, "users": users}


class CreateTransactionDataModel(BaseModel):
    name: str
    type: TransactionType
    amount: float | int
    users: list[uuid.UUID] | None = []
    transaction_at: datetime | None = None

@finance_router.post("/CreateTransaction")
async def create_transaction(
    data: CreateTransactionDataModel,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    ids = []
    tx_time = data.transaction_at or datetime.utcnow()

    for user_id in data.users or []:
        target_user_res = await db.execute(select(User).where(User.id == user_id))
        target_user = target_user_res.scalar_one_or_none()
        if not target_user:
            continue

        shared_transaction = Transaction(
            user_id=target_user.id,
            name=data.name,
            type=data.type,
            amount=float(data.amount),
            transaction_at=tx_time,
            is_removed=False,
        )
        db.add(shared_transaction)

        # 🔹 Форсуємо flush — отримуємо id з бази до комміту
        await db.flush()
        ids.append(str(shared_transaction.id))

        # Оновлюємо баланс
        target_user.balance = (target_user.balance or 0.0) + float(data.amount)
        if data.type == TransactionType.WITHDRAWAL:
            user.withdrawn_amount = (user.withdrawn_amount or 0.0) + data.amount
        db.add(target_user)

    # Один комміт для всіх
    await db.commit()

    return {
        "ids": ids,
        "message": "transaction_created",
    }

@finance_router.post("/ApproveWithdrawalRequest")
async def approve_withdrawal_request(
    data: dict,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    request_id = data.get("request_id")
    if not request_id:
        raise HTTPException(status_code=400, detail="request_id_required")

    request_res = await db.execute(
        select(WithdrawalRequest).where(WithdrawalRequest.id == request_id)
    )
    request = request_res.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="withdrawal_request_not_found")

    if request.status != WithdrawalRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="withdrawal_request_not_pending")

    request.status = WithdrawalRequestStatus.APPROVED
    await db.commit()

    return {
        "id": str(request.id),
        "status": "approved",
        "message": "withdrawal_request_approved",
    }

@finance_router.post("/RejectWithdrawalRequest")
async def reject_withdrawal_request(
    data: dict,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    request_id = data.get("request_id")
    reason = data.get("reason", "No reason provided")
    if not request_id:
        raise HTTPException(status_code=400, detail="request_id_required")

    request_res = await db.execute(
        select(WithdrawalRequest).where(WithdrawalRequest.id == request_id)
    )
    request = request_res.scalar_one_or_none()
    if not request:
        raise HTTPException(status_code=404, detail="withdrawal_request_not_found")

    if request.status != WithdrawalRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="withdrawal_request_not_pending")

    request.status = WithdrawalRequestStatus.REJECTED
    request.reason = reason
    await db.commit()

    # Повертаємо кошти на баланс користувача
    user_res = await db.execute(select(User).where(User.id == request.user_id))
    target_user = user_res.scalar_one_or_none()
    if target_user:
        target_user.balance = (target_user.balance or 0.0) + float(request.amount)
        db.add(target_user)
        await db.commit()

    return {
        "id": str(request.id),
        "status": "rejected",
        "message": "withdrawal_request_rejected",
    }