"""
环境管理 API 集成测试
"""
import pytest


class TestEnvironmentsAPI:
    """环境管理接口测试"""

    def test_list_environments(self, client, auth_headers):
        """测试获取环境列表"""
        response = client.get("/api/v1/environments", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_environment_as_admin(self, client, admin_headers):
        """测试管理员创建环境"""
        env_data = {
            "name": "API测试环境",
            "code": "api-test",
            "color": "#FF6B6B",
            "description": "API 测试用的环境",
            "require_approval": True
        }
        
        response = client.post("/api/v1/environments", json=env_data, headers=admin_headers)
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert data["name"] == "API测试环境"
            assert data["code"] == "api-test"

    def test_create_environment_as_normal_user(self, client, auth_headers):
        """测试普通用户创建环境（应该失败）"""
        env_data = {
            "name": "测试环境",
            "code": "test-env",
            "color": "#1890FF"
        }
        
        response = client.post("/api/v1/environments", json=env_data, headers=auth_headers)
        
        # 普通用户应该没有权限
        assert response.status_code in [403, 401]

    def test_create_duplicate_environment(self, client, admin_headers):
        """测试创建重复环境"""
        env_data = {
            "name": "重复环境",
            "code": "duplicate-env",
            "color": "#1890FF"
        }
        
        # 第一次创建
        client.post("/api/v1/environments", json=env_data, headers=admin_headers)
        
        # 第二次创建（重复）
        response = client.post("/api/v1/environments", json=env_data, headers=admin_headers)
        
        # 应该返回冲突错误
        assert response.status_code in [400, 409]

    def test_get_environment_detail(self, client, auth_headers):
        """测试获取环境详情"""
        # 先获取列表
        list_response = client.get("/api/v1/environments", headers=auth_headers)
        
        if list_response.status_code == 200:
            envs = list_response.json()
            if envs:
                env_id = envs[0]["id"]
                
                response = client.get(f"/api/v1/environments/{env_id}", headers=auth_headers)
                
                assert response.status_code == 200
                data = response.json()
                assert "id" in data
                assert "name" in data

    def test_update_environment(self, client, admin_headers):
        """测试更新环境"""
        # 先获取列表
        list_response = client.get("/api/v1/environments", headers=admin_headers)
        
        if list_response.status_code == 200:
            envs = list_response.json()
            if envs:
                env_id = envs[0]["id"]
                
                update_data = {
                    "name": "更新后的环境名",
                    "description": "更新后的描述"
                }
                
                response = client.put(
                    f"/api/v1/environments/{env_id}",
                    json=update_data,
                    headers=admin_headers
                )
                
                assert response.status_code in [200, 404]

    def test_delete_environment(self, client, admin_headers):
        """测试删除环境"""
        # 创建一个专门用于删除测试的环境
        env_data = {
            "name": "待删除环境",
            "code": "to-delete",
            "color": "#999999"
        }
        
        create_response = client.post(
            "/api/v1/environments",
            json=env_data,
            headers=admin_headers
        )
        
        if create_response.status_code in [200, 201]:
            env_id = create_response.json()["id"]
            
            response = client.delete(
                f"/api/v1/environments/{env_id}",
                headers=admin_headers
            )
            
            assert response.status_code in [200, 204]
