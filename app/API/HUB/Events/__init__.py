from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.Infrastructure.Database import getdb
from app.Services.Hub.EventService import EventService
from app.Services.Hub.EventService.contracts import CreateEventRequest, CreateEventResponse, ListEventsResponse

events_router = APIRouter(prefix="/Events", tags=["Hub > Events"])

@events_router.get("/List", response_model=ListEventsResponse)
async def list_events(db: AsyncSession = Depends(getdb)):
    return await EventService(db).GetEventsList()

@events_router.post("/Create", response_model=CreateEventResponse)
async def create_event(data: CreateEventRequest, db: AsyncSession = Depends(getdb)):
    return await EventService(db).CreateEvent(data)
