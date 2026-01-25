"""
Сервіс для роботи з організаційною структурою
"""
import uuid
from typing import List, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.Objects.OrgStructureModel import OrgStructureNode, NodeType
from app.Objects.UserModel import User
from app.Objects.OrgStructureSchemas import OrgNodeCreate, OrgNodeUpdate


class OrgStructureService:
    """Сервіс для управління організаційною структурою"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_tree(self, include_inactive: bool = False) -> List[OrgStructureNode]:
        """
        Отримати повне дерево організаційної структури.
        Повертає тільки кореневі вузли (без parent_id), діти завантажуються через relationship.
        """
        # Create a deep eager load chain to prevent MissingGreenlet error
        # Support up to 10 levels deep of recursion
        loader = selectinload(OrgStructureNode.children)
        for _ in range(10):
             loader = loader.selectinload(OrgStructureNode.children)

        query = select(OrgStructureNode).where(
            OrgStructureNode.parent_id.is_(None)
        ).order_by(OrgStructureNode.order).options(loader)
        
        if not include_inactive:
            query = query.where(OrgStructureNode.is_active == True)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_node(self, node_id: uuid.UUID, include_children: bool = True) -> Optional[OrgStructureNode]:
        """Отримати вузол за ID"""
        query = select(OrgStructureNode).where(
            OrgStructureNode.id == node_id
        )
        
        if include_children:
            query = query.options(selectinload(OrgStructureNode.children))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_node(self, data: OrgNodeCreate) -> OrgStructureNode:
        """Створити новий вузол"""
        # Валідація
        if data.node_type == "user" and not data.user_id:
            raise ValueError("user_id is required for user nodes")
        
        if data.node_type in ["department", "project"] and not data.name:
            raise ValueError("name is required for department and project nodes")
        
        # Перевірка чи батьківський вузол існує
        if data.parent_id:
            parent = await self.get_node(uuid.UUID(data.parent_id), include_children=False)
            if not parent:
                raise ValueError(f"Parent node {data.parent_id} not found")
        
        # Створення вузла
        node = OrgStructureNode(
            node_type=NodeType(data.node_type),
            name=data.name,
            description=data.description,
            user_id=uuid.UUID(data.user_id) if data.user_id else None,
            parent_id=uuid.UUID(data.parent_id) if data.parent_id else None,
            order=data.order,
            meta_data=data.meta_data,
        )
        
        self.db.add(node)
        await self.db.commit()
        return await self.get_node(node.id, include_children=False)
    
    async def update_node(self, node_id: uuid.UUID, data: OrgNodeUpdate) -> OrgStructureNode:
        """Оновити вузол"""
        node = await self.get_node(node_id, include_children=False)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        # Оновлення полів
        if data.name is not None:
            node.name = data.name
        if data.description is not None:
            node.description = data.description
        if data.parent_id is not None:
            # Перевірка на циклічні залежності
            if await self._would_create_cycle(node_id, uuid.UUID(data.parent_id)):
                raise ValueError("Moving node would create a cycle")
            node.parent_id = uuid.UUID(data.parent_id) if data.parent_id else None
        if data.order is not None:
            node.order = data.order
        if data.meta_data is not None:
            node.meta_data = data.meta_data
        if data.is_active is not None:
            node.is_active = data.is_active
        
        await self.db.commit()
        return await self.get_node(node.id, include_children=False)
    
    async def delete_node(self, node_id: uuid.UUID, cascade: bool = False) -> bool:
        """
        Видалити вузол.
        Якщо cascade=True, видаляє всі дочірні вузли.
        Якщо cascade=False і є діти, викидає помилку.
        """
        node = await self.get_node(node_id, include_children=True)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        if not cascade and node.children:
            raise ValueError("Cannot delete node with children. Use cascade=True to delete all children.")
        
        await self.db.delete(node)
        await self.db.commit()
        
        return True
    
    async def move_node(
        self, 
        node_id: uuid.UUID, 
        new_parent_id: Optional[uuid.UUID], 
        new_order: Optional[int] = None
    ) -> OrgStructureNode:
        """Перемістити вузол до нового батька"""
        node = await self.get_node(node_id, include_children=False)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        # Перевірка на циклічні залежності
        if new_parent_id and await self._would_create_cycle(node_id, new_parent_id):
            raise ValueError("Moving node would create a cycle")
        
        # Переміщення
        node.parent_id = new_parent_id
        if new_order is not None:
            node.order = new_order
        
        await self.db.commit()
        return await self.get_node(node.id, include_children=False)
    
    async def get_node_path(self, node_id: uuid.UUID) -> List[OrgStructureNode]:
        """Отримати шлях від кореня до вузла"""
        path = []
        current_node = await self.get_node(node_id, include_children=False)
        
        while current_node:
            path.insert(0, current_node)
            if current_node.parent_id:
                current_node = await self.get_node(current_node.parent_id, include_children=False)
            else:
                break
        
        return path
    
    async def _would_create_cycle(self, node_id: uuid.UUID, new_parent_id: uuid.UUID) -> bool:
        """Перевірка чи створить переміщення циклічну залежність"""
        if node_id == new_parent_id:
            return True
        
        # Перевіряємо чи new_parent не є нащадком node
        current = await self.get_node(new_parent_id, include_children=False)
        while current:
            if current.id == node_id:
                return True
            if current.parent_id:
                current = await self.get_node(current.parent_id, include_children=False)
            else:
                break
        
        return False
    
    async def search_nodes(
        self, 
        query: str, 
        node_types: Optional[List[NodeType]] = None
    ) -> List[OrgStructureNode]:
        """Пошук вузлів за назвою"""
        stmt = select(OrgStructureNode).where(
            and_(
                OrgStructureNode.is_active == True,
                or_(
                    OrgStructureNode.name.ilike(f"%{query}%"),
                    OrgStructureNode.description.ilike(f"%{query}%")
                )
            )
        )
        
        if node_types:
            stmt = stmt.where(OrgStructureNode.node_type.in_(node_types))
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
