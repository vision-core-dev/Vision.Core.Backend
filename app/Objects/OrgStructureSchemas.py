"""
Pydantic схеми для організаційної структури
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


class OrgNodeBase(BaseModel):
    """Базова схема вузла організаційної структури"""
    node_type: Literal["department", "project", "user"]
    name: Optional[str] = None
    description: Optional[str] = None
    user_id: Optional[str] = None
    parent_id: Optional[str] = None
    order: int = 0
    meta_data: Optional[dict] = None


class OrgNodeCreate(OrgNodeBase):
    """Схема для створення вузла"""
    pass


class OrgNodeUpdate(BaseModel):
    """Схема для оновлення вузла"""
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    order: Optional[int] = None
    meta_data: Optional[dict] = None
    is_active: Optional[bool] = None


class UserInfo(BaseModel):
    """Інформація про користувача"""
    id: str
    first_name: str
    last_name: Optional[str] = None
    email: str
    avatar_url: Optional[str] = None
    role: Optional[dict] = None


class OrgNodeResponse(BaseModel):
    """Схема відповіді з вузлом"""
    id: str
    node_type: str
    name: Optional[str] = None
    description: Optional[str] = None
    user_id: Optional[str] = None
    parent_id: Optional[str] = None
    order: int
    meta_data: Optional[dict] = None
    is_active: bool
    created_at: str
    updated_at: str
    user: Optional[UserInfo] = None
    children: Optional[List["OrgNodeResponse"]] = None


class OrgTreeResponse(BaseModel):
    """Схема відповіді з деревом організаційної структури"""
    roots: List[OrgNodeResponse]
    total_nodes: int


class MoveNodeRequest(BaseModel):
    """Запит на переміщення вузла"""
    new_parent_id: Optional[str] = Field(None, description="ID нового батьківського вузла (None для кореня)")
    new_order: Optional[int] = Field(None, description="Новий порядок серед сусідів")
