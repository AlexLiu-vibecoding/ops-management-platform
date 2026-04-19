"""
用户管理API

注意：环境权限现在由角色控制，不再绑定到单个用户
用户的环境权限 = 用户所属角色的环境权限
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserUpdate, UserResponse, MessageResponse
from app.deps import require_permission, get_current_user
from app.services import UserService

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("")
async def list_users(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_permission("system:user_manage")),
    db: Session = Depends(get_db)
):
    """获取用户列表（需要权限）"""
    user_service = UserService(db)
    users, total = user_service.get_multi_with_count(skip=skip, limit=limit)
    return {
        "total": total,
        "items": [UserResponse.model_validate(u) for u in users]
    }


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_permission("system:user_manage")),
    db: Session = Depends(get_db)
):
    """获取用户详情"""
    user_service = UserService(db)
    user = user_service.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserResponse.model_validate(user)


@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_permission("system:user_manage")),
    db: Session = Depends(get_db)
):
    """创建用户（仅超级管理员）"""
    user_service = UserService(db)
    user = user_service.create_user(
        username=user_data.username,
        password=user_data.password,
        real_name=user_data.real_name,
        email=user_data.email,
        role=user_data.role,
        phone=user_data.phone
    )
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_permission("system:user_manage")),
    db: Session = Depends(get_db)
):
    """更新用户（仅超级管理员）"""
    user_service = UserService(db)
    user = user_service.update_user(
        user_id=user_id,
        real_name=user_data.real_name,
        email=user_data.email,
        phone=user_data.phone,
        role=user_data.role,
        status=user_data.status
    )
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_permission("system:user_manage")),
    db: Session = Depends(get_db)
):
    """删除用户（仅超级管理员）"""
    user_service = UserService(db)
    user_service.delete_user(user_id, operator_id=current_user.id)
    return MessageResponse(message="用户删除成功")


@router.post("/{user_id}/reset-password", response_model=MessageResponse)
async def reset_user_password(
    user_id: int,
    new_password: str,
    current_user: User = Depends(require_permission("system:user_manage")),
    db: Session = Depends(get_db)
):
    """重置用户密码（仅超级管理员）"""
    user_service = UserService(db)
    success = user_service.update_password(user_id, new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return MessageResponse(message="密码重置成功")


@router.get("/{user_id}/environments")
async def get_user_environments(
    user_id: int,
    current_user: User = Depends(require_permission("system:user_manage")),
    db: Session = Depends(get_db)
):
    """
    获取用户的环境权限
    
    注意：环境权限现在由角色控制
    用户的环境权限 = 用户所属角色的环境权限
    """
    user_service = UserService(db)
    return user_service.get_user_environments(user_id)


@router.post("/{user_id}/environments", response_model=MessageResponse)
async def bind_user_environments(
    user_id: int,
    environment_ids: list[int],
    current_user: User = Depends(require_permission("system:user_manage")),
    db: Session = Depends(get_db)
):
    """
    绑定用户环境权限（已废弃）
    
    注意：环境权限现在由角色控制，此接口仅保留兼容性
    如需修改环境权限，请前往角色管理页面修改角色的环境权限
    """
    return MessageResponse(
        message="环境权限现在由角色控制，请前往角色管理页面修改角色的环境权限"
    )
