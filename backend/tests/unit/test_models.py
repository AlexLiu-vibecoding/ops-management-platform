"""
数据模型单元测试
"""
import pytest
from datetime import datetime

from app.models import (
    User, UserRole, Environment, RDBInstance, RedisInstance,
    Script, ScriptType, ExecutionStatus, ScheduledTask
)


class TestUserModel:
    """用户模型测试"""

    def test_user_creation(self, db_session):
        """测试用户创建"""
        user = User(
            username="testuser",
            password_hash="hashed_password",
            real_name="Test User",
            email="test@example.com",
            role=UserRole.OPERATOR,
            status=True
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.role == UserRole.OPERATOR
        assert user.created_at is not None

    def test_user_role_enum(self):
        """测试用户角色枚举"""
        assert UserRole.SUPER_ADMIN.value == "super_admin"
        assert UserRole.APPROVAL_ADMIN.value == "approval_admin"
        assert UserRole.OPERATOR.value == "operator"
        assert UserRole.DEVELOPER.value == "developer"

    def test_user_is_admin(self, db_session):
        """测试用户管理员判断"""
        admin = User(username="admin", role=UserRole.SUPER_ADMIN)
        user = User(username="user", role=UserRole.DEVELOPER)
        
        assert admin.role == UserRole.SUPER_ADMIN
        assert user.role != UserRole.SUPER_ADMIN


class TestEnvironmentModel:
    """环境模型测试"""

    def test_environment_creation(self, db_session):
        """测试环境创建"""
        env = Environment(
            name="测试环境",
            code="testing",
            color="#1890FF",
            require_approval=True,
            status=True
        )
        db_session.add(env)
        db_session.commit()
        
        assert env.id is not None
        assert env.name == "测试环境"
        assert env.code == "testing"
        assert env.require_approval is True

    def test_environment_default_values(self, db_session):
        """测试环境默认值"""
        env = Environment(name="开发环境", code="dev")
        db_session.add(env)
        db_session.commit()
        
        assert env.status is True
        assert env.require_approval is False
        assert env.color is not None


class TestRDBInstanceModel:
    """RDB 实例模型测试"""

    def test_rdb_instance_creation(self, db_session):
        """测试 RDB 实例创建"""
        env = Environment(name="测试环境", code="test")
        db_session.add(env)
        db_session.commit()
        
        instance = RDBInstance(
            name="test_mysql",
            host="localhost",
            port=3306,
            username="root",
            environment_id=env.id,
            instance_type="mysql",
            status=True
        )
        db_session.add(instance)
        db_session.commit()
        
        assert instance.id is not None
        assert instance.name == "test_mysql"
        assert instance.port == 3306


class TestScriptModel:
    """脚本模型测试"""

    def test_script_creation(self, db_session):
        """测试脚本创建"""
        user = User(username="creator", role=UserRole.OPERATOR)
        db_session.add(user)
        db_session.commit()
        
        script = Script(
            name="测试脚本",
            script_type=ScriptType.PYTHON,
            content="print('hello')",
            description="这是一个测试脚本",
            created_by=user.id,
            is_enabled=True
        )
        db_session.add(script)
        db_session.commit()
        
        assert script.id is not None
        assert script.name == "测试脚本"
        assert script.script_type == ScriptType.PYTHON
        assert script.version == 1

    def test_script_version_increment(self, db_session):
        """测试脚本版本号"""
        user = User(username="creator", role=UserRole.OPERATOR)
        db_session.add(user)
        db_session.commit()
        
        script = Script(
            name="版本测试脚本",
            script_type=ScriptType.BASH,
            content="echo 'v1'",
            created_by=user.id
        )
        db_session.add(script)
        db_session.commit()
        
        initial_version = script.version
        script.version += 1
        db_session.commit()
        
        assert script.version == initial_version + 1


class TestScheduledTaskModel:
    """定时任务模型测试"""

    def test_scheduled_task_creation(self, db_session):
        """测试定时任务创建"""
        user = User(username="creator", role=UserRole.OPERATOR)
        db_session.add(user)
        db_session.commit()
        
        script = Script(
            name="定时任务脚本",
            script_type=ScriptType.PYTHON,
            content="print('task')",
            created_by=user.id
        )
        db_session.add(script)
        db_session.commit()
        
        task = ScheduledTask(
            name="测试定时任务",
            script_id=script.id,
            cron_expression="0 0 * * *",
            timezone="Asia/Shanghai",
            status="enabled",
            created_by=user.id
        )
        db_session.add(task)
        db_session.commit()
        
        assert task.id is not None
        assert task.name == "测试定时任务"
        assert task.cron_expression == "0 0 * * *"
        assert task.status == "enabled"
