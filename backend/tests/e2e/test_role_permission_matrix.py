"""
端到端测试：角色权限控制验证

覆盖所有角色的权限矩阵：
1. super_admin - 全部权限
2. approval_admin - 审批+查看+执行
3. operator - 查看+创建+编辑（部分）
4. developer - 仅查看+申请变更
5. readonly - 仅查看

测试内容：
- 导航栏菜单可见性（/menu/user-menu）
- API 接口访问控制
- 角色切换后权限变化

运行方式：pytest tests/e2e/test_role_permission_matrix.py -v --no-cov
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import (
    User, UserRole,
    MenuConfig, Environment, GlobalConfig,
    RoleEnvironment,
)
from app.utils.auth import hash_password


# 使用内存数据库
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        _init_test_data(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _init_test_data(db):
    """初始化测试数据：用户 + 基础菜单 + 权限（使用默认配置回退）"""
    # 默认配置
    for c in [
        GlobalConfig(config_key="storage_type", config_value="local"),
        GlobalConfig(config_key="retention_days", config_value="30"),
        GlobalConfig(config_key="size_threshold", config_value="10000000"),
        GlobalConfig(config_key="local_path", config_value="/app/data/sql_files"),
    ]:
        db.add(c)

    # 环境
    for e in [
        Environment(id=1, name="开发环境", code="development", color="#52C41A"),
        Environment(id=2, name="测试环境", code="testing", color="#1890FF"),
        Environment(id=4, name="生产环境", code="production", color="#FF4D4F", require_approval=True),
    ]:
        db.add(e)

    # 用户（5个角色）
    for username, password, real_name, role in [
        ("admin", "admin123", "超级管理员", "super_admin"),
        ("approver", "approver123", "审批管理员", "approval_admin"),
        ("operator", "operator123", "运维人员", "operator"),
        ("dev_user", "dev123", "开发人员", "developer"),
        ("reader", "reader123", "只读用户", "readonly"),
    ]:
        db.add(User(
            username=username,
            password_hash=hash_password(password),
            real_name=real_name,
            email=f"{username}@test.com",
            role=UserRole(role),
            status=True,
        ))
    db.commit()

    # 菜单数据（带 permission 字段，用于权限过滤测试）
    # 关键：不创建 Permission 和 RolePermission 记录，
    # 这样 PermissionService.get_role_permissions() 会回退到 DEFAULT_ROLE_PERMISSIONS
    _init_menus(db)

    # 角色环境权限
    for role, env_id in [
        ("super_admin", 1), ("super_admin", 2), ("super_admin", 4),
        ("approval_admin", 1), ("approval_admin", 2), ("approval_admin", 4),
        ("operator", 1), ("operator", 2),
        ("developer", 1), ("developer", 2),
        ("readonly", 1), ("readonly", 2),
    ]:
        db.add(RoleEnvironment(role=role, environment_id=env_id))
    db.commit()


def _init_menus(db):
    """初始化菜单配置 - 覆盖主要业务菜单"""
    menus_data = [
        # 一级菜单（无 parent_id）
        (21, None, "实例管理", "/instances", "Grid", "instance:view", 11),
        (22, None, "环境管理", "/environments", "Collection", "environment:view", 12),
        (91, None, "通知管理", "/notification", "Bell", "notification:view", 60),

        # 变更管理（parent_id=4）
        (4, None, "变更管理", "/change", "EditPen", None, 30),
        (41, 4, "DB变更", "/change/requests", "Coin", "approval:view", 1),
        (19, 4, "Redis变更", "/change/redis-requests", "Key", "approval:view", 2),
        (83, 4, "变更窗口", "/change/windows", "Clock", "approval:view", 3),

        # 监控中心（parent_id=5）
        (5, None, "监控中心", "/monitor", "Monitor", None, 40),
        (51, 5, "性能监控", "/monitor/performance", "TrendCharts", "monitor:view", 1),
        (52, 5, "慢查询监控", "/monitor/slow-query", "Timer", "monitor:view", 2),
        (85, 5, "告警中心", "/monitor/alerts", "Bell", "monitor:view", 3),
        (86, 5, "主从复制", "/monitor/replication", "Connection", "monitor:view", 4),
        (87, 5, "事务与锁", "/monitor/locks", "Lock", "monitor:view", 5),
        (88, 5, "巡检报告", "/monitor/inspection", "DocumentChecked", "monitor:view", 6),
        (89, 5, "定时巡检", "/monitor/scheduled-inspection", "AlarmClock", "monitor:view", 7),
        (53, 5, "监控配置", "/monitor/settings", "Setting", "monitor:config", 9),
        (97, 5, "SQL性能对比", "/monitor/sql-performance", "DataLine", "monitor:view", 90),

        # 自动化（parent_id=6）
        (6, None, "自动化", "/automation", "SetUp", None, 50),
        (61, 6, "脚本管理", "/scripts", "DocumentCopy", "script:view", 51),
        (62, 6, "定时任务", "/scheduled-tasks", "AlarmClock", "scheduler:view", 52),

        # 系统管理（parent_id=7）
        (7, None, "系统管理", "/system-root", "Setting", None, 100),
        (71, 7, "用户管理", "/users", "User", "system:user_manage", 101),
        (77, 7, "权限管理", "/permissions", "Lock", "system:role_manage", 105),
        (75, 7, "审计日志", "/audit", "Tickets", "system:audit_log", 103),
        (76, 7, "系统设置", "/system", "Tools", "system:config", 104),
        (96, 7, "AI 模型配置", "/ai-models", "MagicStick", "ai:model_view", 15),
    ]

    for item in menus_data:
        db.add(MenuConfig(
            id=item[0],
            parent_id=item[1],
            name=item[2],
            path=item[3],
            icon=item[4],
            permission=item[5] if len(item) > 5 else None,
            sort_order=item[6] if len(item) > 6 else 0,
            is_visible=True,
            is_enabled=True,
        ))
    db.commit()


@pytest.fixture(scope="function")
def async_client(db_session):
    """创建异步测试客户端"""
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")


async def _login(async_client, username="admin", password="admin123"):
    """登录获取 token"""
    resp = await async_client.post("/api/v1/auth/login", json={
        "username": username,
        "password": password,
    })
    assert resp.status_code == 200, f"登录失败: {resp.json()}"
    return resp.json()["access_token"]


def _get_menu_paths(menus):
    """递归提取所有菜单的 path（排除空路径的父级分组菜单）"""
    paths = []
    skip_paths = {"/change", "/monitor", "/automation", "/system-root"}
    for menu in menus:
        path = menu.get("path")
        if path and path not in skip_paths:
            paths.append(path)
        children = menu.get("children", [])
        if children:
            paths.extend(_get_menu_paths(children))
    return paths


# ==================== 测试类：菜单可见性 ====================

class TestRoleMenuVisibility:

    @pytest.mark.asyncio
    async def test_super_admin_sees_all_menus(self, async_client):
        token = await _login(async_client, "admin", "admin123")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await async_client.get("/api/v1/menu/user-menu", headers=headers)
        assert resp.status_code == 200
        visible_paths = _get_menu_paths(resp.json())

        must_see = [
            "/instances", "/environments",
            "/change/requests", "/change/redis-requests",
            "/monitor/performance", "/monitor/settings",
            "/scripts", "/scheduled-tasks",
            "/notification", "/ai-models",
            "/users", "/permissions", "/audit", "/system",
        ]
        for p in must_see:
            assert p in visible_paths, f"super_admin 看不到菜单: {p}，当前可见: {visible_paths}"

    @pytest.mark.asyncio
    async def test_readonly_visible_and_hidden(self, async_client):
        """
        readonly 的菜单可见性 - 核心测试用例
        
        验证修复后的行为：
        1. readonly 能看到实例管理（修复前被前端路由 roles 限制）
        2. readonly 能看到 AI 模型配置（新增 ai:model_view 权限）
        3. readonly 能看到通知管理（新增 notification:view 权限）
        4. readonly 不能看到用户管理等系统管理菜单
        """
        token = await _login(async_client, "reader", "reader123")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await async_client.get("/api/v1/menu/user-menu", headers=headers)
        assert resp.status_code == 200
        visible_paths = _get_menu_paths(resp.json())

        # === 应该看到的功能 ===
        assert "/instances" in visible_paths, \
            f"FAIL: readonly 用户看不到实例管理！可见: {visible_paths}"
        assert "/ai-models" in visible_paths, \
            f"FAIL: readonly 应该能看到 AI 模型配置！可见: {visible_paths}"
        assert "/notification" in visible_paths, \
            f"FAIL: readonly 应该能看到通知管理！可见: {visible_paths}"
        assert "/environments" in visible_paths, \
            f"readonly 应该看到环境管理！可见: {visible_paths}"
        assert "/change/requests" in visible_paths, \
            f"readonly 应该看到变更请求！可见: {visible_paths}"
        assert "/monitor/performance" in visible_paths, \
            f"readonly 应该看到性能监控！可见: {visible_paths}"
        assert "/scripts" in visible_paths, \
            f"readonly 应该看到脚本管理！可见: {visible_paths}"
        assert "/scheduled-tasks" in visible_paths, \
            f"readonly 应该看到定时任务！可见: {visible_paths}"

        # === 不应该看到的功能 ===
        assert "/users" not in visible_paths, "PASS: readonly 正确看不到用户管理"
        assert "/permissions" not in visible_paths, "PASS: readonly 正确看不到权限管理"
        assert "/system" not in visible_paths, "PASS: readonly 正确看不到系统设置"
        assert "/audit" not in visible_paths, "PASS: readonly 正确看不到审计日志"
        assert "/monitor/settings" not in visible_paths, "PASS: readonly 正确看不到监控配置"

    @pytest.mark.asyncio
    async def test_operator_visible_and_hidden(self, async_client):
        token = await _login(async_client, "operator", "operator123")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await async_client.get("/api/v1/menu/user-menu", headers=headers)
        assert resp.status_code == 200
        paths = _get_menu_paths(resp.json())

        assert "/instances" in paths, "operator 应该看到实例管理"
        assert "/ai-models" in paths, "operator 应该看到 AI 模型配置"
        assert "/notification" in paths, "operator 应该看到通知管理"
        assert "/users" not in paths, "operator 不应看到用户管理"
        assert "/system" not in paths, "operator 不应看到系统设置"
        assert "/audit" not in paths, "operator 不应看到审计日志"
        assert "/monitor/settings" not in paths, "operator 不应看到监控配置"

    @pytest.mark.asyncio
    async def test_developer_visible_and_hidden(self, async_client):
        token = await _login(async_client, "dev_user", "dev123")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await async_client.get("/api/v1/menu/user-menu", headers=headers)
        assert resp.status_code == 200
        paths = _get_menu_paths(resp.json())

        assert "/instances" in paths, "developer 应该看到实例管理"
        assert "/ai-models" in paths, "developer 应该看到 AI 模型配置"
        assert "/notification" in paths, "developer 应该看到通知管理"
        assert "/users" not in paths, "developer 不应看到用户管理"
        assert "/system" not in paths, "developer 不应看到系统设置"

    @pytest.mark.asyncio
    async def test_approval_admin_visible_and_hidden(self, async_client):
        token = await _login(async_client, "approver", "approver123")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await async_client.get("/api/v1/menu/user-menu", headers=headers)
        assert resp.status_code == 200
        paths = _get_menu_paths(resp.json())

        assert "/instances" in paths, "approval_admin 应该看到实例管理"
        assert "/ai-models" in paths, "approval_admin 应该看到 AI 模型配置"
        assert "/notification" in paths, "approval_admin 应该看到通知管理"
        assert "/audit" in paths, "approval_admin 应该看到审计日志"
        assert "/monitor/settings" in paths, "approval_admin 应该看到监控配置"
        assert "/users" not in paths, "approval_admin 不应看到用户管理"
        assert "/system" not in paths, "approval_admin 不应看到系统设置"


# ==================== 测试类：API 访问权限 ====================

class TestRoleAPIAccess:

    @pytest.mark.asyncio
    async def test_readonly_can_list_instances(self, async_client):
        token = await _login(async_client, "reader", "reader123")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await async_client.get("/api/v1/rdb-instances", headers=headers)
        assert resp.status_code != 403, "readonly 应该能访问实例列表接口"
        assert resp.status_code != 401, "认证问题"

    @pytest.mark.asyncio
    async def test_readonly_cannot_create_instance(self, async_client):
        token = await _login(async_client, "reader", "reader123")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await async_client.post("/api/v1/rdb-instances",
                                       json={"name": "test", "host": "localhost", "port": 3306},
                                       headers=headers)
        assert resp.status_code == 403, f"readonly 不应能创建实例，实际: {resp.status_code}"

    @pytest.mark.asyncio
    async def test_developer_cannot_create_instance(self, async_client):
        token = await _login(async_client, "dev_user", "dev123")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await async_client.post("/api/v1/rdb-instances",
                                       json={"name": "test", "host": "localhost", "port": 3306},
                                       headers=headers)
        assert resp.status_code == 403, f"developer 不应能创建实例，实际: {resp.status_code}"

    @pytest.mark.asyncio
    async def test_operator_can_create_instance(self, async_client):
        token = await _login(async_client, "operator", "operator123")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await async_client.post("/api/v1/rdb-instances",
                                       json={"name": "test", "host": "localhost", "port": 3306, "db_type": "MYSQL"},
                                       headers=headers)
        assert resp.status_code != 403, f"operator 应该能创建实例，实际: {resp.status_code}"

    @pytest.mark.asyncio
    async def test_non_admin_cannot_manage_users(self, async_client):
        """非管理员角色不能通过 POST 创建/修改用户（写操作受限）"""
        for role, pwd in [("operator", "operator123"), ("dev_user", "dev123"),
                          ("reader", "reader123")]:
            token = await _login(async_client, role, pwd)
            headers = {"Authorization": f"Bearer {token}"}
            # 尝试创建用户（写操作应该被拒绝）
            resp = await async_client.post("/api/v1/users",
                                            json={"username": "hack", "password": "hack123", "role": "readonly"},
                                            headers=headers)
            assert resp.status_code == 403, f"{role} 不应能创建用户，实际: {resp.status_code}"

    @pytest.mark.asyncio
    async def test_only_superuser_access_permissions_api(self, async_client):
        for role, pwd in [("approver", "approver123"), ("operator", "operator123"),
                          ("dev_user", "dev123"), ("reader", "reader123")]:
            token = await _login(async_client, role, pwd)
            headers = {"Authorization": f"Bearer {token}"}
            resp = await async_client.get("/api/v1/permissions", headers=headers)
            assert resp.status_code == 403, f"{role} 不应访问 /permissions，实际: {resp.status_code}"

    @pytest.mark.asyncio
    async def test_readonly_can_list_environments(self, async_client):
        token = await _login(async_client, "reader", "reader123")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await async_client.get("/api/v1/environments", headers=headers)
        assert resp.status_code != 403, "readonly 应该能访问环境列表"

    @pytest.mark.asyncio
    async def test_readonly_cannot_create_environment(self, async_client):
        token = await _login(async_client, "reader", "reader123")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await async_client.post("/api/v1/environments",
                                       json={"name": "test", "code": "test"},
                                       headers=headers)
        assert resp.status_code == 403, f"readonly 不应能创建环境，实际: {resp.status_code}"


# ==================== 测试类：只读用户核心场景 ====================

class TestReadonlyUserCoreScenario:

    @pytest.mark.asyncio
    async def test_readuser_instance_management_flow(self, async_client):
        """
        完整流程：只读用户访问实例管理
        
        场景复现：
        1. 只读用户登录
        2. 获取导航栏菜单 -> 应包含实例管理
        3. 访问实例列表 API -> 应返回成功
        4. 尝试添加实例 -> 应被拒绝
        """
        token = await _login(async_client, "reader", "reader123")
        headers = {"Authorization": f"Bearer {token}"}

        # 步骤 2: 获取导航栏菜单
        resp = await async_client.get("/api/v1/menu/user-menu", headers=headers)
        assert resp.status_code == 200
        visible_paths = _get_menu_paths(resp.json())
        assert "/instances" in visible_paths, \
            f"[核心问题] 只读用户导航栏没有实例管理菜单！可见: {visible_paths}"

        print(f"\n只读用户可见菜单 ({len(visible_paths)} 个):")
        for p in sorted(visible_paths):
            print(f"   - {p}")

        # 步骤 3: 访问实例列表
        resp = await async_client.get("/api/v1/rdb-instances", headers=headers)
        assert resp.status_code == 200, f"只读用户无法访问实例列表，状态码: {resp.status_code}"
        data = resp.json()
        assert "items" in data or "total" in data, "实例列表响应格式异常"

        # 步骤 4: 尝试添加实例（应被拒绝）
        resp = await async_client.post("/api/v1/rdb-instances",
                                        json={
                                            "name": "unauthorized-instance",
                                            "host": "localhost",
                                            "port": 3306,
                                            "db_type": "MYSQL",
                                        },
                                        headers=headers)
        assert resp.status_code == 403, \
            f"只读用户不应该能创建实例，实际状态码: {resp.status_code}"

    @pytest.mark.asyncio
    async def test_readuser_ai_model_menu_visibility(self, async_client):
        """只读用户应该能看到 AI 模型配置菜单（修复后的新功能）"""
        token = await _login(async_client, "reader", "reader123")
        headers = {"Authorization": f"Bearer {token}"}
        resp = await async_client.get("/api/v1/menu/user-menu", headers=headers)
        assert resp.status_code == 200
        paths = _get_menu_paths(resp.json())
        assert "/ai-models" in paths, \
            f"只读用户应该能看到 AI 模型配置菜单！可见: {paths}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--no-cov"])
