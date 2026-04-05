import math
import uuid
from datetime import datetime

import pytz
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, case, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Objects.finance.TransactionModel import Transaction, TransactionType
from app.Objects.finance.WithdrawalLimitModel import WithdrawalLimitModel
from app.Objects.finance.WithdrawalRequestModel import WithdrawalRequest, WithdrawalRequestStatus
from app.Objects.tasks.TaskModel import Task
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.NotifyService import NotifyService

finance_router = APIRouter(prefix="/Finance", tags=["Hub > Finance"])

TRANSACTION_TYPE_LABEL = {
    TransactionType.INCOME: ("Надходження", "💰"),
    TransactionType.EXPENSE: ("Витрати", "💸"),
    TransactionType.TRANSFER: ("Переказ", "🔄"),
    TransactionType.WITHDRAWAL: ("Виведення", "🏦"),
    TransactionType.DEDUCTION: ("Корегування", "📝"),
}


@finance_router.get("/GetRealTimeBalance")
async def get_real_time_balance(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    """Calculate balance in real-time from transactions instead of stored value."""
    # Sum all non-removed transactions for this user
    income_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
            Transaction.user_id == user.id,
            Transaction.is_removed == False,
            Transaction.type.in_([TransactionType.INCOME, TransactionType.TRANSFER]),
        )
    )
    income = float(income_result.scalar())

    expense_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
            Transaction.user_id == user.id,
            Transaction.is_removed == False,
            Transaction.type.in_([TransactionType.EXPENSE, TransactionType.WITHDRAWAL, TransactionType.DEDUCTION]),
        )
    )
    expenses = float(expense_result.scalar())

    calculated_balance = income + expenses  # expenses are negative

    # Update stored balance to keep in sync
    user.balance = calculated_balance
    await db.commit()

    return {
        "balance": calculated_balance,
        "income_total": income,
        "expense_total": expenses,
    }

