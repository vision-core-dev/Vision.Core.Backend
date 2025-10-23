import uuid
from datetime import datetime

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.Infrastructure.Storage import _upload_to_bunny, _delete_from_bunny
from app.Objects.UserModel import User, UserPreview
from app.Objects.tasks.BoardListModel import BoardList
from app.Objects.tasks.BoardModel import Board
from app.Objects.tasks.TaskModel import Task, TaskPreview
from app.Objects.tasks.TaskTags import TaskTag
from app.Services.Hub.BoardService.contracts import CreateBoardResponse, BoardsListResponse, BoardDetailsResponse


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
        boards = result.scalars().all()

        previews = [
            {
                "id": b.id,
                "name": b.name,
                "description": b.description,
                "created_at": b.created_at,
            }
            for b in boards
        ]

        return BoardsListResponse(total=len(boards), list=previews)


    async def GetBoardDetails(self, board_id, user: User) -> BoardDetailsResponse:
        # 🟩 1. Отримуємо саму дошку
        board_result = await self.db.execute(select(Board).where(Board.id == board_id))
        board = board_result.scalar_one_or_none()
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        # 🟩 2. Отримуємо учасників (many-to-many)
        members_query = (
            select(User)
            .join(Board.members)  # 👈 правильно
            .where(Board.id == board_id)
        )
        members_result = await self.db.execute(members_query)
        members = members_result.scalars().all()

        # 🟩 3. Отримуємо списки (колонки)
        lists_result = await self.db.execute(
            select(BoardList).where(BoardList.board_id == board_id).order_by(BoardList.order)
        )
        lists = lists_result.scalars().all()

        # 🟩 4. Отримуємо задачі разом з assignees
        tasks_result = await self.db.execute(
            select(Task)
            .where(Task.board_id == board_id)
            .order_by(Task.order)
        )
        tasks = tasks_result.scalars().unique().all()

        # 🟩 5. Отримуємо всі теги задач
        tags_result = await self.db.execute(select(TaskTag).where(TaskTag.board_id == board_id))
        tags = tags_result.scalars().all()

        # 🟩 6. Формуємо відповідь
        return BoardDetailsResponse(
            board=board,
            members=[
                UserPreview(
                    id=m.id,
                    first_name=m.first_name,
                    last_name=m.last_name,
                    avatar_url=m.avatar_url,
                    role_name=getattr(m.role, "name", None)
                )
                for m in members
            ],
            lists=lists,
            tasks=[
                TaskPreview(
                    id=t.id,
                    name=t.name,
                    list_id=t.list_id,
                    tags=t.tags or [],
                    status=t.status,
                    priority=t.priority,
                    deadline_at=t.deadline_at,
                    assignees=t.assignee_ids or []
                )
                for t in tasks
            ],
            tags=tags
        )

    async def CreateTag(self, board_id: uuid.UUID, name: str, color: str):
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        new_tag = TaskTag(
            name=name,
            color=color,
            board_id=board_id  # 👈 додай це поле в модель TaskTag, якщо ще нема
        )
        self.db.add(new_tag)
        await self.db.commit()
        await self.db.refresh(new_tag)
        return {"ok": True, "id": new_tag.id}

    async def RemoveTag(self, board_id: uuid.UUID, tag_id: uuid.UUID):
        tag = await self.db.get(TaskTag, tag_id)
        if not tag or getattr(tag, "board_id", None) != board_id:
            raise HTTPException(status_code=404, detail="tag_not_found")
        await self.db.delete(tag)
        await self.db.commit()
        return {"ok": True}

        # --- Списки ---

    async def CreateList(self, board_id: uuid.UUID, name: str, color: str):
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        max_order_query = await self.db.execute(
            select(BoardList.order).where(BoardList.board_id == board_id)
        )
        max_order = max([o for o, in max_order_query] or [0]) + 1

        new_list = BoardList(
            board_id=board_id,
            name=name,
            color=color,
            order=max_order
        )
        self.db.add(new_list)
        await self.db.commit()
        await self.db.refresh(new_list)
        return {"ok": True, "id": new_list.id}

    async def RemoveList(self, board_id: uuid.UUID, list_id: uuid.UUID):
        lst = await self.db.get(BoardList, list_id)
        if not lst or lst.board_id != board_id:
            raise HTTPException(status_code=404, detail="list_not_found")
        await self.db.delete(lst)
        await self.db.commit()
        return {"ok": True}

    async def SetBoardBanner(self, board_id: uuid.UUID, banner_url: str, user: User):
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        # Оновлюємо банер
        board.banner_url = banner_url
        await self.db.commit()
        await self.db.refresh(board)

        return {"ok": True, "banner_url": board.banner_url}

    async def UploadBannerFile(self, board_id: uuid.UUID, file: UploadFile, user: User) -> str:
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        # читаємо файл із UploadFile
        contents = await file.read()
        filename = f"boards/{board_id}/{uuid.uuid4()}_{file.filename}"

        # викликаємо Bunny upload
        banner_url = await _upload_to_bunny(filename, contents, file.content_type)

        if board.banner_url:
            path = board.banner_url.split("/", 3)[-1]
            try:
                await _delete_from_bunny(path)
            except Exception:
                pass  # ігноруємо помилки видалення старого банера

        # оновлюємо дошку
        board.banner_url = banner_url
        await self.db.commit()
        await self.db.refresh(board)

        return banner_url

    async def CreateTask(
        self,
        board_id: uuid.UUID,
        list_id: uuid.UUID,
        name: str,
        description: str | None,
        assignee_ids: list[uuid.UUID] | None,
        priority: str | None,
        deadline_at: datetime | None,
        value_uah: float | None,
        created_by: User
    ):
        # ✅ Перевірка дошки
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        # ✅ Перевірка списку
        lst = await self.db.get(BoardList, list_id)
        if not lst or lst.board_id != board_id:
            raise HTTPException(status_code=404, detail="list_not_found")

        # ✅ Визначення порядку (останній +1)
        order_query = await self.db.execute(
            select(Task.order)
            .where(Task.list_id == list_id)
            .order_by(Task.order.desc())
            .limit(1)
        )
        last_order = order_query.scalar()
        new_order = (last_order or 0) + 1

        # ✅ Створюємо задачу
        task = Task(
            board_id=board_id,
            list_id=list_id,
            name=name,
            description=description,
            created_by_id=created_by.id,
            priority=priority or "low",
            deadline_at=deadline_at,
            order=new_order,
            value_uah=value_uah or 0.0,
            assignee_ids=assignee_ids or []
        )

        self.db.add(task)
        await self.db.flush()  # потрібно, щоб отримати ID

        await self.db.commit()
        await self.db.refresh(task)

        return {
            "ok": True,
            "id": task.id,
            "name": task.name,
            "list_id": task.list_id,
            "priority": task.priority,
            "deadline_at": task.deadline_at,
        }