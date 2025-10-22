import uuid

from pydantic import BaseModel

from app.Objects.UserModel import UserPreview
from app.Objects.tasks.BoardListModel import BoardListBase
from app.Objects.tasks.BoardModel import BoardBase, BoardPreview
from app.Objects.tasks.TaskModel import TaskPreview
from app.Objects.tasks.TaskTags import TaskTagBase


class CreateBoardRequest(BaseModel):
    name: str
    description: str | None = None

class CreateBoardResponse(BaseModel):
    board_id: uuid.UUID

class BoardsListResponse(BaseModel):
    total: int
    list: list[BoardPreview]

class BoardDetailsResponse(BaseModel):
    board: BoardBase
    members: list[UserPreview]
    lists: list[BoardListBase]
    tasks: list[TaskPreview]
    tags: list[TaskTagBase]