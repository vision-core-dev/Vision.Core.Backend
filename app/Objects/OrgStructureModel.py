"""
Моделі для організаційної структури: відділи та проекти
"""
from sqlalchemy import Column, String, ForeignKey, Integer, Boolean, Text, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, backref
import uuid
import enum
from datetime import datetime

from app.Infrastructure.Database import Base


class NodeType(str, enum.Enum):
    """Тип вузла в організаційній структурі"""
    DEPARTMENT = "department"  # Відділ
    PROJECT = "project"  # Проект
    USER = "user"  # Користувач


class OrgStructureNode(Base):
    """
    Вузол організаційної структури.
    Може бути відділом, проектом або користувачем.
    Використовує adjacency list pattern для побудови дерева.
    """
    __tablename__ = "OrgStructureNodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Тип вузла
    node_type = Column(SQLEnum(NodeType), nullable=False, index=True)
    
    # Назва (для відділів та проектів)
    name = Column(String(200), nullable=True)
    
    # Опис
    description = Column(Text, nullable=True)
    
    # Посилання на користувача (якщо node_type = USER)
    user_id = Column(UUID(as_uuid=True), ForeignKey("Users.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Батьківський вузол (для побудови дерева)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("OrgStructureNodes.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Порядок сортування серед сусідів
    order = Column(Integer, default=0, nullable=False)
    
    # Додаткові дані (колір, іконка, тощо)
    meta_data = Column(JSONB, nullable=True)
    
    # Чи активний вузол
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], lazy="selectin", backref="org_nodes")
    parent = relationship("OrgStructureNode", remote_side=[id], backref=backref("children", lazy="selectin"))
    
    def __repr__(self):
        if self.node_type == NodeType.USER:
            return f"<OrgNode User {self.user_id}>"
        return f"<OrgNode {self.node_type.value} '{self.name}'>"
    
    def to_dict(self, include_children=False, include_user=False):
        """Конвертація в словник"""
        data = {
            "id": str(self.id),
            "node_type": self.node_type.value,
            "name": self.name,
            "description": self.description,
            "user_id": str(self.user_id) if self.user_id else None,
            "parent_id": str(self.parent_id) if self.parent_id else None,
            "order": self.order,
            "meta_data": self.meta_data,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_user and self.user:
            data["user"] = {
                "id": str(self.user.id),
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
                "email": self.user.email,
                "avatar_url": self.user.avatar_url,
                "role": {
                    "id": str(self.user.role.id),
                    "name": self.user.role.name,
                } if self.user.role else None,
            }
        
        if include_children and self.children:
            data["children"] = [
                child.to_dict(include_children=True, include_user=include_user)
                for child in sorted(self.children, key=lambda x: x.order)
            ]
        
        return data
