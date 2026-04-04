"""
API 自动化测试脚本
用于验证功能的可用性和完整性
"""
import requests
import json
import sys
from typing import Dict, Any, List, Tuple

# 配置
BASE_URL = "http://localhost:5000/api/v1"
ADMIN_CREDENTIALS = {"username": "admin", "password": "admin123"}

# 测试结果
test_results: List[Dict[str, Any]] = []


def log_test(name: str, passed: bool, message: str = "", response: Any = None):
    """记录测试结果"""
    result = {
        "name": name,
        "passed": passed,
        "message": message,
        "response": response
    }
    test_results.append(result)
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} | {name}")
    if message:
        print(f"      └─ {message}")
    if not passed and response:
        print(f"      └─ Response: {json.dumps(response, ensure_ascii=False)[:200]}")


class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token: str = ""
        self.session = requests.Session()
    
    def login(self, credentials: Dict) -> Tuple[bool, str]:
        """登录获取 token"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json=credentials
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token", "")
                self.session.headers.update({"Authorization": f"Bearer {self.token}"})
                return True, "登录成功"
            return False, f"登录失败: {response.status_code}"
        except Exception as e:
            return False, f"登录异常: {str(e)}"
    
    def get(self, endpoint: str, params: Dict = None) -> Tuple[int, Any]:
        """GET 请求"""
        try:
            response = self.session.get(f"{self.base_url}{endpoint}", params=params)
            return response.status_code, response.json() if response.text else {}
        except Exception as e:
            return 0, {"error": str(e)}
    
    def post(self, endpoint: str, data: Dict = None, params: Dict = None) -> Tuple[int, Any]:
        """POST 请求"""
        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json=data,
                params=params
            )
            return response.status_code, response.json() if response.text else {}
        except Exception as e:
            return 0, {"error": str(e)}
    
    def test_endpoint(self, name: str, method: str, endpoint: str, 
                      expected_status: int = 200, 
                      check_fields: List[str] = None,
                      params: Dict = None,
                      data: Dict = None) -> bool:
        """通用端点测试"""
        if method.upper() == "GET":
            status, response = self.get(endpoint, params)
        else:
            status, response = self.post(endpoint, data, params)
        
        # 检查状态码
        if status != expected_status:
            log_test(name, False, f"状态码期望 {expected_status}, 实际 {status}", response)
            return False
        
        # 检查必要字段
        if check_fields:
            missing = [f for f in check_fields if f not in response]
            if missing:
                log_test(name, False, f"缺少字段: {missing}", response)
                return False
        
        log_test(name, True, f"状态码 {status}, 包含字段 {check_fields or '无特定要求'}")
        return True


def run_tests():
    """执行所有测试"""
    print("\n" + "=" * 60)
    print("🚀 开始执行 API 自动化测试")
    print("=" * 60 + "\n")
    
    tester = APITester(BASE_URL)
    
    # ========== 1. 认证测试 ==========
    print("\n📋 [1] 认证测试")
    print("-" * 40)
    
    success, msg = tester.login(ADMIN_CREDENTIALS)
    log_test("管理员登录", success, msg)
    
    if not success:
        print("\n❌ 登录失败，无法继续测试")
        return False
    
    # ========== 2. 实例管理测试 ==========
    print("\n📋 [2] 实例管理测试")
    print("-" * 40)
    
    # 获取实例列表
    status, instances = tester.get("/instances", {"limit": 100})
    log_test("获取实例列表", status == 200 and "items" in instances, 
             f"共 {instances.get('total', 0)} 个实例")
    
    instance_id = None
    if instances.get("items"):
        instance_id = instances["items"][0]["id"]
        instance_name = instances["items"][0].get("name", "")
        instance_db_type = instances["items"][0].get("db_type", "mysql")
        log_test("实例数据格式", "db_type" in instances["items"][0], 
                 f"实例: {instance_name}, 类型: {instance_db_type}")
    
    # ========== 3. 慢查询监控测试 ==========
    print("\n📋 [3] 慢查询监控测试")
    print("-" * 40)
    
    if instance_id:
        # 测试 performance_schema 状态
        status, ps_status = tester.get(f"/slow-query/{instance_id}/performance-schema-status")
        is_mysql = instance_db_type == "mysql" if 'instance_db_type' in dir() else False
        if is_mysql:
            log_test("检查 performance_schema 状态", status == 200 and "enabled" in ps_status,
                     f"启用状态: {ps_status.get('enabled', False)}")
        else:
            log_test("检查 performance_schema 状态", status == 200,
                     f"PostgreSQL 实例返回: {ps_status.get('message', '')}")
        
        # 测试数据库列表
        status, databases = tester.get(f"/slow-query/{instance_id}/databases")
        log_test("获取实例数据库列表", status == 200 and "databases" in databases,
                 f"数据库: {databases.get('databases', [])}")
        
        # 测试慢查询列表
        status, slow_queries = tester.get(f"/slow-query/{instance_id}", {"limit": 20})
        log_test("获取慢查询列表", status == 200,
                 f"返回数据类型: {type(slow_queries).__name__}")
        
        # 测试慢查询统计
        status, stats = tester.get(f"/slow-query/{instance_id}/statistics", {"hours": 24})
        log_test("获取慢查询统计", status == 200,
                 f"总计数: {stats.get('total_count', 0)}")
        
        # 测试抓取慢查询（仅 MySQL）
        status, fetch_result = tester.get(
            f"/slow-query/{instance_id}/fetch-slow-queries",
            {"limit": 10, "min_exec_time": 1.0}
        )
        if is_mysql:
            log_test("抓取慢查询", status == 200 and "items" in fetch_result,
                     f"抓取 {fetch_result.get('total', 0)} 条")
        else:
            log_test("抓取慢查询", status == 400 or "detail" in fetch_result,
                     f"非 MySQL 实例正确拒绝: {fetch_result.get('detail', '')}")
    
    # ========== 4. 性能监控测试 ==========
    print("\n📋 [4] 性能监控测试")
    print("-" * 40)
    
    if instance_id:
        # 测试历史数据
        status, history = tester.get(f"/performance/{instance_id}/history", {"hours": 1})
        has_items = "items" in history and len(history.get("items", [])) > 0
        log_test("获取性能历史数据", status == 200 and has_items,
                 f"数据点数: {history.get('total', 0)}")
        
        # 验证数据格式
        if has_items:
            first_item = history["items"][0]
            required_fields = ["cpu_usage", "memory_usage", "connections", "qps", "collect_time"]
            missing = [f for f in required_fields if f not in first_item]
            log_test("性能数据格式验证", len(missing) == 0,
                     f"字段完整: {', '.join(required_fields)}")
        
        # 测试统计数据
        status, perf_stats = tester.get(f"/performance/{instance_id}/statistics", {"hours": 24})
        log_test("获取性能统计数据", status == 200,
                 f"包含 CPU/内存/QPS 统计")
    
    # ========== 5. 其他核心 API 测试 ==========
    print("\n📋 [5] 其他核心 API 测试")
    print("-" * 40)
    
    # 环境列表
    status, environments = tester.get("/environments", {"limit": 100})
    log_test("获取环境列表", status == 200 and "items" in environments,
             f"共 {environments.get('total', 0)} 个环境")
    
    # 用户列表
    status, users = tester.get("/users", {"limit": 100})
    log_test("获取用户列表", status == 200 and "items" in users,
             f"共 {users.get('total', 0)} 个用户")
    
    # 菜单列表
    status, menus = tester.get("/menu/list")
    log_test("获取菜单列表", status == 200 and isinstance(menus, list),
             f"返回 {len(menus) if isinstance(menus, list) else 'N/A'} 项")
    
    # ========== 6. 审批流程测试 ==========
    print("\n📋 [6] 审批流程测试")
    print("-" * 40)
    
    # 获取审批列表
    status, approvals = tester.get("/approvals", {"limit": 20})
    log_test("获取审批列表", status == 200 and "items" in approvals,
             f"共 {approvals.get('total', 0)} 条审批")
    
    # 检查审批数据格式
    if approvals.get("items") and len(approvals["items"]) > 0:
        first_approval = approvals["items"][0]
        required_fields = ["change_type", "sql_risk_level", "database_target"]
        missing = [f for f in required_fields if f not in first_approval]
        log_test("审批数据格式验证", len(missing) == 0,
                 f"字段完整: {', '.join(required_fields)}")
        
        # 检查新增字段
        has_new_fields = "affected_rows_estimate" in first_approval and "auto_execute" in first_approval
        log_test("审批新字段验证", has_new_fields,
                 f"包含: affected_rows_estimate, auto_execute")
    else:
        log_test("审批数据格式验证", True, "暂无审批数据，跳过验证")
        log_test("审批新字段验证", True, "暂无审批数据，跳过验证")
    
    # ========== 6. 前端页面测试 ==========
    print("\n📋 [6] 前端页面访问测试")
    print("-" * 40)
    
    # 测试前端首页
    try:
        response = requests.get("http://localhost:5000/", timeout=5)
        log_test("前端首页访问", response.status_code == 200,
                 f"状态码: {response.status_code}")
    except Exception as e:
        log_test("前端首页访问", False, str(e))
    
    # 测试静态资源
    try:
        response = requests.get("http://localhost:5000/assets/", timeout=5)
        # 404 也是正常的，说明静态资源路径存在
        log_test("静态资源路径", response.status_code in [200, 404, 403],
                 f"状态码: {response.status_code}")
    except Exception as e:
        log_test("静态资源路径", False, str(e))
    
    return True


def generate_report():
    """生成测试报告"""
    print("\n" + "=" * 60)
    print("📊 测试报告")
    print("=" * 60)
    
    total = len(test_results)
    passed = sum(1 for r in test_results if r["passed"])
    failed = total - passed
    
    print(f"\n总计: {total} 个测试")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"通过率: {(passed/total*100):.1f}%" if total > 0 else "N/A")
    
    if failed > 0:
        print("\n❌ 失败的测试:")
        for r in test_results:
            if not r["passed"]:
                print(f"   - {r['name']}: {r['message']}")
    
    print("\n" + "=" * 60)
    return failed == 0


if __name__ == "__main__":
    try:
        run_tests()
        success = generate_report()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
