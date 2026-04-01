"""
异步实例服务层

提供异步的实例操作，适用于高并发场景

使用方式：
```python
from app.services.instance_service_async import AsyncRDBInstanceService
from app.database_async import get_async_db_context

async with get_async_db_context() as db:
    instance_service = AsyncRDBInstanceService(db)
    instances, total = await instance_service.get_multi_with_environment()
```
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.services.base_async import AsyncBaseService
from app.models import RDBInstance, RedisInstance, Environment
from app.utils.auth import encrypt_instance_password, decrypt_instance_password
from app.utils.structured_logger import get_logger

logger = get_logger(__name__)


class AsyncRDBInstanceService(AsyncBaseService[RDBInstance]):
    """
    异步 RDB 实例服务类
    
    处理 MySQL/PostgreSQL 实例的业务逻辑（异步版本）
    """
    
    def __init__(self, db: AsyncSession):
        super().__init__(RDBInstance, db)
    
    async def get_with_environment(self, instance_id: int) -> Optional[RDBInstance]:
        """
        获取实例详情（预加载环境信息）
        
        Args:
            instance_id: 实例 ID
        
        Returns:
            实例实例或 None
        """
        result = await self.db.execute(
            select(RDBInstance)
            .options(joinedload(RDBInstance.environment))
            .where(RDBInstance.id == instance_id)
        )
        return result.scalar_one_or_none()
    
    async def get_multi_with_environment(
        self,
        skip: int = 0,
        limit: int = 20,
        environment_id: Optional[int] = None,
        group_id: Optional[int] = None,
        db_type: Optional[str] = None,
        status: Optional[bool] = None
    ) -> tuple[List[RDBInstance], int]:
        """
        获取实例列表（预加载环境信息）
        
        Args:
            skip: 跳过记录数
            limit: 返回记录数
            environment_id: 环境ID过滤
            group_id: 分组ID过滤
            db_type: 数据库类型过滤
            status: 状态过滤
        
        Returns:
            (实例列表, 总数)
        """
        # 构建查询条件
        conditions = []
        if environment_id:
            conditions.append(RDBInstance.environment_id == environment_id)
        if group_id:
            conditions.append(RDBInstance.group_id == group_id)
        if db_type:
            conditions.append(RDBInstance.db_type == db_type)
        if status is not None:
            conditions.append(RDBInstance.status == status)
        
        # 查询总数
        count_query = select(func.count()).select_from(RDBInstance)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 查询列表
        query = (
            select(RDBInstance)
            .options(selectinload(RDBInstance.environment))
        )
        if conditions:
            query = query.where(and_(*conditions))
        query = query.offset(skip).limit(limit).order_by(RDBInstance.id.desc())
        
        result = await self.db.execute(query)
        instances = list(result.unique().scalars().all())
        
        logger.debug(
            "查询RDB实例列表",
            total=total,
            returned=len(instances),
            filters={
                "environment_id": environment_id,
                "db_type": db_type,
                "status": status
            }
        )
        
        return instances, total
    
    async def get_by_name(self, name: str) -> Optional[RDBInstance]:
        """
        根据名称获取实例
        
        Args:
            name: 实例名称
        
        Returns:
            实例实例或 None
        """
        result = await self.db.execute(
            select(RDBInstance).where(RDBInstance.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_by_environment(self, environment_id: int) -> List[RDBInstance]:
        """
        获取指定环境的所有实例
        
        Args:
            environment_id: 环境 ID
        
        Returns:
            实例列表
        """
        result = await self.db.execute(
            select(RDBInstance)
            .where(RDBInstance.environment_id == environment_id)
            .order_by(RDBInstance.name)
        )
        return list(result.scalars().all())
    
    async def count_by_environment(self, environment_id: int) -> int:
        """
        统计指定环境的实例数量
        
        Args:
            environment_id: 环境 ID
        
        Returns:
            实例数量
        """
        result = await self.db.execute(
            select(func.count())
            .select_from(RDBInstance)
            .where(RDBInstance.environment_id == environment_id)
        )
        return result.scalar()
    
    async def get_active_instances(self) -> List[RDBInstance]:
        """
        获取所有启用的实例
        
        Returns:
            启用的实例列表
        """
        result = await self.db.execute(
            select(RDBInstance)
            .where(RDBInstance.status == True)
            .order_by(RDBInstance.name)
        )
        return list(result.scalars().all())


class AsyncRedisInstanceService(AsyncBaseService[RedisInstance]):
    """
    异步 Redis 实例服务类
    
    处理 Redis 实例的业务逻辑（异步版本）
    """
    
    def __init__(self, db: AsyncSession):
        super().__init__(RedisInstance, db)
    
    async def get_with_environment(self, instance_id: int) -> Optional[RedisInstance]:
        """
        获取实例详情（预加载环境信息）
        
        Args:
            instance_id: 实例 ID
        
        Returns:
            实例实例或 None
        """
        result = await self.db.execute(
            select(RedisInstance)
            .options(joinedload(RedisInstance.environment))
            .where(RedisInstance.id == instance_id)
        )
        return result.scalar_one_or_none()
    
    async def get_multi_with_environment(
        self,
        skip: int = 0,
        limit: int = 20,
        environment_id: Optional[int] = None,
        status: Optional[bool] = None
    ) -> tuple[List[RedisInstance], int]:
        """
        获取实例列表（预加载环境信息）
        
        Args:
            skip: 跳过记录数
            limit: 返回记录数
            environment_id: 环境ID过滤
            status: 状态过滤
        
        Returns:
            (实例列表, 总数)
        """
        conditions = []
        if environment_id:
            conditions.append(RedisInstance.environment_id == environment_id)
        if status is not None:
            conditions.append(RedisInstance.status == status)
        
        # 查询总数
        count_query = select(func.count()).select_from(RedisInstance)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 查询列表
        query = (
            select(RedisInstance)
            .options(selectinload(RedisInstance.environment))
        )
        if conditions:
            query = query.where(and_(*conditions))
        query = query.offset(skip).limit(limit).order_by(RedisInstance.id.desc())
        
        result = await self.db.execute(query)
        instances = list(result.unique().scalars().all())
        
        return instances, total
    
    async def get_by_name(self, name: str) -> Optional[RedisInstance]:
        """
        根据名称获取实例
        
        Args:
            name: 实例名称
        
        Returns:
            实例实例或 None
        """
        result = await self.db.execute(
            select(RedisInstance).where(RedisInstance.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_active_instances(self) -> List[RedisInstance]:
        """
        获取所有启用的实例
        
        Returns:
            启用的实例列表
        """
        result = await self.db.execute(
            select(RedisInstance)
            .where(RedisInstance.status == True)
            .order_by(RedisInstance.name)
        )
        return list(result.scalars().all())


# ==================== 导出 ====================

__all__ = [
    "AsyncRDBInstanceService",
    "AsyncRedisInstanceService",
]
