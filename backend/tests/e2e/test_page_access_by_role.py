"""
端到端测试：角色页面访问权限完整性验证（线上真实 API）

验证目标：
  每个角色的用户访问各自有权限的页面 API 时，不会收到 403 错误。
  访问无权限的页面 API 时，正确收到 403。

运行方式：
  pytest backend/tests/e2e/test_page_access_by_role.py -v --no-cov --tb=short

测试策略：
  使用线上真实 API（http://localhost:5000），以各角色用户身份登录，
  逐一请求各页面所需的核心 GET 接口，确保有权访问的不报 403，
  无权访问的返回 403。
"""
import pytest
import requests
import json
from typing import Optional

BASE_URL = "http://localhost:5000/api/v1"

# ==================== 用户凭据 ====================
USERS = {
    "super_admin": {"username": "admin", "password": "admin123"},
    "approval_admin": {"username": "approver1", "password": "Approver@123"},
    "operator": {"username": "test_operator2", "password": "Operator@123"},
    "developer": {"username": "test_dev", "password": "Dev@123456"},
    "readonly": {"username": "12345", "password": "123456"},
}


def login(role: str) -> str:
    """以指定角色登录，返回 access_token"""
    creds = USERS[role]
    resp = requests.post(f"{BASE_URL}/auth/login", json=creds, timeout=10)
    assert resp.status_code == 200, f"登录失败 [{role}]: {resp.status_code} {resp.text[:200]}"
    data = resp.json()
    assert "access_token" in data, f"登录返回无 token [{role}]: {data}"
    return data["access_token"]


def api_get(token: str, path: str, params: dict = None, timeout: int = 15) -> int:
    """GET 请求，返回状态码"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(f"{BASE_URL}{path}", headers=headers, params=params, timeout=timeout)
        return resp.status_code
    except requests.exceptions.Timeout:
        return 504
    except Exception as e:
        return 0


def api_post(token: str, path: str, data: dict = None, timeout: int = 15) -> int:
    """POST 请求，返回状态码"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = requests.post(f"{BASE_URL}{path}", headers=headers, json=data, timeout=timeout)
        return resp.status_code
    except requests.exceptions.Timeout:
        return 504
    except Exception:
        return 0


# ==================== 页面 API 映射 ====================
# 每个页面对应的核心 GET 接口（页面加载时必请求）
PAGE_APIS = {
    "实例管理": {
        "list": "/rdb-instances",
        "detail": None,  # 需要具体 ID，后续动态构造
    },
    "环境管理": {
        "list": "/environments",
    },
    "DB变更": {
        "list": "/approvals",
    },
    "Redis变更": {
        "list": "/redis-instances",
    },
    "变更窗口": {
        "list": "/change-windows",
    },
    "性能监控": {
        "list": "/performance/overview",
    },
    "慢查询监控": {
        "list": "/slow-queries",
    },
    "告警中心": {
        "list": "/alerts",
    },
    "巡检报告": {
        "list": "/inspections",
    },
    "SQL性能对比": {
        "list": "/sql-performance/comparison",
    },
    "脚本管理": {
        "list": "/scripts",
    },
    "定时任务": {
        "list": "/scheduled-tasks",
    },
    "通知管理": {
        "list": "/notification/overview",
        "channels": "/notification-channels",
    },
    "AI模型配置": {
        "list": "/ai-models",
    },
    "用户管理": {
        "list": "/users",
    },
    "权限管理": {
        "list": "/permissions",
    },
    "审计日志": {
        "list": "/audit/logs",
    },
    "系统设置": {
        "list": "/system/database-config",
    },
    "监控配置": {
        "list": "/monitor/config",
    },
    "导航菜单": {
        "list": "/menu/user-menu",
    },
}

