import uuid

from pydantic import BaseModel

from app.Objects.tasks.BoardModel import BoardBase


class CreateBoardRequest(BaseModel):
    name: str
    description: str | None = None

class CreateBoardResponse(BaseModel):
    board_id: uuid.UUID

class BoardsListResponse(BaseModel):
    total: int
    boards: list[BoardBase]

class BoardDetailsResponse(BaseModel):
    board: BoardBase
    # members: list[UserPreview]
    # lists: list[BoardListBase]
    # tasks: list[TaskPreview]
    # tags: list[TaskTagBase]