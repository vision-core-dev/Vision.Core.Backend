import uuid

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Objects.tasks.BoardModel import Board
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.BoardService import BoardService

board_members_router = APIRouter()

@board_members_router.post("/{board_id}/Members/Add")
async def add_board_member(
    board_id: uuid.UUID,
    data: dict = Body(...),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """
    Додає користувача на борд (лише для адмінів).
    body: { "user_id": "<uuid>", "role": "member|admin|viewer" }
    """
    return await BoardService(db).AddBoardMember(
        board_id=board_id,
        user_id=data.get("user_id"),
        role=data.get("role", "member"),
        actor=user
    )

@board_members_router.post("/{board_id}/Members/Remove")
async def remove_board_member(
    board_id: uuid.UUID,
    data: dict = Body(...),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """
    Видаляє користувача з борда (лише для адмінів).
    body: { "user_id": "<uuid>" }
    """
    return await BoardService(db).RemoveBoardMember(
        board_id=board_id,
        user_id=data.get("user_id"),
        actor=user
    )

@board_members_router.post("/{board_id}/Members/ChangeRole")
async def change_board_member_role(
    board_id: uuid.UUID,
    data: dict = Body(...),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """
    Змінює роль учасника (admin/member/viewer).
    body: { "user_id": "<uuid>", "new_role": "admin|member|viewer" }
    """
    return await BoardService(db).ChangeMemberRole(
        board_id=board_id,
        user_id=data.get("user_id"),
        new_role=data.get("new_role"),
        actor=user
    )


@board_members_router.get("/{board_id}/Members/List")
async def get_board_members(
    board_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    """
    Повертає список учасників борда з їхніми ролями.
    """
    board = await db.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="board_not_found")

    return {"ok": True, "members": board.members or {}}
