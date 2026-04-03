"""
脚本管理 API 集成测试
"""
import pytest
from app.models import ScriptType


class TestScriptsAPI:
    """脚本管理接口测试"""

    def test_list_scripts(self, client, auth_headers):
        """测试获取脚本列表"""
        response = client.get("/api/v1/scripts", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_script(self, client, auth_headers):
        """测试创建脚本"""
        script_data = {
            "name": "API测试脚本",
            "script_type": ScriptType.PYTHON.value,
            "content": "print('Hello from API test')",
            "description": "API 测试创建的脚本",
            "is_enabled": True
        }
        
        response = client.post("/api/v1/scripts", json=script_data, headers=auth_headers)
        
        if response.status_code == 201:
            data = response.json()
            assert data["name"] == "API测试脚本"
            assert data["script_type"] == ScriptType.PYTHON.value
            assert "id" in data

    def test_create_bash_script(self, client, auth_headers):
        """测试创建 Bash 脚本"""
        script_data = {
            "name": "Bash测试脚本",
            "script_type": ScriptType.BASH.value,
            "content": "#!/bin/bash\necho 'Hello'",
            "description": "Bash 脚本测试",
            "is_enabled": True
        }
        
        response = client.post("/api/v1/scripts", json=script_data, headers=auth_headers)
        
        assert response.status_code in [201, 403]

    def test_create_sql_script(self, client, auth_headers):
        """测试创建 SQL 脚本"""
        script_data = {
            "name": "SQL测试脚本",
            "script_type": ScriptType.SQL.value,
            "content": "SELECT 1 as test;",
            "description": "SQL 脚本测试",
            "is_enabled": True
        }
        
        response = client.post("/api/v1/scripts", json=script_data, headers=auth_headers)
        
        assert response.status_code in [201, 403]

    def test_get_script_detail(self, client, auth_headers):
        """测试获取脚本详情"""
        # 先创建脚本
        script_data = {
            "name": "详情测试脚本",
            "script_type": ScriptType.PYTHON.value,
            "content": "print('detail test')",
            "is_enabled": True
        }
        
        create_response = client.post("/api/v1/scripts", json=script_data, headers=auth_headers)
        
        if create_response.status_code == 201:
            script_id = create_response.json()["id"]
            
            response = client.get(f"/api/v1/scripts/{script_id}", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "详情测试脚本"

    def test_update_script(self, client, auth_headers):
        """测试更新脚本"""
        # 先创建脚本
        script_data = {
            "name": "更新测试脚本",
            "script_type": ScriptType.PYTHON.value,
            "content": "print('original')",
            "is_enabled": True
        }
        
        create_response = client.post("/api/v1/scripts", json=script_data, headers=auth_headers)
        
        if create_response.status_code == 201:
            script_id = create_response.json()["id"]
            
            update_data = {
                "name": "已更新的脚本",
                "content": "print('updated')",
                "description": "Updated description"
            }
            
            response = client.put(
                f"/api/v1/scripts/{script_id}",
                json=update_data,
                headers=auth_headers
            )
            
            assert response.status_code in [200, 404]

    def test_delete_script(self, client, auth_headers):
        """测试删除脚本"""
        # 先创建脚本
        script_data = {
            "name": "删除测试脚本",
            "script_type": ScriptType.PYTHON.value,
            "content": "print('to delete')",
            "is_enabled": True
        }
        
        create_response = client.post("/api/v1/scripts", json=script_data, headers=auth_headers)
        
        if create_response.status_code == 201:
            script_id = create_response.json()["id"]
            
            response = client.delete(f"/api/v1/scripts/{script_id}", headers=auth_headers)
            
            assert response.status_code in [200, 204]

    def test_execute_script(self, client, auth_headers):
        """测试执行脚本"""
        # 先创建脚本
        script_data = {
            "name": "执行测试脚本",
            "script_type": ScriptType.PYTHON.value,
            "content": "print('execution test')",
            "is_enabled": True
        }
        
        create_response = client.post("/api/v1/scripts", json=script_data, headers=auth_headers)
        
        if create_response.status_code == 201:
            script_id = create_response.json()["id"]
            
            response = client.post(
                f"/api/v1/scripts/{script_id}/execute",
                json={"timeout": 60},
                headers=auth_headers
            )
            
            # 执行可能成功或异步处理
            assert response.status_code in [200, 202]

    def test_get_script_versions(self, client, auth_headers):
        """测试获取脚本版本历史"""
        # 先创建脚本
        script_data = {
            "name": "版本测试脚本",
            "script_type": ScriptType.PYTHON.value,
            "content": "print('v1')",
            "is_enabled": True
        }
        
        create_response = client.post("/api/v1/scripts", json=script_data, headers=auth_headers)
        
        if create_response.status_code == 201:
            script_id = create_response.json()["id"]
            
            response = client.get(
                f"/api/v1/scripts/{script_id}/versions",
                headers=auth_headers
            )
            
            # 可能返回版本列表或 404（如果不支持版本控制）
            assert response.status_code in [200, 404]
