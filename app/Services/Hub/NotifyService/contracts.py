from pydantic import BaseModel

from app.Objects.NotificationModel import MyNotifBase


class NotifiesListResponse(BaseModel):
    total: int
    list: list[MyNotifBase]

    class Config:
        from_attributes = True

class UnreadNotifiesCountResponse(BaseModel):
    count: int