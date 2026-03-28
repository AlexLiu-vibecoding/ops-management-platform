"""
权限管理 API
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.permissions import Permission, RolePermission, PermissionCode, DEFAULT_ROLE_PERMISSIONS
from app.models import User
from app.deps import get_current_user

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
    permission_ids: List[int]


class RoleCreate(BaseModel):
    role: str
    permission_ids: List[int] = []


# ==================== 权限管理 API ====================

@router.get("")
async def get_permissions(
    module: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取权限列表（树形结构）"""
    # 检查权限
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    query = db.query(Permission)
    if module:
        query = query.filter(Permission.module == module)
    if category:
        query = query.filter(Permission.category == category)
    
    permissions = query.order_by(Permission.sort_order, Permission.id).all()
    
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
    
    # 检查权限编码是否已存在
    existing = db.query(Permission).filter(Permission.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="权限编码已存在")
    
    permission = Permission(
        code=data.code,
        name=data.name,
        category=data.category,
        module=data.module,
        description=data.description,
        parent_id=data.parent_id,
        sort_order=data.sort_order
    )
    db.add(permission)
    db.commit()
    db.refresh(permission)
    
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
    
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=404, detail="权限不存在")
    
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(permission, key, value)
    
    db.commit()
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
    
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(status_code=404, detail="权限不存在")
    
    # 删除关联的角色权限
    db.query(RolePermission).filter(RolePermission.permission_id == permission_id).delete()
    db.delete(permission)
    db.commit()
    
    return {"success": True, "message": "删除成功"}


# ==================== 角色权限管理 API ====================

# 角色定义
ROLES = [
    {"role": "super_admin", "name": "超级管理员", "description": "系统最高权限，可管理所有功能"},
    {"role": "approval_admin", "name": "审批管理员", "description": "负责审批变更请求，可执行SQL"},
    {"role": "operator", "name": "运维人员", "description": "可创建变更请求，查看监控，管理实例"},
    {"role": "developer", "name": "开发人员", "description": "可查看监控、SQL编辑器、申请变更"},
    {"role": "readonly", "name": "只读用户", "description": "仅查看权限，无操作权限"}
]


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
            "description": role_info["description"]
        })
    
    return {"items": result}


@router.get("/roles")
async def get_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有角色"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    result = []
    for role_info in ROLES:
        role = role_info["role"]
        # 获取该角色的权限数量
        perm_count = db.query(RolePermission).filter(RolePermission.role == role).count()
        result.append({
            **role_info,
            "permission_count": perm_count
        })
    
    return {"items": result}


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
    
    # 获取角色权限
    role_perms = db.query(RolePermission).filter(RolePermission.role == role).all()
    permission_ids = [rp.permission_id for rp in role_perms]
    
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
    
    # 删除原有权限
    db.query(RolePermission).filter(RolePermission.role == role).delete()
    
    # 添加新权限
    for perm_id in data.permission_ids:
        role_perm = RolePermission(role=role, permission_id=perm_id)
        db.add(role_perm)
    
    db.commit()
    
    return {"success": True, "message": "权限更新成功"}


@router.post("/roles/reset-default")
async def reset_default_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重置为默认权限配置"""
    if current_user.role not in ["super_admin"]:
        raise HTTPException(status_code=403, detail="无权限访问")
    
    # 初始化权限数据（如果不存在）
    for role, perm_codes in DEFAULT_ROLE_PERMISSIONS.items():
        for perm_code in perm_codes:
            # 确保权限存在
            perm = db.query(Permission).filter(Permission.code == perm_code).first()
            if not perm:
                # 根据权限编码推断模块和名称
                module, name = perm_code.split(":")
                module_names = {
                    "instance": "实例管理",
                    "environment": "环境管理",
                    "approval": "变更管理",
                    "monitor": "监控管理",
                    "script": "脚本管理",
                    "system": "系统管理"
                }
                perm = Permission(
                    code=perm_code,
                    name=name,
                    module=module,
                    category="button"
                )
                db.add(perm)
                db.flush()
            
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
    role = current_user.role
    
    # 获取角色的权限
    role_perms = db.query(RolePermission).filter(RolePermission.role == role).all()
    permission_ids = [rp.permission_id for rp in role_perms]
    
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
    role = current_user.role
    
    # 获取权限
    perm = db.query(Permission).filter(Permission.code == permission_code).first()
    if not perm:
        return {"has_permission": False, "message": "权限不存在"}
    
    # 检查角色权限
    role_perm = db.query(RolePermission).filter(
        and_(
            RolePermission.role == role,
            RolePermission.permission_id == perm.id
        )
    ).first()
    
    return {"has_permission": role_perm is not None}
