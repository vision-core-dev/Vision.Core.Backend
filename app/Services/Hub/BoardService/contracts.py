import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel

from app.Objects.UserModel import UserPreview
from app.Objects.tasks.BoardListModel import BoardListBase
from app.Objects.tasks.BoardModel import BoardBase, BoardPreview
from app.Objects.tasks.TaskModel import TaskPreview, TaskPriority
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
    users: list[UserPreview]
    lists: list[BoardListBase]
    tasks: list[TaskPreview]
    tags: list[TaskTagBase]

class CreateTaskRequest(BaseModel):
    list_id: uuid.UUID
    name: str
    description: Optional[str] = None
    assignee_ids: Optional[List[uuid.UUID]] = None
    priority: Optional[str] = TaskPriority.low
    deadline_at: Optional[datetime] = None
    value_uah: Optional[float] = 0.0

class CreateTaskResponse(BaseModel):
    ok: bool
    id: uuid.UUID
    name: str
    list_id: uuid.UUID
    priority: str
    deadline_at: Optional[datetime] = None