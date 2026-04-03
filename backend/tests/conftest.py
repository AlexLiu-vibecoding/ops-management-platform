"""
测试配置
"""
import pytest
import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import User, UserRole, Environment, GlobalConfig
from app.utils.auth import hash_password, create_access_token


# 使用内存数据库进行测试
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# 覆盖数据库依赖
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        # 初始化默认配置
        _init_default_configs(db)
        yield db
    finally:
        db.close()
        # 清理所有表
        Base.metadata.drop_all(bind=engine)


def _init_default_configs(db):
    """初始化默认配置"""
    configs = [
        GlobalConfig(config_key="storage_type", config_value="local"),
        GlobalConfig(config_key="retention_days", config_value="30"),
        GlobalConfig(config_key="size_threshold", config_value="10000000"),
        GlobalConfig(config_key="local_path", config_value="/app/data/sql_files"),
    ]
    for config in configs:
        db.add(config)
    db.commit()


@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端 - 使用同步方式处理异步 ASGI 应用"""
    transport = httpx.ASGITransport(app=app)
    
    class SyncTestClient:
        """同步测试客户端包装器"""
        def __init__(self, app, base_url="http://testserver"):
            self._transport = httpx.ASGITransport(app=app)
            self._base_url = base_url
            self._client = None
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
        
        def _run_async(self, coro):
            """在同步上下文中运行异步协程"""
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            
            if loop and loop.is_running():
                # 如果已有运行中的事件循环，创建新的
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            else:
                return asyncio.run(coro)
        
        def get(self, url, **kwargs):
            async def _get():
                async with httpx.AsyncClient(transport=self._transport, base_url=self._base_url) as client:
                    return await client.get(url, **kwargs)
            return self._run_async(_get())
        
        def post(self, url, **kwargs):
            async def _post():
                async with httpx.AsyncClient(transport=self._transport, base_url=self._base_url) as client:
                    return await client.post(url, **kwargs)
            return self._run_async(_post())
        
        def put(self, url, **kwargs):
            async def _put():
                async with httpx.AsyncClient(transport=self._transport, base_url=self._base_url) as client:
                    return await client.put(url, **kwargs)
            return self._run_async(_put())
        
        def delete(self, url, **kwargs):
            async def _delete():
                async with httpx.AsyncClient(transport=self._transport, base_url=self._base_url) as client:
                    return await client.delete(url, **kwargs)
            return self._run_async(_delete())
    
    return SyncTestClient(app)


@pytest.fixture(scope="function")
def super_admin_token(db_session):
    """创建超级管理员并返回 token"""
    admin = User(
        username="admin",
        password_hash=hash_password("admin123"),
        real_name="管理员",
        email="admin@test.com",
        role=UserRole.SUPER_ADMIN,
        status=True
    )
    db_session.add(admin)
    db_session.commit()
    
    token = create_access_token({"sub": admin.id})
    return token


@pytest.fixture(scope="function")
def operator_token(db_session):
    """创建普通运维用户并返回 token"""
    user = User(
        username="operator",
        password_hash=hash_password("operator123"),
        real_name="运维人员",
        email="operator@test.com",
        role=UserRole.OPERATOR,
        status=True
    )
    db_session.add(user)
    db_session.commit()
    
    token = create_access_token({"sub": user.id})
    return token


@pytest.fixture(scope="function")
def approval_admin_token(db_session):
    """创建审批管理员并返回 token"""
    user = User(
        username="approval_admin",
        password_hash=hash_password("admin123"),
        real_name="审批管理员",
        email="approval@test.com",
        role=UserRole.APPROVAL_ADMIN,
        status=True
    )
    db_session.add(user)
    db_session.commit()
    
    token = create_access_token({"sub": user.id})
    return token


@pytest.fixture(scope="function")
def test_environment(db_session):
    """创建测试环境"""
    env = Environment(
        name="测试环境",
        code="test",
        color="#52C41A",
        require_approval=False,
        status=True
    )
    db_session.add(env)
    db_session.commit()
    db_session.refresh(env)
    return env


@pytest.fixture(scope="function")
def readonly_token(db_session):
    """创建只读用户并返回 token"""
    user = User(
        username="readonly",
        password_hash=hash_password("readonly123"),
        real_name="只读用户",
        email="readonly@test.com",
        role=UserRole.READONLY,
        status=True
    )
    db_session.add(user)
    db_session.commit()
    
    token = create_access_token({"sub": user.id})
    return token


@pytest.fixture(scope="function")
def test_rdb_instance(db_session, test_environment):
    """创建测试 RDB 实例"""
    from app.models import RDBInstance, RDBType
    
    instance = RDBInstance(
        name="test-mysql-instance",
        host="localhost",
        port=3306,
        db_type=RDBType.MYSQL,
        environment_id=test_environment.id,
        status=True
    )
    db_session.add(instance)
    db_session.commit()
    db_session.refresh(instance)
    return instance


@pytest.fixture(scope="function")
def auth_headers(operator_token):
    """普通用户认证头"""
    return {"Authorization": f"Bearer {operator_token}"}


@pytest.fixture(scope="function")
def admin_headers(super_admin_token):
    """管理员认证头"""
    return {"Authorization": f"Bearer {super_admin_token}"}


@pytest.fixture(scope="function")
def approval_headers(approval_admin_token):
    """审批管理员认证头"""
    return {"Authorization": f"Bearer {approval_admin_token}"}


@pytest.fixture(scope="function")
def create_test_user(db_session):
    """创建测试用户的工厂函数"""
    def _create_user(username, password="testpass", role=UserRole.DEVELOPER, **kwargs):
        user = User(
            username=username,
            password_hash=hash_password(password),
            real_name=kwargs.get("real_name", f"User {username}"),
            email=kwargs.get("email", f"{username}@test.com"),
            role=role,
            status=kwargs.get("status", True)
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return _create_user


@pytest.fixture(scope="function")
def create_test_environment(db_session):
    """创建测试环境的工厂函数"""
    def _create_env(name, code, **kwargs):
        env = Environment(
            name=name,
            code=code,
            color=kwargs.get("color", "#1890FF"),
            require_approval=kwargs.get("require_approval", False),
            status=kwargs.get("status", True),
            description=kwargs.get("description")
        )
        db_session.add(env)
        db_session.commit()
        db_session.refresh(env)
        return env
    return _create_env


@pytest.fixture(scope="function")
def create_test_script(db_session, create_test_user):
    """创建测试脚本的工厂函数"""
    from app.models import Script, ScriptType
    
    def _create_script(name, script_type=ScriptType.PYTHON, content=None, **kwargs):
        # 创建用户（如果没有指定）
        user = kwargs.get("created_by")
        if user is None:
            user = create_test_user(f"script_creator_{name}")
        
        if content is None:
            if script_type == ScriptType.PYTHON:
                content = f"print('Hello from {name}')"
            elif script_type == ScriptType.BASH:
                content = f"#!/bin/bash\necho 'Hello from {name}'"
            else:
                content = f"-- Script {name}"
        
        script = Script(
            name=name,
            script_type=script_type,
            content=content,
            description=kwargs.get("description", f"Test script: {name}"),
            created_by=user.id,
            is_enabled=kwargs.get("is_enabled", True)
        )
        db_session.add(script)
        db_session.commit()
        db_session.refresh(script)
        return script
    return _create_script


@pytest.fixture(scope="function")
def create_test_notification_channel(db_session, create_test_user):
    """创建测试通知通道的工厂函数"""
    from app.models import NotificationChannel
    
    def _create_channel(name, channel_type="webhook", **kwargs):
        user = kwargs.get("created_by")
        if user is None:
            user = create_test_user(f"channel_creator_{name}")
        
        channel = NotificationChannel(
            name=name,
            channel_type=channel_type,
            config=kwargs.get("config", {"url": "http://test.com/webhook"}),
            description=kwargs.get("description", f"Test channel: {name}"),
            created_by=user.id,
            is_enabled=kwargs.get("is_enabled", True)
        )
        db_session.add(channel)
        db_session.commit()
        db_session.refresh(channel)
        return channel
    return _create_channel


@pytest.fixture(scope="function")
def event_loop():
    """创建事件循环供异步测试使用"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
