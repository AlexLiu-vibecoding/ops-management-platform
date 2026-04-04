#!/usr/bin/env python3
"""
自动化测试脚本 - 测试 API 异常处理
"""
import requests
import json
import sys

BASE_URL = "http://localhost:5000/api/v1"

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def success(self, name):
        self.passed += 1
        print(f"✅ {name}")
    
    def fail(self, name, reason):
        self.failed += 1
        self.errors.append(f"{name}: {reason}")
        print(f"❌ {name}: {reason}")
    
    def summary(self):
        print(f"\n{'='*50}")
        print(f"测试结果: 通过 {self.passed}, 失败 {self.failed}")
        if self.errors:
            print("\n失败详情:")
            for e in self.errors:
                print(f"  - {e}")
        return self.failed == 0


def test_api_health():
    """测试 API 健康状态"""
    result = TestResult()
    
    # 1. 测试健康检查
    try:
        resp = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health", timeout=5)
        if resp.status_code == 200 and resp.json().get("status") == "healthy":
            result.success("健康检查")
        else:
            result.fail("健康检查", f"状态码: {resp.status_code}")
    except Exception as e:
        result.fail("健康检查", str(e))
    
    return result


def test_auth_api():
    """测试认证 API 异常处理"""
    result = TestResult()
    
    # 1. 测试登录 - 用户不存在
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "nonexistent_user",
            "password": "wrong_password"
        }, timeout=5)
        if resp.status_code == 401:
            result.success("登录-用户不存在返回401")
        else:
            result.fail("登录-用户不存在", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("登录-用户不存在", str(e))
    
    # 2. 测试登录 - 缺少参数
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={}, timeout=5)
        if resp.status_code == 422:  # 验证错误
            result.success("登录-缺少参数返回422")
        else:
            result.fail("登录-缺少参数", f"期望422, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("登录-缺少参数", str(e))
    
    # 3. 测试获取当前用户 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/auth/me", timeout=5)
        if resp.status_code == 401:
            result.success("获取用户信息-未登录返回401")
        else:
            result.fail("获取用户信息-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取用户信息-未登录", str(e))
    
    # 4. 测试注册 - 缺少必填字段
    try:
        resp = requests.post(f"{BASE_URL}/auth/register", json={}, timeout=5)
        if resp.status_code == 422:
            result.success("注册-缺少参数返回422")
        else:
            result.fail("注册-缺少参数", f"期望422, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("注册-缺少参数", str(e))
    
    return result


def test_init_api():
    """测试初始化 API"""
    result = TestResult()
    
    # 1. 测试获取初始化状态
    try:
        resp = requests.get(f"{BASE_URL}/init/status", timeout=5)
        if resp.status_code == 200 and "is_initialized" in resp.json():
            result.success("获取初始化状态")
        else:
            result.fail("获取初始化状态", f"状态码: {resp.status_code}")
    except Exception as e:
        result.fail("获取初始化状态", str(e))
    
    # 2. 测试数据库连接 - 无效配置
    try:
        resp = requests.post(f"{BASE_URL}/init/test-database", json={
            "host": "invalid_host_12345",
            "port": 3306,
            "username": "test",
            "password": "test",
            "database": "test"
        }, timeout=10)
        if resp.status_code == 200 and resp.json().get("success") == False:
            result.success("测试数据库连接-无效配置返回失败")
        else:
            result.fail("测试数据库连接-无效配置", f"响应: {resp.json()}")
    except Exception as e:
        result.fail("测试数据库连接-无效配置", str(e))
    
    return result


def test_instances_api():
    """测试实例管理 API"""
    result = TestResult()
    
    # 1. 测试获取实例列表 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/instances", timeout=5)
        if resp.status_code == 401:
            result.success("获取实例列表-未登录返回401")
        else:
            result.fail("获取实例列表-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取实例列表-未登录", str(e))
    
    # 2. 测试获取不存在的实例 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/instances/99999", timeout=5)
        if resp.status_code == 401:
            result.success("获取实例详情-未登录返回401")
        else:
            result.fail("获取实例详情-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取实例详情-未登录", str(e))
    
    return result


def test_approvals_api():
    """测试审批 API"""
    result = TestResult()
    
    # 1. 测试获取审批列表 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/approvals", timeout=5)
        if resp.status_code == 401:
            result.success("获取审批列表-未登录返回401")
        else:
            result.fail("获取审批列表-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取审批列表-未登录", str(e))
    
    # 2. 测试获取不存在的审批 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/approvals/99999", timeout=5)
        if resp.status_code == 401:
            result.success("获取审批详情-未登录返回401")
        else:
            result.fail("获取审批详情-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取审批详情-未登录", str(e))
    
    return result


def test_sql_api():
    """测试 SQL 执行 API"""
    result = TestResult()
    
    # 1. 测试执行 SQL - 未登录
    try:
        resp = requests.post(f"{BASE_URL}/sql/execute", json={
            "instance_id": 1,
            "sql": "SELECT 1"
        }, timeout=5)
        if resp.status_code == 401:
            result.success("执行SQL-未登录返回401")
        else:
            result.fail("执行SQL-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("执行SQL-未登录", str(e))
    
    # 2. 测试获取数据库列表 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/sql/databases/1", timeout=5)
        if resp.status_code == 401:
            result.success("获取数据库列表-未登录返回401")
        else:
            result.fail("获取数据库列表-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取数据库列表-未登录", str(e))
    
    return result


def test_environments_api():
    """测试环境管理 API"""
    result = TestResult()
    
    # 1. 测试获取环境列表 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/environments", timeout=5)
        if resp.status_code == 401:
            result.success("获取环境列表-未登录返回401")
        else:
            result.fail("获取环境列表-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取环境列表-未登录", str(e))
    
    return result


def test_users_api():
    """测试用户管理 API"""
    result = TestResult()
    
    # 1. 测试获取用户列表 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/users", timeout=5)
        if resp.status_code == 401:
            result.success("获取用户列表-未登录返回401")
        else:
            result.fail("获取用户列表-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取用户列表-未登录", str(e))
    
    return result


def test_scripts_api():
    """测试脚本管理 API"""
    result = TestResult()
    
    # 1. 测试获取脚本列表 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/scripts", timeout=5)
        if resp.status_code == 401:
            result.success("获取脚本列表-未登录返回401")
        else:
            result.fail("获取脚本列表-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取脚本列表-未登录", str(e))
    
    return result


def test_scheduled_tasks_api():
    """测试定时任务 API"""
    result = TestResult()
    
    # 1. 测试获取定时任务列表 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/scheduled-tasks", timeout=5)
        if resp.status_code == 401:
            result.success("获取定时任务列表-未登录返回401")
        else:
            result.fail("获取定时任务列表-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取定时任务列表-未登录", str(e))
    
    return result


def main():
    print("=" * 50)
    print("开始执行自动化测试...")
    print("=" * 50)
    
    all_results = []
    
    print("\n📋 测试 API 健康状态")
    all_results.append(test_api_health())
    
    print("\n📋 测试认证 API")
    all_results.append(test_auth_api())
    
    print("\n📋 测试初始化 API")
    all_results.append(test_init_api())
    
    print("\n📋 测试实例管理 API")
    all_results.append(test_instances_api())
    
    print("\n📋 测试审批 API")
    all_results.append(test_approvals_api())
    
    print("\n📋 测试 SQL 执行 API")
    all_results.append(test_sql_api())
    
    print("\n📋 测试环境管理 API")
    all_results.append(test_environments_api())
    
    print("\n📋 测试用户管理 API")
    all_results.append(test_users_api())
    
    print("\n📋 测试脚本管理 API")
    all_results.append(test_scripts_api())
    
    print("\n📋 测试定时任务 API")
    all_results.append(test_scheduled_tasks_api())
    
    # 汇总结果
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)
    
    print(f"\n{'='*50}")
    print(f"总测试结果: 通过 {total_passed}, 失败 {total_failed}")
    
    if total_failed > 0:
        print("\n失败详情:")
        for r in all_results:
            for e in r.errors:
                print(f"  - {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
