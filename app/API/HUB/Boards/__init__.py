from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.BoardService import BoardService, BoardsListResponse, CreateBoardResponse
from app.Services.Hub.BoardService.contracts import CreateBoardRequest

boards_router = APIRouter(prefix="/Boards")

@boards_router.get("/List", response_model=BoardsListResponse)
async def boards_list(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await BoardService(db).GetBoardsList()

@boards_router.post("/Create", response_model=CreateBoardResponse)
async def create_board(data: CreateBoardRequest, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await BoardService(db).CreateBoard(data.name, data.description, user)