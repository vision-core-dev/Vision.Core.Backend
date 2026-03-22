import uuid
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.orm.attributes import flag_modified

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
            created_by_id=user.id,
            members={str(user.id): "admin"}
        )
        self.db.add(new_board)
        await self.db.commit()
        await self.db.refresh(new_board)
        return CreateBoardResponse(board_id=new_board.id)

    async def GetBoardsList(self, actor: User) -> BoardsListResponse:
        result = await self.db.execute(
            select(Board).where(Board.is_removed == False)
        )
        boards = result.scalars().all()

        # 🧠 Фільтруємо дошки, де користувач є учасником або власником
        visible_boards = []
        for b in boards:
            members = b.members or {}
            if str(actor.id) in members or str(actor.id) == str(b.created_by_id):
                visible_boards.append(b)

        previews = [
            {
                "id": b.id,
                "name": b.name,
                "description": b.description,
                "banner_url": b.banner_url,
                "created_at": b.created_at,
            }
            for b in visible_boards
        ]

        return BoardsListResponse(total=len(previews), list=previews)


    async def GetBoardDetails(self, board_id, user: User) -> BoardDetailsResponse:
        # 🟩 1. Отримуємо саму дошку
        board_result = await self.db.execute(select(Board).where(Board.id == board_id))
        board = board_result.scalar_one_or_none()
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        # 🟩 2. Отримуємо учасників (many-to-many)
        users_query = (select(User))
        users_result = await self.db.execute(users_query)
        users = users_result.scalars().all()

        # 🟩 3. Отримуємо списки (колонки)
        lists_result = await self.db.execute(
            select(BoardList).where(BoardList.board_id == board_id).order_by(BoardList.order)
        )
        lists = lists_result.scalars().all()

        # 🟩 4. Отримуємо задачі разом з subtasks та accruals
        tasks_result = await self.db.execute(
            select(Task)
            .options(joinedload(Task.subtasks), joinedload(Task.accruals))
            .where(
                Task.board_id == board_id,
                or_(Task.is_archived.is_(False), Task.is_archived.is_(None)),
                or_(Task.is_removed.is_(False), Task.is_removed.is_(None))
            ).order_by(Task.order)
        )
        tasks = tasks_result.scalars().unique().all()

        # 🟩 5. Отримуємо всі теги задач
        tags_result = await self.db.execute(select(TaskTag).where(TaskTag.board_id == board_id))
        tags = tags_result.scalars().all()

        # 🟩 6. Формуємо відповідь
        return BoardDetailsResponse(
            board=board,
            users=[
                UserPreview(
                    id=u.id,
                    first_name=u.first_name,
                    last_name=u.last_name,
                    avatar_url=u.avatar_url,
                    is_active=u.is_active,
                )
                for u in users
            ],
            lists=lists,
            tasks=[
                TaskPreview(
                    id=t.id,
                    name=t.name,
                    banner_url=t.banner_url,
                    list_id=t.list_id,
                    tags=t.tags or [],
                    status=t.status,
                    priority=t.priority,
                    started_at=t.started_at,
                    deadline_at=t.deadline_at,
                    assignees=t.assignee_ids or [],
                    subtasks_total=len(t.subtasks) if t.subtasks else 0,
                    subtasks_completed=sum(1 for s in t.subtasks if s.status == "completed"),
                    has_description=bool(t.description and t.description.strip()),
                    accruals_count=len([a for a in (t.accruals or []) if not a.is_removed]),
                    accruals_sum=sum(a.amount for a in (t.accruals or []) if not a.is_removed),
                    created_at=t.created_at,
                    completed_at=t.completed_at,
                )
                for t in tasks
            ],
            tags=tags
        )

    async def GetPublicBoardDetails(self, board_id: uuid.UUID):
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        if not board.is_public:
            raise HTTPException(status_code=403, detail="board_is_not_public")

        lists_result = await self.db.execute(
            select(BoardList).where(BoardList.board_id == board_id).order_by(BoardList.order)
        )
        lists = lists_result.scalars().all()

        tasks_result = await self.db.execute(
            select(Task)
            .options(joinedload(Task.subtasks), joinedload(Task.accruals))
            .where(
                Task.board_id == board_id,
                or_(Task.is_archived.is_(False), Task.is_archived.is_(None)),
                or_(Task.is_removed.is_(False), Task.is_removed.is_(None))
            )
            .order_by(Task.order)
        )
        tasks = tasks_result.scalars().unique().all()

        tags_result = await self.db.execute(select(TaskTag).where(TaskTag.board_id == board_id))
        tags = tags_result.scalars().all()

        return BoardDetailsResponse(
            board=board,
            users=[],
            lists=lists,
            tasks=[
                TaskPreview(
                    id=t.id,
                    name=t.name,
                    banner_url=t.banner_url,
                    list_id=t.list_id,
                    tags=t.tags or [],
                    status=t.status,
                    priority=t.priority,
                    started_at=t.started_at,
                    deadline_at=t.deadline_at,
                    assignees=t.assignee_ids or [],
                    subtasks_total=len(t.subtasks) if t.subtasks else 0,
                    subtasks_completed=sum(1 for s in t.subtasks if s.status == "completed"),
                    has_description=bool(t.description and t.description.strip()),
                    accruals_count=len([a for a in (t.accruals or []) if not a.is_removed]),
                    accruals_sum=sum(a.amount for a in (t.accruals or []) if not a.is_removed),
                )
                for t in tasks
            ],
            tags=tags
        )

    async def CreateTag(self, board_id: uuid.UUID, name: str, color: str, actor: User):
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        await self._check_board_admin(board, actor)

        new_tag = TaskTag(
            name=name,
            color=color,
            board_id=board_id  # 👈 додай це поле в модель TaskTag, якщо ще нема
        )
        self.db.add(new_tag)
        await self.db.commit()
        await self.db.refresh(new_tag)
        
        # 🔔 WebSocket сповіщення
        await self._notify_board_update(board_id, "tag_created", {
            "tag_id": str(new_tag.id),
            "name": new_tag.name,
            "color": new_tag.color,
        })
        
        return {"ok": True, "id": new_tag.id}

    async def RemoveTag(self, board_id: uuid.UUID, tag_id: uuid.UUID, actor: User):
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        await self._check_board_admin(board, actor)

        tag = await self.db.get(TaskTag, tag_id)
        if not tag or getattr(tag, "board_id", None) != board_id:
            raise HTTPException(status_code=404, detail="tag_not_found")
        
        # Зберігаємо дані перед видаленням
        tag_name = tag.name
        
        await self.db.delete(tag)
        await self.db.commit()
        
        # 🔔 WebSocket сповіщення
        await self._notify_board_update(board_id, "tag_removed", {
            "tag_id": str(tag_id),
            "tag_name": tag_name,
        })
        
        return {"ok": True}


    async def CreateList(self, board_id: uuid.UUID, name: str, color: str, actor: User):
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        await self._check_board_admin(board, actor)

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
        
        # 🔔 WebSocket сповіщення
        await self._notify_board_update(board_id, "list_created", {
            "list_id": str(new_list.id),
            "name": new_list.name,
            "color": new_list.color,
            "order": new_list.order,
        })
        
        return {"ok": True, "id": new_list.id}

    async def UpdateList(
            self,
            board_id: uuid.UUID,
            list_id: uuid.UUID,
            name: Optional[str],
            color: Optional[str],
            actor: User
    ):
        # 1. Перевіряємо дошку
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        await self._check_board_admin(board, actor)

        # 2. Отримуємо список
        lst = await self.db.get(BoardList, list_id)
        if not lst or lst.board_id != board_id:
            raise HTTPException(status_code=404, detail="list_not_found")

        # Зберігаємо старі значення для сповіщення
        old_name = lst.name
        old_color = lst.color
        changed_fields = []

        # 3. Апдейт полів (partial update)
        if name is not None:
            lst.name = name.strip()
            if old_name != lst.name:
                changed_fields.append("name")

        if color is not None:
            lst.color = color
            if old_color != lst.color:
                changed_fields.append("color")

        # 4. Commit
        await self.db.commit()
        await self.db.refresh(lst)
        
        # 🔔 WebSocket сповіщення
        if changed_fields:
            await self._notify_board_update(board_id, "list_updated", {
                "list_id": str(lst.id),
                "name": lst.name,
                "color": lst.color,
                "changed_fields": changed_fields,
            })

        return {
            "ok": True,
            "id": lst.id,
            "name": lst.name,
            "color": lst.color,
            "order": lst.order,
        }

    async def RemoveList(self, board_id: uuid.UUID, list_id: uuid.UUID, actor: User):
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        await self._check_board_admin(board, actor)

        lst = await self.db.get(BoardList, list_id)
        if not lst or lst.board_id != board_id:
            raise HTTPException(status_code=404, detail="list_not_found")
        
        # Зберігаємо дані перед видаленням
        list_name = lst.name
        
        await self.db.delete(lst)
        await self.db.commit()
        
        # 🔔 WebSocket сповіщення
        await self._notify_board_update(board_id, "list_removed", {
            "list_id": str(list_id),
            "list_name": list_name,
        })
        
        return {"ok": True}

    async def SetBoardBanner(self, board_id: uuid.UUID, banner_url: str, actor: User):
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        await self._check_board_admin(board, actor)

        # Оновлюємо банер
        board.banner_url = banner_url
        await self.db.commit()
        await self.db.refresh(board)

        return {"ok": True, "banner_url": board.banner_url}

    async def UploadBannerFile(self, board_id: uuid.UUID, file: UploadFile, actor: User) -> str:
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        await self._check_board_admin(board, actor)

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

    async def _check_board_admin(self, board: Board, actor: User):
        """✅ Перевіряє, чи actor є адміном на дошці."""
        # if not board.members:
        #     raise HTTPException(status_code=404, detail="no_members_defined")
        membs = board.members or {}

        role = membs.get(str(actor.id))
        if role != "admin" and str(actor.id) != str(board.created_by_id):
            raise HTTPException(
                status_code=403,
                detail="permission_denied_not_admin"
            )
    
    async def _notify_board_update(self, board_id: uuid.UUID, action: str, data: dict = None):
        """🔔 Відправляє WebSocket сповіщення про зміни на дошці"""
        try:
            from app.API.HUB.Boards.websocket import notify_board_update
            await notify_board_update(board_id, action, data)
        except Exception as e:
            # Не блокуємо основну операцію, якщо WebSocket не працює
            print(f"⚠️ WebSocket notification failed: {e}")

    async def AddBoardMember(self, board_id: uuid.UUID, user_id: uuid.UUID, actor: User, role: str = "member"):
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        # 🧠 Перевірка прав
        await self._check_board_admin(board, actor)

        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="user_not_found")

        print(board.members, user_id, role)

        new_members = board.members or {}

        if str(user_id) in new_members:
            raise HTTPException(status_code=400, detail="member_already_exists")

        new_members[str(user_id)] = role
        board.members = new_members
        flag_modified(board, "members")

        await self.db.commit()
        await self.db.refresh(board)
        return {"ok": True, "role": role}

    async def RemoveBoardMember(self, board_id: uuid.UUID, user_id: uuid.UUID, actor: User):
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        # 🧠 Перевірка прав
        await self._check_board_admin(board, actor)

        new_members = board.members or {}
        if str(user_id) in new_members:
            del new_members[str(user_id)]
            board.members = new_members
            flag_modified(board, "members")

            await self.db.commit()
            await self.db.refresh(board)

        return {"ok": True}

    async def ChangeMemberRole(self, board_id: uuid.UUID, user_id: uuid.UUID, new_role: str, actor: User):
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")

        # 🧠 Перевірка прав
        await self._check_board_admin(board, actor)

        new_members = board.members or {}
        if str(user_id) not in new_members:
            raise HTTPException(status_code=404, detail="member_not_found")

        new_members[str(user_id)] = new_role
        board.members = new_members
        flag_modified(board, "members")

        await self.db.commit()
        await self.db.refresh(board)
        return {"ok": True, "role": new_role}

    async def UpdateBoardName(self, board_id: uuid.UUID, new_name: str, actor: User):
        board = await self.db.get(Board, board_id)
        if not board:
            raise HTTPException(status_code=404, detail="board_not_found")
        await self._check_board_admin(board, actor)
        
        # Зберігаємо стару назву
        old_name = board.name
        
        board.name = new_name
        await self.db.commit()
        await self.db.refresh(board)
        
        # 🔔 WebSocket сповіщення
        await self._notify_board_update(board_id, "board_renamed", {
            "old_name": old_name,
            "new_name": new_name,
        })
        
        return {"ok": True, "name": board.name}