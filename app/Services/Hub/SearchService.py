from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func, cast, String
from sqlalchemy.orm import selectinload

from app.Objects.tasks.BoardModel import Board
from app.Objects.tasks.TaskModel import Task
from app.Objects.knowledge import KnowledgeDocument, KnowledgeVersion
from app.Objects.UserModel import User
from app.Objects.ChatModel import Chat, ChatType, ChatMember

class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def global_search(self, query: str, user_id: str, role_id: str) -> Dict[str, List[Any]]:
        search_term = f"%{query}%"
        
        results = {
            "boards": [],
            "tasks": [],
            "docs": [],
            "doc_fragments": [],
            "users": [],
            "files": [], # Placeholder as we discussed
            "groups": []
        }

        # 1. Boards
        # Search boards where result matches name or description (if exists), AND user has access? 
        # For now, let's assume if user is in `members` (if that rel exists) or it's public? 
        # Checking BoardModel... usually relies on UserBoard association or similar.
        # Assuming simple search for now, refactor later for permissions.
        stmt_boards = select(Board).where(
            Board.title.ilike(search_term)
        ).limit(5)
        boards = (await self.db.execute(stmt_boards)).scalars().all()
        results["boards"] = [{"id": str(b.id), "name": b.title, "description": getattr(b, "description", "")} for b in boards]

        # 2. Tasks
        # Tasks where user is assigned or in the board?
        # Let's search all tasks for now, limited to 5.
        stmt_tasks = select(Task).where(
            Task.title.ilike(search_term)
        ).options(selectinload(Task.board)).limit(5)
        tasks = (await self.db.execute(stmt_tasks)).scalars().all()
        results["tasks"] = [{
            "id": str(t.id), 
            "name": t.title, 
            "description": f"{t.board.title if t.board else ''} • {t.status_id or ''}" 
        } for t in tasks]

        # 3. Knowledge Base (Docs)
        # Search by Title
        stmt_docs = select(KnowledgeDocument).where(
            KnowledgeDocument.title.ilike(search_term)
        ).limit(5)
        docs = (await self.db.execute(stmt_docs)).scalars().all()
        results["docs"] = [{"id": str(d.id), "name": d.title, "description": "Knowledge Base"} for d in docs]

        # 4. Doc Fragments (Content)
        # Search inside KnowledgeVersion content
        # We join KnowledgeDocument to get the title
        stmt_fragments = select(KnowledgeVersion).join(KnowledgeDocument).where(
            KnowledgeVersion.content.ilike(search_term)
        ).options(selectinload(KnowledgeVersion.document)).limit(5)
        fragments = (await self.db.execute(stmt_fragments)).scalars().all()
        
        fragment_results = []
        for f in fragments:
            # Create a snippet
            content_lower = f.content.lower()
            q_lower = query.lower()
            try:
                idx = content_lower.index(q_lower)
                start = max(0, idx - 20)
                end = min(len(f.content), idx + len(query) + 20)
                snippet = f"...{f.content[start:end]}..."
            except ValueError:
                snippet = "Fragment found"

            fragment_results.append({
                "id": str(f.document_id), # Link to doc
                "name": snippet,
                "description": f"{f.document.title if f.document else 'Document'}",
            })
        results["doc_fragments"] = fragment_results

        # 5. Users
        stmt_users = select(User).where(
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                User.email.ilike(search_term)
            )
        ).limit(5)
        users = (await self.db.execute(stmt_users)).scalars().all()
        results["users"] = [{
            "id": str(u.id), 
            "name": f"{u.first_name} {u.last_name}", 
            "description": u.email,
            "avatar_url": u.avatar_url
        } for u in users]

        # 6. Groups (Chats)
        # Search chats of type GROUP where name matches
        stmt_groups = select(Chat).where(
            and_(
                Chat.chat_type == ChatType.GROUP,
                Chat.name.ilike(search_term)
            )
        ).limit(5)
        groups = (await self.db.execute(stmt_groups)).scalars().all()
        results["groups"] = [{"id": str(g.id), "name": g.name, "description": "Group Chat"} for g in groups]

        return results
