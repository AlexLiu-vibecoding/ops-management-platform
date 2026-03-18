"""
菜单配置API
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import MenuConfig, User, UserRole
from app.schemas import (
    MenuConfigCreate, MenuConfigUpdate, MenuConfigResponse,
    MenuItemResponse, MessageResponse
)
from app.deps import get_super_admin, get_current_user

router = APIRouter(prefix="/menu", tags=["菜单配置"])


def menu_to_dict(menu: MenuConfig) -> Dict[str, Any]:
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
        "roles": menu.roles,
        "meta": menu.meta,
        "created_at": menu.created_at,
        "children": []
    }


def build_menu_tree(menus: List[MenuConfig], parent_id: Optional[int] = None) -> List[Dict[str, Any]]:
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


def filter_menu_by_role(menus: List[Dict[str, Any]], user_role: UserRole) -> List[Dict[str, Any]]:
    """根据角色过滤菜单"""
    result = []
    for menu in menus:
        # 检查菜单是否启用
        if not menu.get("is_enabled", True):
            continue
        
        # 检查角色权限
        if menu.get("roles"):
            allowed_roles = [r.strip() for r in menu["roles"].split(',')]
            if user_role.value not in allowed_roles and user_role != UserRole.SUPER_ADMIN:
                continue
        
        # 递归处理子菜单
        if menu.get("children"):
            menu["children"] = filter_menu_by_role(menu["children"], user_role)
        
        result.append(menu)
    
    return result


@router.get("/list", response_model=List[MenuConfigResponse])
async def get_menu_list(
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """获取完整菜单列表（管理员用）"""
    menus = db.query(MenuConfig).order_by(MenuConfig.sort_order).all()
    return build_menu_tree(menus)


@router.get("/user-menu", response_model=List[MenuItemResponse])
async def get_user_menu(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的菜单（前端导航用）"""
    menus = db.query(MenuConfig).filter(
        MenuConfig.is_visible == True,
        MenuConfig.is_enabled == True
    ).order_by(MenuConfig.sort_order).all()
    
    # 构建树形结构
    menu_tree = build_menu_tree(menus)
    
    # 根据角色过滤
    filtered_menus = filter_menu_by_role(menu_tree, current_user.role)
    
    # 转换为前端需要的格式
    def to_menu_item(menus: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    # 检查父菜单是否存在
    if menu_data.parent_id:
        parent = db.query(MenuConfig).filter(MenuConfig.id == menu_data.parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="父菜单不存在"
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
        roles=menu_data.roles,
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
            detail="菜单不存在"
        )
    
    # 检查父菜单是否有效
    if menu_data.parent_id is not None:
        if menu_data.parent_id == menu_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能将自己设为父菜单"
            )
        if menu_data.parent_id:
            parent = db.query(MenuConfig).filter(MenuConfig.id == menu_data.parent_id).first()
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="父菜单不存在"
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
            detail="菜单不存在"
        )
    
    # 检查是否有子菜单
    children = db.query(MenuConfig).filter(MenuConfig.parent_id == menu_id).count()
    if children > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该菜单下有子菜单，无法删除"
        )
    
    db.delete(menu)
    db.commit()
    
    return MessageResponse(message="删除成功")


