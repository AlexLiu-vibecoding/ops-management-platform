"""
依赖注入容器

提供 Service 层的依赖注入管理，支持：
- 服务工厂注册
- 请求级别实例（每次请求创建新实例）
- 单例模式（无状态服务）
- 测试时轻松替换实现

使用示例：
```python
# 在 API 层使用
from app.container import get_user_service, get_permission_service

@router.get("/users")
def list_users(
    user_service: UserService = get_user_service(),
    current_user: User = Depends(get_current_user)
):
    return user_service.get_multi_with_count()

# 在测试中替换实现
from app.container import container

def test_with_mock():
    mock_service = MockUserService()
    container.register_singleton(UserService, mock_service)
    # 测试代码...
```
"""
from typing import TypeVar, Callable, Dict, Type, Optional, Any
from functools import lru_cache
from sqlalchemy.orm import Session

from app.database import get_db


T = TypeVar('T')


class ServiceContainer:
    """
    简单的依赖注入容器
    
    设计原则：
    - 轻量级，不引入复杂的 DI 框架
    - 与 FastAPI 的 Depends 系统无缝集成
    - 支持测试时替换实现
    """
    
    def __init__(self):
        self._factories: Dict[Type, Callable] = {}
        self._singletons: Dict[Type, Any] = {}
        self._request_factories: Dict[Type, Callable] = {}
    
    def register_factory(
        self, 
        service_type: Type[T], 
        factory: Callable[..., T]
    ) -> None:
        """
        注册服务工厂
        
        Args:
            service_type: 服务类型
            factory: 工厂函数，接收 db 参数
        """
        self._factories[service_type] = factory
    
    def register_singleton(self, service_type: Type[T], instance: T) -> None:
        """
        注册单例实例
        
        Args:
            service_type: 服务类型
            instance: 单例实例
        """
        self._singletons[service_type] = instance
    
    def register_request_factory(
        self,
        service_type: Type[T],
        factory: Callable[[Session], T]
    ) -> None:
        """
        注册请求级别服务工厂
        
        每次请求都会创建新实例
        
        Args:
            service_type: 服务类型
            factory: 工厂函数，接收 db Session
        """
        self._request_factories[service_type] = factory
    
    def get_singleton(self, service_type: Type[T]) -> Optional[T]:
        """
        获取单例实例
        
        Args:
            service_type: 服务类型
            
        Returns:
            单例实例或 None
        """
        return self._singletons.get(service_type)
    
    def get_factory(self, service_type: Type[T]) -> Optional[Callable]:
        """
        获取服务工厂
        
        Args:
            service_type: 服务类型
            
        Returns:
            工厂函数或 None
        """
        return self._factories.get(service_type) or self._request_factories.get(service_type)
    
    def create(self, service_type: Type[T], db: Session) -> T:
        """
        创建服务实例
        
        Args:
            service_type: 服务类型
            db: 数据库会话
            
        Returns:
            服务实例
        """
        if service_type in self._singletons:
            return self._singletons[service_type]
        
        factory = self.get_factory(service_type)
        if factory:
            return factory(db)
        
        raise ValueError(f"Service {service_type.__name__} not registered")
    
    def clear(self) -> None:
        """清空容器（测试用）"""
        self._factories.clear()
        self._singletons.clear()
        self._request_factories.clear()


# 全局容器实例
container = ServiceContainer()


# ==================== 服务注册 ====================

def _register_services() -> None:
    """注册所有服务"""
    # 用户服务
    from app.services.user_service import UserService
    container.register_request_factory(UserService, lambda db: UserService(db))
    
    # 权限服务
    from app.services.permission_service import PermissionService
    container.register_request_factory(PermissionService, lambda db: PermissionService(db))
    
    # 实例服务
    from app.services.instance_service import RDBInstanceService, RedisInstanceService
    container.register_request_factory(RDBInstanceService, lambda db: RDBInstanceService(db))
    container.register_request_factory(RedisInstanceService, lambda db: RedisInstanceService(db))
    
    # 存储服务（单例，无状态）
    from app.services.storage import storage_manager
    from app.services.storage import StorageManager
    container.register_singleton(StorageManager, storage_manager)


# 延迟注册（避免循环导入）
_services_registered = False

def ensure_services_registered() -> None:
    """确保服务已注册"""
    global _services_registered
    if not _services_registered:
        _register_services()
        _services_registered = True


# ==================== FastAPI 依赖注入辅助函数 ====================

def get_service(service_type: Type[T]) -> Callable:
    """
    创建 FastAPI 依赖项
    
    用法：
        @router.get("/users")
        def list_users(
            user_service: UserService = get_service(UserService)
        ):
            return user_service.get_multi_with_count()
    
    Args:
        service_type: 服务类型
        
    Returns:
        FastAPI Depends 函数
    """
    from fastapi import Depends
    
    def _get_service(db: Session = Depends(get_db)) -> T:
        ensure_services_registered()
        return container.create(service_type, db)
    
    return Depends(_get_service)


# 预定义的常用服务依赖（更简洁的用法）
def get_user_service() -> Callable:
    """获取 UserService 依赖"""
    from app.services.user_service import UserService
    return get_service(UserService)


def get_permission_service() -> Callable:
    """获取 PermissionService 依赖"""
    from app.services.permission_service import PermissionService
    return get_service(PermissionService)


def get_rdb_instance_service() -> Callable:
    """获取 RDBInstanceService 依赖"""
    from app.services.instance_service import RDBInstanceService
    return get_service(RDBInstanceService)


# ==================== 导出 ====================

__all__ = [
    "ServiceContainer",
    "container",
    "get_service",
    "get_user_service",
    "get_permission_service",
    "get_rdb_instance_service",
    "ensure_services_registered",
]