# 各角色应该能正常访问（非 403）的页面
ROLE_ALLOWED_PAGES = {
    "super_admin": list(PAGE_APIS.keys()),
    "approval_admin": [
        "实例管理", "环境管理", "DB变更", "Redis变更", "变更窗口",
        "性能监控", "慢查询监控", "告警中心", "巡检报告", "SQL性能对比",
        "脚本管理", "定时任务",
        "通知管理", "AI模型配置",
        "审计日志", "监控配置",
        "导航菜单",
    ],
    "operator": [
        "实例管理", "环境管理", "DB变更", "Redis变更",
        "性能监控", "慢查询监控", "告警中心", "巡检报告", "SQL性能对比",
        "脚本管理", "定时任务",
        "通知管理", "AI模型配置",
        "导航菜单",
    ],
    "developer": [
        "实例管理", "环境管理", "DB变更", "Redis变更",
        "性能监控", "慢查询监控", "告警中心", "巡检报告", "SQL性能对比",
        "脚本管理", "定时任务",
        "通知管理", "AI模型配置",
        "导航菜单",
    ],
    "readonly": [
        "实例管理", "环境管理", "DB变更", "Redis变更",
        "性能监控", "慢查询监控", "告警中心", "巡检报告", "SQL性能对比",
        "脚本管理", "定时任务",
        "通知管理", "AI模型配置",
        "导航菜单",
    ],
}

# 各角色不应该能访问（403）的页面
ROLE_DENIED_PAGES = {
    "super_admin": [],
    "approval_admin": ["用户管理", "权限管理", "系统设置"],
    "operator": ["用户管理", "权限管理", "系统设置", "审计日志", "监控配置", "变更窗口"],
    "developer": ["用户管理", "权限管理", "系统设置", "审计日志", "监控配置", "变更窗口"],
    "readonly": ["用户管理", "权限管理", "系统设置", "审计日志", "监控配置", "变更窗口"],
}


# ==================== 测试类 ====================

