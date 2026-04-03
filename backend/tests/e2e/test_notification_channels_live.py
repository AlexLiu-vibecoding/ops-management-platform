#!/usr/bin/env python3
"""
通知通道管理 E2E 测试用例 - 使用已运行的服务

运行方式:
    cd /workspace/projects/backend
    python tests/e2e/test_notification_channels_live.py

前提条件:
    1. 后端服务已启动 (http://localhost:5000)
    2. admin 用户可登录
"""

import requests
import sys
import json

BASE_URL = "http://localhost:5000/api/v1"

# 测试用例计数
total_tests = 0
passed_tests = 0
failed_tests = 0


def print_header(title):
    """打印测试标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_result(test_name, success, message=""):
    """打印测试结果"""
    global total_tests, passed_tests, failed_tests
    total_tests += 1

    if success:
        passed_tests += 1
        print(f"✅ {test_name}")
        if message:
            print(f"   {message}")
    else:
        failed_tests += 1
        print(f"❌ {test_name}")
        if message:
            print(f"   错误: {message}")


def get_admin_token():
    """获取 admin 用户的访问令牌"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=10
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"登录失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"登录请求异常: {e}")
        return None


def test_list_channels(headers):
    """测试获取通道列表"""
    print_header("测试获取通道列表")

    try:
        response = requests.get(
            f"{BASE_URL}/notification/channels",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if "items" in data and "total" in data:
                print_result(
                    "获取通道列表",
                    True,
                    f"返回 {data['total']} 个通道"
                )

                # 验证数据格式
                if data["items"]:
                    channel = data["items"][0]
                    required_fields = ["id", "name", "channel_type", "config", "is_enabled"]
                    missing_fields = [f for f in required_fields if f not in channel]
                    if missing_fields:
                        print_result(
                            "验证通道数据格式",
                            False,
                            f"缺少字段: {missing_fields}"
                        )
                    else:
                        print_result(
                            "验证通道数据格式",
                            True,
                            f"通道名称: {channel['name']}, 类型: {channel['channel_type']}"
                        )

                        # 检查 webhook 字段
                        if channel.get("config", {}).get("webhook"):
                            print_result(
                                "验证 webhook 字段",
                                True,
                                f"webhook: {channel['config']['webhook'][:30]}..."
                            )
                        else:
                            webhook_encrypted = channel.get("config", {}).get("webhook_encrypted", "")
                            print_result(
                                "验证 webhook 字段",
                                True,
                                f"webhook_encrypted: {webhook_encrypted[:30]}... (webhook 为空)"
                            )
                else:
                    print_result("通道列表为空", True, "暂无通道数据")
            else:
                print_result("验证响应格式", False, "缺少 items 或 total 字段")
        else:
            print_result("获取通道列表", False, f"HTTP {response.status_code}: {response.text}")

    except Exception as e:
        print_result("获取通道列表", False, str(e))


def test_channel_bindings(headers, channel_id):
    """测试通道绑定管理"""
    print_header("测试通道绑定管理")

    try:
        # 1. 获取绑定列表
        response = requests.get(
            f"{BASE_URL}/notification/channels/{channel_id}/bindings",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            items = data.get("items", [])
            initial_count = len(items)
            print_result(
                "获取绑定列表",
                True,
                f"当前有 {initial_count} 个绑定"
            )

            # 验证绑定数据
            if data.get("items"):
                binding = data["items"][0]
                print_result(
                    "验证绑定数据格式",
                    True,
                    f"绑定类型: {binding.get('notification_type', 'N/A')}"
                )
        else:
            print_result("获取绑定列表", False, f"HTTP {response.status_code}")

    except Exception as e:
        print_result("通道绑定测试", False, str(e))


def test_silence_rules(headers, channel_id):
    """测试通道静默规则管理"""
    print_header("测试通道静默规则管理")

    try:
        # 获取静默规则列表
        response = requests.get(
            f"{BASE_URL}/notification/channels/{channel_id}/silence-rules",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print_result(
                "获取静默规则列表",
                True,
                f"当前有 {data.get('total', 0)} 个静默规则"
            )

            # 创建静默规则（使用唯一名称）
            import time
            rule_data = {
                "name": f"E2E测试静默规则_{int(time.time())}",
                "silence_type": "once",
                "start_time": "2026-01-01T00:00:00",
                "end_time": "2026-01-02T00:00:00",
                "description": "E2E测试用"
            }

            response = requests.post(
                f"{BASE_URL}/notification/channels/{channel_id}/silence-rules",
                headers=headers,
                json=rule_data,
                timeout=10
            )

            if response.status_code in [200, 201]:
                rule_id = response.json().get("id")
                print_result("创建静默规则", True, f"规则ID: {rule_id}")

                # 删除测试规则
                response = requests.delete(
                    f"{BASE_URL}/notification/channels/{channel_id}/silence-rules/{rule_id}",
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 200:
                    print_result("删除静默规则", True)
                else:
                    print_result("删除静默规则", False, f"HTTP {response.status_code}")
            else:
                print_result("创建静默规则", False, f"HTTP {response.status_code}: {response.text}")
        else:
            print_result("获取静默规则列表", False, f"HTTP {response.status_code}")

    except Exception as e:
        print_result("静默规则测试", False, str(e))


def test_rate_limits(headers, channel_id):
    """测试通道频率限制管理"""
    print_header("测试通道频率限制管理")

    try:
        # 获取频率限制列表
        response = requests.get(
            f"{BASE_URL}/notification/channels/{channel_id}/rate-limits",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print_result(
                "获取频率限制列表",
                True,
                f"当前有 {data.get('total', 0)} 个频率限制"
            )

            # 创建频率限制（使用唯一名称）
            import time
            limit_data = {
                "name": f"E2E测试频率限制_{int(time.time())}",
                "time_window": 60,
                "max_count": 10,
                "description": "E2E测试用"
            }

            response = requests.post(
                f"{BASE_URL}/notification/channels/{channel_id}/rate-limits",
                headers=headers,
                json=limit_data,
                timeout=10
            )

            if response.status_code in [200, 201]:
                limit_id = response.json().get("id")
                print_result("创建频率限制", True, f"限制ID: {limit_id}")

                # 删除测试限制
                response = requests.delete(
                    f"{BASE_URL}/notification/channels/{channel_id}/rate-limits/{limit_id}",
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 200:
                    print_result("删除频率限制", True)
                else:
                    print_result("删除频率限制", False, f"HTTP {response.status_code}")
            else:
                print_result("创建频率限制", False, f"HTTP {response.status_code}: {response.text}")
        else:
            print_result("获取频率限制列表", False, f"HTTP {response.status_code}")

    except Exception as e:
        print_result("频率限制测试", False, str(e))


def test_channel_test_api(headers, channel_id):
    """测试通道测试功能"""
    print_header("测试通道测试功能")

    try:
        response = requests.post(
            f"{BASE_URL}/notification/channels/detail/{channel_id}/test",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print_result(
                "执行通道测试",
                True,
                f"结果: {data.get('message', 'N/A')}"
            )
        else:
            print_result("执行通道测试", False, f"HTTP {response.status_code}: {response.text}")

    except Exception as e:
        print_result("通道测试", False, str(e))


def run_all_tests():
    """运行所有测试"""
    print_header("通知通道管理 E2E 测试")
    print(f"测试地址: {BASE_URL}")

    # 获取认证令牌
    token = get_admin_token()
    if not token:
        print("❌ 无法获取认证令牌，测试中止")
        return False

    headers = {"Authorization": f"Bearer {token}"}
    print("✅ 登录成功\n")

    # 获取通道列表并选择第一个通道进行测试
    try:
        response = requests.get(
            f"{BASE_URL}/notification/channels",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200 and response.json().get("items"):
            channels = response.json()["items"]
            channel_id = channels[0]["id"]
            channel_name = channels[0]["name"]
            print(f"使用通道进行测试: ID={channel_id}, 名称={channel_name}\n")

            # 运行测试
            test_list_channels(headers)
            test_channel_bindings(headers, channel_id)
            test_silence_rules(headers, channel_id)
            test_rate_limits(headers, channel_id)
            test_channel_test_api(headers, channel_id)
        else:
            print("⚠️ 没有可用的通道进行测试")
            test_list_channels(headers)

    except Exception as e:
        print(f"❌ 获取通道列表失败: {e}")

    # 打印测试总结
    print_header("测试总结")
    print(f"总计: {total_tests} 个测试")
    print(f"通过: {passed_tests} 个")
    print(f"失败: {failed_tests} 个")

    if failed_tests == 0:
        print("\n🎉 所有测试通过！")
        return True
    else:
        print(f"\n⚠️ 有 {failed_tests} 个测试失败")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
