"""
FastAPI依赖项
"""
from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.utils.auth import decode_access_token
from app.models import User, UserRole
from app.models.permissions import RoleEnvironment

# HTTP Bearer认证
security = HTTPBearer(auto_error=False)


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
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 检查是否提供了凭据
    if credentials is None:
        raise credentials_exception
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise credentials_exception
    
    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    # 处理 sub 可能是字符串的情况
    if isinstance(user_id, str):
        try:
            user_id = int(user_id)
        except ValueError:
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


# ==================== 环境权限校验 ====================

def get_user_environment_ids(db: Session, user: User) -> List[int]:
    """
    获取用户可访问的环境ID列表
    
    用户的环境权限 = 用户所属角色的环境权限
    
    Args:
        db: 数据库会话
        user: 用户对象
    
    Returns:
        环境ID列表
    """
    role = user.role.value if isinstance(user.role, UserRole) else user.role
    
    # 从 RoleEnvironment 表获取角色的环境权限
    role_envs = db.query(RoleEnvironment).filter(RoleEnvironment.role == role).all()
    return [re.environment_id for re in role_envs]


def check_environment_access(db: Session, user: User, environment_id: int) -> bool:
    """
    检查用户是否有权限访问指定环境
    
    Args:
        db: 数据库会话
        user: 用户对象
        environment_id: 环境ID
    
    Returns:
        是否有权限
    """
    # 超级管理员有所有环境的访问权限
    if user.role == UserRole.SUPER_ADMIN:
        return True
    
    allowed_env_ids = get_user_environment_ids(db, user)
    return environment_id in allowed_env_ids


async def require_environment_access(
    environment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> int:
    """
    要求用户有指定环境的访问权限（依赖注入用）
    
    Args:
        environment_id: 环境ID
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        环境ID
    
    Raises:
        HTTPException: 无权限访问该环境
    """
    if not check_environment_access(db, current_user, environment_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限访问该环境"
        )
    return environment_id