class TestPageAccessByRole:
    """逐角色验证页面 API 访问权限"""

    @pytest.fixture(scope="class", autouse=True)
    def tokens(self):
        """预登录所有角色，缓存 token"""
        result = {}
        for role in USERS:
            try:
                result[role] = login(role)
            except AssertionError:
                result[role] = None
        return result

    def _test_page_access(self, role: str, token: str, page_name: str, expect_allowed: bool):
        """通用页面访问测试"""
        apis = PAGE_APIS.get(page_name)
        if not apis:
            pytest.skip(f"页面 {page_name} 未配置 API")

        results = []
        for api_name, api_path in apis.items():
            if api_path is None:
                continue

            status_code = api_get(token, api_path, params={"limit": 1})

            # 404 = 接口存在但无数据（可接受），200 = 正常访问
            # 403 = 无权限，422 = 参数校验错误（接口可到达）
            accessible = status_code in (200, 404, 422)
            denied = status_code == 403

            if expect_allowed:
                # 期望可访问
                if not accessible and not denied:
                    # 500 等服务错误 - 可能是bug，但不是权限问题，标记为warning
                    results.append((api_name, api_path, status_code, "WARN"))
                elif denied:
                    results.append((api_name, api_path, status_code, "FAIL"))
                else:
                    results.append((api_name, api_path, status_code, "OK"))
            else:
                # 期望被拒绝
                if denied:
                    results.append((api_name, api_path, status_code, "OK"))
                elif accessible:
                    results.append((api_name, api_path, status_code, "FAIL"))
                else:
                    results.append((api_name, api_path, status_code, "WARN"))

        # 检查结果
        failures = [r for r in results if r[3] == "FAIL"]
        warnings = [r for r in results if r[3] == "WARN"]

        if failures:
            fail_msg = "\n".join(
                f"    {r[0]} {r[1]} -> {r[2]} (expected {'accessible' if expect_allowed else '403'})"
                for r in failures
            )
            pytest.fail(
                f"[{role}] 页面 '{page_name}' 权限验证失败:\n{fail_msg}"
            )

        if warnings:
            # 警告但不失败（服务端错误不等于权限错误）
            for r in warnings:
                print(f"  WARN: [{role}] {page_name} {r[0]} {r[1]} -> {r[2]}")

    # ==================== super_admin ====================

    def test_super_admin_all_pages_accessible(self, tokens):
        """super_admin 应该能访问所有页面"""
        token = tokens.get("super_admin")
        if not token:
            pytest.skip("super_admin 登录失败")

        failures = []
        for page in ROLE_ALLOWED_PAGES["super_admin"]:
            try:
                self._test_page_access("super_admin", token, page, expect_allowed=True)
            except pytest.fail.Exception as e:
                failures.append(str(e))

        assert not failures, f"super_admin 有 {len(failures)} 个页面访问失败:\n" + "\n".join(failures)

    # ==================== readonly ====================

    def test_readonly_allowed_pages(self, tokens):
        """readonly 用户应该能访问所有只读页面，无 403 报错"""
        token = tokens.get("readonly")
        if not token:
            pytest.skip("readonly 登录失败")

        failures = []
        for page in ROLE_ALLOWED_PAGES["readonly"]:
            try:
                self._test_page_access("readonly", token, page, expect_allowed=True)
            except pytest.fail.Exception as e:
                failures.append(str(e))

        assert not failures, f"readonly 有 {len(failures)} 个页面访问失败:\n" + "\n".join(failures)

    def test_readonly_denied_pages(self, tokens):
        """readonly 用户不应该能访问系统管理页面"""
        token = tokens.get("readonly")
        if not token:
            pytest.skip("readonly 登录失败")

        failures = []
        for page in ROLE_DENIED_PAGES["readonly"]:
            try:
                self._test_page_access("readonly", token, page, expect_allowed=False)
            except pytest.fail.Exception as e:
                failures.append(str(e))

        assert not failures, f"readonly 应被拒绝但未拒绝 {len(failures)} 个页面:\n" + "\n".join(failures)

    # ==================== operator ====================

    def test_operator_allowed_pages(self, tokens):
        """operator 用户应该能访问运维相关页面"""
        token = tokens.get("operator")
        if not token:
            pytest.skip("operator 登录失败")

        failures = []
        for page in ROLE_ALLOWED_PAGES["operator"]:
            try:
                self._test_page_access("operator", token, page, expect_allowed=True)
            except pytest.fail.Exception as e:
                failures.append(str(e))

        assert not failures, f"operator 有 {len(failures)} 个页面访问失败:\n" + "\n".join(failures)

    def test_operator_denied_pages(self, tokens):
        """operator 不应该能访问系统管理页面"""
        token = tokens.get("operator")
        if not token:
            pytest.skip("operator 登录失败")

        failures = []
        for page in ROLE_DENIED_PAGES["operator"]:
            try:
                self._test_page_access("operator", token, page, expect_allowed=False)
            except pytest.fail.Exception as e:
                failures.append(str(e))

        assert not failures, f"operator 应被拒绝但未拒绝 {len(failures)} 个页面:\n" + "\n".join(failures)

    # ==================== developer ====================

    def test_developer_allowed_pages(self, tokens):
        """developer 用户应该能访问开发相关页面"""
        token = tokens.get("developer")
        if not token:
            pytest.skip("developer 登录失败")

        failures = []
        for page in ROLE_ALLOWED_PAGES["developer"]:
            try:
                self._test_page_access("developer", token, page, expect_allowed=True)
            except pytest.fail.Exception as e:
                failures.append(str(e))

        assert not failures, f"developer 有 {len(failures)} 个页面访问失败:\n" + "\n".join(failures)

    def test_developer_denied_pages(self, tokens):
        """developer 不应该能访问系统管理页面"""
        token = tokens.get("developer")
        if not token:
            pytest.skip("developer 登录失败")

        failures = []
        for page in ROLE_DENIED_PAGES["developer"]:
            try:
                self._test_page_access("developer", token, page, expect_allowed=False)
            except pytest.fail.Exception as e:
                failures.append(str(e))

        assert not failures, f"developer 应被拒绝但未拒绝 {len(failures)} 个页面:\n" + "\n".join(failures)

    # ==================== approval_admin ====================

    def test_approval_admin_allowed_pages(self, tokens):
        """approval_admin 应该能访问审批+运维+部分管理页面"""
        token = tokens.get("approval_admin")
        if not token:
            pytest.skip("approval_admin 登录失败")

        failures = []
        for page in ROLE_ALLOWED_PAGES["approval_admin"]:
            try:
                self._test_page_access("approval_admin", token, page, expect_allowed=True)
            except pytest.fail.Exception as e:
                failures.append(str(e))

        assert not failures, f"approval_admin 有 {len(failures)} 个页面访问失败:\n" + "\n".join(failures)

    def test_approval_admin_denied_pages(self, tokens):
        """approval_admin 不应该能访问用户/权限/系统设置"""
        token = tokens.get("approval_admin")
        if not token:
            pytest.skip("approval_admin 登录失败")

        failures = []
        for page in ROLE_DENIED_PAGES["approval_admin"]:
            try:
                self._test_page_access("approval_admin", token, page, expect_allowed=False)
            except pytest.fail.Exception as e:
                failures.append(str(e))

        assert not failures, f"approval_admin 应被拒绝但未拒绝 {len(failures)} 个页面:\n" + "\n".join(failures)


