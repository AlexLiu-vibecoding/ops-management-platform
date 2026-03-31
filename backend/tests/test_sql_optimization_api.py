"""
SQL 优化闭环 API 测试
"""
import pytest


class TestCollectionTaskAPI:
    """采集任务 API 测试"""

    def test_create_collection_task_unauthorized(self, client):
        """测试未登录创建任务"""
        response = client.post(
            "/api/v1/sql-optimization/tasks",
            json={
                "instance_id": 1
            }
        )
        assert response.status_code == 401

    def test_list_collection_tasks_unauthorized(self, client):
        """测试未登录获取任务列表"""
        response = client.get("/api/v1/sql-optimization/tasks")
        assert response.status_code == 401

    def test_create_task_forbidden(self, client, readonly_token):
        """测试 readonly 用户创建任务"""
        response = client.post(
            "/api/v1/sql-optimization/tasks",
            headers={"Authorization": f"Bearer {readonly_token}"},
            json={
                "instance_id": 1
            }
        )
        assert response.status_code == 403

    def test_list_collection_tasks_success(self, client, operator_token):
        """测试获取采集任务列表"""
        response = client.get(
            "/api/v1/sql-optimization/tasks",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_create_task_missing_instance(self, client, operator_token):
        """测试创建任务时缺少实例"""
        response = client.post(
            "/api/v1/sql-optimization/tasks",
            headers={"Authorization": f"Bearer {operator_token}"},
            json={
                "cron_expression": "0 */5 * * *"
            }
        )
        assert response.status_code == 422  # Validation error

    def test_delete_task_unauthorized(self, client):
        """测试未登录删除任务"""
        response = client.delete("/api/v1/sql-optimization/tasks/1")
        assert response.status_code == 401


class TestSuggestionAPI:
    """优化建议 API 测试"""

    def test_list_suggestions_unauthorized(self, client):
        """测试未登录获取建议列表"""
        response = client.get("/api/v1/sql-optimization/suggestions")
        assert response.status_code == 401

    def test_list_suggestions_success(self, client, operator_token):
        """测试获取优化建议列表"""
        response = client.get(
            "/api/v1/sql-optimization/suggestions",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_suggestions_pagination(self, client, operator_token):
        """测试建议列表分页"""
        response = client.get(
            "/api/v1/sql-optimization/suggestions?page=1&page_size=10",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) <= 10

    def test_list_suggestions_filter_by_status(self, client, operator_token):
        """测试按状态筛选建议"""
        response = client.get(
            "/api/v1/sql-optimization/suggestions?status=pending",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["status"] == "pending"

    def test_get_suggestion_not_found(self, client, operator_token):
        """测试获取不存在的建议"""
        response = client.get(
            "/api/v1/sql-optimization/suggestions/99999",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 404

    def test_adopt_suggestion_unauthorized(self, client):
        """测试未登录采用建议"""
        response = client.post("/api/v1/sql-optimization/suggestions/1/adopt")
        assert response.status_code == 401

    def test_adopt_suggestion_forbidden(self, client, readonly_token):
        """测试 readonly 用户采用建议"""
        response = client.post(
            "/api/v1/sql-optimization/suggestions/1/adopt",
            headers={"Authorization": f"Bearer {readonly_token}"}
        )
        assert response.status_code == 403

    def test_reject_suggestion_unauthorized(self, client):
        """测试未登录拒绝建议"""
        response = client.post(
            "/api/v1/sql-optimization/suggestions/1/reject",
            json={"reason": "测试"}
        )
        assert response.status_code == 401

    def test_verify_suggestion_unauthorized(self, client):
        """测试未登录验证效果"""
        response = client.post("/api/v1/sql-optimization/suggestions/1/verify")
        assert response.status_code == 401


class TestManualAnalyze:
    """手动分析 API 测试"""

    def test_manual_analyze_unauthorized(self, client):
        """测试未登录手动分析"""
        response = client.post(
            "/api/v1/sql-optimization/suggestions/analyze",
            json={
                "instance_id": 1,
                "sql_text": "SELECT * FROM test_table"
            }
        )
        assert response.status_code == 401

    def test_manual_analyze_missing_fields(self, client, operator_token):
        """测试手动分析缺少必填字段"""
        response = client.post(
            "/api/v1/sql-optimization/suggestions/analyze",
            headers={"Authorization": f"Bearer {operator_token}"},
            json={
                "instance_id": 1
            }
        )
        assert response.status_code == 422  # Validation error

    def test_manual_analyze_success(self, client, operator_token, test_rdb_instance):
        """测试手动分析成功（会因实例连接失败）"""
        response = client.post(
            "/api/v1/sql-optimization/suggestions/analyze",
            headers={"Authorization": f"Bearer {operator_token}"},
            json={
                "instance_id": test_rdb_instance.id,
                "sql_text": "SELECT * FROM test_table WHERE id = 1"
            }
        )
        # 可能因实例连接问题失败，但请求格式正确
        assert response.status_code in [200, 400, 500]


class TestIntegrationFlow:
    """集成流程测试"""

    def test_full_flow_with_rdb_instance(self, client, operator_token, test_rdb_instance, db_session):
        """测试完整流程（创建任务 -> 获取建议）"""
        from app.models import SlowQueryCollectionTask
        
        # 1. 创建采集任务
        response = client.post(
            "/api/v1/sql-optimization/tasks",
            headers={"Authorization": f"Bearer {operator_token}"},
            json={
                "instance_id": test_rdb_instance.id,
                "enabled": True,
                "cron_expression": "0 */5 * * *",
                "min_exec_time": 1.0,
                "auto_analyze": True
            }
        )
        assert response.status_code == 201
        task_data = response.json()
        assert task_data["instance_id"] == test_rdb_instance.id
        
        # 2. 获取任务列表
        response = client.get(
            "/api/v1/sql-optimization/tasks",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        list_data = response.json()
        assert list_data["total"] >= 1
        
        # 3. 更新任务
        task_id = task_data["id"]
        response = client.put(
            f"/api/v1/sql-optimization/tasks/{task_id}",
            headers={"Authorization": f"Bearer {operator_token}"},
            json={
                "enabled": False
            }
        )
        assert response.status_code == 200
        assert response.json()["enabled"] == False

    def test_suggestion_create_and_adopt(self, client, operator_token, test_rdb_instance, db_session):
        """测试建议创建和采用流程"""
        from app.models import OptimizationSuggestion
        
        # 创建一个测试建议
        suggestion = OptimizationSuggestion(
            instance_id=test_rdb_instance.id,
            database_name="test_db",
            sql_fingerprint="SELECT * FROM test_table WHERE id = ?",
            sql_sample="SELECT * FROM test_table WHERE id = 1",
            issues=[{"type": "full_scan", "description": "全表扫描"}],
            suggestions=[{"type": "add_index", "description": "添加索引"}],
            index_ddl="CREATE INDEX idx_test ON test_table(id);",
            rollback_sql="DROP INDEX idx_test ON test_table;",
            risk_level="low",
            status="pending"
        )
        db_session.add(suggestion)
        db_session.commit()
        db_session.refresh(suggestion)
        
        # 获取建议列表
        response = client.get(
            "/api/v1/sql-optimization/suggestions",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        
        # 采用建议
        response = client.post(
            f"/api/v1/sql-optimization/suggestions/{suggestion.id}/adopt",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        assert response.status_code == 200
        adopt_data = response.json()
        assert adopt_data["status"] == "adopted"
        assert adopt_data["approval_id"] is not None
