from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.security import HTTPBearer
from sqlalchemy import text
from starlette.middleware.cors import CORSMiddleware

from app.API import api_router
from app.Infrastructure.Database import Base, engine
from app.Infrastructure.Redis import connect_redis, disconnect_redis
from app.Services.CurrencyService import CurrencyService
from app.Services.Hub.NotifyService.reminders import check_deadline_reminders

load_dotenv()

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting application...")
    try:
        app.state.redis = await connect_redis()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Deadline reminders — every 30 min
        scheduler.add_job(check_deadline_reminders, "interval", minutes=30)
        scheduler.start()

        # await CurrencyService().RefreshExchangeRate(redis=app.state.redis, currency_code="UAH")

        yield
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        raise
    finally:
        scheduler.shutdown(wait=False)
        await disconnect_redis(app.state.redis)
        print("👋 Application stopped")

app = FastAPI(
    title="Vision Core Dev API",
    description="Новий Погляд на Український Контент",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True},
)

security_scheme = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hub.vcore.dev",
        "https://hub.visioncore.dev",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "X-Request-Id"],
)

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
