"""
Service 基类单元测试
"""
import pytest
from sqlalchemy import Column, Integer, String

from app.services.base import BaseService
from app.models import Environment


class TestBaseService:
    """Service 基类测试"""

    def test_get_by_id(self, db_session):
        """测试根据 ID 获取记录"""
        # 创建测试环境
        env = Environment(name="Test Env", code="test-env")
        db_session.add(env)
        db_session.commit()
        
        service = BaseService(Environment, db_session)
        result = service.get(env.id)
        
        assert result is not None
        assert result.id == env.id
        assert result.name == "Test Env"

    def test_get_not_found(self, db_session):
        """测试获取不存在的记录"""
        service = BaseService(Environment, db_session)
        result = service.get(99999)
        
        assert result is None

    def test_get_multi(self, db_session):
        """测试获取多条记录"""
        # 创建多个环境
        for i in range(5):
            env = Environment(name=f"Env {i}", code=f"env-{i}")
            db_session.add(env)
        db_session.commit()
        
        service = BaseService(Environment, db_session)
        results = service.get_multi(skip=0, limit=3)
        
        assert len(results) == 3

    def test_get_multi_with_skip(self, db_session):
        """测试分页跳过"""
        # 创建多个环境
        for i in range(5):
            env = Environment(name=f"Env {i}", code=f"env-{i}")
            db_session.add(env)
        db_session.commit()
        
        service = BaseService(Environment, db_session)
        results = service.get_multi(skip=2, limit=10)
        
        assert len(results) == 3  # 5 - 2 = 3

    def test_create(self, db_session):
        """测试创建记录"""
        service = BaseService(Environment, db_session)
        
        data = {"name": "New Env", "code": "new-env"}
        result = service.create(data)
        
        assert result is not None
        assert result.id is not None
        assert result.name == "New Env"
        assert result.code == "new-env"

    def test_create_with_additional_fields(self, db_session):
        """测试创建带额外字段的记录"""
        service = BaseService(Environment, db_session)
        
        data = {
            "name": "Full Env",
            "code": "full-env",
            "color": "#FF0000",
            "description": "Test description"
        }
        result = service.create(data)
        
        assert result.name == "Full Env"
        assert result.color == "#FF0000"

    def test_update(self, db_session):
        """测试更新记录"""
        env = Environment(name="Old Name", code="update-test")
        db_session.add(env)
        db_session.commit()
        
        service = BaseService(Environment, db_session)
        result = service.update(env.id, {"name": "New Name"})
        
        assert result is not None
        assert result.name == "New Name"
        assert result.code == "update-test"  # 未修改的字段保持不变

    def test_update_not_found(self, db_session):
        """测试更新不存在的记录"""
        service = BaseService(Environment, db_session)
        result = service.update(99999, {"name": "Test"})
        
        assert result is None

    def test_update_multiple_fields(self, db_session):
        """测试更新多个字段"""
        env = Environment(name="Original", code="multi-update")
        db_session.add(env)
        db_session.commit()
        
        service = BaseService(Environment, db_session)
        result = service.update(env.id, {
            "name": "Updated",
            "color": "#00FF00",
            "description": "Updated desc"
        })
        
        assert result.name == "Updated"
        assert result.color == "#00FF00"
        assert result.description == "Updated desc"

    def test_delete(self, db_session):
        """测试删除记录"""
        env = Environment(name="To Delete", code="delete-me")
        db_session.add(env)
        db_session.commit()
        env_id = env.id
        
        service = BaseService(Environment, db_session)
        result = service.delete(env_id)
        
        assert result is True
        
        # 验证已删除
        deleted = service.get(env_id)
        assert deleted is None

    def test_delete_not_found(self, db_session):
        """测试删除不存在的记录"""
        service = BaseService(Environment, db_session)
        result = service.delete(99999)
        
        assert result is False

    def test_exists(self, db_session):
        """测试检查记录是否存在"""
        env = Environment(name="Exists Test", code="exists-test")
        db_session.add(env)
        db_session.commit()
        
        service = BaseService(Environment, db_session)
        
        assert service.exists(env.id) is True
        assert service.exists(99999) is False

    def test_count(self, db_session):
        """测试计数"""
        # 创建多个记录
        for i in range(5):
            env = Environment(name=f"Count {i}", code=f"count-{i}")
            db_session.add(env)
        db_session.commit()
        
        service = BaseService(Environment, db_session)
        count = service.count()
        
        assert count >= 5
