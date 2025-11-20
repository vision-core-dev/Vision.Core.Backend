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

        # 1. Доступи
        accesses = (await self.db.execute(
            select(KnowledgeAccess).where(KnowledgeAccess.role_id == role_id)
        )).scalars().all()

        allowed_folders = set()
        allowed_docs = set()

        for a in accesses:
            if a.folder_id:
                allowed_folders.add(str(a.folder_id))

            if a.document_id:
                allowed_docs.add(str(a.document_id))

        # 2. Завантажуємо всі папки + документи
        all_folders = (await self.db.execute(
            select(KnowledgeFolder)
            .options(selectinload(KnowledgeFolder.documents))
        )).scalars().unique().all()

        folder_map = {str(f.id): f for f in all_folders}

        # === 🆕 Додамо папки документів до allowed_folders ===
        for doc_id in list(allowed_docs):
            folder_id = (await self.db.execute(
                select(KnowledgeDocument.folder_id).where(KnowledgeDocument.id == doc_id)
            )).scalar_one_or_none()

            if folder_id:
                allowed_folders.add(str(folder_id))

                # підіймаємось до root
                parent = folder_map.get(str(folder_id))
                while parent and parent.parent_id:
                    allowed_folders.add(str(parent.parent_id))
                    parent = folder_map.get(str(parent.parent_id))

        # 3. Будуємо children map
        children_map = {}
        for f in all_folders:
            pid = str(f.parent_id) if f.parent_id else None
            children_map.setdefault(pid, []).append(f)

        # === 🆕 Додаємо всі дочірні папки ===
        def add_children(folder_id):
            for child in children_map.get(folder_id, []):
                cid = str(child.id)
                if cid not in allowed_folders:
                    allowed_folders.add(cid)
                    add_children(cid)

        for fid in list(allowed_folders):
            add_children(fid)

        # 4. serialize()
        def serialize(folder):
            if str(folder.id) not in allowed_folders:
                return None

            return {
                "id": str(folder.id),
                "name": folder.name,
                "parent_id": str(folder.parent_id) if folder.parent_id else None,

                "documents": [
                    {"id": str(d.id), "title": d.title}
                    for d in folder.documents
                    if (str(folder.id) in allowed_folders) or (str(d.id) in allowed_docs)
                ],

                "subfolders": [
                    sf for sf in (
                        serialize(child)
                        for child in children_map.get(str(folder.id), [])
                    ) if sf is not None
                ],
            }

        # 5. знаходимо root-и
        roots = [
            folder_map[fid]
            for fid in allowed_folders
            if folder_map[fid].parent_id is None
        ]

        return [serialize(r) for r in roots]

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

    async def get_document(self, document_id: str) -> Optional[KnowledgeDocument]:
        query = (
            select(KnowledgeDocument)
            .where(KnowledgeDocument.id == document_id)
            .options(
                selectinload(KnowledgeDocument.current_version),
                selectinload(KnowledgeDocument.folder),
                selectinload(KnowledgeDocument.author),  # ⭐ додаємо автора
            )
        )

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
