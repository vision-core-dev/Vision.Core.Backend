from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter
from fastapi.params import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.API.RoVision.Hangout.game_data import HangoutUserData
from app.Infrastructure.Mongo import getrvhmongo

hangout_data_router = APIRouter()

class GetUserDataRequest(BaseModel):
    rbx_user_id: Optional[int] = None
    create_if_not_exists: Optional[bool] = False

class UserDataResponse(BaseModel):
    user_data: Optional[HangoutUserData]

def normalize_user(doc: dict) -> HangoutUserData:
    doc["_id"] = str(doc["_id"])
    return HangoutUserData(**doc)


@hangout_data_router.post("/Users/GetUserData", response_model=UserDataResponse)
async def get_user_data(
    data: GetUserDataRequest,
    mongo: AsyncIOMotorDatabase = Depends(getrvhmongo)
):
    collection = mongo["users"]

    user = await collection.find_one(
        {"rbx_user_id": data.rbx_user_id}
    )

    if user:
        normalized = normalize_user(user)

        await collection.update_one(
            {"_id": user["_id"]},
            {"$set": normalized.dict(by_alias=True, exclude={"_id"})}
        )

        return {"user_data": normalized}

    if not data.create_if_not_exists:
        return {"user_data": None}

    new_user = HangoutUserData(
        rbx_user_id=data.rbx_user_id
    )

    result = await collection.insert_one(
        new_user.dict(by_alias=True)
    )

    new_user.id = str(result.inserted_id)

    return {"user_data": new_user}

class SaveUserDataRequest(BaseModel):
    user_data: HangoutUserData

class SaveUserDataResponse(BaseModel):
    success: bool

@hangout_data_router.post("/Users/SaveUserData", response_model=SaveUserDataResponse)
async def save_user_data(
    data: SaveUserDataRequest,
    mongo: AsyncIOMotorDatabase = Depends(getrvhmongo)
):
    collection = mongo["users"]

    if not data.user_data.id:
        return {"success": False}

    await collection.update_one(
        {"_id": ObjectId(data.user_data.id)},
        {"$set": data.user_data.dict(by_alias=True, exclude={"_id"})}
    )

    return {"success": True}