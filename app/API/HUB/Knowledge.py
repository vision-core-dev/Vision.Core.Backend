from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.Infrastructure.Database import getdb
from app.Services.Hub.AuthService.depends import getuser, getuser_check_me
from app.Objects.UserModel import User
from app.Services.Hub.KnowledgeService import KnowledgeService

knowledge_router = APIRouter(prefix="/Knowledge", tags=["Knowledge Base"])


# 🌳 Отримати дерево папок з документами
@knowledge_router.get("/GetTree")
async def get_knowledge_tree(
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    service = KnowledgeService(db)
    folders = await service.get_accessible_tree(role_id=user.role_id)
    return {"folders": folders}


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
            "author_id": str(doc.author_id),
            "updated_at": doc.updated_at,
        },
    }


# 🧠 Створити новий документ (тільки для WRITE-доступу)
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


# 🧩 Створити нову версію документа
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