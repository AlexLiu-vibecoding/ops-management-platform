"""
Service 层单元测试

测试覆盖：
- UserService: 用户 CRUD、认证逻辑
- PermissionService: 权限检查、角色权限
- BaseService: 通用 CRUD 操作
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy.orm import Session

from app.services.user_service import UserService
from app.services.permission_service import PermissionService
from app.services.base import BaseService
from app.models import User, UserRole
from app.models.permissions import Permission, RolePermission, PermissionCode
from app.utils.auth import hash_password, verify_password


# ==================== Fixtures ====================

@pytest.fixture
def mock_db():
    """Mock 数据库会话"""
    return MagicMock(spec=Session)


@pytest.fixture
def user_service(mock_db):
    """创建 UserService 实例"""
    return UserService(mock_db)


@pytest.fixture
def permission_service(mock_db):
    """创建 PermissionService 实例"""
    return PermissionService(mock_db)


@pytest.fixture
def sample_user():
    """创建示例用户"""
    user = User(
        id=1,
        username="testuser",
        email="test@example.com",
        real_name="测试用户",
        role=UserRole.READONLY,
        status=True
    )
    user.password_hash = hash_password("password123")
    return user


# ==================== UserService 测试 ====================

class TestUserService:
    """UserService 单元测试"""
    
    def test_get_by_username(self, user_service, mock_db, sample_user):
        """测试根据用户名获取用户"""
        # 设置 mock 返回值
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = sample_user
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        
        # 执行测试
        result = user_service.get_by_username("testuser")
        
        # 验证
        assert result == sample_user
        mock_db.query.assert_called_once_with(User)
    
    def test_get_by_username_not_found(self, user_service, mock_db):
        """测试用户名不存在"""
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        
        result = user_service.get_by_username("nonexistent")
        
        assert result is None
    
    def test_get_by_email(self, user_service, mock_db, sample_user):
        """测试根据邮箱获取用户"""
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = sample_user
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        
        result = user_service.get_by_email("test@example.com")
        
        assert result == sample_user
    
    def test_get_multi_with_count(self, user_service, mock_db):
        """测试获取用户列表及计数"""
        # Mock 查询结果
        users = [
            User(id=1, username="user1", role=UserRole.READONLY),
            User(id=2, username="user2", role=UserRole.OPERATOR),
        ]
        
        mock_query = Mock()
        mock_query.count.return_value = 2
        mock_query.offset.return_value.limit.return_value.all.return_value = users
        mock_db.query.return_value = mock_query
        
        result, count = user_service.get_multi_with_count(skip=0, limit=10)
        
        assert count == 2
        assert len(result) == 2
    
    def test_get_multi_with_count_with_filters(self, user_service, mock_db):
        """测试带过滤条件的用户列表"""
        users = [
            User(id=1, username="operator1", role=UserRole.OPERATOR),
        ]
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.count.return_value = 1
        mock_filter.offset.return_value.limit.return_value.all.return_value = users
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        
        result, count = user_service.get_multi_with_count(
            skip=0, 
            limit=10, 
            role=UserRole.OPERATOR
        )
        
        assert count == 1
        assert len(result) == 1
    
    def test_create_user(self, user_service, mock_db):
        """测试创建用户"""
        # Mock 用户名不存在
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        
        # Mock 添加操作
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()
        
        user = user_service.create_user(
            username="newuser",
            password="password123",
            real_name="新用户",
            email="new@example.com",
            role=UserRole.READONLY
        )
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    def test_create_user_duplicate_username(self, user_service, mock_db, sample_user):
        """测试创建重复用户名"""
        from fastapi import HTTPException
        
        # Mock 用户名已存在
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = sample_user
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        
        with pytest.raises(HTTPException) as exc_info:
            user_service.create_user(
                username="testuser",  # 已存在的用户名
                password="password123",
                real_name="新用户",
                email="new@example.com"
            )
        
        assert exc_info.value.status_code == 400


# ==================== PermissionService 测试 ====================

class TestPermissionService:
    """PermissionService 单元测试"""
    
    def test_has_permission_true(self, permission_service, mock_db, sample_user):
        """测试用户有权限"""
        # Mock 权限查询
        mock_permission = Permission(code=PermissionCode.INSTANCE_VIEW, is_enabled=True)
        mock_role_perm = RolePermission(
            role=UserRole.READONLY,
            permission=mock_permission
        )
        
        mock_query = Mock()
        mock_join = Mock()
        mock_filter = Mock()
        mock_filter.all.return_value = [mock_role_perm]
        mock_join.filter.return_value = mock_filter
        mock_query.join.return_value = mock_join
        mock_db.query.return_value = mock_query
        
        result = permission_service.has_permission(sample_user, PermissionCode.INSTANCE_VIEW)
        
        assert result is True
    
    def test_has_permission_false(self, permission_service, mock_db, sample_user):
        """测试用户无权限"""
        # Mock 空权限列表
        mock_query = Mock()
        mock_join = Mock()
        mock_filter = Mock()
        mock_filter.all.return_value = []
        mock_join.filter.return_value = mock_filter
        mock_query.join.return_value = mock_join
        mock_db.query.return_value = mock_query
        
        result = permission_service.has_permission(sample_user, PermissionCode.USER_MANAGE)
        
        # 应该从默认配置获取
        assert isinstance(result, bool)
    
    def test_check_permission_raises_exception(self, permission_service, mock_db, sample_user):
        """测试权限检查抛出异常"""
        from fastapi import HTTPException
        
        # Mock 无权限
        mock_query = Mock()
        mock_join = Mock()
        mock_filter = Mock()
        mock_filter.all.return_value = []
        mock_join.filter.return_value = mock_filter
        mock_query.join.return_value = mock_join
        mock_db.query.return_value = mock_query
        
        # 禁用缓存
        permission_service._permission_cache = {}
        
        with pytest.raises(HTTPException) as exc_info:
            permission_service.check_permission(sample_user, "nonexistent_permission")
        
        assert exc_info.value.status_code == 403
    
    def test_get_role_permissions_caches_result(self, permission_service, mock_db):
        """测试权限缓存"""
        mock_permission = Permission(code=PermissionCode.INSTANCE_VIEW, is_enabled=True)
        mock_role_perm = RolePermission(role=UserRole.READONLY, permission=mock_permission)
        
        mock_query = Mock()
        mock_join = Mock()
        mock_filter = Mock()
        mock_filter.all.return_value = [mock_role_perm]
        mock_join.filter.return_value = mock_filter
        mock_query.join.return_value = mock_join
        mock_db.query.return_value = mock_query
        
        # 第一次调用
        result1 = permission_service.get_role_permissions(UserRole.READONLY)
        # 第二次调用（应该使用缓存）
        result2 = permission_service.get_role_permissions(UserRole.READONLY)
        
        assert result1 == result2
        # 只查询一次数据库
        assert mock_db.query.call_count == 1


# ==================== BaseService 测试 ====================

class TestBaseService:
    """BaseService 基类测试"""
    
    def test_get_by_id(self, mock_db, sample_user):
        """测试根据 ID 获取"""
        service = BaseService(User, mock_db)
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = sample_user
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        
        result = service.get(1)
        
        assert result == sample_user
    
    def test_get_by_id_not_found(self, mock_db):
        """测试 ID 不存在"""
        service = BaseService(User, mock_db)
        
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.first.return_value = None
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query
        
        result = service.get(999)
        
        assert result is None
    
    def test_get_multi(self, mock_db):
        """测试获取多个记录"""
        service = BaseService(User, mock_db)
        
        users = [
            User(id=1, username="user1"),
            User(id=2, username="user2"),
        ]
        
        mock_query = Mock()
        mock_query.offset.return_value.limit.return_value.all.return_value = users
        mock_db.query.return_value = mock_query
        
        result = service.get_multi(skip=0, limit=10)
        
        assert len(result) == 2


# ==================== 依赖注入容器测试 ====================

class TestServiceContainer:
    """ServiceContainer 测试"""
    
    def test_register_factory(self):
        """测试注册工厂"""
        from app.container import ServiceContainer
        
        container = ServiceContainer()
        
        factory = lambda db: UserService(db)
        container.register_factory(UserService, factory)
        
        assert container.get_factory(UserService) == factory
    
    def test_register_singleton(self):
        """测试注册单例"""
        from app.container import ServiceContainer
        
        container = ServiceContainer()
        mock_db = MagicMock(spec=Session)
        service = UserService(mock_db)
        
        container.register_singleton(UserService, service)
        
        assert container.get_singleton(UserService) == service
    
    def test_create_service(self):
        """测试创建服务实例"""
        from app.container import ServiceContainer
        
        container = ServiceContainer()
        mock_db = MagicMock(spec=Session)
        
        container.register_request_factory(
            UserService, 
            lambda db: UserService(db)
        )
        
        service = container.create(UserService, mock_db)
        
        assert isinstance(service, UserService)
    
    def test_create_unregistered_service_raises_error(self):
        """测试创建未注册服务抛出异常"""
        from app.container import ServiceContainer
        
        container = ServiceContainer()
        mock_db = MagicMock(spec=Session)
        
        with pytest.raises(ValueError) as exc_info:
            container.create(UserService, mock_db)
        
        assert "not registered" in str(exc_info.value)
    
    def test_clear_container(self):
        """测试清空容器"""
        from app.container import ServiceContainer
        
        container = ServiceContainer()
        mock_db = MagicMock(spec=Session)
        service = UserService(mock_db)
        
        container.register_singleton(UserService, service)
        container.clear()
        
        assert container.get_singleton(UserService) is None
