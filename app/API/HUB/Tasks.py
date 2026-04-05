import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Services.Hub.AuthService.depends import getuser
from app.Objects.UserModel import User
from app.Services.Hub.TaskService import TaskService
from app.Services.Hub.TaskService.contracts import TaskDetailsResponse

async def _notify_update(board_id, action, data):
    try:
        from app.API.HUB.Boards.websocket import notify_board_update
        await notify_board_update(board_id, action, data)
    except Exception as e:
        print(f"Error notifying WS: {e}")

tasks_router = APIRouter(prefix="/Tasks", tags=["Tasks"])

# 🔹 Деталі задачі
@tasks_router.get("/{task_id}/GetDetails", response_model=TaskDetailsResponse)
async def get_task_details(task_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await TaskService(db).GetTaskDetails(task_id, user)

@tasks_router.get("/{task_id}/GetPublicDetails", response_model=TaskDetailsResponse)
async def get_public_task_details(task_id: uuid.UUID, db: AsyncSession = Depends(getdb)):
    return await TaskService(db).GetPublicTaskDetails(task_id)

# 🔹 Призначити користувача
@tasks_router.post("/{task_id}/AssignUser")
async def assign_user(task_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id_required")
    res = await TaskService(db).AssignUser(task_id, uuid.UUID(user_id), current_user=user)
    if res.get("board_id"):
        await _notify_update(res["board_id"], "task_updated", {"task_id": str(task_id)})
    return res

# 🔹 Зняти користувача
@tasks_router.post("/{task_id}/UnassignUser")
async def unassign_user(task_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id_required")
    res = await TaskService(db).UnassignUser(task_id, uuid.UUID(user_id))
    if res.get("board_id"):
        await _notify_update(res["board_id"], "task_updated", {"task_id": str(task_id)})
    return res

# 🔹 Додати мітку
@tasks_router.post("/{task_id}/AssignTag")
async def assign_tag(task_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    tag_id = payload.get("tag_id")
    if not tag_id:
        raise HTTPException(status_code=400, detail="tag_id_required")
    res = await TaskService(db).AssignTag(task_id, uuid.UUID(tag_id))
    if res.get("board_id"):
        await _notify_update(res["board_id"], "task_updated", {"task_id": str(task_id)})
    return res

# 🔹 Зняти мітку
@tasks_router.post("/{task_id}/UnassignTag")
async def unassign_tag(task_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    tag_id = payload.get("tag_id")
    if not tag_id:
        raise HTTPException(status_code=400, detail="tag_id_required")
    res = await TaskService(db).UnassignTag(task_id, uuid.UUID(tag_id))
    if res.get("board_id"):
        await _notify_update(res["board_id"], "task_updated", {"task_id": str(task_id)})
    return res

# 🔹 Архівувати задачу
@tasks_router.post("/{task_id}/Archive")
async def archive_task(task_id: uuid.UUID, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    res = await TaskService(db).ArchiveTask(task_id, user)
    if res.get("board_id"):
        await _notify_update(res["board_id"], "task_archived", {"task_id": str(task_id)})
    return res


@tasks_router.post("/{task_id}/UpdateDescription")
async def update_task_description(task_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    description = payload.get("description")
    if description is None:
        raise HTTPException(status_code=400, detail="description_required")
    res = await TaskService(db).UpdateTaskDescription(task_id, description, user)
    if res.get("board_id"):
        await _notify_update(res["board_id"], "task_updated", {"task_id": str(task_id)})
    return res


@tasks_router.post("/{task_id}/UpdateName")
async def update_task_name(task_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    name = payload.get("name")
    if name is None:
        raise HTTPException(status_code=400, detail="name_required")
    res = await TaskService(db).UpdateTaskName(task_id, name, user)
    if res.get("board_id"):
        await _notify_update(res["board_id"], "task_updated", {"task_id": str(task_id)})
    return res


@tasks_router.post("/{task_id}/Attachments/UploadFile")
async def upload_task_attachment(task_id: uuid.UUID, file: UploadFile = File(...), db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    return await TaskService(db).UploadFileAttachment(task_id, file, user)

@tasks_router.post("/{task_id}/Attachments/AddLink")
async def add_task_link_attachment(task_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    link_url = payload.get("url")
    name = payload.get("name")
    if link_url is None:
        raise HTTPException(status_code=400, detail="link_url_required")
    return await TaskService(db).AddLinkAttachment(task_id, link_url, name, user)

@tasks_router.post("/{task_id}/Attachments/{attachment_id}/Remove")
async def remove_task_attachment(task_id: uuid.UUID, attachment_id: uuid.UUID, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    return await TaskService(db).RemoveAttachment(task_id, attachment_id, user)

@tasks_router.post("/{task_id}/Attachments/{attachment_id}/Rename")
async def rename_task_attachment(task_id: uuid.UUID, attachment_id: uuid.UUID, payload: dict, db: AsyncSession = Depends(getdb), user: User = Depends(getuser)):
    new_name = payload.get("new_name")
    if new_name is None:
        raise HTTPException(status_code=400, detail="new_name_required")
    return await TaskService(db).RenameAttachment(task_id, attachment_id, new_name, user)


@tasks_router.post("/{task_id}/UploadBanner")
async def upload_task_banner(
    task_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await TaskService(db).UploadTaskBanner(task_id, file, user)

@tasks_router.post("/{task_id}/SetBanner")
async def set_task_banner(
    task_id: uuid.UUID,
    payload: dict,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    banner_url = payload.get("banner_url")
    if not banner_url:
        raise HTTPException(status_code=400, detail="banner_url_required")
    return await TaskService(db).SetTaskBanner(task_id, banner_url, user)

@tasks_router.post("/{task_id}/MoveToList")
async def move_task_to_list(
    task_id: uuid.UUID,
    payload: dict,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    list_id = payload.get("list_id")
    if not list_id:
        raise HTTPException(status_code=400, detail="list_id_required")
    
    res = await TaskService(db).MoveTaskToList(task_id, uuid.UUID(list_id), user)
    
    if res.get("board_id"):
        await _notify_update(
            res["board_id"],
            "task_moved",
            {"task_id": str(task_id), "new_list_id": list_id}
        )
    
    return res



@tasks_router.post("/{task_id}/SetTaskOrder")
async def set_task_order(
    task_id: uuid.UUID,
    payload: dict,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    order = payload.get("order")
    list_id = payload.get("list_id")
    if order is None and list_id is None:
        raise HTTPException(status_code=400, detail="new_order_required")
    res = await TaskService(db).SetTaskOrder(task_id, order, list_id, user)
    if res.get("board_id"):
        await _notify_update(res["board_id"], "task_moved", {"task_id": str(task_id)})
    return res


@tasks_router.post("/{task_id}/UpdateDates")
async def update_dates(
    task_id: uuid.UUID,
    payload: dict,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    deadline_at = payload.get("deadline_at")
    started_at = payload.get("started_at")
    completed_at = payload.get("completed_at")
    res = await TaskService(db).UpdateTaskDates(
        task_id,
        deadline_at=deadline_at,
        started_at=started_at,
        completed_at=completed_at,
        user=user
    )
    if res.get("board_id"):
        await _notify_update(res["board_id"], "task_updated", {"task_id": str(task_id)})
    return res

from .Subtasks import subtasks_router
tasks_router.include_router(subtasks_router)


# ======================== TASK ACCRUALS ========================
from pydantic import BaseModel
from app.Objects.finance.TaskAccrualModel import TaskAccrual
from app.Objects.finance.TransactionModel import Transaction, TransactionType
from sqlalchemy import select

class CreateAccrualPayload(BaseModel):
    user_id: str
    amount: float
    name: str | None = None

@tasks_router.post("/{task_id}/Accruals/Create")
async def create_task_accrual(
    task_id: uuid.UUID,
    payload: CreateAccrualPayload,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    from app.Objects.tasks.TaskModel import Task
    
    if not user.role or user.role.order > 3:
        raise HTTPException(status_code=403, detail="forbidden")
    
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")

    target_user = await db.get(User, uuid.UUID(payload.user_id))
    if not target_user:
        raise HTTPException(status_code=404, detail="user_not_found")

    accrual_name = payload.name or f"Виплата за задачу: {task.name}"

    # 1. Create accrual record
    accrual = TaskAccrual(
        task_id=task_id,
        user_id=target_user.id,
        created_by_id=user.id,
        name=accrual_name,
        amount=float(payload.amount),
    )
    db.add(accrual)
    await db.flush()

    # 2. Create a corresponding transaction
    transaction = Transaction(
        user_id=target_user.id,
        created_by_id=user.id,
        task_id=task_id,
        name=accrual_name,
        type=TransactionType.INCOME,
        amount=float(payload.amount),
        is_removed=False,
    )
    db.add(transaction)

    # 3. Update user balance
    target_user.balance = (target_user.balance or 0.0) + float(payload.amount)

    # 4. Notify user about accrual
    from app.Services.Hub.NotifyService import NotifyService
    new_balance = target_user.balance or 0.0
    await NotifyService(db).CreateNotification(
        user_id=target_user.id,
        title="💰 Нарахування",
        message=f"<b>{accrual_name}</b> — {payload.amount:.2f} ₴\nБаланс: {new_balance:.2f} ₴",
        link=f"/boards/b/{task.board_id}/t/{task_id}",
    )

    await db.commit()
    await db.refresh(accrual)

    return {
        "id": str(accrual.id),
        "task_id": str(accrual.task_id),
        "user_id": str(accrual.user_id),
        "name": accrual.name,
        "amount": float(accrual.amount),
        "created_at": accrual.created_at.isoformat(),
    }


class UpdateAccrualPayload(BaseModel):
    amount: float | None = None
    name: str | None = None

@tasks_router.post("/{task_id}/Accruals/{accrual_id}/Update")
async def update_task_accrual(
    task_id: uuid.UUID,
    accrual_id: uuid.UUID,
    payload: UpdateAccrualPayload,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    if not user.role or user.role.order > 3:
        raise HTTPException(status_code=403, detail="forbidden")

    accrual = await db.get(TaskAccrual, accrual_id)
    if not accrual or accrual.task_id != task_id or accrual.is_removed:
        raise HTTPException(status_code=404, detail="accrual_not_found")

    target_user = await db.get(User, accrual.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="user_not_found")

    # Handle amount change — adjust user balance
    if payload.amount is not None and payload.amount != accrual.amount:
        old_amount = float(accrual.amount)
        new_amount = float(payload.amount)
        diff = new_amount - old_amount
        target_user.balance = (target_user.balance or 0.0) + diff
        accrual.amount = new_amount

        # Update matching transaction
        tx_result = await db.execute(
            select(Transaction).where(
                Transaction.task_id == task_id,
                Transaction.user_id == accrual.user_id,
                Transaction.is_removed == False,
            ).order_by(Transaction.created_at.desc()).limit(1)
        )
        tx = tx_result.scalar_one_or_none()
        if tx:
            tx.amount = new_amount

    if payload.name is not None:
        accrual.name = payload.name
        # Also update matching transaction name
        tx_result = await db.execute(
            select(Transaction).where(
                Transaction.task_id == task_id,
                Transaction.user_id == accrual.user_id,
                Transaction.is_removed == False,
            ).order_by(Transaction.created_at.desc()).limit(1)
        )
        tx = tx_result.scalar_one_or_none()
        if tx:
            tx.name = payload.name

    await db.commit()
    await db.refresh(accrual)

    return {
        "id": str(accrual.id),
        "task_id": str(accrual.task_id),
        "user_id": str(accrual.user_id),
        "name": accrual.name,
        "amount": float(accrual.amount),
        "created_at": accrual.created_at.isoformat(),
    }


@tasks_router.post("/{task_id}/Accruals/{accrual_id}/Delete")
async def delete_task_accrual(
    task_id: uuid.UUID,
    accrual_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    if not user.role or user.role.order > 3:
        raise HTTPException(status_code=403, detail="forbidden")

    accrual = await db.get(TaskAccrual, accrual_id)
    if not accrual or accrual.task_id != task_id:
        raise HTTPException(status_code=404, detail="accrual_not_found")

    target_user = await db.get(User, accrual.user_id)
    if target_user:
        target_user.balance = (target_user.balance or 0.0) - float(accrual.amount)

    # Soft-delete the accrual
    accrual.is_removed = True

    # Soft-delete the matching transaction
    tx_result = await db.execute(
        select(Transaction).where(
            Transaction.task_id == task_id,
            Transaction.user_id == accrual.user_id,
            Transaction.is_removed == False,
        ).order_by(Transaction.created_at.desc()).limit(1)
    )
    tx = tx_result.scalar_one_or_none()
    if tx:
        tx.is_removed = True

    await db.commit()

    return {"ok": True, "message": "accrual_deleted"}