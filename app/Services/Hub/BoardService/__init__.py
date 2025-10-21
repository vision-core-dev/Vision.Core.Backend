from sqlalchemy import select

from app.Objects.UserModel import User
from app.Objects.tasks.BoardModel import Board
from app.Services.Hub.BoardService.contracts import CreateBoardResponse, BoardsListResponse


class BoardService:
    def __init__(self, db):
        self.db = db

    async def CreateBoard(self, name, description, user: User) -> CreateBoardResponse:
        new_board = Board(
            name=name,
            description=description,
            created_by_id=user.id
        )
        self.db.add(new_board)
        await self.db.commit()
        await self.db.refresh(new_board)
        return CreateBoardResponse(board_id=new_board.id)

    async def GetBoardsList(self) -> BoardsListResponse:
        result = await self.db.execute(select(Board))
        boards = result.fetchall()
        return BoardsListResponse(total=len(boards), boards=boards)

    async def GetBoardDetails(self, board_id, user: User):
        result = await self.db.execute(
            select(Board)
            .where(Board.id == board_id)
        )
        board = result.scalar_one_or_none()
        if not board:
            raise Exception("Board not found")
        return board