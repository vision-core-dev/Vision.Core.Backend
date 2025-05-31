from fastapi import APIRouter, Depends
from pydantic import BaseModel
import os

from sqlalchemy.orm import Session

from database import get_db
from models import Document

router = APIRouter()


class DocumentRequest(BaseModel):
    document_path: str


class DocumentResponse(BaseModel):
    message: str
    content: str | None = None


@router.post("/Get", response_model=DocumentResponse)
async def get_document(
    request: DocumentRequest,
    db: Session = Depends(get_db)
):
    """
    Retrieve a document by its path.
    """
    document = db.query(Document).filter(Document.path == request.document_path).first()

    if not document:
        return DocumentResponse(message="Документ не знайдено", content=None)

    print(document.content)

    return DocumentResponse(message="Документ отримано успішно", content=str(document.content))
