import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.Infrastructure.Database import getdb
from app.Objects.EventModel import EventInviteStatus
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser
from app.Services.Hub.EventService import EventService
from app.Services.Hub.EventService.contracts import CreateEventRequest, CreateEventResponse, ListEventsResponse, \
    PublicEventDetailsResponse, ModerateEventDetailsResponse, ChangeEventStatusResponse

events_router = APIRouter(prefix="/Events", tags=["Hub > Events"])

@events_router.get("/List", response_model=ListEventsResponse)
async def list_events(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await EventService(db).GetEventsList()

@events_router.post("/Create", response_model=CreateEventResponse)
async def create_event(data: CreateEventRequest, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await EventService(db).CreateEvent(data)

@events_router.get("/{event_id}/GetPublicDetails", response_model=PublicEventDetailsResponse)
async def get_event_public_details(
    event_id: str,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await EventService(db).GetEventPublicDetails(event_id, user)

@events_router.get("/{event_id}/GetModerateDetails", response_model=ModerateEventDetailsResponse)
async def get_event_moderate_details(event_id: str, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    return await EventService(db).GetEventModerateDetails(event_id, user)

@events_router.post("/{event_id}/AcceptInvite", response_model=ChangeEventStatusResponse)
async def accept_event_invite(
    event_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await EventService(db).ChangeEventInviteStatus(event_id, user, EventInviteStatus.ACCEPTED)

@events_router.post("/{event_id}/DeclineInvite", response_model=ChangeEventStatusResponse)
async def decline_event_invite(
    event_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await EventService(db).ChangeEventInviteStatus(event_id, user, EventInviteStatus.DECLINED)



@events_router.post("/{event_id}/MarkAttended", response_model=ChangeEventStatusResponse)
async def mark_event_attended(
    event_id: uuid.UUID,
    user_id: uuid.UUID = Query(..., description="ID користувача, якого відмічаємо"),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await EventService(db).MarkAttendance(event_id, user_id, True)


@events_router.post("/{event_id}/MarkAbsent", response_model=ChangeEventStatusResponse)
async def mark_event_absent(
    event_id: uuid.UUID,
    user_id: uuid.UUID = Query(..., description="ID користувача, якого відмічаємо"),
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb)
):
    return await EventService(db).MarkAttendance(event_id, user_id, False)
