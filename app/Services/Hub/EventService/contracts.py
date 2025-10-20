import uuid

from pydantic import BaseModel
from datetime import date, time

from app.Objects.EventModel import EventBase, EventInviteBase, EventInviteStatus


class CreateEventRequest(BaseModel):
    name: str
    description: str | None = None
    date: date
    time_from: time
    time_to: time
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
    invitees: list[EventInviteBase]
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