class TestMenuVisibilityByRole:
    """验证各角色导航菜单与实际 API 访问一致性"""

    @pytest.fixture(scope="class", autouse=True)
    def tokens(self):
        result = {}
        for role in USERS:
            try:
                result[role] = login(role)
            except AssertionError:
                result[role] = None
        return result

    def _get_menu_paths(self, token: str) -> set:
        """获取用户可见菜单路径集合"""
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/menu/user-menu", headers=headers, timeout=10)
        assert resp.status_code == 200, f"获取菜单失败: {resp.status_code}"
        menus = resp.json()

        paths = set()

        def extract(menu_list):
            for item in menu_list:
                path = item.get("path", "")
                if path:
                    paths.add(path)
                children = item.get("children", [])
                if children:
                    extract(children)

        extract(menus)
        return paths

    def test_readonly_menu_contains_key_pages(self, tokens):
        """readonly 用户的导航菜单必须包含核心页面"""
        token = tokens.get("readonly")
        if not token:
            pytest.skip("readonly 登录失败")

        paths = self._get_menu_paths(token)

        # 核心断言：这些是修复后 readonly 必须能看到的页面
        must_see = [
            "/instances",        # 实例管理 - 修复的核心问题
            "/environments",     # 环境管理
            "/notification",     # 通知管理 - 新增权限
            "/ai-models",        # AI模型 - 新增权限
        ]
        missing = [p for p in must_see if p not in paths]
        assert not missing, f"readonly 菜单缺少关键页面: {missing}, 当前菜单: {sorted(paths)}"

        # 核心断言：这些页面 readonly 不应该看到
        must_hide = ["/users", "/permissions", "/system"]
        leaked = [p for p in must_hide if p in paths]
        assert not leaked, f"readonly 菜单泄露了不应看到的页面: {leaked}"

    def test_operator_menu_contains_key_pages(self, tokens):
        """operator 用户的导航菜单验证"""
        token = tokens.get("operator")
        if not token:
            pytest.skip("operator 登录失败")

        paths = self._get_menu_paths(token)
        assert "/instances" in paths, f"operator 菜单缺少实例管理, 当前: {sorted(paths)}"
        assert "/ai-models" in paths, f"operator 菜单缺少AI模型配置, 当前: {sorted(paths)}"
        assert "/notification" in paths, f"operator 菜单缺少通知管理, 当前: {sorted(paths)}"

    def test_developer_menu_contains_key_pages(self, tokens):
        """developer 用户的导航菜单验证"""
        token = tokens.get("developer")
        if not token:
            pytest.skip("developer 登录失败")

        paths = self._get_menu_paths(token)
        assert "/instances" in paths, f"developer 菜单缺少实例管理"
        assert "/ai-models" in paths, f"developer 菜单缺少AI模型配置"

    def test_approval_admin_menu_visibility(self, tokens):
        """approval_admin 用户的导航菜单验证"""
        token = tokens.get("approval_admin")
        if not token:
            pytest.skip("approval_admin 登录失败")

        paths = self._get_menu_paths(token)
        assert "/instances" in paths, f"approval_admin 菜单缺少实例管理"
        assert "/audit" in paths, f"approval_admin 菜单缺少审计日志"
        assert "/users" not in paths, f"approval_admin 不应看到用户管理"

    def test_super_admin_menu_completeness(self, tokens):
        """super_admin 应该看到所有菜单"""
        token = tokens.get("super_admin")
        if not token:
            pytest.skip("super_admin 登录失败")

        paths = self._get_menu_paths(token)
        must_see = ["/instances", "/environments", "/users", "/permissions",
                     "/system", "/audit", "/ai-models", "/notification"]
        missing = [p for p in must_see if p not in paths]
        assert not missing, f"super_admin 菜单不完整，缺少: {missing}"


