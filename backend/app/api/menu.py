"""
菜单配置API

菜单权限控制：
- 权限过滤：检查用户是否拥有菜单的 permission 字段对应的权限码
- 如果没有配置 permission，所有登录用户都能访问
"""
from typing import List, Optional, Dict, Any, Set
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import MenuConfig, User, UserRole
from app.schemas import (
    MenuConfigCreate, MenuConfigUpdate, MenuConfigResponse,
    MenuItemResponse, MessageResponse
)
from app.deps import get_super_admin, get_current_user
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/menu", tags=["Menu Config"])


def menu_to_dict(menu: MenuConfig) -> dict[str, Any]:
    """将菜单模型转换为字典"""
    return {
        "id": menu.id,
        "parent_id": menu.parent_id,
        "name": menu.name,
        "path": menu.path,
        "icon": menu.icon,
        "component": menu.component,
        "sort_order": menu.sort_order,
        "is_visible": menu.is_visible,
        "is_enabled": menu.is_enabled,
        "permission": menu.permission,
        "meta": menu.meta,
        "created_at": menu.created_at,
        "children": []
    }


def build_menu_tree(menus: list[MenuConfig], parent_id: Optional[int] = None) -> list[dict[str, Any]]:
    """构建菜单树"""
    result = []
    for menu in menus:
        if menu.parent_id == parent_id:
            item = menu_to_dict(menu)
            children = build_menu_tree(menus, menu.id)
            if children:
                item["children"] = children
            result.append(item)
    return result


def filter_menu_by_role(menus: list[dict[str, Any]], user_role: UserRole, user_permissions: set[str]) -> list[dict[str, Any]]:
    """
    根据权限过滤菜单
    
    过滤规则：
    1. 如果菜单配置了 permission 字段，检查用户是否有该权限
    2. 如果没有配置 permission，所有登录用户都能访问
    
    Args:
        menus: 菜单列表
        user_role: 用户角色（保留参数，便于扩展）
        user_permissions: 用户拥有的权限码集合
    
    Returns:
        过滤后的菜单列表
    """
    result = []
    for menu in menus:
        # 检查菜单是否启用
        if not menu.get("is_enabled", True):
            continue
        
        # 权限检查
        if menu.get("permission"):
            # 检查权限码
            if menu["permission"] not in user_permissions:
                continue
        
        # 递归处理子菜单
        if menu.get("children"):
            menu["children"] = filter_menu_by_role(menu["children"], user_role, user_permissions)
        
        result.append(menu)
    
    return result


@router.get("/list", response_model=list[MenuConfigResponse])
async def get_menu_list(
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """获取完整菜单列表（管理员用）"""
    menus = db.query(MenuConfig).order_by(MenuConfig.sort_order).all()
    return build_menu_tree(menus)


@router.get("/user-menu", response_model=list[MenuItemResponse])
async def get_user_menu(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的菜单（前端导航用）"""
    menus = db.query(MenuConfig).filter(
        MenuConfig.is_visible,
        MenuConfig.is_enabled
    ).order_by(MenuConfig.sort_order).all()
    
    # 构建树形结构
    menu_tree = build_menu_tree(menus)
    
    # 获取用户权限
    permission_service = PermissionService(db)
    user_permissions = permission_service.get_role_permissions(current_user.role)
    
    # 根据角色和权限过滤
    filtered_menus = filter_menu_by_role(menu_tree, current_user.role, user_permissions)
    
    # 转换为前端需要的格式
    def to_menu_item(menus: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for menu in menus:
            item = {
                "id": menu["id"],
                "name": menu["name"],
                "path": menu.get("path") or "",
                "icon": menu.get("icon")
            }
            if menu.get("children"):
                item["children"] = to_menu_item(menu["children"])
            result.append(item)
        return result
    
    return to_menu_item(filtered_menus)


@router.post("", response_model=MenuConfigResponse)
async def create_menu(
    menu_data: MenuConfigCreate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """创建菜单配置"""
    # Check if parent menu exists
    if menu_data.parent_id:
        parent = db.query(MenuConfig).filter(MenuConfig.id == menu_data.parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent menu not found"
            )
    
    menu = MenuConfig(
        parent_id=menu_data.parent_id,
        name=menu_data.name,
        path=menu_data.path,
        icon=menu_data.icon,
        component=menu_data.component,
        sort_order=menu_data.sort_order,
        is_visible=menu_data.is_visible,
        is_enabled=menu_data.is_enabled,
        permission=menu_data.permission,
        meta=menu_data.meta
    )
    db.add(menu)
    db.commit()
    db.refresh(menu)
    
    return menu_to_dict(menu)


@router.put("/{menu_id}", response_model=MenuConfigResponse)
async def update_menu(
    menu_id: int,
    menu_data: MenuConfigUpdate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """更新菜单配置"""
    menu = db.query(MenuConfig).filter(MenuConfig.id == menu_id).first()
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found"
        )
    
    # Check if parent menu is valid
    if menu_data.parent_id is not None:
        if menu_data.parent_id == menu_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot set self as parent menu"
            )
        if menu_data.parent_id:
            parent = db.query(MenuConfig).filter(MenuConfig.id == menu_data.parent_id).first()
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent menu not found"
                )
    
    # 更新字段
    update_data = menu_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(menu, key, value)
    
    db.commit()
    db.refresh(menu)
    
    return menu_to_dict(menu)


@router.delete("/{menu_id}", response_model=MessageResponse)
async def delete_menu(
    menu_id: int,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """删除菜单配置"""
    menu = db.query(MenuConfig).filter(MenuConfig.id == menu_id).first()
    if not menu:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu not found"
        )
    
    # Check if there are child menus
    children = db.query(MenuConfig).filter(MenuConfig.parent_id == menu_id).count()
    if children > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete menu with child menus"
        )
    
    db.delete(menu)
    db.commit()
    
    return MessageResponse(message="Deleted successfully")
