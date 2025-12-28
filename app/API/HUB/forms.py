# app/API/forms/router.py
import uuid
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Objects.forms import Form, FormResult
from app.Objects.UserModel import User
from app.Services.Hub.AuthService.depends import getuser


forms_router = APIRouter(prefix="/Forms", tags=["Forms"])


class GetFormRequest(BaseModel):
    slug: str


class GetFormResponse(BaseModel):
    id: uuid.UUID
    title: str
    is_anonymous: bool
    data: Dict[str, Any]


class SubmitFormRequest(BaseModel):
    form_id: uuid.UUID
    answers: Dict[str, Any]

@forms_router.post("/GetForm", response_model=GetFormResponse)
async def get_form(
    req: GetFormRequest,
    db: AsyncSession = Depends(getdb),
    user: User | None = Depends(getuser),
):
    form = await db.execute(select(Form).where(Form.slug == req.slug))
    form = form.scalars().first()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    if not form.is_anonymous and not user:
        raise HTTPException(status_code=401, detail="Auth required")

    return GetFormResponse(
        id=form.id,
        title=form.title,
        is_anonymous=form.is_anonymous,
        data=form.data,
    )



@forms_router.post("/Submit")
async def submit_form(
    payload: SubmitFormRequest,
    db: AsyncSession = Depends(getdb),
    user: User | None = Depends(getuser),
):
    form = await db.get(Form, payload.form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    if not form.is_anonymous and not user:
        raise HTTPException(status_code=401, detail="Auth required")

    result = FormResult(
        form_id=form.id,
        user_id=None if form.is_anonymous else user.id,
        data=payload.answers,
    )

    db.add(result)
    await db.commit()

    return {"status": "ok"}



class FormFieldSchema(BaseModel):
    id: str
    title: str
    type: str
    required: bool | None = False
    properties: Dict[str, Any] | None = None


class FormInfoSchema(BaseModel):
    id: uuid.UUID
    title: str
    fields: List[FormFieldSchema]


class FormResultItemSchema(BaseModel):
    id: uuid.UUID
    submitted_at: datetime
    data: Dict[str, Any]


class GetFormResultsResponse(BaseModel):
    form: FormInfoSchema
    results: List[FormResultItemSchema]


class GetFormResultsRequest(BaseModel):
    form_id: uuid.UUID

@forms_router.post("/GetResults", response_model=GetFormResultsResponse)
async def get_form_results(
    req: GetFormResultsRequest,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    # 1️⃣ отримуємо форму
    form = await db.get(Form, req.form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    # 2️⃣ доступ (ВАЖЛИВО)
    # 👉 тільки автор або адмін
    if form.author_id and form.author_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    # 3️⃣ результати
    result = await db.execute(
        select(FormResult)
        .where(FormResult.form_id == req.form_id)
        .order_by(FormResult.submitted_at.asc())
    )
    rows = result.scalars().all()

    return GetFormResultsResponse(
        form=FormInfoSchema(
            id=form.id,
            title=form.title,
            fields=form.data.get("fields", []),
        ),
        results=[
            FormResultItemSchema(
                id=r.id,
                submitted_at=r.submitted_at,
                data=r.data or {},
            )
            for r in rows
        ],
    )
