import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.Infrastructure.Database import getdb
from app.Objects.UserModel import User
from app.Objects.JobModel import Job
from app.Objects.JobSchemas import (
    CreateJobRequest,
    UpdateJobRequest,
    JobResponse,
    ListJobsResponse,
)
from app.Services.Hub.AuthService.depends import getuser
from app.Services.RoVision.content import sanitize_html

jobs_router = APIRouter(prefix="/Jobs", tags=["RoVision > Jobs"])


def check_permission(user: User):
    if not user.role or user.role.order not in [0, 1]:
        raise HTTPException(status_code=403, detail="Тільки CEO/COO можуть керувати вакансіями")


# ---------- Public ----------

@jobs_router.get("/List", response_model=ListJobsResponse)
async def list_jobs(db: AsyncSession = Depends(getdb), include_unpublished: bool = False):
    stmt = select(Job).order_by(desc(Job.created_at))
    if not include_unpublished:
        stmt = stmt.where(Job.is_published.is_(True))
    result = await db.execute(stmt)
    return {"items": result.scalars().all()}


@jobs_router.get("/BySlug/{slug}", response_model=JobResponse)
async def get_job_by_slug(slug: str, db: AsyncSession = Depends(getdb)):
    result = await db.execute(select(Job).where(Job.slug == slug))
    job = result.scalar_one_or_none()
    if not job or not job.is_published:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# ---------- Admin ----------

@jobs_router.get("/Admin/List", response_model=ListJobsResponse)
async def admin_list(user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    check_permission(user)
    result = await db.execute(select(Job).order_by(desc(Job.created_at)))
    return {"items": result.scalars().all()}


@jobs_router.get("/Admin/{job_id}", response_model=JobResponse)
async def admin_get(job_id: uuid.UUID, user: User = Depends(getuser), db: AsyncSession = Depends(getdb)):
    check_permission(user)
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@jobs_router.post("/Create", response_model=JobResponse)
async def create_job(
    data: CreateJobRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)

    existing = await db.execute(select(Job).where(Job.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug вже існує")

    payload = data.model_dump()
    payload["description"] = sanitize_html(payload.get("description"))

    job = Job(**payload)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@jobs_router.patch("/{job_id}/Update", response_model=JobResponse)
async def update_job(
    job_id: uuid.UUID,
    data: UpdateJobRequest,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)

    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    updates = data.model_dump(exclude_unset=True)
    if "description" in updates:
        updates["description"] = sanitize_html(updates["description"])
    for key, value in updates.items():
        setattr(job, key, value)

    await db.commit()
    await db.refresh(job)
    return job


@jobs_router.delete("/{job_id}/Delete")
async def delete_job(
    job_id: uuid.UUID,
    user: User = Depends(getuser),
    db: AsyncSession = Depends(getdb),
):
    check_permission(user)

    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await db.delete(job)
    await db.commit()
    return {"status": "success"}
