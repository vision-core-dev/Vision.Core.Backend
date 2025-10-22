import uuid
from datetime import datetime

import pytz
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Objects.EventModel import Event, EventInvite, EventInviteStatus, EventPreview
from app.Objects.UserModel import User
from app.Services.Hub.EventService.contracts import CreateEventRequest, CreateEventResponse, ListEventsResponse, \
    PublicEventDetailsResponse, ModerateEventDetailsResponse, ChangeEventStatusResponse
from app.Services.Hub.NotifyService import NotifyService


class EventService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def GetEventsList(self):
        result = await self.db.execute(
            select(Event)
        )
        events = result.scalars().all()
        return ListEventsResponse(total=len(events), list=events)

    async def GetUserEventsList(self, user: User) -> list[EventPreview]:
        result = await self.db.execute(
            select(Event).join(EventInvite).where(EventInvite.user_id == user.id)
        )
        events = result.scalars().all()
        return [
            EventPreview(
                id=event.id,
                name=event.name,
                date=event.date,
                time_from=event.time_from,
                time_to=event.time_to,
            ) for event in events
        ]

    async def CreateEvent(self, data: CreateEventRequest) -> CreateEventResponse:
        new_event = Event(
            id=uuid.uuid4(),
            name=data.name,
            description=data.description,
            date=data.date,
            time_from=data.time_from,
            time_to=data.time_to,
            location=data.location
        )
        self.db.add(new_event)
        await self.db.commit()
        await self.db.refresh(new_event)

        date_str = new_event.date.strftime("%d.%m.%Y")
        time_from_str = new_event.time_from.strftime("%H:%M")
        time_to_str = new_event.time_to.strftime("%H:%M")

        for user_id in data.invitees:
            new_invite = EventInvite(
                event_id=new_event.id,
                user_id=user_id,
                status="pending"
            )
            self.db.add(new_invite)

            await NotifyService(self.db).CreateNotification(
                user_id,
                "Запрошення на подію",
                f"Вас запрошено на подію <b>{new_event.name}</b> 🗓️ {date_str} 🕐 {time_from_str}–{time_to_str} у {new_event.location}.",
                link=f"/calendar/e/{new_event.id}"
            )

        await self.db.commit()

        return CreateEventResponse(event_id=str(new_event.id))

    async def GetEventPublicDetails(self, event_id: uuid.UUID, user: User) -> PublicEventDetailsResponse:
        try:
            event_uuid = uuid.UUID(str(event_id))
            user_uuid = uuid.UUID(str(user.id))
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid_uuid")

        event_result = await self.db.execute(
            select(Event).where(Event.id == event_uuid)
        )
        event = event_result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="event_not_found")

        invite_result = await self.db.execute(
            select(EventInvite).where(
                EventInvite.event_id == event_uuid,
                EventInvite.user_id == user_uuid
            )
        )
        invite = invite_result.scalar_one_or_none()

        if not invite:
            raise HTTPException(status_code=403, detail="invite_not_found")

        actions = []
        if invite.status == "pending":
            actions = ["accept", "decline"]
        elif invite.status == "accepted":
            actions = ["decline"]
        elif invite.status == "declined":
            actions = ["accept"]

        if invite.status == "accepted":
            actions.append("join")

        return PublicEventDetailsResponse(
            event=event,
            invite=invite,
            actions=actions
        )

    async def GetEventModerateDetails(self, event_id: str, user: User) -> ModerateEventDetailsResponse:
        event_result = await self.db.execute(
            select(Event).where(Event.id == uuid.UUID(event_id))
        )
        event = event_result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="event_not_found")

        # 👇 JOIN з таблицею користувачів
        invitees_query = (
            select(
                EventInvite,
                User.id.label("user_id"),
                User.first_name,
                User.last_name,
                User.avatar_url,
            )
            .join(User, User.id == EventInvite.user_id)
            .where(EventInvite.event_id == uuid.UUID(event_id))
        )

        invitees_result = await self.db.execute(invitees_query)
        invitees = [
            {
                "id": inv.EventInvite.id,
                "event_id": inv.EventInvite.event_id,
                "user_id": inv.user_id,
                "status": inv.EventInvite.status,
                "reason": inv.EventInvite.reason,
                "responded_at": inv.EventInvite.responded_at,
                "attended_at": inv.EventInvite.attended_at,
                "created_at": inv.EventInvite.created_at,
                "user": {
                    "id": inv.user_id,
                    "first_name": inv.first_name,
                    "last_name": inv.last_name,
                    "avatar_url": inv.avatar_url,
                },
            }
            for inv in invitees_result.mappings()
        ]

        return ModerateEventDetailsResponse(
            event=event,
            invitees=invitees,
            actions=["edit", "cancel", "remove", "mark_attended", "mark_absent"]
        )

    async def ChangeEventInviteStatus(self, event_id: uuid.UUID, user: User, new_status: EventInviteStatus) -> ChangeEventStatusResponse:
        try:
            event_uuid = uuid.UUID(str(event_id))
            user_uuid = uuid.UUID(str(user.id))
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid_uuid")

        event_result = await self.db.execute(
            select(Event).where(Event.id == event_uuid)
        )
        event = event_result.scalar_one_or_none()
        if not event:
            raise HTTPException(status_code=404, detail="event_not_found")

        invite_result = await self.db.execute(
            select(EventInvite).where(
                EventInvite.event_id == event_uuid,
                EventInvite.user_id == user_uuid
            )
        )
        invite = invite_result.scalar_one_or_none()
        if not invite:
            raise HTTPException(status_code=403, detail="invite_not_found")

        kyiv_tz = pytz.timezone("Europe/Kyiv")

        invite.status = new_status.value
        invite.responded_at = datetime.now(kyiv_tz)

        await self.db.commit()
        await self.db.refresh(invite)

        return ChangeEventStatusResponse(
            event_id=event.id,
            status=new_status.value
        )

    async def MarkAttendance(self, event_id: uuid.UUID, target_user_id: uuid.UUID,
                             attended: bool) -> ChangeEventStatusResponse:
        try:
            event_uuid = uuid.UUID(str(event_id))
            user_uuid = uuid.UUID(str(target_user_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid_uuid")

        # 🧩 Отримуємо запрошення
        invite_result = await self.db.execute(
            select(EventInvite).where(
                EventInvite.event_id == event_uuid,
                EventInvite.user_id == user_uuid
            )
        )
        invite = invite_result.scalar_one_or_none()
        if not invite:
            raise HTTPException(status_code=404, detail="invite_not_found")

        # 🇺🇦 Київський час
        kyiv_tz = pytz.timezone("Europe/Kyiv")
        now_kyiv = datetime.now(kyiv_tz)

        # 🧠 Оновлюємо статус
        if attended:
            invite.status = EventInviteStatus.ATTENDED.value
            invite.attended_at = now_kyiv
        else:
            invite.status = EventInviteStatus.NO_SHOW.value
            invite.responded_at = now_kyiv

        await self.db.commit()
        await self.db.refresh(invite)

        return ChangeEventStatusResponse(
            event_id=str(event_uuid),
            status=invite.status
        )