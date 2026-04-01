"""
API 路由自动注册

提供路由自动发现和注册能力，简化路由管理

使用示例:
    # api/__init__.py
    from app.api.router_registry import APIRouterRegistry
    
    registry = APIRouterRegistry()
    api_v1 = registry.create_router("/api/v1")
    
    # 自动注册所有 api/*.py 中的路由
    registry.auto_register()
    
    # main.py
    from app.api import api_v1
    app.include_router(api_v1)
"""
import importlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)


class RouterConfig:
    """路由配置"""
    
    def __init__(
        self,
        name: str,
        router: APIRouter,
        prefix: str = "",
        tags: Optional[List[str]] = None,
        priority: int = 100
    ):
        """
        路由配置
        
        Args:
            name: 路由名称
            router: FastAPI 路由器
            prefix: URL 前缀
            tags: OpenAPI 标签
            priority: 注册优先级（数字越小越先注册）
        """
        self.name = name
        self.router = router
        self.prefix = prefix
        self.tags = tags or [name]
        self.priority = priority


class APIRouterRegistry:
    """
    API 路由注册器
    
    提供路由的自动发现、注册和管理
    """
    
    def __init__(self):
        self._routers: Dict[str, RouterConfig] = {}
        self._main_router: Optional[APIRouter] = None
    
    def register(
        self,
        name: str,
        router: APIRouter,
        prefix: str = "",
        tags: Optional[List[str]] = None,
        priority: int = 100
    ) -> None:
        """
        注册路由
        
        Args:
            name: 路由名称
            router: FastAPI 路由器
            prefix: URL 前缀
            tags: OpenAPI 标签
            priority: 注册优先级
        """
        self._routers[name] = RouterConfig(
            name=name,
            router=router,
            prefix=prefix,
            tags=tags,
            priority=priority
        )
        logger.debug(f"注册路由: {name} -> {prefix or '/'}, 优先级: {priority}")
    
    def unregister(self, name: str) -> bool:
        """
        取消注册路由
        
        Args:
            name: 路由名称
        
        Returns:
            是否成功取消注册
        """
        if name in self._routers:
            del self._routers[name]
            return True
        return False
    
    def create_router(
        self,
        prefix: str = "/api/v1",
        title: str = "API v1"
    ) -> APIRouter:
        """
        创建主路由器
        
        Args:
            prefix: 主路由前缀
            title: 路由标题
        
        Returns:
            APIRouter: 主路由器
        """
        self._main_router = APIRouter(prefix=prefix, tags=[title])
        return self._main_router
    
    def auto_register(
        self,
        package_path: str = "app.api",
        exclude: Optional[List[str]] = None
    ) -> int:
        """
        自动发现并注册路由
        
        扫描指定包下的所有模块，查找 router 变量并注册
        
        Args:
            package_path: 包路径
            exclude: 排除的模块列表
        
        Returns:
            注册的路由数量
        """
        exclude = exclude or ["__init__", "router_registry"]
        registered_count = 0
        
        try:
            package = importlib.import_module(package_path)
            package_dir = Path(package.__file__).parent
            
            for module_file in package_dir.glob("*.py"):
                module_name = module_file.stem
                
                if module_name in exclude or module_name.startswith("_"):
                    continue
                
                try:
                    module = importlib.import_module(f"{package_path}.{module_name}")
                    
                    if hasattr(module, "router"):
                        router = module.router
                        prefix = getattr(module, "ROUTER_PREFIX", "")
                        tags = getattr(module, "ROUTER_TAGS", [module_name])
                        priority = getattr(module, "ROUTER_PRIORITY", 100)
                        
                        self.register(
                            name=module_name,
                            router=router,
                            prefix=prefix,
                            tags=tags,
                            priority=priority
                        )
                        registered_count += 1
                        
                except ImportError as e:
                    logger.warning(f"无法导入模块 {module_name}: {e}")
                except Exception as e:
                    logger.error(f"注册路由 {module_name} 失败: {e}")
            
            logger.info(f"自动注册完成: {registered_count} 个路由")
            
        except Exception as e:
            logger.error(f"自动注册路由失败: {e}")
        
        return registered_count
    
    def build_main_router(self) -> APIRouter:
        """
        构建主路由器（将所有注册的路由合并）
        
        Returns:
            APIRouter: 包含所有路由的主路由器
        """
        if self._main_router is None:
            self._main_router = APIRouter()
        
        # 按优先级排序
        sorted_routers = sorted(
            self._routers.values(),
            key=lambda x: x.priority
        )
        
        for config in sorted_routers:
            self._main_router.include_router(
                config.router,
                prefix=config.prefix,
                tags=config.tags
            )
            logger.info(f"合并路由: {config.name} -> {config.prefix or '/'}")
        
        return self._main_router
    
    def get_router(self, name: str) -> Optional[APIRouter]:
        """获取指定名称的路由器"""
        config = self._routers.get(name)
        return config.router if config else None
    
    def list_routers(self) -> List[Dict[str, Any]]:
        """列出所有注册的路由"""
        return [
            {
                "name": config.name,
                "prefix": config.prefix,
                "tags": config.tags,
                "priority": config.priority
            }
            for config in sorted(self._routers.values(), key=lambda x: x.priority)
        ]


# 全局注册器实例
registry = APIRouterRegistry()


def create_api_router(
    prefix: str = "",
    tags: Optional[List[str]] = None,
    responses: Optional[Dict] = None
) -> APIRouter:
    """
    创建 API 路由器的便捷函数
    
    使用示例:
        # api/users.py
        from app.api.router_registry import create_api_router
        
        router = create_api_router(tags=["用户管理"])
        
        @router.get("/users")
        async def list_users():
            ...
    
    Args:
        prefix: 路由前缀
        tags: OpenAPI 标签
        responses: 响应模型
    
    Returns:
        APIRouter: FastAPI 路由器
    """
    return APIRouter(
        prefix=prefix,
        tags=tags,
        responses=responses
    )


__all__ = [
    'APIRouterRegistry',
    'RouterConfig',
    'registry',
    'create_api_router'
]
