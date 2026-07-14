"""
API для організаційної структури
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.Infrastructure.Database import getdb
from app.Services.Hub.AuthService.depends import getuser, require_role
from app.Services.Hub.OrgStructureService import OrgStructureService
from app.Objects.OrgStructureSchemas import (
    OrgNodeCreate,
    OrgNodeUpdate,
    OrgNodeResponse,
    OrgTreeResponse,
    MoveNodeRequest,
)
from app.Objects.UserModel import User

org_structure_router = APIRouter(prefix="/OrgStructure", tags=["Organization Structure"])


@org_structure_router.get("/Tree", response_model=OrgTreeResponse)
async def get_org_tree(
    include_inactive: bool = Query(False, description="Include inactive nodes"),
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """
    Отримати повне дерево організаційної структури.
    Повертає кореневі вузли з усіма дочірніми елементами.
    """
    service = OrgStructureService(db)
    roots = await service.get_tree(include_inactive=include_inactive)
    
    return {
        "roots": [node.to_dict(include_children=True, include_user=True) for node in roots],
        "total_nodes": sum(1 + _count_children(node) for node in roots),
    }


def _count_children(node) -> int:
    """Рекурсивно підрахувати кількість дочірніх вузлів"""
    count = len(node.children) if node.children else 0
    for child in (node.children or []):
        count += _count_children(child)
    return count


@org_structure_router.get("/Node/{node_id}", response_model=OrgNodeResponse)
async def get_node(
    node_id: str,
    include_children: bool = Query(True, description="Include children nodes"),
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """Отримати вузол за ID"""
    service = OrgStructureService(db)
    
    try:
        node = await service.get_node(uuid.UUID(node_id), include_children=include_children)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node ID format")
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    return node.to_dict(include_children=include_children, include_user=True)


@org_structure_router.post("/Node", response_model=OrgNodeResponse)
async def create_node(
    data: OrgNodeCreate,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """
    Створити новий вузол організаційної структури.
    
    Типи вузлів:
    - department: Відділ (потрібна назва)
    - project: Проект (потрібна назва)
    - user: Користувач (потрібен user_id)
    """
    require_role(user, 2)
    service = OrgStructureService(db)

    try:
        node = await service.create_node(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return node.to_dict(include_children=False, include_user=True)


@org_structure_router.patch("/Node/{node_id}", response_model=OrgNodeResponse)
async def update_node(
    node_id: str,
    data: OrgNodeUpdate,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """Оновити вузол"""
    require_role(user, 2)
    service = OrgStructureService(db)

    try:
        node = await service.update_node(uuid.UUID(node_id), data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return node.to_dict(include_children=False, include_user=True)


@org_structure_router.delete("/Node/{node_id}")
async def delete_node(
    node_id: str,
    cascade: bool = Query(False, description="Delete all children recursively"),
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """
    Видалити вузол.
    
    Якщо cascade=true, видаляє всі дочірні вузли рекурсивно.
    Якщо cascade=false і є діти, повертає помилку.
    """
    require_role(user, 2)
    service = OrgStructureService(db)

    try:
        await service.delete_node(uuid.UUID(node_id), cascade=cascade)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"ok": True, "message": "Node deleted successfully"}


@org_structure_router.post("/Node/{node_id}/Move", response_model=OrgNodeResponse)
async def move_node(
    node_id: str,
    data: MoveNodeRequest,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """
    Перемістити вузол до нового батька.
    
    new_parent_id: ID нового батьківського вузла (null для кореня)
    new_order: Новий порядок серед сусідів
    """
    require_role(user, 2)
    service = OrgStructureService(db)

    try:
        new_parent_uuid = uuid.UUID(data.new_parent_id) if data.new_parent_id else None
        node = await service.move_node(uuid.UUID(node_id), new_parent_uuid, data.new_order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return node.to_dict(include_children=False, include_user=True)


@org_structure_router.get("/Node/{node_id}/Path", response_model=List[OrgNodeResponse])
async def get_node_path(
    node_id: str,
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """Отримати шлях від кореня до вузла (breadcrumbs)"""
    service = OrgStructureService(db)
    
    try:
        path = await service.get_node_path(uuid.UUID(node_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid node ID format")
    
    return [node.to_dict(include_children=False, include_user=True) for node in path]


@org_structure_router.get("/Search", response_model=List[OrgNodeResponse])
async def search_nodes(
    q: str = Query(..., min_length=1, description="Search query"),
    node_types: Optional[List[str]] = Query(None, description="Filter by node types"),
    db: AsyncSession = Depends(getdb),
    user: User = Depends(getuser),
):
    """Пошук вузлів за назвою або описом"""
    from app.Objects.OrgStructureModel import NodeType
    
    service = OrgStructureService(db)
    
    types = None
    if node_types:
        try:
            types = [NodeType(t) for t in node_types]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid node type")
    
    nodes = await service.search_nodes(q, types)
    
    return [node.to_dict(include_children=False, include_user=True) for node in nodes]
