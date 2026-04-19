"""
权限管理 API

权限模型：RBAC + 数据权限混合模型
- 功能权限：通过 Permission + RolePermission 管理
- 数据权限（环境权限）：通过 RoleEnvironment 管理
- 用户继承角色的所有权限
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, text
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.permissions import Permission, RolePermission, PermissionCode, DEFAULT_ROLE_PERMISSIONS, RoleEnvironment
from app.models import User, Environment, UserRole
from app.deps import get_current_user
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/api/v1/permissions", tags=["权限管理"])


# ==================== Schema 定义 ====================

class PermissionCreate(BaseModel):
    code: str
    name: str
    category: Optional[str] = "button"
    module: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = 0


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    module: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None
    is_enabled: Optional[bool] = None


class RolePermissionUpdate(BaseModel):
    role: str
    permission_ids: list[int]


class RoleCreate(BaseModel):
    role: str
    permission_ids: list[int] = []


class RoleEnvironmentUpdate(BaseModel):
    """角色环境权限更新"""
    environment_ids: list[int]


class RoleUsersUpdate(BaseModel):
    """角色用户更新"""
    user_ids: list[int]


class BatchAddUsersToRole(BaseModel):
    """批量添加用户到角色"""
    user_ids: list[int]


# ==================== 角色定义（集中管理） ====================

ROLES = [
    {"role": "super_admin", "name": "超级管理员", "description": "系统最高权限，可管理所有功能", "color": "#f56c6c"},
    {"role": "approval_admin", "name": "审批管理员", "description": "负责审批变更请求，可执行SQL", "color": "#e6a23c"},
    {"role": "operator", "name": "运维人员", "description": "可创建变更请求，查看监控，管理实例", "color": "#409eff"},
    {"role": "developer", "name": "开发人员", "description": "可查看监控、SQL编辑器、申请变更", "color": "#67c23a"},
    {"role": "readonly", "name": "只读用户", "description": "仅查看权限，无操作权限", "color": "#909399"}
]


def get_role_info(role_code: str) -> Optional[dict]:
    """获取角色信息"""
    for r in ROLES:
        if r["role"] == role_code:
            return r
    return None


# ==================== 权限管理 API ====================

@router.get("")
async def get_permissions(
    module: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取权限列表（树形结构），含关联菜单信息"""
    # 检查权限
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    service = PermissionService(db)
    permissions = service.get_permissions(module=module, category=category)
    
    # 查询权限码→菜单的映射关系
    from app.models import MenuConfig as MenuConfigModel
    menu_perms = db.query(MenuConfigModel).filter(
        MenuConfigModel.permission.isnot(None),
        MenuConfigModel.is_enabled == True
    ).all()
    
    # 构建 permission_code → [menu_names] 映射
    perm_menu_map: dict[str, list[str]] = {}
    for m in menu_perms:
        if m.permission not in perm_menu_map:
            perm_menu_map[m.permission] = []
        perm_menu_map[m.permission].append(m.name)
    
    # 构建树形结构
    def build_tree(items, parent_id=None):
        result = []
        for item in items:
            if item.parent_id == parent_id:
                node = {
                    "id": item.id,
                    "code": item.code,
                    "name": item.name,
                    "category": item.category,
                    "module": item.module,
                    "description": item.description,
                    "parent_id": item.parent_id,
                    "sort_order": item.sort_order,
                    "is_enabled": item.is_enabled,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "linked_menus": perm_menu_map.get(item.code, []),
                    "children": build_tree(items, item.id)
                }
                result.append(node)
        return result
    
    return {
        "items": build_tree(permissions),
        "total": len(permissions)
    }


