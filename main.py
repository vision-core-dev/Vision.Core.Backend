from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db

origins = [
]

app = FastAPI(title="Vision Core Dev API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.on_event("startup")
async def startup_event():
    init_db()

from v1 import v1_api
app.include_router(v1_api)

@app.get("/")
async def root():
    return {"message": "Vision Core Dev API"}