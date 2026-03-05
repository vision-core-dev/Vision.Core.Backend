import uuid

from pydantic import BaseModel
import datetime

from app.Objects.EventModel import EventBase, EventInviteBase, EventInviteStatus, EventInviteWithUser


class CreateEventRequest(BaseModel):
    name: str
    description: str | None = None
    date: datetime.date
    time_from: datetime.time
    time_to: datetime.time
    location: str | None = None
    location_url: str | None = None
    invitees: list[uuid.UUID] = []

class CreateEventResponse(BaseModel):
    event_id: str

class ListEventsResponse(BaseModel):
    total: int
    list: list[EventBase]

class ModerateEventDetailsResponse(BaseModel):
    event: EventBase
    invitees: list[EventInviteWithUser]
    actions: list[str] = []

    class Config:
        from_attributes = True

class PublicEventDetailsResponse(BaseModel):
    event: EventBase
    invite: EventInviteBase | None = None
    actions: list[str] = []

    class Config:
        from_attributes = True

class ChangeEventStatusResponse(BaseModel):
    event_id: uuid.UUID
    status: str

class UpdateEventRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    date: datetime.date | None = None
    time_from: datetime.time | None = None
    time_to: datetime.time | None = None
    location: str | None = None
    location_url: str | None = None

class AddInviteesRequest(BaseModel):
    user_ids: list[uuid.UUID]

class GenericSuccessResponse(BaseModel):
    success: bool = True