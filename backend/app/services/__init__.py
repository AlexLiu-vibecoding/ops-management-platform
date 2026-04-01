"""
Service 层模块

分层架构规范：
- API 层：接收请求、参数校验、调用 Service、返回响应
- Service 层：业务逻辑处理、事务管理、跨模块协调
- Model 层：数据库操作

使用规范：
1. API 层禁止直接操作数据库，必须通过 Service 层
2. Service 层负责业务逻辑，返回业务对象或 DTO
3. 复杂查询可在 Service 层使用 joinedload 预加载

异步操作：
- 高并发场景推荐使用异步 Service（AsyncXxxService）
- 异步 Service 使用 AsyncSession，通过 get_async_db_context() 获取

使用示例：
```python
# 同步 Service
from app.services import UserService

def list_users(db: Session = Depends(get_db)):
    user_service = UserService(db)
    return user_service.get_multi_with_count()

# 异步 Service
from app.services import AsyncUserService
from app.database_async import get_async_db_context

async def list_users_async():
    async with get_async_db_context() as db:
        user_service = AsyncUserService(db)
        return await user_service.get_multi_with_count()
```
"""

from app.services.base import BaseService
from app.services.base_async import AsyncBaseService
from app.services.user_service import UserService
from app.services.user_service_async import AsyncUserService
from app.services.instance_service import RDBInstanceService, RedisInstanceService
from app.services.instance_service_async import AsyncRDBInstanceService, AsyncRedisInstanceService
from app.services.permission_service import PermissionService, BatchOperationService
from app.services.permission_service_async import AsyncPermissionService

__all__ = [
    # 同步基类
    "BaseService",
    # 异步基类
    "AsyncBaseService",
    # 同步用户服务
    "UserService",
    # 异步用户服务
    "AsyncUserService",
    # 同步实例服务
    "RDBInstanceService",
    "RedisInstanceService",
    # 异步实例服务
    "AsyncRDBInstanceService",
    "AsyncRedisInstanceService",
    # 同步权限服务
    "PermissionService",
    "BatchOperationService",
    # 异步权限服务
    "AsyncPermissionService",
]
