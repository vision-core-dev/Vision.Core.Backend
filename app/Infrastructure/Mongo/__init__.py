import os

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

async def _ping_server():
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        await client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)

def getrvhmongo():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client["RoVision-Hangout"]
    return db

def _getmongo():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.get_default_database()
    return db