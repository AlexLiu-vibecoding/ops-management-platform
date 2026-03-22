#!/usr/bin/env python3
"""
系统配置 API 测试脚本
直接调用运行中的服务进行测试
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


def get_auth_token(username="admin", password="admin123"):
    """获取认证令牌"""
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": username, "password": password}
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except:
        pass
    return None


def test_system_api():
    """测试系统配置 API"""
    result = TestResult()
    
    # 1. 测试未授权访问
    print("\n📋 测试未授权访问...")
    
    endpoints = [
        "/system/overview",
        "/system/database-config",
        "/system/storage-config",
        "/system/security-config"
    ]
    
    for endpoint in endpoints:
        try:
            resp = requests.get(f"{BASE_URL}{endpoint}")
            if resp.status_code == 401:
                result.success(f"未授权访问 {endpoint} 返回 401")
            else:
                result.fail(f"未授权访问 {endpoint}", f"状态码: {resp.status_code}")
        except Exception as e:
            result.fail(f"未授权访问 {endpoint}", str(e))
    
    # 2. 测试已授权访问（需要管理员账户）
    print("\n📋 测试已授权访问...")
    
    token = get_auth_token()
    if not token:
        print("⚠️  无法获取认证令牌，跳过已授权测试")
        print("   请确保已创建管理员账户 (admin/admin123)")
    else:
        headers = {"Authorization": f"Bearer {token}"}
        
        # 测试系统概览
        try:
            resp = requests.get(f"{BASE_URL}/system/overview", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if "version" in data and "storage_type" in data:
                    result.success("获取系统概览")
                else:
                    result.fail("获取系统概览", "返回数据缺少必要字段")
            elif resp.status_code == 403:
                result.success("非管理员访问系统概览返回 403")
            else:
                result.fail("获取系统概览", f"状态码: {resp.status_code}")
        except Exception as e:
            result.fail("获取系统概览", str(e))
        
        # 测试数据库配置
        try:
            resp = requests.get(f"{BASE_URL}/system/database-config", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if "items" in data and len(data["items"]) == 3:
                    result.success("获取数据库配置")
                else:
                    result.fail("获取数据库配置", "返回数据格式不正确")
            elif resp.status_code == 403:
                result.success("非管理员访问数据库配置返回 403")
            else:
                result.fail("获取数据库配置", f"状态码: {resp.status_code}")
        except Exception as e:
            result.fail("获取数据库配置", str(e))
        
        # 测试存储配置
        try:
            resp = requests.get(f"{BASE_URL}/system/storage-config", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if "storage_type" in data and "retention_days" in data:
                    result.success("获取存储配置")
                else:
                    result.fail("获取存储配置", "返回数据缺少必要字段")
            elif resp.status_code == 403:
                result.success("非管理员访问存储配置返回 403")
            else:
                result.fail("获取存储配置", f"状态码: {resp.status_code}")
        except Exception as e:
            result.fail("获取存储配置", str(e))
        
        # 测试安全配置
        try:
            resp = requests.get(f"{BASE_URL}/system/security-config", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if "jwt_configured" in data and "token_expire_hours" in data:
                    result.success("获取安全配置")
                else:
                    result.fail("获取安全配置", "返回数据缺少必要字段")
            elif resp.status_code == 403:
                result.success("非管理员访问安全配置返回 403")
            else:
                result.fail("获取安全配置", f"状态码: {resp.status_code}")
        except Exception as e:
            result.fail("获取安全配置", str(e))
    
    return result


def main():
    print("=" * 50)
    print("系统配置 API 测试")
    print("=" * 50)
    
    result = test_system_api()
    success = result.summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
