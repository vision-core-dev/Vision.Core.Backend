import uuid
from fastapi import HTTPException
from pydantic import EmailStr
from sqlalchemy import select, any_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.Objects.BadgeModel import UserBadge, Badge, UserBadgeBase
from app.Objects.UserModel import User, UserRole, UserPreview
from app.Objects.finance.TransactionModel import Transaction
from app.Objects.tasks.TaskModel import Task, TaskStatus
from app.Services.Hub.AuthService import AuthService, get_hashed_password
from app.Services.Hub.UserService.contracts import (
    UsersListResponse,
    UsersPublicListResponse,
    UserDetailsResponse,
    CreateUserRequest,
    CreateUserResponse,
    ActivateUserResponse,
    DeactivateUserResponse,
    UserTaskPreview
)


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def CreateUser(self, email: str | EmailStr, password: str, first_name: str, role_id: uuid.UUID | None =None) -> CreateUserResponse:
        result = await AuthService(self.db).RegisterUser(email, password, first_name, role_id=role_id)
        return CreateUserResponse(user_id=result.user_id)

    async def GetUsersList(self, only_active: bool = False) -> UsersListResponse:
        from app.Objects.tasks.BoardModel import Board

        stmt = await self.db.execute(
            select(User).where(User.is_active == only_active if only_active else True).options(selectinload(User.role))
        )
        users = stmt.scalars().all()

        # Load all boards once to map user -> board names
        boards_result = await self.db.execute(
            select(Board).where(Board.is_removed == False)
        )
        all_boards = boards_result.scalars().all()

        user_boards: dict[str, list[str]] = {}
        for b in all_boards:
            members = b.members or {}
            for uid in list(members.keys()) + ([str(b.created_by_id)] if b.created_by_id else []):
                if uid not in user_boards:
                    user_boards[uid] = []
                if b.name not in user_boards[uid]:
                    user_boards[uid].append(b.name)

        previews = []
        for u in users:
            preview = UserPreview.model_validate(u)
            preview.board_names = user_boards.get(str(u.id), [])
            previews.append(preview)

        return UsersListResponse(total=len(previews), list=previews)

    async def GetPublicUsersList(self) -> UsersPublicListResponse:
        stmt = await self.db.execute(
            select(User).where(User.is_active == True)
        )
        result = stmt.scalars().all()
        return UsersPublicListResponse(total=len(result), list=result)

    async def GetUserDetails(self, user_id: uuid.UUID, actor: User) -> UserDetailsResponse:
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="user_not_found")

        actor_role = await self.db.get(UserRole, actor.role_id)
        target_role = await self.db.get(UserRole, user.role_id)

        actions = []
        if actor_role.order < target_role.order:
            actions.append("change_role")
            actions.append("change_org_structure")
            if user.is_active:
                actions.append("deactivate_user")
            else:
                actions.append("activate_user")
        if actor_role.order <= 2:
            actions.append("give_badge")
            actions.append("remove_badge")

        # 🧑‍💼 Керівники
        supervisors = []
        if user.supervisor_ids:
            q = await self.db.execute(
                select(User).where(User.id.in_(user.supervisor_ids)).options(selectinload(User.role))
            )
            supervisors = q.scalars().all()

        # 👨‍💻 Підлеглі
        q2 = await self.db.execute(
            select(User)
            .where(user.id == any_(User.supervisor_ids))
            .options(selectinload(User.role))
        )
        subordinates = q2.scalars().all()

        # 🏅 Бейджі користувача (інтегровано тут)
        badge_stmt = (
            select(UserBadge)
            .where(UserBadge.user_id == user.id)
            .options(joinedload(UserBadge.badge))  # ✅ тепер це працює
        )

        badge_result = await self.db.execute(badge_stmt)
        user_badges = badge_result.scalars().all()

        badges = [
            UserBadgeBase(
                id=ub.badge.id,
                name=ub.badge.name,
                description=ub.badge.description,
                icon_url=ub.badge.icon_url,
                emoji=ub.badge.emoji,
                awarded_at=ub.awarded_at
            )
            for ub in user_badges
        ]

        transactions_result = await self.db.execute(
            select(Transaction).where(Transaction.user_id == user.id, Transaction.is_removed == False)
        )
        transactions = transactions_result.scalars().all()

        # 📝 Задачі користувача
        tasks_stmt = (
            select(Task)
            .where(Task.assignee_ids.any(user_id))
            .where(Task.is_archived == False)
            .where(Task.is_removed == False)
            .options(selectinload(Task.list))
            .order_by(Task.deadline_at.asc())
        )
        tasks_result = await self.db.execute(tasks_stmt)
        user_tasks = tasks_result.scalars().all()
        
        tasks_list = [
            UserTaskPreview(
                id=t.id,
                name=t.name,
                status=t.status.value if hasattr(t.status, "value") else str(t.status),
                deadline_at=t.deadline_at,
                board_id=t.board_id,
                list_name=t.list.name if t.list else None
            )
            for t in user_tasks
        ]

        # 📊 Статистика
        # 1. Загальна кількість виконаних задач (включаючи архівовані)
        completed_count_stmt = (
            select(func.count(Task.id))
            .where(Task.assignee_ids.any(user_id))
            .where(Task.status == TaskStatus.done)
            .where(Task.is_removed == False)
        )
        completed_count = (await self.db.execute(completed_count_stmt)).scalar_one()

        # 2. Активні задачі (з тих, що ми вже завантажили - не архівовані, не видалені)
        # Активні = не 'done' і не 'backlog' (опціонально, але зазвичай активні це в роботі)
        # Або просто всі, що не 'done', бо backlog теж може бути активним
        # Якщо брати просто tasks_list, то там відфільтровані is_archived=False
        # Тому просто рахуємо скільки з них не done
        active_count = sum(1 for t in user_tasks if t.status != TaskStatus.done)

        return UserDetailsResponse(
            user=user,
            actions=actions,
            supervisors=supervisors,
            subordinates=subordinates,
            badges=badges,
            transactions=transactions,
            tasks=tasks_list,
            tasks_total_completed=completed_count,
            tasks_total_active=active_count
        )

    async def ChangeUserRole(self, user_id: uuid.UUID, new_role_id: uuid.UUID, actor: User) -> UserDetailsResponse:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="user_not_found")

        actor_role = await self.db.get(UserRole, actor.role_id)
        target_role = await self.db.get(UserRole, user.role_id)
        new_role = await self.db.get(UserRole, new_role_id)

        if not new_role:
            raise HTTPException(status_code=404, detail="role_not_found")

        if actor_role.order < target_role.order and actor_role.order < new_role.order:
            user.role_id = str(new_role.id)
            await self.db.commit()
            await self.db.refresh(user)
            return await self.GetUserDetails(user_id, actor)
        else:
            raise HTTPException(status_code=403, detail="insufficient_permissions")

    async def DeactivateUser(self, user_id: uuid.UUID, actor: User) -> DeactivateUserResponse:
        result = await self.db.execute(select(User).options(selectinload(User.role)).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="user_not_found")

        actor_role = await self.db.get(UserRole, actor.role_id)

        if user.role.order < actor_role.order:
            raise HTTPException(status_code=403, detail="insufficient_permissions")

        user.is_active = False
        await self.db.commit()

        return DeactivateUserResponse(user_id=user.id)

    async def ActivateUser(self, user_id: uuid.UUID, actor: User) -> ActivateUserResponse:
        result = await self.db.execute(select(User).options(selectinload(User.role)).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="user_not_found")

        actor_role = await self.db.get(UserRole, actor.role_id)

        if user.role.order < actor_role.order:
            raise HTTPException(status_code=403, detail="insufficient_permissions")

        user.is_active = True
        await self.db.commit()

        return ActivateUserResponse(user_id=user.id)

    async def AddSupervisor(self, user_id: uuid.UUID, supervisor_id: uuid.UUID, actor: User):
        user = await self.db.get(User, user_id)
        supervisor = await self.db.get(User, supervisor_id)
        if not user or not supervisor:
            raise HTTPException(status_code=404, detail="user_not_found")

        if supervisor_id not in (user.supervisor_ids or []):
            user.supervisor_ids = (user.supervisor_ids or []) + [supervisor_id]
            await self.db.commit()
        return await self.GetUserDetails(user_id, actor)

    async def RemoveSupervisor(self, user_id: uuid.UUID, supervisor_id: uuid.UUID, actor: User):
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="user_not_found")

        user.supervisor_ids = [sid for sid in (user.supervisor_ids or []) if sid != supervisor_id]
        await self.db.commit()
        return await self.GetUserDetails(user_id, actor)

    async def AddSubordinate(self, user_id: uuid.UUID, subordinate_id: uuid.UUID, actor: User):
        subordinate = await self.db.get(User, subordinate_id)
        if not subordinate:
            raise HTTPException(status_code=404, detail="user_not_found")

        subordinate.supervisor_ids = (subordinate.supervisor_ids or []) + [user_id]
        await self.db.commit()
        return await self.GetUserDetails(user_id, actor)

    async def RemoveSubordinate(self, user_id: uuid.UUID, subordinate_id: uuid.UUID, actor: User):
        subordinate = await self.db.get(User, subordinate_id)
        if not subordinate:
            raise HTTPException(status_code=404, detail="user_not_found")

        subordinate.supervisor_ids = [sid for sid in (subordinate.supervisor_ids or []) if sid != user_id]
        await self.db.commit()
        return await self.GetUserDetails(user_id, actor)

    async def ChangeUserPassword(self, user_id: uuid.UUID, new_password: str, actor: User):
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="user_not_found")

        actor_role = await self.db.get(UserRole, actor.role_id)
        target_role = await self.db.get(UserRole, user.role_id)

        if actor.id != user_id:
            if target_role.order < actor_role.order:
                raise HTTPException(status_code=403, detail="insufficient_permissions")

        if len(new_password) < 8:
            raise HTTPException(status_code=400, detail="password_too_short")

        hashed_password = get_hashed_password(new_password)
        user.hashed_password = hashed_password
        user.temp_token = uuid.uuid4()
        await self.db.commit()

        return {"user_id": user.id, "new_password": new_password}