@router.post("")
async def create_permission(
    data: PermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建权限"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    service = PermissionService(db)
    
    # 检查权限编码是否已存在
    existing = service.get_permission_by_code(data.code)
    if existing:
        raise HTTPException(status_code=400, detail="权限编码已存在")
    
    permission = service.create_permission(
        code=data.code,
        name=data.name,
        category=data.category,
        module=data.module,
        description=data.description,
        parent_id=data.parent_id,
        sort_order=data.sort_order
    )
    
    return {"success": True, "id": permission.id, "message": "创建成功"}


@router.put("/{permission_id}")
async def update_permission(
    permission_id: int,
    data: PermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新权限"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    service = PermissionService(db)
    
    update_data = data.dict(exclude_unset=True)
    permission = service.update_permission(permission_id, **update_data)
    
    if not permission:
        raise HTTPException(status_code=404, detail="权限不存在")
    
    return {"success": True, "message": "更新成功"}


@router.delete("/{permission_id}")
async def delete_permission(
    permission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除权限"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    service = PermissionService(db)
    
    if not service.delete_permission(permission_id):
        raise HTTPException(status_code=404, detail="权限不存在")
    
    return {"success": True, "message": "删除成功"}


# ==================== 角色权限管理 API ====================

@router.get("/roles/list")
async def get_roles_list(
    current_user: User = Depends(get_current_user)
):
    """
    获取角色列表（用于前端下拉选择）
    
    所有登录用户可访问，返回角色选项列表
    """
    result = []
    for role_info in ROLES:
        result.append({
            "value": role_info["role"],
            "label": role_info["name"],
            "description": role_info["description"],
            "color": role_info.get("color", "#909399")
        })
    
    return {"items": result}


@router.get("/roles")
async def get_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有角色（带统计信息）"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    service = PermissionService(db)
    result = []
    
    for role_info in ROLES:
        role = role_info["role"]
        
        # 获取该角色的权限数量
        perm_count = service.get_role_permission_count(role)
        
        # 获取该角色的用户数量
        user_count = service.get_user_count_by_role(role)
        
        # 获取该角色的环境权限数量
        env_count = service.get_role_environment_count(role)
        
        result.append({
            **role_info,
            "permission_count": perm_count,
            "user_count": user_count,
            "environment_count": env_count
        })
    
    return {"items": result}


@router.get("/roles/{role}")
async def get_role_detail(
    role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取角色详情（包含环境权限、功能权限、用户列表）"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    # 验证角色
    role_info = get_role_info(role)
    if not role_info:
        raise HTTPException(status_code=400, detail="无效的角色")
    
    service = PermissionService(db)
    
    # 获取环境权限
    environment_ids = service.get_role_environment_ids(role)
    
    # 获取环境详情
    environments = []
    if environment_ids:
        envs = db.query(Environment).filter(Environment.id.in_(environment_ids)).all()
        environments = [
            {"id": e.id, "name": e.name, "code": e.code, "color": e.color}
            for e in envs
        ]
    
    # 获取功能权限
    permission_ids = service.get_role_permission_ids(role)
    
    permissions = []
    if permission_ids:
        perms = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
        permissions = [
            {"id": p.id, "code": p.code, "name": p.name, "module": p.module}
            for p in perms
        ]
    
    # 获取用户列表
    users = service.get_users_by_role(role)
    user_list = [
        {
            "id": u.id,
            "username": u.username,
            "real_name": u.real_name,
            "email": u.email,
            "status": u.status,
            "last_login_time": u.last_login_time.isoformat() if u.last_login_time else None
        }
        for u in users
    ]
    
    return {
        "role": role,
        "name": role_info["name"],
        "description": role_info["description"],
        "color": role_info.get("color", "#909399"),
        "environments": environments,
        "environment_ids": environment_ids,
        "permissions": permissions,
        "permission_ids": permission_ids,
        "users": user_list,
        "user_count": len(user_list)
    }


# ==================== 角色环境权限 API ====================

@router.get("/roles/{role}/environments")
async def get_role_environments(
    role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取角色的环境权限"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    # 验证角色
    role_info = get_role_info(role)
    if not role_info:
        raise HTTPException(status_code=400, detail="无效的角色")
    
    service = PermissionService(db)
    
    # 获取角色环境权限
    environment_ids = service.get_role_environment_ids(role)
    
    # 获取所有环境
    all_envs = db.query(Environment).filter(Environment.status).order_by(Environment.id).all()
    
    return {
        "role": role,
        "environment_ids": environment_ids,
        "all_environments": [
            {"id": e.id, "name": e.name, "code": e.code, "color": e.color}
            for e in all_envs
        ]
    }


@router.put("/roles/{role}/environments")
async def update_role_environments(
    role: str,
    data: RoleEnvironmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新角色的环境权限"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    # 验证角色
    role_info = get_role_info(role)
    if not role_info:
        raise HTTPException(status_code=400, detail="无效的角色")
    
    service = PermissionService(db)
    service.update_role_environments(role, data.environment_ids)
    
    return {"success": True, "message": "环境权限更新成功"}


# ==================== 角色功能权限 API ====================


@router.get("/roles/{role}/permissions")
async def get_role_permissions(
    role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取角色的权限列表"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    # 验证角色
    valid_roles = [r["role"] for r in ROLES]
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail="无效的角色")
    
    service = PermissionService(db)
    permission_ids = service.get_role_permission_ids(role)
    
    return {
        "role": role,
        "permission_ids": permission_ids
    }


@router.put("/roles/{role}/permissions")
async def update_role_permissions(
    role: str,
    data: RolePermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新角色权限"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    # 验证角色
    valid_roles = [r["role"] for r in ROLES]
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail="无效的角色")
    
    service = PermissionService(db)
    service.update_role_permissions(role, data.permission_ids)
    
    return {"success": True, "message": "权限更新成功"}


@router.post("/roles/reset-default")
async def reset_default_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重置为默认权限配置"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    service = PermissionService(db)
    
    # 初始化权限数据（如果不存在）
    for role, perm_codes in DEFAULT_ROLE_PERMISSIONS.items():
        for perm_code in perm_codes:
            # 确保权限存在
            perm = service.get_permission_by_code(perm_code)
            if not perm:
                # 根据权限编码推断模块和名称
                module, name = perm_code.split(":")
                perm = service.create_permission(
                    code=perm_code,
                    name=name,
                    module=module,
                    category="button"
                )
            
            # 检查是否已存在关联
            existing = db.query(RolePermission).filter(
                and_(
                    RolePermission.role == role,
                    RolePermission.permission_id == perm.id
                )
            ).first()
            
            if not existing:
                role_perm = RolePermission(role=role, permission_id=perm.id)
                db.add(role_perm)
    
    db.commit()
    return {"success": True, "message": "权限已重置为默认配置"}


# ==================== 用户权限查询 API ====================

@router.get("/my-permissions")
async def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取当前用户的权限列表"""
    service = PermissionService(db)
    role = current_user.role
    
    # 获取角色的权限
    permission_ids = service.get_role_permission_ids(role)
    
    # 获取权限详情
    permissions = db.query(Permission).filter(Permission.id.in_(permission_ids)).all()
    
    return {
        "role": role,
        "permissions": [
            {
                "code": p.code,
                "name": p.name,
                "module": p.module
            }
            for p in permissions
        ],
        "permission_codes": [p.code for p in permissions]
    }


@router.get("/check/{permission_code}")
async def check_permission(
    permission_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """检查当前用户是否有指定权限"""
    service = PermissionService(db)
    role = current_user.role
    
    # 获取权限
    perm = service.get_permission_by_code(permission_code)
    if not perm:
        return {"has_permission": False, "message": "权限不存在"}
    
    # 检查角色权限
    permission_ids = service.get_role_permission_ids(role)
    
    return {"has_permission": perm.id in permission_ids}


# ==================== 角色用户管理 API ====================

@router.get("/roles/{role}/available-users")
async def get_available_users_for_role(
    role: str,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取可添加到该角色的用户列表（不属于该角色的用户）"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    # 验证角色
    role_info = get_role_info(role)
    if not role_info:
        raise HTTPException(status_code=400, detail="无效的角色")
    
    service = PermissionService(db)
    users = service.get_users_not_in_role(role, search=search, limit=100)
    
    return {
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "real_name": u.real_name,
                "email": u.email,
                "role": u.role.value if isinstance(u.role, UserRole) else u.role,
                "status": u.status
            }
            for u in users
        ],
        "total": len(users)
    }


@router.post("/roles/{role}/users")
async def add_users_to_role(
    role: str,
    data: BatchAddUsersToRole,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量添加用户到角色"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    # 验证角色
    role_info = get_role_info(role)
    if not role_info:
        raise HTTPException(status_code=400, detail="无效的角色")
    
    if not data.user_ids:
        raise HTTPException(status_code=400, detail="请选择要添加的用户")
    
    service = PermissionService(db)
    
    # 更新用户角色
    updated_count = 0
    for user_id in data.user_ids:
        if service.update_user_role(user_id, role):
            updated_count += 1
    
    return {
        "success": True,
        "message": f"成功添加 {updated_count} 个用户到角色",
        "updated_count": updated_count
    }


@router.put("/roles/{role}/users")
async def update_role_users(
    role: str,
    data: RoleUsersUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """设置角色的用户列表（替换模式）"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    # 验证角色
    role_info = get_role_info(role)
    if not role_info:
        raise HTTPException(status_code=400, detail="无效的角色")
    
    service = PermissionService(db)
    
    # 获取当前属于该角色的用户
    current_users = service.get_users_by_role(role)
    current_user_ids = {u.id for u in current_users}
    
    # 新用户ID集合
    new_user_ids = set(data.user_ids)
    
    # 需要移除的用户（从角色移除，设为只读用户）
    to_remove = current_user_ids - new_user_ids
    for user_id in to_remove:
        service.update_user_role(user_id, "readonly")
    
    # 需要添加的用户
    to_add = new_user_ids - current_user_ids
    for user_id in to_add:
        service.update_user_role(user_id, role)
    
    return {
        "success": True,
        "message": f"已更新用户列表：添加 {len(to_add)} 人，移除 {len(to_remove)} 人"
    }


@router.delete("/roles/{role}/users/{user_id}")
async def remove_user_from_role(
    role: str,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """从角色中移除用户"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    # 验证角色
    role_info = get_role_info(role)
    if not role_info:
        raise HTTPException(status_code=400, detail="无效的角色")
    
    service = PermissionService(db)
    
    # 获取用户
    users = service.get_users_by_role(role)
    user = next((u for u in users if u.id == user_id), None)
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在或不属于此角色")
    
    # 将用户角色改为只读
    service.update_user_role(user_id, "readonly")
    
    return {"success": True, "message": "已将用户从角色中移除"}


@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: int,
    role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """修改单个用户的角色"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    # 验证角色
    role_info = get_role_info(role)
    if not role_info:
        raise HTTPException(status_code=400, detail="无效的角色")
    
    service = PermissionService(db)
    
    # 不能修改自己的角色
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")
    
    # 获取用户
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # 修改用户角色
    old_role = user.role.value if isinstance(user.role, UserRole) else user.role
    service.update_user_role(user_id, role)
    
    return {
        "success": True,
        "message": f"用户角色已从 {old_role} 改为 {role}"
    }


# ==================== 菜单预览 API ====================

@router.get("/menu-preview/{role}")
async def get_menu_preview(
    role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    预览指定角色能看到的导航菜单
    
    用于权限管理页面的"所见即所得"预览功能，
    根据角色当前绑定的权限码，实时计算可见的菜单树。
    """
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    from app.models import MenuConfig
    from app.api.menu import build_menu_tree, filter_menu_by_role
    
    # 获取所有启用的菜单
    menus = db.query(MenuConfig).filter(
        MenuConfig.is_visible == True,
        MenuConfig.is_enabled == True
    ).order_by(MenuConfig.sort_order).all()
    
    # 获取角色权限
    service = PermissionService(db)
    role_value = role
    user_permissions = service.get_role_permissions(role_value)
    
    # 构建菜单树
    menu_tree = build_menu_tree(menus)
    
    # 根据权限过滤
    role_enum = UserRole(role_value) if role_value in [e.value for e in UserRole] else role_value
    filtered_menus = filter_menu_by_role(menu_tree, role_enum, user_permissions)
    
    # 转换为前端需要的格式
    def to_menu_item(menus: list) -> list:
        result = []
        for menu in menus:
            item = {
                "id": menu["id"],
                "name": menu["name"],
                "path": menu.get("path") or "",
                "icon": menu.get("icon"),
            }
            if menu.get("children"):
                item["children"] = to_menu_item(menu["children"])
            result.append(item)
        return result
    
    return {
        "role": role,
        "menus": to_menu_item(filtered_menus),
        "permission_count": len(user_permissions),
        "menu_count": sum(1 for m in menus if m.permission and m.permission in user_permissions)
    }
