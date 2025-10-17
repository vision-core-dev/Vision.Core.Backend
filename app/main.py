import os

from dotenv import load_dotenv
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.security import HTTPBearer
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.API import api_router
from app.Infrastructure.Database import Base, engine

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting application...")
    try:
        # await redis_client.connect()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        raise
    finally:
        # await redis_client.disconnect()
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
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
