import uuid

from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.BoardService import BoardService, BoardsListResponse, CreateBoardResponse
from app.Services.Hub.BoardService.contracts import CreateBoardRequest, BoardDetailsResponse

boards_router = APIRouter(prefix="/Boards")

@boards_router.get("/List", response_model=BoardsListResponse)
async def boards_list(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await BoardService(db).GetBoardsList()

@boards_router.post("/Create", response_model=CreateBoardResponse)
async def create_board(data: CreateBoardRequest, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await BoardService(db).CreateBoard(data.name, data.description, user)

@boards_router.get("/{board_id}/GetDetails", response_model=BoardDetailsResponse)
async def get_board_details(board_id: str, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await BoardService(db).GetBoardDetails(board_id, user)




@boards_router.post("/{board_id}/Tags/Create")
async def create_tag(
    board_id: uuid.UUID,
    data: dict = Body(...),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await BoardService(db).CreateTag(board_id, data["name"], data["color"])


@boards_router.post("/{board_id}/Tags/{tag_id}/Remove")
async def remove_tag(
    board_id: uuid.UUID,
    tag_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await BoardService(db).RemoveTag(board_id, tag_id)


# --- Lists ---
@boards_router.post("/{board_id}/Lists/Create")
async def create_list(
    board_id: uuid.UUID,
    data: dict = Body(...),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await BoardService(db).CreateList(board_id, data["name"], data["color"])


@boards_router.post("/{board_id}/Lists/{list_id}/Remove")
async def remove_list(
    board_id: uuid.UUID,
    list_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await BoardService(db).RemoveList(board_id, list_id)