@finance_router.get("/GetSalaryInfo")
async def get_salary_info(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    # 🧮 Баланс користувача
    current_balance = user.balance or 0.0
    withdrawn_amount = user.withdrawn_amount or 0.0

    # 💰 Трансакції
    transactions_result = await db.execute(
        select(Transaction, Task)
        .outerjoin(Task, Transaction.task_id == Task.id)
        .where(Transaction.user_id == user.id, Transaction.is_removed == False)
        .order_by(Transaction.created_at.desc())
    )
    
    transactions = []
    for t, task in transactions_result.all():
        tx_data = {
            "id": str(t.id),
            "name": t.name,
            "type": t.type.value,
            "amount": float(t.amount),
            "transaction_at": t.transaction_at.isoformat(),
        }
        if task:
            tx_data["task"] = {
                "name": task.name,
                "start_at": task.started_at.isoformat() if task.started_at else None,
                "deadline_at": task.deadline_at.isoformat() if task.deadline_at else None,
            }
        transactions.append(tx_data)

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

@finance_router.get("/GetTransactionsList")
async def get_transactions_list(
    page: int = Query(1, ge=1),
    limit: int = Query(30, le=100),
    search: str | None = None,
    user: User = Depends(getuser), 
    db: AsyncSession = Depends(getdb)
):
    query = select(Transaction).where(Transaction.is_removed == False)
    
    if search:
        query = query.where(Transaction.name.ilike(f"%{search}%"))
        
    total_count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = total_count_result.scalar() or 0

    transactions_result = await db.execute(
        query.order_by(Transaction.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    transactions = [
        {
            "id": str(t.id),
            "user_id": str(t.user_id),
            "name": t.name,
            "type": t.type.value,
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

    return {
        "transactions": transactions, 
        "users": users, 
        "total_count": total_count, 
        "page": page, 
        "limit": limit
    }


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
    kyiv_tz = pytz.timezone("Europe/Kyiv")

    tx_time = (
        data.transaction_at.astimezone(kyiv_tz)
        if data.transaction_at
        else datetime.now(kyiv_tz)
    )

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
            target_user.withdrawn_amount = (target_user.withdrawn_amount or 0.0) + (-data.amount)
        db.add(target_user)

    # Сповіщення
    notify = NotifyService(db)
    for user_id in data.users or []:
        target_res = await db.execute(select(User).where(User.id == user_id))
        tu = target_res.scalar_one_or_none()
        if not tu:
            continue
        label, emoji = TRANSACTION_TYPE_LABEL.get(data.type, ("Транзакція", "📋"))
        new_balance = tu.balance or 0.0
        await notify.CreateNotification(
            user_id=user_id,
            title=f"{emoji} {label}",
            message=f"<b>{data.name}</b> — {data.amount:.2f} ₴\nБаланс: {new_balance:.2f} ₴",
            link="/finance/transactions/list",
        )

    # Один комміт для всіх
    await db.commit()

    return {
        "ids": ids,
        "message": "transaction_created",
    }

@finance_router.post("/UpdateTransaction")
async def update_transaction(
    data: dict,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    transaction_id = data.get("transaction_id")
    if not transaction_id:
        raise HTTPException(status_code=400, detail="transaction_id_required")

    tx_res = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.is_removed == False)
    )
    tx = tx_res.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="transaction_not_found")

    target_user = await db.get(User, tx.user_id)

    new_name = data.get("name")
    new_amount = data.get("amount")

    if new_name is not None:
        tx.name = new_name

    if new_amount is not None:
        new_amount = float(new_amount)
        old_amount = float(tx.amount)
        diff = new_amount - old_amount
        tx.amount = new_amount
        if target_user:
            target_user.balance = (target_user.balance or 0.0) + diff

    await db.commit()
    await db.refresh(tx)

    return {
        "id": str(tx.id),
        "name": tx.name,
        "amount": float(tx.amount),
        "type": tx.type.value,
        "message": "transaction_updated",
    }


@finance_router.post("/DeleteTransaction")
async def delete_transaction(
    data: dict,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    transaction_id = data.get("transaction_id")
    if not transaction_id:
        raise HTTPException(status_code=400, detail="transaction_id_required")

    tx_res = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.is_removed == False)
    )
    tx = tx_res.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="transaction_not_found")

    # Reverse balance
    target_user = await db.get(User, tx.user_id)
    if target_user:
        target_user.balance = (target_user.balance or 0.0) - float(tx.amount)
        if tx.type == TransactionType.WITHDRAWAL:
            target_user.withdrawn_amount = (target_user.withdrawn_amount or 0.0) - (-float(tx.amount))

    tx.is_removed = True

    if target_user:
        label, _ = TRANSACTION_TYPE_LABEL.get(tx.type, ("Транзакція", "📋"))
        new_balance = target_user.balance or 0.0
        await NotifyService(db).CreateNotification(
            user_id=target_user.id,
            title="🗑️ Скасування транзакції",
            message=f"<b>{tx.name}</b> ({label}, {tx.amount:.2f} ₴) скасовано\nБаланс: {new_balance:.2f} ₴",
            link="/finance/transactions/list",
        )

    await db.commit()

    return {
        "id": str(tx.id),
        "message": "transaction_deleted",
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


@finance_router.get("/GetUnwithdrawnList")
async def get_unwithdrawn_list(
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    # 🟢 1. Отримуємо всіх активних юзерів
    users_result = await db.execute(
        select(User).order_by(User.created_at.asc())
    )
    users = users_result.scalars().all()

    response = []

    # 🟢 2. Для кожного юзера рахуємо баланс в реальному часі
    for u in users:
        # Real-time balance calculation
        balance_result = await db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0.0)).where(
                Transaction.user_id == u.id,
                Transaction.is_removed == False,
            )
        )
        real_balance = float(balance_result.scalar())

        # Sync stored balance
        if u.balance != real_balance:
            u.balance = real_balance

        if real_balance <= 0:
            continue

        last_withdraw = await db.execute(
            select(Transaction)
            .where(
                Transaction.user_id == u.id,
                Transaction.type == TransactionType.WITHDRAWAL,
                Transaction.is_removed == False
            )
            .order_by(Transaction.transaction_at.desc())
            .limit(1)
        )
        last_tx = last_withdraw.scalar_one_or_none()

        response.append({
            "user": {
                "id": str(u.id),
                "first_name": u.first_name,
                "last_name": u.last_name,
                "avatar_url": u.avatar_url,
            },
            "amount": real_balance,
            "last_withdraw_amount": float(last_tx.amount) if last_tx else 0.0,
            "last_withdraw_at": last_tx.transaction_at.isoformat() if last_tx else None,
        })

    await db.commit()

    return {"items": response}


@finance_router.get("/GetLeaderboard")
async def get_leaderboard(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    """Get ranked list of users by total earnings."""
    # Sum all INCOME and TRANSFER transactions for each user using conditional aggregation
    total_earnings_expr = func.coalesce(
        func.sum(
            case(
                (
                    (Transaction.is_removed == False) & 
                    Transaction.type.in_([TransactionType.INCOME, TransactionType.TRANSFER]) &
                    (func.date_trunc("month", Transaction.transaction_at) == func.date_trunc("month", datetime.utcnow())),
                    Transaction.amount
                ),
                else_=0.0
            )
        ),
        0.0
    )

    result = await db.execute(
        select(
            User.id,
            User.first_name,
            User.last_name,
            User.avatar_url,
            total_earnings_expr.label("total_earnings")
        )
        .outerjoin(Transaction, Transaction.user_id == User.id)
        .where(User.is_active == True)
        .group_by(User.id)
        .having((total_earnings_expr > 0) | (User.id == user.id))
        .order_by(total_earnings_expr.desc())
    )

    items = []
    for row in result.all():
        items.append({
            "user_id": str(row.id),
            "first_name": row.first_name,
            "last_name": row.last_name,
            "avatar_url": row.avatar_url,
            "total_earnings": float(row.total_earnings)
        })

    return {"items": items}
