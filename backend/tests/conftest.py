"""
测试配置
"""
import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import User, UserRole, Environment
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
        yield db
    finally:
        db.close()
        # 清理所有表
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端"""
    with TestClient(app) as c:
        yield c


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