@router.post("/init-default", response_model=MessageResponse)
async def init_default_menus(
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """初始化默认菜单配置"""
    # 检查是否已有菜单
    existing = db.query(MenuConfig).count()
    if existing > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="菜单已存在，无法重复初始化"
        )
    
    # 默认菜单配置（一级菜单）
    parent_menus = [
        {"name": "仪表盘", "path": "/dashboard", "icon": "DataAnalysis", "sort_order": 1},
        {"name": "实例管理", "path": "/instances", "icon": "Server", "sort_order": 2, "roles": "super_admin,approval_admin,operator"},
        {"name": "环境管理", "path": "/environments", "icon": "Collection", "sort_order": 3, "roles": "super_admin,approval_admin,operator"},
        {"name": "SQL编辑器", "path": "/sql-editor", "icon": "Document", "sort_order": 4},
        {"name": "变更审批", "path": "/approvals", "icon": "Stamp", "sort_order": 5},
        {"name": "监控中心", "path": "/monitor", "icon": "Monitor", "sort_order": 6},
        {"name": "脚本管理", "path": "/scripts", "icon": "DocumentCopy", "sort_order": 7, "roles": "super_admin,approval_admin,operator"},
        {"name": "定时任务", "path": "/scheduled-tasks", "icon": "Timer", "sort_order": 8, "roles": "super_admin,approval_admin,operator"},
        {"name": "用户管理", "path": "/users", "icon": "User", "sort_order": 9, "roles": "super_admin"},
        {"name": "注册审批", "path": "/registrations", "icon": "UserFilled", "sort_order": 10, "roles": "super_admin"},
        {"name": "钉钉通道", "path": "/dingtalk", "icon": "ChatDotRound", "sort_order": 11, "roles": "super_admin"},
        {"name": "审计日志", "path": "/audit", "icon": "Tickets", "sort_order": 12},
        {"name": "菜单配置", "path": "/menu-config", "icon": "Menu", "sort_order": 13, "roles": "super_admin"},
    ]
    
    # 子菜单配置
    child_menus = [
        {"name": "性能监控", "path": "/monitor/performance", "icon": "TrendCharts", "sort_order": 1, "parent_path": "/monitor"},
        {"name": "慢查询监控", "path": "/monitor/slow-query", "icon": "Timer", "sort_order": 2, "parent_path": "/monitor"},
        {"name": "监控配置", "path": "/monitor/settings", "icon": "Setting", "sort_order": 3, "parent_path": "/monitor"},
    ]
    
    # 创建一级菜单并记录路径到ID的映射
    path_to_id = {}
    for menu_data in parent_menus:
        menu = MenuConfig(**menu_data)
        db.add(menu)
        db.flush()  # 获取ID
        path_to_id[menu_data["path"]] = menu.id
    
    # 创建子菜单
    for menu_data in child_menus:
        parent_path = menu_data.pop("parent_path", None)
        parent_id = path_to_id.get(parent_path)
        menu = MenuConfig(**menu_data, parent_id=parent_id)
        db.add(menu)
    
    db.commit()
    
    return MessageResponse(message=f"成功初始化 {len(parent_menus) + len(child_menus)} 个菜单")


@router.post("/add-missing", response_model=MessageResponse)
async def add_missing_menus(
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """添加缺失的菜单（用于版本升级时补充新菜单）"""
    # 需要确保存在的菜单
    required_menus = [
        {"name": "仪表盘", "path": "/dashboard", "icon": "DataAnalysis", "sort_order": 1},
        {"name": "实例管理", "path": "/instances", "icon": "Server", "sort_order": 2, "roles": "super_admin,approval_admin,operator"},
        {"name": "环境管理", "path": "/environments", "icon": "Collection", "sort_order": 3, "roles": "super_admin,approval_admin,operator"},
        {"name": "SQL编辑器", "path": "/sql-editor", "icon": "Document", "sort_order": 4},
        {"name": "变更审批", "path": "/approvals", "icon": "Stamp", "sort_order": 5},
        {"name": "监控中心", "path": "/monitor", "icon": "Monitor", "sort_order": 6},
        {"name": "脚本管理", "path": "/scripts", "icon": "DocumentCopy", "sort_order": 7, "roles": "super_admin,approval_admin,operator"},
        {"name": "定时任务", "path": "/scheduled-tasks", "icon": "Timer", "sort_order": 8, "roles": "super_admin,approval_admin,operator"},
        {"name": "用户管理", "path": "/users", "icon": "User", "sort_order": 9, "roles": "super_admin"},
        {"name": "注册审批", "path": "/registrations", "icon": "UserFilled", "sort_order": 10, "roles": "super_admin"},
        {"name": "钉钉通道", "path": "/dingtalk", "icon": "ChatDotRound", "sort_order": 11, "roles": "super_admin"},
        {"name": "审计日志", "path": "/audit", "icon": "Tickets", "sort_order": 12},
        {"name": "菜单配置", "path": "/menu-config", "icon": "Menu", "sort_order": 13, "roles": "super_admin"},
    ]
    
    added_count = 0
    for menu_data in required_menus:
        # 检查菜单是否已存在
        existing = db.query(MenuConfig).filter(MenuConfig.path == menu_data["path"]).first()
        if not existing:
            menu = MenuConfig(**menu_data)
            db.add(menu)
            added_count += 1
    
    # 检查监控中心子菜单
    monitor_parent = db.query(MenuConfig).filter(MenuConfig.path == "/monitor").first()
    if monitor_parent:
        child_menus = [
            {"name": "性能监控", "path": "/monitor/performance", "icon": "TrendCharts", "sort_order": 1},
            {"name": "慢查询监控", "path": "/monitor/slow-query", "icon": "Timer", "sort_order": 2},
            {"name": "监控配置", "path": "/monitor/settings", "icon": "Setting", "sort_order": 3},
        ]
        
        for menu_data in child_menus:
            existing = db.query(MenuConfig).filter(MenuConfig.path == menu_data["path"]).first()
            if not existing:
                menu = MenuConfig(**menu_data, parent_id=monitor_parent.id)
                db.add(menu)
                added_count += 1
    
    db.commit()
    
    return MessageResponse(message=f"成功添加 {added_count} 个缺失的菜单")
