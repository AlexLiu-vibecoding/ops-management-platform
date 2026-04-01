"""
异步 Service 层基类

提供异步 CRUD 操作封装，用于高性能异步数据库操作

使用方式：
```python
from app.services.base_async import AsyncBaseService
from app.database_async import get_async_db_context

class AsyncUserService(AsyncBaseService[User]):
    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()

# 在异步端点中使用
async with get_async_db_context() as db:
    user_service = AsyncUserService(User, db)
    user = await user_service.get_by_username("admin")
```
"""
from typing import TypeVar, Generic, Type, List, Optional, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base


# 泛型类型变量
ModelType = TypeVar("ModelType", bound=Base)


class AsyncBaseService(Generic[ModelType]):
    """
    异步 Service 层基类
    
    提供异步 CRUD 操作，适用于高并发场景
    
    使用示例：
    ```python
    class AsyncUserService(AsyncBaseService[User]):
        def __init__(self, db: AsyncSession):
            super().__init__(User, db)
        
        async def get_by_username(self, username: str) -> Optional[User]:
            result = await self.db.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()
    ```
    """
    
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """
        初始化异步 Service
        
        Args:
            model: SQLAlchemy 模型类
            db: 异步数据库会话
        """
        self.model = model
        self.db = db
    
    async def get(self, id: int) -> Optional[ModelType]:
        """
        根据 ID 获取单个记录
        
        Args:
            id: 记录 ID
        
        Returns:
            模型实例或 None
        """
        result = await self.db.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        order_by: Any = None
    ) -> List[ModelType]:
        """
        获取多条记录（分页）
        
        Args:
            skip: 跳过记录数
            limit: 返回记录数
            order_by: 排序字段
        
        Returns:
            模型实例列表
        """
        query = select(self.model)
        if order_by is not None:
            query = query.order_by(order_by)
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        创建记录
        
        Args:
            obj_in: 创建数据字典
        
        Returns:
            创建的模型实例
        """
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update(self, id: int, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """
        更新记录
        
        Args:
            id: 记录 ID
            obj_in: 更新数据字典
        
        Returns:
            更新后的模型实例或 None
        """
        db_obj = await self.get(id)
        if db_obj is None:
            return None
        
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def delete(self, id: int) -> bool:
        """
        删除记录
        
        Args:
            id: 记录 ID
        
        Returns:
            是否删除成功
        """
        db_obj = await self.get(id)
        if db_obj is None:
            return False
        
        await self.db.delete(db_obj)
        await self.db.flush()
        return True
    
    async def count(self) -> int:
        """
        获取记录总数
        
        Returns:
            记录总数
        """
        result = await self.db.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()
    
    async def exists(self, id: int) -> bool:
        """
        检查记录是否存在
        
        Args:
            id: 记录 ID
        
        Returns:
            是否存在
        """
        result = await self.db.execute(
            select(func.count()).select_from(self.model).where(self.model.id == id)
        )
        return result.scalar_one() > 0
    
    async def get_by_field(self, field_name: str, value: Any) -> Optional[ModelType]:
        """
        根据字段值获取记录
        
        Args:
            field_name: 字段名
            value: 字段值
        
        Returns:
            模型实例或 None
        """
        field = getattr(self.model, field_name)
        result = await self.db.execute(
            select(self.model).where(field == value)
        )
        return result.scalar_one_or_none()
    
    async def get_multi_by_field(
        self, 
        field_name: str, 
        value: Any,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        根据字段值获取多条记录
        
        Args:
            field_name: 字段名
            value: 字段值
            skip: 跳过记录数
            limit: 返回记录数
        
        Returns:
            模型实例列表
        """
        field = getattr(self.model, field_name)
        query = select(self.model).where(field == value).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