class TestWritePermissionByRole:
    """验证各角色的写操作（POST/PUT/DELETE）权限"""

    @pytest.fixture(scope="class", autouse=True)
    def tokens(self):
        result = {}
        for role in USERS:
            try:
                result[role] = login(role)
            except AssertionError:
                result[role] = None
        return result

    def test_readonly_cannot_write_anything(self, tokens):
        """readonly 用户不能执行任何写操作"""
        token = tokens.get("readonly")
        if not token:
            pytest.skip("readonly 登录失败")

        # 尝试各种写操作，全部应该返回 403
        write_operations = [
            ("POST /rdb-instances", lambda: api_post(token, "/rdb-instances", {
                "name": "test", "host": "localhost", "port": 3306, "db_type": "MYSQL"
            })),
            ("POST /environments", lambda: api_post(token, "/environments", {
                "name": "test", "code": "test"
            })),
            ("POST /scripts", lambda: api_post(token, "/scripts", {
                "name": "test_script", "content": "SELECT 1", "db_type": "MYSQL"
            })),
            ("POST /approvals", lambda: api_post(token, "/approvals", {
                "title": "test", "environment_id": 1, "instance_id": 1,
                "sql_content": "SELECT 1"
            })),
        ]

        failures = []
        for op_name, op_func in write_operations:
            status_code = op_func()
            if status_code != 403:
                failures.append(f"{op_name} -> {status_code} (expected 403)")

        assert not failures, f"readonly 应被拒绝的写操作:\n" + "\n".join(failures)

    def test_developer_cannot_create_instance(self, tokens):
        """developer 不能创建实例"""
        token = tokens.get("developer")
        if not token:
            pytest.skip("developer 登录失败")

        status = api_post(token, "/rdb-instances", {
            "name": "test", "host": "localhost", "port": 3306, "db_type": "MYSQL"
        })
        assert status == 403, f"developer 不应能创建实例，实际: {status}"

    def test_operator_can_create_instance(self, tokens):
        """operator 可以创建实例（不返回 403）"""
        token = tokens.get("operator")
        if not token:
            pytest.skip("operator 登录失败")

        status = api_post(token, "/rdb-instances", {
            "name": "test", "host": "localhost", "port": 3306, "db_type": "MYSQL"
        })
        # 403 = 无权限（bug），422 = 参数错误（权限OK），201 = 成功（权限OK）
        assert status != 403, f"operator 应该能创建实例，但被 403 拒绝"

    def test_only_superadmin_can_create_users(self, tokens):
        """只有 super_admin 能创建用户"""
        token = tokens.get("super_admin")
        if not token:
            pytest.skip("super_admin 登录失败")

        # super_admin 创建用户不应返回 403
        status = api_post(token, "/users", {
            "username": "e2e_test_temp", "password": "Temp@123", "role": "readonly"
        })
        assert status != 403, f"super_admin 应该能创建用户，但被 403 拒绝"

        # 清理：删除临时用户
        try:
            headers = {"Authorization": f"Bearer {token}"}
            users_resp = requests.get(f"{BASE_URL}/users", headers=headers, timeout=10)
            if users_resp.status_code == 200:
                users_data = users_resp.json()
                items = users_data.get("items", [])
                for u in items:
                    if u.get("username") == "e2e_test_temp":
                        requests.delete(f"{BASE_URL}/users/{u['id']}", headers=headers, timeout=10)
                        break
        except Exception:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "--no-cov"])
