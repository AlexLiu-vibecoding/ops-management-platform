#!/usr/bin/env python3
"""
自动化测试脚本 - 测试告警中心、监控扩展、巡检报告 API
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
        print(f"\n{'=' * 50}")
        print(f"测试结果: 通过 {self.passed}, 失败 {self.failed}")
        if self.errors:
            print("\n失败详情:")
            for e in self.errors:
                print(f"  - {e}")
        return self.failed == 0


def test_alerts_api():
    """测试告警中心 API"""
    result = TestResult()

    # 1. 测试获取告警列表 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/alerts", timeout=5)
        if resp.status_code == 401:
            result.success("获取告警列表-未登录返回401")
        else:
            result.fail("获取告警列表-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取告警列表-未登录", str(e))

    # 2. 测试获取告警统计 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/alerts/stats", timeout=5)
        if resp.status_code == 401:
            result.success("获取告警统计-未登录返回401")
        else:
            result.fail("获取告警统计-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取告警统计-未登录", str(e))

    # 3. 测试获取告警详情 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/alerts/1", timeout=5)
        if resp.status_code == 401:
            result.success("获取告警详情-未登录返回401")
        else:
            result.fail("获取告警详情-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取告警详情-未登录", str(e))

    # 4. 测试确认告警 - 未登录
    try:
        resp = requests.post(f"{BASE_URL}/alerts/1/acknowledge", json={"note": "test"}, timeout=5)
        if resp.status_code == 401:
            result.success("确认告警-未登录返回401")
        else:
            result.fail("确认告警-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("确认告警-未登录", str(e))

    # 5. 测试解决告警 - 未登录
    try:
        resp = requests.post(f"{BASE_URL}/alerts/1/resolve", json={"note": "test"}, timeout=5)
        if resp.status_code == 401:
            result.success("解决告警-未登录返回401")
        else:
            result.fail("解决告警-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("解决告警-未登录", str(e))

    # 6. 测试批量确认告警 - 未登录
    try:
        resp = requests.post(f"{BASE_URL}/alerts/batch-acknowledge", json=[1, 2, 3], timeout=5)
        if resp.status_code == 401:
            result.success("批量确认告警-未登录返回401")
        else:
            result.fail("批量确认告警-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("批量确认告警-未登录", str(e))

    # 7. 测试获取指标类型列表
    try:
        resp = requests.get(f"{BASE_URL}/alerts/metric-types/list", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                result.success("获取指标类型列表-成功")
            else:
                result.fail("获取指标类型列表", f"返回数据格式错误: {data}")
        else:
            result.fail("获取指标类型列表", f"状态码: {resp.status_code}")
    except Exception as e:
        result.fail("获取指标类型列表", str(e))

    # 8. 测试获取告警级别列表
    try:
        resp = requests.get(f"{BASE_URL}/alerts/levels/list", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                result.success("获取告警级别列表-成功")
            else:
                result.fail("获取告警级别列表", f"返回数据格式错误: {data}")
        else:
            result.fail("获取告警级别列表", f"状态码: {resp.status_code}")
    except Exception as e:
        result.fail("获取告警级别列表", str(e))

    # 9. 测试获取告警状态列表
    try:
        resp = requests.get(f"{BASE_URL}/alerts/statuses/list", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                result.success("获取告警状态列表-成功")
            else:
                result.fail("获取告警状态列表", f"返回数据格式错误: {data}")
        else:
            result.fail("获取告警状态列表", f"状态码: {resp.status_code}")
    except Exception as e:
        result.fail("获取告警状态列表", str(e))

    return result


def test_monitor_ext_api():
    """测试监控扩展 API"""
    result = TestResult()

    # 1. 测试获取主从复制状态列表 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/monitor-ext/replication", timeout=5)
        if resp.status_code == 401:
            result.success("获取主从复制状态列表-未登录返回401")
        else:
            result.fail("获取主从复制状态列表-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取主从复制状态列表-未登录", str(e))

    # 2. 测试检查主从复制状态 - 未登录
    try:
        resp = requests.post(f"{BASE_URL}/monitor-ext/replication/check/1", timeout=5)
        if resp.status_code == 401:
            result.success("检查主从复制状态-未登录返回401")
        else:
            result.fail("检查主从复制状态-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("检查主从复制状态-未登录", str(e))

    # 3. 测试获取锁等待列表 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/monitor-ext/locks", timeout=5)
        if resp.status_code == 401:
            result.success("获取锁等待列表-未登录返回401")
        else:
            result.fail("获取锁等待列表-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取锁等待列表-未登录", str(e))

    # 4. 测试检查锁等待 - 未登录
    try:
        resp = requests.post(f"{BASE_URL}/monitor-ext/locks/check/1", timeout=5)
        if resp.status_code == 401:
            result.success("检查锁等待-未登录返回401")
        else:
            result.fail("检查锁等待-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("检查锁等待-未登录", str(e))

    # 5. 测试获取长事务列表 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/monitor-ext/transactions", timeout=5)
        if resp.status_code == 401:
            result.success("获取长事务列表-未登录返回401")
        else:
            result.fail("获取长事务列表-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取长事务列表-未登录", str(e))

    # 6. 测试检查长事务 - 未登录
    try:
        resp = requests.post(f"{BASE_URL}/monitor-ext/transactions/check/1", timeout=5)
        if resp.status_code == 401:
            result.success("检查长事务-未登录返回401")
        else:
            result.fail("检查长事务-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("检查长事务-未登录", str(e))

    # 7. 测试Kill长事务 - 未登录
    try:
        resp = requests.post(f"{BASE_URL}/monitor-ext/transactions/kill/1?instance_id=1", timeout=5)
        if resp.status_code == 401:
            result.success("Kill长事务-未登录返回401")
        else:
            result.fail("Kill长事务-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("Kill长事务-未登录", str(e))

    return result


def test_inspection_api():
    """测试巡检报告 API"""
    result = TestResult()

    # 1. 测试获取巡检指标列表 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/inspection/metrics", timeout=5)
        if resp.status_code == 401:
            result.success("获取巡检指标列表-未登录返回401")
        else:
            result.fail("获取巡检指标列表-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取巡检指标列表-未登录", str(e))

    # 2. 测试创建巡检指标 - 未登录
    try:
        resp = requests.post(f"{BASE_URL}/inspection/metrics", json={
            "module": "slow_query",
            "metric_name": "测试指标",
            "metric_code": "test_metric_001"
        }, timeout=5)
        if resp.status_code == 401:
            result.success("创建巡检指标-未登录返回401")
        else:
            result.fail("创建巡检指标-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("创建巡检指标-未登录", str(e))

    # 3. 测试获取巡检结果列表 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/inspection/results", timeout=5)
        if resp.status_code == 401:
            result.success("获取巡检结果列表-未登录返回401")
        else:
            result.fail("获取巡检结果列表-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取巡检结果列表-未登录", str(e))

    # 4. 测试执行巡检 - 未登录
    try:
        resp = requests.post(f"{BASE_URL}/inspection/run", json={
            "instance_id": 1,
            "modules": ["slow_query"]
        }, timeout=5)
        if resp.status_code == 401:
            result.success("执行巡检-未登录返回401")
        else:
            result.fail("执行巡检-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("执行巡检-未登录", str(e))

    # 5. 测试获取巡检报告列表 - 未登录
    try:
        resp = requests.get(f"{BASE_URL}/inspection/reports", timeout=5)
        if resp.status_code == 401:
            result.success("获取巡检报告列表-未登录返回401")
        else:
            result.fail("获取巡检报告列表-未登录", f"期望401, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取巡检报告列表-未登录", str(e))

    # 6. 测试获取巡检模块列表
    try:
        resp = requests.get(f"{BASE_URL}/inspection/modules/list", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                result.success("获取巡检模块列表-成功")
            else:
                result.fail("获取巡检模块列表", f"返回数据格式错误: {data}")
        else:
            result.fail("获取巡检模块列表", f"状态码: {resp.status_code}")
    except Exception as e:
        result.fail("获取巡检模块列表", str(e))

    return result


def test_alerts_api_with_auth():
    """测试告警中心 API（需要认证）- 使用数据库中已存在的管理员账户"""
    result = TestResult()

    # 先登录获取token
    try:
        # 尝试使用系统默认管理员登录
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "admin",
            "password": "admin123"
        }, timeout=5)

        if login_resp.status_code != 200:
            print(f"  ⚠️ 登录失败，跳过认证测试: {login_resp.json()}")
            return result

        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

    except Exception as e:
        print(f"  ⚠️ 登录异常，跳过认证测试: {e}")
        return result

    # 1. 测试获取告警列表 - 已登录
    try:
        resp = requests.get(f"{BASE_URL}/alerts", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "total" in data and "items" in data:
                result.success("获取告警列表-已登录返回正确格式")
            else:
                result.fail("获取告警列表-已登录", f"返回格式错误: {data}")
        else:
            result.fail("获取告警列表-已登录", f"期望200, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取告警列表-已登录", str(e))

    # 2. 测试获取告警统计 - 已登录
    try:
        resp = requests.get(f"{BASE_URL}/alerts/stats", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            required_fields = ["total", "pending", "acknowledged", "resolved", "critical", "warning", "info"]
            if all(f in data for f in required_fields):
                result.success("获取告警统计-已登录返回正确格式")
            else:
                result.fail("获取告警统计-已登录", f"缺少字段: {data}")
        else:
            result.fail("获取告警统计-已登录", f"期望200, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取告警统计-已登录", str(e))

    # 3. 测试获取不存在的告警 - 已登录
    try:
        resp = requests.get(f"{BASE_URL}/alerts/99999", headers=headers, timeout=5)
        if resp.status_code == 404:
            result.success("获取不存在的告警-返回404")
        else:
            result.fail("获取不存在的告警", f"期望404, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取不存在的告警", str(e))

    return result


def test_inspection_api_with_auth():
    """测试巡检报告 API（需要认证）"""
    result = TestResult()

    # 先登录获取token
    try:
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "admin",
            "password": "admin123"
        }, timeout=5)

        if login_resp.status_code != 200:
            print(f"  ⚠️ 登录失败，跳过认证测试")
            return result

        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

    except Exception as e:
        print(f"  ⚠️ 登录异常，跳过认证测试: {e}")
        return result

    # 1. 测试获取巡检指标列表 - 已登录
    try:
        resp = requests.get(f"{BASE_URL}/inspection/metrics", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "total" in data and "items" in data:
                result.success("获取巡检指标列表-已登录返回正确格式")
            else:
                result.fail("获取巡检指标列表-已登录", f"返回格式错误: {data}")
        else:
            result.fail("获取巡检指标列表-已登录", f"期望200, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取巡检指标列表-已登录", str(e))

    # 2. 测试获取巡检结果列表 - 已登录
    try:
        resp = requests.get(f"{BASE_URL}/inspection/results", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "total" in data and "items" in data:
                result.success("获取巡检结果列表-已登录返回正确格式")
            else:
                result.fail("获取巡检结果列表-已登录", f"返回格式错误: {data}")
        else:
            result.fail("获取巡检结果列表-已登录", f"期望200, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取巡检结果列表-已登录", str(e))

    # 3. 测试执行巡检 - 不存在的实例
    try:
        resp = requests.post(f"{BASE_URL}/inspection/run", json={
            "instance_id": 99999
        }, headers=headers, timeout=5)
        if resp.status_code == 404:
            result.success("执行巡检-实例不存在返回404")
        else:
            result.fail("执行巡检-实例不存在", f"期望404, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("执行巡检-实例不存在", str(e))

    return result


def test_monitor_ext_api_with_auth():
    """测试监控扩展 API（需要认证）"""
    result = TestResult()

    # 先登录获取token
    try:
        login_resp = requests.post(f"{BASE_URL}/auth/login", json={
            "username": "admin",
            "password": "admin123"
        }, timeout=5)

        if login_resp.status_code != 200:
            print(f"  ⚠️ 登录失败，跳过认证测试")
            return result

        token = login_resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

    except Exception as e:
        print(f"  ⚠️ 登录异常，跳过认证测试: {e}")
        return result

    # 1. 测试获取主从复制状态列表 - 已登录
    try:
        resp = requests.get(f"{BASE_URL}/monitor-ext/replication", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "total" in data and "items" in data:
                result.success("获取主从复制状态列表-已登录返回正确格式")
            else:
                result.fail("获取主从复制状态列表-已登录", f"返回格式错误: {data}")
        else:
            result.fail("获取主从复制状态列表-已登录", f"期望200, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取主从复制状态列表-已登录", str(e))

    # 2. 测试获取锁等待列表 - 已登录
    try:
        resp = requests.get(f"{BASE_URL}/monitor-ext/locks", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "total" in data and "items" in data:
                result.success("获取锁等待列表-已登录返回正确格式")
            else:
                result.fail("获取锁等待列表-已登录", f"返回格式错误: {data}")
        else:
            result.fail("获取锁等待列表-已登录", f"期望200, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取锁等待列表-已登录", str(e))

    # 3. 测试获取长事务列表 - 已登录
    try:
        resp = requests.get(f"{BASE_URL}/monitor-ext/transactions", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if "total" in data and "items" in data:
                result.success("获取长事务列表-已登录返回正确格式")
            else:
                result.fail("获取长事务列表-已登录", f"返回格式错误: {data}")
        else:
            result.fail("获取长事务列表-已登录", f"期望200, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("获取长事务列表-已登录", str(e))

    # 4. 测试检查主从复制状态 - 不存在的实例
    try:
        resp = requests.post(f"{BASE_URL}/monitor-ext/replication/check/99999", headers=headers, timeout=5)
        if resp.status_code == 404:
            result.success("检查主从复制状态-实例不存在返回404")
        else:
            result.fail("检查主从复制状态-实例不存在", f"期望404, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("检查主从复制状态-实例不存在", str(e))

    # 5. 测试检查锁等待 - 不存在的实例
    try:
        resp = requests.post(f"{BASE_URL}/monitor-ext/locks/check/99999", headers=headers, timeout=5)
        if resp.status_code == 404:
            result.success("检查锁等待-实例不存在返回404")
        else:
            result.fail("检查锁等待-实例不存在", f"期望404, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("检查锁等待-实例不存在", str(e))

    # 6. 测试检查长事务 - 不存在的实例
    try:
        resp = requests.post(f"{BASE_URL}/monitor-ext/transactions/check/99999", headers=headers, timeout=5)
        if resp.status_code == 404:
            result.success("检查长事务-实例不存在返回404")
        else:
            result.fail("检查长事务-实例不存在", f"期望404, 实际: {resp.status_code}")
    except Exception as e:
        result.fail("检查长事务-实例不存在", str(e))

    return result


def main():
    print("=" * 50)
    print("开始执行监控模块 API 测试...")
    print("=" * 50)

    all_results = []

    print("\n📋 测试告警中心 API - 未认证")
    all_results.append(test_alerts_api())

    print("\n📋 测试监控扩展 API - 未认证")
    all_results.append(test_monitor_ext_api())

    print("\n📋 测试巡检报告 API - 未认证")
    all_results.append(test_inspection_api())

    print("\n📋 测试告警中心 API - 已认证")
    all_results.append(test_alerts_api_with_auth())

    print("\n📋 测试监控扩展 API - 已认证")
    all_results.append(test_monitor_ext_api_with_auth())

    print("\n📋 测试巡检报告 API - 已认证")
    all_results.append(test_inspection_api_with_auth())

    # 汇总结果
    total_passed = sum(r.passed for r in all_results)
    total_failed = sum(r.failed for r in all_results)

    print(f"\n{'=' * 50}")
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
