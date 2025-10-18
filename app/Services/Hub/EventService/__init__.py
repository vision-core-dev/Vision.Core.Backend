from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.Objects.EventModel import Event
from app.Services.Hub.EventService.contracts import CreateEventRequest, CreateEventResponse, ListEventsResponse
import uuid

class EventService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def GetEventsList(self):
        result = await self.db.execute(
            select(Event)
        )
        events = result.scalars().all()
        return ListEventsResponse(total=len(events), list=events)

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

        return CreateEventResponse(event_id=str(new_event.id))

