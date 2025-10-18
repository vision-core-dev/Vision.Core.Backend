from pydantic import BaseModel
from datetime import date, time

from app.Objects.EventModel import EventBase


class CreateEventRequest(BaseModel):
    name: str
    description: str | None = None
    date: date
    time_from: time
    time_to: time
    location: str | None = None

class CreateEventResponse(BaseModel):
    event_id: str

class ListEventsResponse(BaseModel):
    total: int
    list: list[EventBase]