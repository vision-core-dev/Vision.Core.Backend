import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, model_validator

from app.Infrastructure.Database import PydModel


class CreateContactRequest(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    category_label: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    telegram: str | None = Field(default=None, max_length=100)
    message: str = Field(min_length=10, max_length=10000)
    consent: bool = False
    turnstile_token: str | None = None

    @model_validator(mode="after")
    def require_consent(self):
        if not self.consent:
            raise ValueError("Потрібна згода з політикою конфіденційності")
        return self

    @model_validator(mode="after")
    def at_least_one_contact(self):
        if not any([self.email, self.phone, self.telegram]):
            raise ValueError("Вкажіть хоча б один спосіб звʼязку: email, телефон або Telegram")
        return self


class ContactRequestResponse(PydModel):
    id: uuid.UUID
    category: str
    category_label: str
    email: str | None = None
    phone: str | None = None
    telegram: str | None = None
    message: str
    is_handled: bool
    created_at: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    user_id: uuid.UUID | None = None


class ListContactRequestsResponse(BaseModel):
    items: list[ContactRequestResponse]


class UpdateContactRequest(PydModel):
    is_handled: bool | None = None
