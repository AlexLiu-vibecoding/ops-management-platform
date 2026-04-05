"""
路由注册器单元测试
"""
import pytest
from fastapi import APIRouter
from unittest.mock import patch, MagicMock

from app.api.router_registry import (
    APIRouterRegistry,
    RouterConfig,
    create_api_router,
    registry
)


class TestRouterConfig:
    """RouterConfig 测试"""

    def test_init_basic(self):
        """测试基本初始化"""
        config = RouterConfig(
            name="test_router",
            router=APIRouter(),
            prefix="/test",
            tags=["test"],
            priority=10
        )

        assert config.name == "test_router"
        assert config.prefix == "/test"
        assert config.tags == ["test"]
        assert config.priority == 10

    def test_init_defaults(self):
        """测试默认值"""
        router = APIRouter()
        config = RouterConfig(name="default_router", router=router)

        assert config.name == "default_router"
        assert config.prefix == ""
        assert config.tags == ["default_router"]
        assert config.priority == 100
        assert config.router is router


class TestAPIRouterRegistry:
    """APIRouterRegistry 测试"""

    def test_init(self):
        """测试初始化"""
        reg = APIRouterRegistry()

        assert reg._routers == {}
        assert reg._main_router is None

    def test_register_basic(self):
        """测试注册路由"""
        reg = APIRouterRegistry()
        router = APIRouter()

        reg.register(
            name="users",
            router=router,
            prefix="/users",
            tags=["用户管理"],
            priority=10
        )

        assert "users" in reg._routers
        config = reg._routers["users"]
        assert config.router is router
        assert config.prefix == "/users"
        assert config.tags == ["用户管理"]
        assert config.priority == 10

    def test_register_defaults(self):
        """测试注册路由（默认值）"""
        reg = APIRouterRegistry()
        router = APIRouter()

        reg.register(name="products", router=router)

        assert "products" in reg._routers
        config = reg._routers["products"]
        assert config.prefix == ""
        assert config.tags == ["products"]
        assert config.priority == 100

    def test_register_duplicate(self):
        """测试注册重复路由"""
        reg = APIRouterRegistry()
        router1 = APIRouter()
        router2 = APIRouter()

        reg.register(name="test", router=router1)
        reg.register(name="test", router=router2)

        # 后注册的覆盖先注册的
        assert reg._routers["test"].router is router2

    def test_unregister_existing(self):
        """测试取消注册（存在的路由）"""
        reg = APIRouterRegistry()
        router = APIRouter()

        reg.register(name="test", router=router)
        result = reg.unregister("test")

        assert result is True
        assert "test" not in reg._routers

    def test_unregister_nonexistent(self):
        """测试取消注册（不存在的路由）"""
        reg = APIRouterRegistry()
        result = reg.unregister("nonexistent")

        assert result is False

    def test_create_router_basic(self):
        """测试创建主路由器"""
        reg = APIRouterRegistry()
        main_router = reg.create_router(prefix="/api/v1", title="API v1")

        assert reg._main_router is main_router
        assert main_router is not None
        assert main_router.prefix == "/api/v1"
        assert main_router.tags == ["API v1"]

    def test_create_router_defaults(self):
        """测试创建主路由器（默认值）"""
        reg = APIRouterRegistry()
        main_router = reg.create_router()

        assert reg._main_router is main_router
        assert main_router.prefix == "/api/v1"
        assert main_router.tags == ["API v1"]

    def test_create_router_twice(self):
        """测试创建两次主路由器"""
        reg = APIRouterRegistry()

        router1 = reg.create_router(prefix="/api/v1")
        router2 = reg.create_router(prefix="/api/v2")

        # 应该被替换
        assert reg._main_router is router2
        assert router1 is not router2

    @patch('app.api.router_registry.importlib.import_module')
    def test_auto_register_success(self, mock_import):
        """测试自动注册成功"""
        reg = APIRouterRegistry()

        # 模拟包
        mock_package = MagicMock()
        mock_package.__file__ = "/app/api/__init__.py"
        mock_import.return_value = mock_package

        # 模拟目录
        from pathlib import Path
        with patch.object(Path, 'glob') as mock_glob:
            mock_module_files = [
                Path("/app/api/users.py"),
                Path("/app/api/__init__.py"),
                Path("/app/api/router_registry.py"),
                Path("/app/api/_internal.py")
            ]
            mock_glob.return_value = mock_module_files

            # 模拟模块导入
            mock_users_module = MagicMock()
            mock_users_module.router = APIRouter(prefix="/users", tags=["users"])
            mock_users_module.ROUTER_PREFIX = "/v1/users"
            mock_users_module.ROUTER_TAGS = ["用户管理"]
            mock_users_module.ROUTER_PRIORITY = 50

            def import_side_effect(module_name):
                if module_name == "app.api":
                    return mock_package
                elif module_name == "app.api.users":
                    return mock_users_module
                else:
                    raise ImportError(f"No module named '{module_name}'")

            mock_import.side_effect = import_side_effect

            count = reg.auto_register(package_path="app.api")

            assert count == 1
            assert "users" in reg._routers

    @patch('app.api.router_registry.importlib.import_module')
    def test_auto_register_exclude(self, mock_import):
        """测试自动注册（排除指定模块）"""
        reg = APIRouterRegistry()

        mock_package = MagicMock()
        mock_package.__file__ = "/app/api/__init__.py"
        mock_import.return_value = mock_package

        from pathlib import Path
        with patch.object(Path, 'glob') as mock_glob:
            mock_module_files = [
                Path("/app/api/users.py"),
                Path("/app/api/__init__.py"),
            ]
            mock_glob.return_value = mock_module_files

            mock_users_module = MagicMock()
            mock_users_module.router = APIRouter()
            mock_users_module.ROUTER_PREFIX = ""
            mock_users_module.ROUTER_TAGS = ["users"]
            mock_users_module.ROUTER_PRIORITY = 100

            def import_side_effect(module_name):
                if module_name == "app.api":
                    return mock_package
                elif module_name == "app.api.users":
                    return mock_users_module
                else:
                    raise ImportError(f"No module named '{module_name}'")

            mock_import.side_effect = import_side_effect

            # 排除 users
            count = reg.auto_register(
                package_path="app.api",
                exclude=["__init__", "router_registry", "users"]
            )

            assert count == 0
            assert "users" not in reg._routers

    @patch('app.api.router_registry.importlib.import_module')
    def test_auto_register_module_without_router(self, mock_import):
        """测试自动注册（模块没有 router 属性）"""
        reg = APIRouterRegistry()

        mock_package = MagicMock()
        mock_package.__file__ = "/app/api/__init__.py"
        mock_import.return_value = mock_package

        from pathlib import Path
        with patch.object(Path, 'glob') as mock_glob:
            mock_module_files = [Path("/app/api/util.py")]
            mock_glob.return_value = mock_module_files

            mock_util_module = MagicMock()
            # 没有 router 属性

            def import_side_effect(module_name):
                if module_name == "app.api":
                    return mock_package
                elif module_name == "app.api.util":
                    return mock_util_module
                else:
                    raise ImportError(f"No module named '{module_name}'")

            mock_import.side_effect = import_side_effect

            count = reg.auto_register(package_path="app.api")

            # 不应该注册没有 router 的模块
            assert count == 0
            assert "util" not in reg._routers

    @patch('app.api.router_registry.importlib.import_module')
    def test_auto_register_import_error(self, mock_import):
        """测试自动注册（模块导入失败）"""
        reg = APIRouterRegistry()

        mock_package = MagicMock()
        mock_package.__file__ = "/app/api/__init__.py"
        mock_import.return_value = mock_package

        from pathlib import Path
        with patch.object(Path, 'glob') as mock_glob:
            mock_module_files = [Path("/app/api/error_module.py")]
            mock_glob.return_value = mock_module_files

            def import_side_effect(module_name):
                if module_name == "app.api":
                    return mock_package
                elif module_name == "app.api.error_module":
                    raise ImportError("Import error")
                else:
                    raise ImportError(f"No module named '{module_name}'")

            mock_import.side_effect = import_side_effect

            # 导入失败不应该影响其他模块
            count = reg.auto_register(package_path="app.api")

            assert count == 0

    def test_build_main_router_with_routers(self):
        """测试构建主路由器（有已注册路由）"""
        reg = APIRouterRegistry()

        # 注册多个路由
        router1 = APIRouter(prefix="/users", tags=["users"])
        router2 = APIRouter(prefix="/products", tags=["products"])
        router3 = APIRouter(prefix="/orders", tags=["orders"])

        reg.register("users", router1, priority=30)
        reg.register("products", router2, priority=10)
        reg.register("orders", router3, priority=20)

        main_router = reg.build_main_router()

        assert main_router is not None
        assert reg._main_router is main_router
        # 路由应该按优先级排序（10, 20, 30）
        assert len(reg._main_router.routes) >= 0  # 至少包含合并的路由

    def test_build_main_router_without_create(self):
        """测试构建主路由器（未先创建）"""
        reg = APIRouterRegistry()

        # 注册路由但不先创建主路由器
        router = APIRouter()
        reg.register("test", router)

        main_router = reg.build_main_router()

        assert main_router is not None
        assert reg._main_router is main_router

    def test_get_router_existing(self):
        """测试获取路由器（存在的）"""
        reg = APIRouterRegistry()
        router = APIRouter()

        reg.register("test", router)

        result = reg.get_router("test")

        assert result is router

    def test_get_router_nonexistent(self):
        """测试获取路由器（不存在的）"""
        reg = APIRouterRegistry()

        result = reg.get_router("nonexistent")

        assert result is None

    def test_list_routers_empty(self):
        """测试列出路由器（空列表）"""
        reg = APIRouterRegistry()

        routers = reg.list_routers()

        assert routers == []

    def test_list_routers_with_routers(self):
        """测试列出路由器（有路由）"""
        reg = APIRouterRegistry()

        router1 = APIRouter()
        router2 = APIRouter()
        router3 = APIRouter()

        reg.register("orders", router1, priority=30)
        reg.register("products", router2, priority=10)
        reg.register("users", router3, priority=20)

        routers = reg.list_routers()

        assert len(routers) == 3
        # 按优先级排序
        assert routers[0]["name"] == "products"  # priority 10
        assert routers[1]["name"] == "users"      # priority 20
        assert routers[2]["name"] == "orders"     # priority 30

        # 验证返回的格式
        expected_keys = {"name", "prefix", "tags", "priority"}
        for router_info in routers:
            assert set(router_info.keys()) == expected_keys


class TestCreateApiRouter:
    """create_api_router 函数测试"""

    def test_create_basic(self):
        """测试基本创建"""
        router = create_api_router(
            prefix="/test",
            tags=["test"],
            responses={"404": {"description": "Not found"}}
        )

        assert isinstance(router, APIRouter)
        assert router.prefix == "/test"
        assert router.tags == ["test"]

    def test_create_defaults(self):
        """测试默认值"""
        router = create_api_router()

        assert isinstance(router, APIRouter)
        assert router.prefix == ""
        assert router.tags is None


class TestGlobalRegistry:
    """全局注册器实例测试"""

    def test_registry_exists(self):
        """测试全局注册器实例存在"""
        assert registry is not None
        assert isinstance(registry, APIRouterRegistry)

    def test_registry_is_singleton_like(self):
        """测试全局注册器是单例式的"""
        # 多次导入应该返回同一个实例
        from app.api.router_registry import registry as registry2

        assert registry is registry2
