from pydantic import BaseModel

from app.Objects.NotifyModel import MyNotifyBase


class NotifiesListResponse(BaseModel):
    total: int
    list: list[MyNotifyBase]

    class Config:
        from_attributes = True

class UnreadNotifiesCountResponse(BaseModel):
    count: int