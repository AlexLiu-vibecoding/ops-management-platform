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
"""

from app.services.base import BaseService
from app.services.user_service import UserService
from app.services.instance_service import RDBInstanceService, RedisInstanceService
from app.services.permission_service import PermissionService, BatchOperationService

__all__ = [
    # 基类
    "BaseService",
    # 用户服务
    "UserService",
    # 实例服务
    "RDBInstanceService",
    "RedisInstanceService",
    # 权限服务
    "PermissionService",
    "BatchOperationService",
]
