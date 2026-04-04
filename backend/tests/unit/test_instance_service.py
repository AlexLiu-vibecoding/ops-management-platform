"""
实例服务层单元测试
"""
import pytest
from fastapi import HTTPException, status

from app.services.instance_service import RDBInstanceService, RedisInstanceService
from app.models import RDBInstance, RedisInstance, Environment, RDBType


class TestRDBInstanceService:
    """RDB 实例服务测试"""

    def test_get_by_name(self, db_session):
        """测试根据名称获取实例"""
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        instance = RDBInstance(
            name="test-mysql",
            host="localhost",
            port=3306,
            db_type=RDBType.MYSQL,
            environment_id=env.id
        )
        db_session.add(instance)
        db_session.commit()
        
        service = RDBInstanceService(db_session)
        result = service.get_by_name("test-mysql")
        
        assert result is not None
        assert result.name == "test-mysql"

    def test_get_by_name_not_found(self, db_session):
        """测试获取不存在的实例"""
        service = RDBInstanceService(db_session)
        result = service.get_by_name("nonexistent")
        
        assert result is None

    def test_get_multi_with_filters(self, db_session):
        """测试带过滤的实例列表查询"""
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        # 创建多个实例
        for i in range(5):
            instance = RDBInstance(
                name=f"mysql-{i}",
                host=f"host{i}",
                port=3306,
                db_type=RDBType.MYSQL,
                environment_id=env.id,
                status=True
            )
            db_session.add(instance)
        db_session.commit()
        
        service = RDBInstanceService(db_session)
        instances, total = service.get_multi_with_environment(
            skip=0, limit=10, environment_id=env.id
        )
        
        assert total == 5
        assert len(instances) == 5

    def test_get_multi_with_db_type_filter(self, db_session):
        """测试按数据库类型过滤"""
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        # 创建 MySQL 实例
        mysql = RDBInstance(
            name="mysql-1", host="localhost", port=3306,
            db_type=RDBType.MYSQL, environment_id=env.id
        )
        db_session.add(mysql)
        
        # 创建 PostgreSQL 实例
        pg = RDBInstance(
            name="pg-1", host="localhost", port=5432,
            db_type=RDBType.POSTGRESQL, environment_id=env.id
        )
        db_session.add(pg)
        db_session.commit()
        
        service = RDBInstanceService(db_session)
        instances, total = service.get_multi_with_environment(
            skip=0, limit=10, db_type="MYSQL"
        )
        
        assert total >= 1
        for inst in instances:
            assert inst.db_type == RDBType.MYSQL

    def test_get_multi_with_status_filter(self, db_session):
        """测试按状态过滤"""
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        active = RDBInstance(
            name="active-db", host="localhost", port=3306,
            db_type=RDBType.MYSQL, environment_id=env.id, status=True
        )
        inactive = RDBInstance(
            name="inactive-db", host="localhost", port=3306,
            db_type=RDBType.MYSQL, environment_id=env.id, status=False
        )
        db_session.add_all([active, inactive])
        db_session.commit()
        
        service = RDBInstanceService(db_session)
        instances, total = service.get_multi_with_environment(
            skip=0, limit=10, status=True
        )
        
        for inst in instances:
            assert inst.status is True

    def test_create_instance_success(self, db_session):
        """测试成功创建实例"""
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        service = RDBInstanceService(db_session)
        instance = service.create_instance(
            name="new-mysql",
            host="192.168.1.100",
            port=3306,
            username="root",
            password="secret123",
            db_type="MYSQL",
            environment_id=env.id,
            description="Test instance"
        )
        
        assert instance.id is not None
        assert instance.name == "new-mysql"
        assert instance.host == "192.168.1.100"

    def test_create_instance_duplicate_name(self, db_session):
        """测试创建重复名称的实例"""
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        instance = RDBInstance(
            name="duplicate-db", host="localhost", port=3306,
            db_type=RDBType.MYSQL, environment_id=env.id
        )
        db_session.add(instance)
        db_session.commit()
        
        service = RDBInstanceService(db_session)
        
        with pytest.raises(HTTPException) as exc_info:
            service.create_instance(
                name="duplicate-db",
                host="localhost",
                port=3306,
                username="root",
                password="secret",
                db_type="MYSQL",
                environment_id=env.id
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_instance(self, db_session):
        """测试更新实例"""
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        instance = RDBInstance(
            name="update-db", host="localhost", port=3306,
            db_type=RDBType.MYSQL, environment_id=env.id,
            description="Old description"
        )
        db_session.add(instance)
        db_session.commit()
        
        service = RDBInstanceService(db_session)
        updated = service.update_instance(
            instance_id=instance.id,
            description="New description"
        )
        
        assert updated.description == "New description"

    def test_update_instance_not_found(self, db_session):
        """测试更新不存在的实例"""
        service = RDBInstanceService(db_session)
        
        with pytest.raises(HTTPException) as exc_info:
            service.update_instance(
                instance_id=99999,
                description="Test"
            )
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_instance(self, db_session):
        """测试删除实例（使用基类 delete 方法）"""
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        instance = RDBInstance(
            name="delete-db", host="localhost", port=3306,
            db_type=RDBType.MYSQL, environment_id=env.id
        )
        db_session.add(instance)
        db_session.commit()
        
        service = RDBInstanceService(db_session)
        result = service.delete(instance.id)
        
        assert result is True
        assert service.get(instance.id) is None

    def test_get_decrypted_password(self, db_session):
        """测试获取解密后的密码"""
        from app.utils.auth import encrypt_instance_password
        
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        encrypted = encrypt_instance_password("mysecretpassword")
        instance = RDBInstance(
            name="pwd-db", host="localhost", port=3306,
            db_type=RDBType.MYSQL, environment_id=env.id,
            password_encrypted=encrypted
        )
        db_session.add(instance)
        db_session.commit()
        
        service = RDBInstanceService(db_session)
        decrypted = service.get_decrypted_password(instance)
        
        assert decrypted == "mysecretpassword"


class TestRedisInstanceService:
    """Redis 实例服务测试"""

    def test_get_by_name(self, db_session):
        """测试根据名称获取 Redis 实例"""
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        instance = RedisInstance(
            name="test-redis",
            host="localhost",
            port=6379,
            environment_id=env.id
        )
        db_session.add(instance)
        db_session.commit()
        
        service = RedisInstanceService(db_session)
        result = service.get_by_name("test-redis")
        
        assert result is not None
        assert result.name == "test-redis"

    def test_get_by_name_not_found(self, db_session):
        """测试获取不存在的 Redis 实例"""
        service = RedisInstanceService(db_session)
        result = service.get_by_name("nonexistent")
        
        assert result is None

    def test_get_multi_with_environment_filter(self, db_session):
        """测试按环境过滤 Redis 实例"""
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        for i in range(3):
            instance = RedisInstance(
                name=f"redis-{i}",
                host=f"host{i}",
                port=6379,
                environment_id=env.id
            )
            db_session.add(instance)
        db_session.commit()
        
        service = RedisInstanceService(db_session)
        instances, total = service.get_multi_with_environment(
            skip=0, limit=10, environment_id=env.id
        )
        
        assert total == 3
        assert len(instances) == 3

    def test_create_instance_success(self, db_session):
        """测试成功创建 Redis 实例"""
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        service = RedisInstanceService(db_session)
        instance = service.create_instance(
            name="new-redis",
            host="192.168.1.100",
            port=6379,
            environment_id=env.id,
            description="Test Redis"
        )
        
        assert instance.id is not None
        assert instance.name == "new-redis"
        assert instance.port == 6379

    def test_create_instance_duplicate_name(self, db_session):
        """测试创建重复名称的 Redis 实例"""
        env = Environment(name="Test", code="test")
        db_session.add(env)
        db_session.commit()
        
        instance = RedisInstance(
            name="duplicate-redis", host="localhost", port=6379,
            environment_id=env.id
        )
        db_session.add(instance)
        db_session.commit()
        
        service = RedisInstanceService(db_session)
        
        with pytest.raises(HTTPException) as exc_info:
            service.create_instance(
                name="duplicate-redis",
                host="localhost",
                port=6379,
                environment_id=env.id
            )
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
