from typing import List, Optional, Any, Coroutine, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.Objects.knowledge import KnowledgeFolder, KnowledgeAccess, KnowledgeAccessLevel, KnowledgeDocument, \
    KnowledgeVersion


class KnowledgeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # 🧭 Отримати всі папки (з підпапками)
    async def get_folders(self) -> Sequence[KnowledgeFolder]:
        result = await self.db.execute(select(KnowledgeFolder))
        return result.scalars().all()

    async def get_accessible_tree(self, role_id: str):
        access_stmt = select(KnowledgeAccess).where(KnowledgeAccess.role_id == role_id)
        result = await self.db.execute(access_stmt)
        accesses = result.scalars().all()

        folder_ids = set()
        for a in accesses:
            if a.folder_id:
                folder_ids.add(a.folder_id)
            elif a.document_id:
                doc_stmt = select(KnowledgeDocument.folder_id).where(KnowledgeDocument.id == a.document_id)
                doc_res = await self.db.execute(doc_stmt)
                folder_id = doc_res.scalar_one_or_none()
                if folder_id:
                    folder_ids.add(folder_id)

        if not folder_ids:
            return []

        folders_stmt = (
            select(KnowledgeFolder)
            .where(KnowledgeFolder.id.in_(folder_ids))
            .options(
                selectinload(KnowledgeFolder.documents),
                selectinload(KnowledgeFolder.subfolders)
            )
        )
        folders = (await self.db.execute(folders_stmt)).scalars().unique().all()

        def serialize_folder(folder: KnowledgeFolder):
            return {
                "id": str(folder.id),
                "name": folder.name,
                "parent_id": str(folder.parent_id) if folder.parent_id else None,
                "documents": [
                    {"id": str(doc.id), "title": doc.title}
                    for doc in (folder.documents or [])
                ],
                "subfolders": [serialize_folder(sub) for sub in (folder.subfolders or [])],
            }

        return [serialize_folder(f) for f in folders]

    async def get_folders_with_access(self, role_id: str) -> list[KnowledgeFolder]:
        """
        Повертає тільки ті папки, до яких у ролі користувача є доступ READ або WRITE.
        """
        # 1️⃣ Отримуємо всі дозволи для ролі
        access_stmt = select(KnowledgeAccess.folder_id).where(
            and_(
                KnowledgeAccess.role_id == role_id,
                KnowledgeAccess.access_level.in_(
                    [KnowledgeAccessLevel.READ, KnowledgeAccessLevel.WRITE]
                )
            )
        )
        result = await self.db.execute(access_stmt)
        allowed_folder_ids = [row[0] for row in result.all() if row[0] is not None]

        if not allowed_folder_ids:
            return []

        # 2️⃣ Отримуємо папки, які дозволені
        folder_stmt = select(KnowledgeFolder).where(KnowledgeFolder.id.in_(allowed_folder_ids))
        folders = (await self.db.execute(folder_stmt)).scalars().all()

        return folders

    # 📄 Отримати документи у папці
    async def get_documents_in_folder(self, folder_id: Optional[str] = None):
        query = select(KnowledgeDocument).where(
            KnowledgeDocument.folder_id == folder_id
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    # 🔍 Отримати один документ з поточною версією
    async def get_document(self, document_id: str) -> Optional[KnowledgeDocument]:
        query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    # ✍️ Створити новий документ
    async def create_document(
        self,
        title: str,
        author_id: str,
        folder_id: Optional[str],
        content: str,
    ) -> KnowledgeDocument:
        version = KnowledgeVersion(author_id=author_id, content=content)
        doc = KnowledgeDocument(
            title=title,
            author_id=author_id,
            folder_id=folder_id,
            current_version=version,
        )

        self.db.add_all([version, doc])
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    # 🧠 Створити нову версію документа
    async def create_version(
        self, document_id: str, author_id: str, content: str
    ) -> KnowledgeVersion:
        version = KnowledgeVersion(
            document_id=document_id, author_id=author_id, content=content
        )
        self.db.add(version)

        # Оновлюємо поточну версію
        query = select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        doc = (await self.db.execute(query)).scalar_one_or_none()
        if doc:
            doc.current_version = version

        await self.db.commit()
        return version

    # 🔒 Перевірка доступу для ролі
    async def has_access(
        self,
        role_id: str,
        document_id: Optional[str] = None,
        folder_id: Optional[str] = None,
        level: KnowledgeAccessLevel = KnowledgeAccessLevel.READ,
    ) -> bool:
        query = select(KnowledgeAccess).where(
            and_(
                KnowledgeAccess.role_id == role_id,
                KnowledgeAccess.access_level.in_(
                    [level, KnowledgeAccessLevel.WRITE]
                ),  # WRITE включає READ
                (KnowledgeAccess.document_id == document_id)
                if document_id
                else (KnowledgeAccess.folder_id == folder_id),
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    # ⚙️ Надати доступ ролі
    async def grant_access(
        self,
        role_id: str,
        access_level: KnowledgeAccessLevel,
        folder_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ):
        access = KnowledgeAccess(
            role_id=role_id,
            access_level=access_level,
            folder_id=folder_id,
            document_id=document_id,
        )
        self.db.add(access)
        await self.db.commit()
        return access
