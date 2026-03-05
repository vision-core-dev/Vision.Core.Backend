from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.Infrastructure.Database import getdb
from app.Services.Hub.AuthService.depends import getuser, getuser_check_me
from app.Objects.UserModel import User
from app.Services.Hub.KnowledgeService import KnowledgeService

knowledge_router = APIRouter(prefix="/Knowledge", tags=["Knowledge Base"])


# ─────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────

class UpdateDocPayload(BaseModel):
    title: str
    content: str

class CreateFolderPayload(BaseModel):
    name: str
    parent_id: str | None = None

class UpdateFolderPayload(BaseModel):
    name: str


# ─────────────────────────────────────────────────────────────
# STATIC routes — must be declared BEFORE any /{param} routes
# ─────────────────────────────────────────────────────────────

# 🌳 Отримати дерево папок з документами
@knowledge_router.get("/GetTree")
async def get_knowledge_tree(
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    service = KnowledgeService(db)
    folders = await service.get_accessible_tree(role_id=user.role_id)
    return {"folders": folders}


# 🧠 Створити новий документ
@knowledge_router.post("/CreateDocument")
async def create_document(
    title: str,
    content: str,
    folder_id: str | None = None,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    service = KnowledgeService(db)
    doc = await service.create_document(
        title=title,
        author_id=user.id,
        folder_id=folder_id,
        content=content,
    )
    return {"document_id": str(doc.id)}


# 🧩 Створити нову версію документа (старий ендпоінт)
@knowledge_router.post("/Documents/{doc_id}/CreateVersion")
async def create_document_version(
    doc_id: str,
    content: str,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    service = KnowledgeService(db)
    version = await service.create_version(
        document_id=doc_id,
        author_id=user.id,
        content=content,
    )
    return {"version_id": str(version.id)}


# ─────────────────────────────────────────────────────────────
# ADMIN routes — static prefixes, declared BEFORE /{doc_id}
# ─────────────────────────────────────────────────────────────

@knowledge_router.post("/Admin/Folder/Create")
async def create_folder(
    payload: CreateFolderPayload,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    if user.role.order > 1:
        raise HTTPException(status_code=403, detail="Forbidden")
    service = KnowledgeService(db)
    folder = await service.create_folder(name=payload.name, parent_id=payload.parent_id)
    return {"ok": True, "folder_id": str(folder.id)}


@knowledge_router.post("/Admin/Folder/{folder_id}/Update")
async def update_folder(
    folder_id: str,
    payload: UpdateFolderPayload,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    if user.role.order > 1:
        raise HTTPException(status_code=403, detail="Forbidden")
    service = KnowledgeService(db)
    await service.update_folder(folder_id, payload.name)
    return {"ok": True}


@knowledge_router.post("/Admin/Folder/{folder_id}/Delete")
async def delete_folder(
    folder_id: str,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    if user.role.order > 1:
        raise HTTPException(status_code=403, detail="Forbidden")
    service = KnowledgeService(db)
    success = await service.delete_folder(folder_id)
    return {"ok": success}


@knowledge_router.post("/Admin/Document/{doc_id}/Delete")
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    if user.role.order > 1:
        raise HTTPException(status_code=403, detail="Forbidden")
    service = KnowledgeService(db)
    success = await service.delete_document(doc_id)
    return {"ok": success}


@knowledge_router.post("/Admin/Version/{version_id}/Delete")
async def delete_version(
    version_id: str,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    if user.role.order > 1:
        raise HTTPException(status_code=403, detail="Forbidden")
    service = KnowledgeService(db)
    success = await service.delete_version(version_id)
    return {"ok": success}




# ─────────────────────────────────────────────────────────────
# DYNAMIC /{doc_id} routes — must be declared LAST
# ─────────────────────────────────────────────────────────────

# 📄 Отримати документ за ID
@knowledge_router.get("/{doc_id}/GetDocument")
async def get_document(
    doc_id: str,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser_check_me),
):
    service = KnowledgeService(db)
    doc = await service.get_document(doc_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document": {
            "id": str(doc.id),
            "title": doc.title,
            "content": doc.current_version.content if doc.current_version else "",
            "author": {
                "id": str(doc.author.id),
                "avatar_url": doc.author.avatar_url,
                "first_name": doc.author.first_name,
                "last_name": doc.author.last_name,
            },
            "updated_at": doc.updated_at,
        },
    }


# 📝 Оновити документ (назва + новий контент → нова версія)
@knowledge_router.post("/{doc_id}/UpdateDocument")
async def update_document(
    doc_id: str,
    payload: UpdateDocPayload,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    service = KnowledgeService(db)
    await service.update_document(doc_id, payload.title)
    version = await service.create_version(
        document_id=doc_id,
        author_id=user.id,
        content=payload.content,
    )
    return {"ok": True, "version_id": str(version.id)}


# 📚 Отримати всі версії документа
@knowledge_router.get("/{doc_id}/Versions")
async def get_document_versions(
    doc_id: str,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    service = KnowledgeService(db)
    versions = await service.get_document_versions(doc_id)

    return {
        "versions": [
            {
                "id": str(v.id),
                "author_id": str(v.author_id),
                "author_first_name": v.author.first_name if v.author else None,
                "author_last_name": v.author.last_name if v.author else None,
                "author_avatar_url": v.author.avatar_url if v.author else None,
                "created_at": v.created_at,
                "content": v.content,
            }
            for v in versions
        ]
    }