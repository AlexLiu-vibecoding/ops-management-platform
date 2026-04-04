"""
异步用户服务层

提供异步用户操作，适用于高并发场景

使用方式：
```python
from app.services.user_service_async import AsyncUserService
from app.database_async import get_async_db_context

async with get_async_db_context() as db:
    user_service = AsyncUserService(db)
    user = await user_service.authenticate("admin", "password")
```
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.services.base_async import AsyncBaseService
from app.models import User, UserRole
from app.utils.auth import hash_password, verify_password


class AsyncUserService(AsyncBaseService[User]):
    """
    异步用户服务类
    
    提供异步用户 CRUD 和认证操作
    """
    
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)
    
    # ==================== 查询方法 ====================
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名获取用户
        
        Args:
            username: 用户名
        
        Returns:
            用户实例或 None
        """
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """
        根据邮箱获取用户
        
        Args:
            email: 邮箱
        
        Returns:
            用户实例或 None
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_multi_with_count(
        self,
        skip: int = 0,
        limit: int = 20,
        role: Optional[UserRole] = None,
        status: Optional[bool] = None
    ) -> tuple[list[User], int]:
        """
        获取用户列表及总数
        
        Args:
            skip: 跳过记录数
            limit: 返回记录数
            role: 角色过滤
            status: 状态过滤
        
        Returns:
            (用户列表, 总数)
        """
        # 构建查询
        query = select(User)
        count_query = select(User)
        
        if role is not None:
            query = query.where(User.role == role)
            count_query = count_query.where(User.role == role)
        if status is not None:
            query = query.where(User.status == status)
            count_query = count_query.where(User.status == status)
        
        # 获取总数
        from sqlalchemy import func
        count_result = await self.db.execute(
            select(func.count()).select_from(count_query.subquery())
        )
        total = count_result.scalar_one()
        
        # 获取列表
        result = await self.db.execute(
            query.offset(skip).limit(limit)
        )
        users = list(result.scalars().all())
        
        return users, total
    
    # ==================== 创建方法 ====================
    
    async def create_user(
        self,
        username: str,
        password: str,
        real_name: str,
        email: str,
        role: UserRole = UserRole.READONLY,
        phone: Optional[str] = None
    ) -> User:
        """
        创建用户（包含业务校验）
        
        Args:
            username: 用户名
            password: 密码
            real_name: 真实姓名
            email: 邮箱
            role: 角色
            phone: 手机号
        
        Returns:
            创建的用户实例
        
        Raises:
            ValueError: 用户名或邮箱已存在
        """
        # 检查用户名是否已存在
        if await self.get_by_username(username):
            raise ValueError(f"用户名 '{username}' 已存在")
        
        # 检查邮箱是否已存在
        if await self.get_by_email(email):
            raise ValueError(f"邮箱 '{email}' 已被使用")
        
        # 创建用户
        user_data = {
            "username": username,
            "password_hash": hash_password(password),
            "real_name": real_name,
            "email": email,
            "role": role,
            "phone": phone,
            "status": True
        }
        
        return await self.create(user_data)
    
    # ==================== 更新方法 ====================
    
    async def update_user(
        self,
        user_id: int,
        real_name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        role: Optional[UserRole] = None,
        status: Optional[bool] = None
    ) -> Optional[User]:
        """
        更新用户信息
        
        Args:
            user_id: 用户 ID
            real_name: 真实姓名
            email: 邮箱
            phone: 手机号
            role: 角色
            status: 状态
        
        Returns:
            更新后的用户实例
        
        Raises:
            ValueError: 用户不存在或邮箱已被使用
        """
        user = await self.get(user_id)
        if not user:
            raise ValueError(f"用户 ID {user_id} 不存在")
        
        # 检查邮箱是否被其他用户使用
        if email and email != user.email:
            existing = await self.get_by_email(email)
            if existing:
                raise ValueError(f"邮箱 '{email}' 已被使用")
        
        update_data = {}
        if real_name is not None:
            update_data["real_name"] = real_name
        if email is not None:
            update_data["email"] = email
        if phone is not None:
            update_data["phone"] = phone
        if role is not None:
            update_data["role"] = role
        if status is not None:
            update_data["status"] = status
        
        return await self.update(user_id, update_data)
    
    async def update_password(self, user_id: int, new_password: str) -> bool:
        """
        更新用户密码
        
        Args:
            user_id: 用户 ID
            new_password: 新密码
        
        Returns:
            是否更新成功
        """
        return await self.update(user_id, {
            "password_hash": hash_password(new_password)
        }) is not None
    
    async def update_last_login(self, user_id: int, ip: str) -> bool:
        """
        更新最后登录信息
        
        Args:
            user_id: 用户 ID
            ip: 登录 IP
        
        Returns:
            是否更新成功
        """
        from datetime import datetime
        
        return await self.update(user_id, {
            "last_login_time": datetime.now(),
            "last_login_ip": ip
        }) is not None
    
    # ==================== 认证方法 ====================
    
    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        验证用户凭证
        
        Args:
            username: 用户名
            password: 密码
        
        Returns:
            验证成功返回用户实例，失败返回 None
        """
        user = await self.get_by_username(username)
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        if not user.status:
            return None
        
        return user


# 导出
__all__ = ["AsyncUserService"]
