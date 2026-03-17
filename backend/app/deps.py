"""
FastAPI依赖项
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.auth import decode_access_token
from app.models import User, UserRole

# HTTP Bearer认证
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前登录用户
    
    Args:
        credentials: HTTP认证凭据
        db: 数据库会话
    
    Returns:
        当前用户对象
    
    Raises:
        HTTPException: 无效的认证凭据
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    if not user.status:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前活跃用户
    
    Args:
        current_user: 当前用户
    
    Returns:
        当前活跃用户
    
    Raises:
        HTTPException: 用户未激活
    """
    if not current_user.status:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户未激活"
        )
    return current_user


def check_permission(required_role: UserRole):
    """
    检查用户权限装饰器
    
    Args:
        required_role: 需要的角色
    
    Returns:
        权限检查函数
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        # 角色权限层级：超级管理员 > 审批管理员 > 普通运维 > 只读用户
        role_hierarchy = {
            UserRole.SUPER_ADMIN: 4,
            UserRole.APPROVAL_ADMIN: 3,
            UserRole.OPERATOR: 2,
            UserRole.READONLY: 1
        }
        
        user_level = role_hierarchy.get(current_user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足"
            )
        
        return current_user
    
    return permission_checker


async def get_super_admin(
    current_user: User = Depends(check_permission(UserRole.SUPER_ADMIN))
) -> User:
    """获取超级管理员"""
    return current_user


async def get_approval_admin(
    current_user: User = Depends(check_permission(UserRole.APPROVAL_ADMIN))
) -> User:
    """获取审批管理员（及以上）"""
    return current_user


async def get_operator(
    current_user: User = Depends(check_permission(UserRole.OPERATOR))
) -> User:
    """获取运维用户（及以上）"""
    return current_user
