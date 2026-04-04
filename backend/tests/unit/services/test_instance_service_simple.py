"""
实例服务简化测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from app.services.instance_service import RDBInstanceService, RedisInstanceService
from app.models import RDBInstance, RedisInstance, Environment


class TestRDBInstanceService:
    """RDB实例服务测试类"""

    @pytest.fixture
    def service(self, db_session):
        """创建服务实例"""
        return RDBInstanceService(db_session)

    @pytest.fixture
    def mock_environment(self, db_session):
        """创建模拟环境"""
        env = Environment(
            name="test_env",
            code="TEST",
            description="测试环境"
        )
        db_session.add(env)
        db_session.commit()
        return env

    # ==================== 实例查询测试 ====================

    def test_get_with_environment(self, service, db_session, mock_environment):
        """测试获取实例（带环境信息）"""
        instance = RDBInstance(
            name="test_mysql",
            host="localhost",
            port=3306,
            db_type="mysql",
            username="root",
            environment_id=mock_environment.id
        )
        db_session.add(instance)
        db_session.commit()

        result = service.get_with_environment(instance.id)

        assert result is not None
        assert result.id == instance.id

    def test_get_with_environment_not_found(self, service):
        """测试获取不存在的实例"""
        result = service.get_with_environment(99999)
        assert result is None

    def test_get_multi_with_environment(self, service, db_session, mock_environment):
        """测试获取实例列表（带环境信息）"""
        # 创建多个实例
        for i in range(3):
            instance = RDBInstance(
                name=f"test_mysql_{i}",
                host="localhost",
                port=3306 + i,
                db_type="mysql",
                environment_id=mock_environment.id
            )
            db_session.add(instance)
        db_session.commit()

        instances, total = service.get_multi_with_environment(skip=0, limit=20)

        assert total >= 3
        assert len(instances) >= 3

    def test_get_multi_with_environment_filter(self, service, db_session, mock_environment):
        """测试带筛选的实例列表"""
        instance = RDBInstance(
            name="specific_mysql",
            host="localhost",
            port=3306,
            db_type="mysql",
            environment_id=mock_environment.id
        )
        db_session.add(instance)
        db_session.commit()

        instances, total = service.get_multi_with_environment(
            environment_id=mock_environment.id,
            db_type="mysql"
        )

        assert total >= 1

    # ==================== 通用CRUD测试 ====================

    def test_get(self, service, db_session, mock_environment):
        """测试获取实例"""
        instance = RDBInstance(
            name="test_mysql",
            host="localhost",
            port=3306,
            db_type="mysql",
            environment_id=mock_environment.id
        )
        db_session.add(instance)
        db_session.commit()

        result = service.get(instance.id)

        assert result is not None
        assert result.id == instance.id

    def test_get_not_found(self, service):
        """测试获取不存在的实例"""
        result = service.get(99999)
        assert result is None

    def test_create(self, service, db_session, mock_environment):
        """测试创建实例"""
        instance_data = {
            "name": "new_mysql",
            "host": "localhost",
            "port": 3306,
            "db_type": "mysql",
            "environment_id": mock_environment.id
        }

        created = service.create(instance_data)

        assert created is not None
        assert created.id is not None
        assert created.name == "new_mysql"

    def test_update(self, service, db_session, mock_environment):
        """测试更新实例"""
        instance = RDBInstance(
            name="test_mysql",
            host="localhost",
            port=3306,
            db_type="mysql",
            environment_id=mock_environment.id
        )
        db_session.add(instance)
        db_session.commit()

        update_data = {"name": "updated_mysql"}
        updated = service.update(instance.id, update_data)

        assert updated.name == "updated_mysql"

    def test_delete(self, service, db_session, mock_environment):
        """测试删除实例"""
        instance = RDBInstance(
            name="test_mysql",
            host="localhost",
            port=3306,
            db_type="mysql",
            environment_id=mock_environment.id
        )
        db_session.add(instance)
        db_session.commit()

        service.delete(instance.id)

        # 确认已删除
        deleted = db_session.get(RDBInstance, instance.id)
        assert deleted is None


class TestRedisInstanceService:
    """Redis实例服务测试类"""

    @pytest.fixture
    def service(self, db_session):
        """创建服务实例"""
        return RedisInstanceService(db_session)

    @pytest.fixture
    def mock_environment(self, db_session):
        """创建模拟环境"""
        env = Environment(
            name="test_env",
            code="TEST",
            description="测试环境"
        )
        db_session.add(env)
        db_session.commit()
        return env

    # ==================== Redis实例测试 ====================

    def test_get_with_environment(self, service, db_session, mock_environment):
        """测试获取Redis实例（带环境信息）"""
        instance = RedisInstance(
            name="test_redis",
            host="localhost",
            port=6379,
            environment_id=mock_environment.id
        )
        db_session.add(instance)
        db_session.commit()

        result = service.get_with_environment(instance.id)

        assert result is not None
        assert result.id == instance.id

    def test_get_multi_with_environment(self, service, db_session, mock_environment):
        """测试获取Redis实例列表"""
        instance = RedisInstance(
            name="test_redis",
            host="localhost",
            port=6379,
            environment_id=mock_environment.id
        )
        db_session.add(instance)
        db_session.commit()

        instances, total = service.get_multi_with_environment(skip=0, limit=20)

        assert total >= 1

    def test_create(self, service, db_session, mock_environment):
        """测试创建Redis实例"""
        instance_data = {
            "name": "new_redis",
            "host": "localhost",
            "port": 6379,
            "environment_id": mock_environment.id
        }

        created = service.create(instance_data)

        assert created is not None
        assert created.id is not None
        assert created.name == "new_redis"

    def test_delete(self, service, db_session, mock_environment):
        """测试删除Redis实例"""
        instance = RedisInstance(
            name="test_redis",
            host="localhost",
            port=6379,
            environment_id=mock_environment.id
        )
        db_session.add(instance)
        db_session.commit()

        service.delete(instance.id)

        # 确认已删除
        deleted = db_session.get(RedisInstance, instance.id)
        assert deleted is None

