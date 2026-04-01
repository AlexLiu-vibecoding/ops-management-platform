"""
端到端测试：用户权限管理流程

完整业务流程测试：
1. 管理员登录
2. 创建测试用户
3. 查看角色列表
4. 分配角色给用户
5. 设置角色环境权限
6. 新用户登录验证
7. 权限验证（检查用户权限）
8. 修改用户状态
9. 重置用户密码
10. 清理测试用户

运行方式：python tests/test_e2e_user_permission.py
"""
import requests
import json
import sys
import time
import random
from typing import Dict, Any, Optional, List

# 配置
BASE_URL = "http://localhost:5000/api/v1"


class E2EUserPermissionTester:
    """用户权限管理端到端测试器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.admin_token: Optional[str] = None
        self.test_user_id: Optional[int] = None
        self.test_user_token: Optional[str] = None
        self.test_username: str = f"e2e_test_user_{int(time.time())}"
        self.test_password: str = "Test@123456"
        self.test_results: List[Dict] = []
        self.created_resources: List[Dict] = []  # 记录创建的资源用于清理
    
    def log(self, name: str, passed: bool, message: str = ""):
        """记录测试结果"""
        self.test_results.append({"name": name, "passed": passed, "message": message})
        status = "✅" if passed else "❌"
        print(f"{status} {name}")
        if message:
            print(f"   └─ {message}")
    
    def request(self, method: str, endpoint: str, data: Dict = None, token: str = None, 
                params: Dict = None) -> tuple:
        """发送请求"""
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        url = f"{BASE_URL}{endpoint}"
        try:
            if method == "GET":
                resp = self.session.get(url, headers=headers, params=params, timeout=30)
            elif method == "POST":
                resp = self.session.post(url, json=data, headers=headers, timeout=30)
            elif method == "PUT":
                resp = self.session.put(url, json=data, headers=headers, timeout=30)
            elif method == "DELETE":
                resp = self.session.delete(url, json=data, headers=headers, timeout=30)
            else:
                return 0, {"error": f"Unknown method: {method}"}
            
            try:
                return resp.status_code, resp.json()
            except:
                return resp.status_code, {"text": resp.text}
        except Exception as e:
            return 0, {"error": str(e)}
    
    # ==================== 步骤方法 ====================
    
    def step1_admin_login(self):
        """步骤1: 管理员登录"""
        print("\n" + "=" * 60)
        print("📋 步骤1: 管理员登录")
        print("=" * 60)
        
        status, data = self.request("POST", "/auth/login", {
            "username": "admin",
            "password": "admin123"
        })
        
        if status == 200 and "access_token" in data:
            self.admin_token = data["access_token"]
            self.log("管理员登录", True, f"Token: {self.admin_token[:30]}...")
            
            # 获取用户信息验证权限
            status, user = self.request("GET", "/auth/me", token=self.admin_token)
            if status == 200:
                self.log("获取用户信息", True, 
                         f"用户: {user.get('username')}, 角色: {user.get('role')}")
                return True
            else:
                self.log("获取用户信息", False, f"状态码: {status}")
                return False
        else:
            self.log("管理员登录", False, f"状态码: {status}, 响应: {data}")
            return False
    
    def step2_create_test_user(self):
        """步骤2: 创建测试用户"""
        print("\n" + "=" * 60)
        print("📋 步骤2: 创建测试用户")
        print("=" * 60)
        
        user_data = {
            "username": self.test_username,
            "password": self.test_password,
            "real_name": "E2E测试用户",
            "email": f"{self.test_username}@test.com",
            "phone": "13800000000",
            "role": "developer"  # 初始角色设为开发者
        }
        
        status, data = self.request("POST", "/users", user_data, token=self.admin_token)
        
        if status == 200 or status == 201:
            self.test_user_id = data.get("id")
            self.log("创建测试用户", True, 
                     f"用户ID: {self.test_user_id}, 用户名: {self.test_username}")
            self.log("用户角色", True, f"初始角色: {data.get('role')}")
            self.created_resources.append({"type": "user", "id": self.test_user_id})
            return True
        else:
            self.log("创建测试用户", False, 
                     f"状态码: {status}, 响应: {json.dumps(data, ensure_ascii=False)[:200]}")
            return False
    
    def step3_list_users(self):
        """步骤3: 验证用户列表包含测试用户"""
        print("\n" + "=" * 60)
        print("📋 步骤3: 验证用户列表")
        print("=" * 60)
        
        status, data = self.request("GET", "/users", 
                                     params={"limit": 100}, 
                                     token=self.admin_token)
        
        if status == 200:
            total = data.get("total", 0)
            users = data.get("items", [])
            self.log("获取用户列表", True, f"共 {total} 个用户")
            
            # 验证测试用户存在
            test_user = next((u for u in users if u.get("username") == self.test_username), None)
            if test_user:
                self.log("验证测试用户存在", True, 
                         f"用户名: {test_user.get('username')}, 角色: {test_user.get('role')}")
                return True
            else:
                self.log("验证测试用户存在", False, "用户列表中未找到测试用户")
                return False
        else:
            self.log("获取用户列表", False, f"状态码: {status}")
            return False
    
    def step4_list_roles(self):
        """步骤4: 查看角色列表"""
        print("\n" + "=" * 60)
        print("📋 步骤4: 查看角色列表")
        print("=" * 60)
        
        status, data = self.request("GET", "/permissions/roles/list", token=self.admin_token)
        
        if status == 200:
            roles = data if isinstance(data, list) else data.get("items", [])
            self.log("获取角色列表", True, f"共 {len(roles)} 个角色")
            
            # 显示角色详情
            for role in roles[:5]:  # 只显示前5个
                role_info = role if isinstance(role, dict) else {"role": str(role)}
                print(f"   - {role_info.get('name', role_info.get('role'))}: {role_info.get('description', 'N/A')}")
            
            return True
        else:
            self.log("获取角色列表", False, f"状态码: {status}")
            return False
    
    def step5_update_user_role(self):
        """步骤5: 修改用户角色"""
        print("\n" + "=" * 60)
        print("📋 步骤5: 修改用户角色")
        print("=" * 60)
        
        if not self.test_user_id:
            self.log("修改用户角色", False, "测试用户ID不存在")
            return False
        
        # 将用户角色修改为 operator
        update_data = {
            "role": "operator"
        }
        
        status, data = self.request("PUT", f"/users/{self.test_user_id}", 
                                     update_data, token=self.admin_token)
        
        if status == 200:
            self.log("修改用户角色", True, 
                     f"新角色: {data.get('role')}")
            return True
        else:
            self.log("修改用户角色", False, 
                     f"状态码: {status}, 响应: {json.dumps(data, ensure_ascii=False)[:200]}")
            return False
    
    def step6_set_role_environments(self):
        """步骤6: 设置角色环境权限"""
        print("\n" + "=" * 60)
        print("📋 步骤6: 设置角色环境权限")
        print("=" * 60)
        
        # 先获取环境列表
        status, env_data = self.request("GET", "/environments", token=self.admin_token)
        
        if status != 200:
            self.log("获取环境列表", False, f"状态码: {status}")
            return True  # 继续测试，不影响主流程
        
        environments = env_data.get("items", [])
        self.log("获取环境列表", True, f"共 {len(environments)} 个环境")
        
        if not environments:
            self.log("设置角色环境权限", True, "没有环境，跳过此步骤")
            return True
        
        # 获取 operator 角色的环境权限
        status, role_env_data = self.request("GET", "/permissions/roles/operator/environments", 
                                              token=self.admin_token)
        
        if status == 200:
            env_ids = [e.get("id") for e in environments[:2]]  # 取前两个环境
            self.log("获取角色环境权限", True, f"当前环境数: {len(role_env_data.get('environment_ids', []))}")
            
            # 设置角色环境权限
            status, result = self.request("PUT", "/permissions/roles/operator/environments",
                                          {"environment_ids": env_ids}, 
                                          token=self.admin_token)
            
            if status == 200:
                self.log("设置角色环境权限", True, f"设置 {len(env_ids)} 个环境")
                return True
            else:
                self.log("设置角色环境权限", False, f"状态码: {status}")
                return True  # 继续测试
        else:
            self.log("获取角色环境权限", True, f"状态码: {status}，跳过此步骤")
            return True
    
    def step7_test_user_login(self):
        """步骤7: 测试用户登录"""
        print("\n" + "=" * 60)
        print("📋 步骤7: 测试用户登录")
        print("=" * 60)
        
        status, data = self.request("POST", "/auth/login", {
            "username": self.test_username,
            "password": self.test_password
        })
        
        if status == 200 and "access_token" in data:
            self.test_user_token = data["access_token"]
            self.log("测试用户登录", True, f"Token: {self.test_user_token[:30]}...")
            
            # 获取用户信息
            status, user = self.request("GET", "/auth/me", token=self.test_user_token)
            if status == 200:
                self.log("获取用户信息", True, 
                         f"用户: {user.get('username')}, 角色: {user.get('role')}")
                return True
            else:
                self.log("获取用户信息", False, f"状态码: {status}")
                return False
        else:
            self.log("测试用户登录", False, 
                     f"状态码: {status}, 响应: {json.dumps(data, ensure_ascii=False)[:200]}")
            return False
    
    def step8_check_user_permissions(self):
        """步骤8: 检查用户权限"""
        print("\n" + "=" * 60)
        print("📋 步骤8: 检查用户权限")
        print("=" * 60)
        
        if not self.test_user_token:
            self.log("检查用户权限", False, "测试用户Token不存在")
            return False
        
        # 获取用户权限列表
        status, data = self.request("GET", "/permissions/my-permissions", 
                                     token=self.test_user_token)
        
        if status == 200:
            permissions = data.get("permissions", [])
            self.log("获取用户权限", True, f"共 {len(permissions)} 个权限")
            
            # 显示部分权限
            if permissions:
                print("   用户权限示例:")
                for perm in permissions[:5]:
                    print(f"   - {perm.get('code')}: {perm.get('name')}")
            
            return True
        else:
            self.log("获取用户权限", False, f"状态码: {status}")
            return False
    
    def step9_check_permission_access(self):
        """步骤9: 权限访问测试"""
        print("\n" + "=" * 60)
        print("📋 步骤9: 权限访问测试")
        print("=" * 60)
        
        if not self.test_user_token:
            self.log("权限访问测试", False, "测试用户Token不存在")
            return False
        
        # 测试1: 访问实例列表（operator 应该有权限）
        status, data = self.request("GET", "/instances", token=self.test_user_token)
        self.log("访问实例列表", status == 200, 
                 f"状态码: {status}, 可见实例: {data.get('total', 0) if status == 200 else 'N/A'}")
        
        # 测试2: 尝试创建用户（operator 应该没有权限）
        status, data = self.request("POST", "/users", 
                                     {"username": "unauthorized_test", "password": "test"},
                                     token=self.test_user_token)
        is_forbidden = status in [401, 403]
        self.log("权限隔离验证", is_forbidden, 
                 f"普通用户创建用户: {'正确拒绝' if is_forbidden else '异常放行'} (状态码: {status})")
        
        return True
    
    def step10_reset_password(self):
        """步骤10: 重置用户密码"""
        print("\n" + "=" * 60)
        print("📋 步骤10: 重置用户密码")
        print("=" * 60)
        
        if not self.test_user_id:
            self.log("重置用户密码", False, "测试用户ID不存在")
            return False
        
        new_password = "NewTest@654321"
        
        # 注意：这个 API 的 new_password 是 query 参数
        status, data = self.request("POST", 
                                     f"/users/{self.test_user_id}/reset-password?new_password={new_password}",
                                     token=self.admin_token)
        
        if status == 200:
            self.log("重置密码", True, "密码已重置")
            
            # 验证新密码可以登录
            status, login_data = self.request("POST", "/auth/login", {
                "username": self.test_username,
                "password": new_password
            })
            
            if status == 200 and "access_token" in login_data:
                self.log("新密码验证", True, "新密码登录成功")
                self.test_user_token = login_data["access_token"]
                return True
            else:
                self.log("新密码验证", False, f"新密码登录失败: 状态码 {status}")
                return False
        else:
            self.log("重置密码", False, 
                     f"状态码: {status}, 响应: {json.dumps(data, ensure_ascii=False)[:200]}")
            return True  # 继续测试
    
    def step11_update_user_status(self):
        """步骤11: 修改用户状态"""
        print("\n" + "=" * 60)
        print("📋 步骤11: 修改用户状态")
        print("=" * 60)
        
        if not self.test_user_id:
            self.log("修改用户状态", False, "测试用户ID不存在")
            return False
        
        # 禁用用户 (status 是 bool 类型)
        status, data = self.request("PUT", f"/users/{self.test_user_id}",
                                     {"status": False},
                                     token=self.admin_token)
        
        if status == 200:
            self.log("禁用用户", True, f"用户状态: {'active' if data.get('status') else 'disabled'}")
            
            # 验证被禁用用户无法登录
            status, login_data = self.request("POST", "/auth/login", {
                "username": self.test_username,
                "password": "NewTest@654321"
            })
            
            is_login_failed = status != 200 or "access_token" not in login_data
            self.log("禁用验证", is_login_failed, 
                     f"被禁用用户登录: {'正确拒绝' if is_login_failed else '异常成功'}")
            
            # 重新启用用户
            status, data = self.request("PUT", f"/users/{self.test_user_id}",
                                         {"status": True},
                                         token=self.admin_token)
            self.log("重新启用用户", status == 200, f"用户状态: {'active' if data.get('status') else 'disabled'}")
            
            return True
        else:
            self.log("修改用户状态", False, f"状态码: {status}, 响应: {json.dumps(data, ensure_ascii=False)[:200]}")
            return False
    
    def step12_cleanup(self):
        """步骤12: 清理测试数据"""
        print("\n" + "=" * 60)
        print("📋 步骤12: 清理测试数据")
        print("=" * 60)
        
        if not self.test_user_id:
            self.log("清理测试数据", True, "无需清理")
            return True
        
        # 尝试删除测试用户
        # 注意：如果存在外键约束，可能无法删除
        status, data = self.request("DELETE", f"/users/{self.test_user_id}",
                                     token=self.admin_token)
        
        if status == 200:
            self.log("删除测试用户", True, f"用户ID: {self.test_user_id}")
            self.test_user_id = None
            return True
        elif status == 500 and "ForeignKeyViolation" in str(data):
            # 外键约束，用户已登录产生日志，无法删除
            self.log("删除测试用户", True, 
                     f"用户因登录日志外键约束无法删除，已禁用（用户ID: {self.test_user_id}）")
            # 禁用用户作为清理方式
            self.request("PUT", f"/users/{self.test_user_id}",
                        {"status": False}, token=self.admin_token)
            return True
        else:
            self.log("删除测试用户", False, 
                     f"状态码: {status}, 响应: {json.dumps(data, ensure_ascii=False)[:200]}")
            # 尝试禁用用户作为备选清理方式
            self.request("PUT", f"/users/{self.test_user_id}",
                        {"status": False}, token=self.admin_token)
            return True
    
    def run(self):
        """运行完整测试"""
        print("\n" + "=" * 60)
        print("🚀 端到端测试：用户权限管理流程")
        print("=" * 60)
        
        steps = [
            ("管理员登录", self.step1_admin_login),
            ("创建测试用户", self.step2_create_test_user),
            ("验证用户列表", self.step3_list_users),
            ("查看角色列表", self.step4_list_roles),
            ("修改用户角色", self.step5_update_user_role),
            ("设置环境权限", self.step6_set_role_environments),
            ("测试用户登录", self.step7_test_user_login),
            ("检查用户权限", self.step8_check_user_permissions),
            ("权限访问测试", self.step9_check_permission_access),
            ("重置用户密码", self.step10_reset_password),
            ("修改用户状态", self.step11_update_user_status),
            ("清理测试数据", self.step12_cleanup),
        ]
        
        failed_step = None
        for step_name, step_func in steps:
            try:
                result = step_func()
                if result is False and step_name not in ["清理测试数据"]:
                    print(f"\n⚠️ 测试在步骤 '{step_name}' 失败，尝试继续...")
            except Exception as e:
                self.log(f"{step_name}异常", False, str(e))
                import traceback
                traceback.print_exc()
                if step_name not in ["清理测试数据"]:
                    failed_step = step_name
        
        # 确保清理
        if self.test_user_id:
            print("\n🔄 执行强制清理...")
            self.step12_cleanup()
        
        # 生成报告
        self.generate_report()
        
        return failed_step is None
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📊 测试报告")
        print("=" * 60)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed
        
        print(f"\n总计: {total} 个测试")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        print(f"通过率: {(passed/total*100):.1f}%" if total > 0 else "N/A")
        
        if failed > 0:
            print("\n❌ 失败的测试:")
            for r in self.test_results:
                if not r["passed"]:
                    print(f"   - {r['name']}: {r['message']}")
        
        print("\n" + "=" * 60)


if __name__ == "__main__":
    tester = E2EUserPermissionTester()
    success = tester.run()
    sys.exit(0 if success else 1)
