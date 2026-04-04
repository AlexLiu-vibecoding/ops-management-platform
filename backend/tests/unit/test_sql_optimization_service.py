"""
SQL优化服务测试
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from app.services.sql_optimization_service import SQLOptimizationService
from app.models import (
    SlowQueryCollectionTask, SlowQuery, OptimizationSuggestion,
    RDBInstance, User
)
from app.schemas import CollectionTaskCreate, CollectionTaskUpdate


class TestSQLOptimizationService:
    """SQL优化服务测试类"""

    @pytest.fixture
    def service(self, db_session):
        """创建服务实例"""
        return SQLOptimizationService(db_session)

    @pytest.fixture
    def mock_instance(self, db_session):
        """创建模拟实例"""
        instance = RDBInstance(
            name="test_mysql",
            host="localhost",
            port=3306,
            db_type="mysql",
            username="root",
            password_encrypted="encrypted_pass"
        )
        db_session.add(instance)
        db_session.commit()
        return instance

    def test_create_collection_task_success(self, service, db_session, mock_instance):
        """测试创建采集任务成功"""
        task_data = CollectionTaskCreate(
            instance_id=mock_instance.id,
            enabled=True,
            cron_expression="0 */1 * * *",
            min_exec_time=1000,
            top_n=10,
            auto_analyze=True,
            analyze_threshold=5,
            llm_analysis=True
        )

        task = service.create_collection_task(task_data, current_user=Mock(id=1))

        assert task is not None
        assert task.instance_id == mock_instance.id
        assert task.enabled is True
        assert task.cron_expression == "0 */1 * * *"

    def test_create_collection_task_instance_not_found(self, service):
        """测试创建采集任务实例不存在"""
        task_data = CollectionTaskCreate(
            instance_id=99999,  # 不存在的ID
            enabled=True,
            cron_expression="0 */1 * * *"
        )

        with pytest.raises(ValueError, match="实例不存在"):
            service.create_collection_task(task_data, current_user=Mock(id=1))

    def test_create_collection_task_duplicate(self, service, db_session, mock_instance):
        """测试创建重复采集任务"""
        # 先创建一个任务
        task_data = CollectionTaskCreate(
            instance_id=mock_instance.id,
            enabled=True,
            cron_expression="0 */1 * * *"
        )
        service.create_collection_task(task_data, current_user=Mock(id=1))

        # 再尝试创建同样的任务
        with pytest.raises(ValueError, match="已存在采集任务"):
            service.create_collection_task(task_data, current_user=Mock(id=1))

    def test_update_collection_task_success(self, service, db_session, mock_instance):
        """测试更新采集任务成功"""
        # 先创建任务
        task_data = CollectionTaskCreate(
            instance_id=mock_instance.id,
            enabled=True,
            cron_expression="0 */1 * * *"
        )
        task = service.create_collection_task(task_data, current_user=Mock(id=1))

        # 更新任务
        update_data = CollectionTaskUpdate(
            enabled=False,
            cron_expression="0 */2 * * *"
        )
        updated = service.update_collection_task(task.id, update_data)

        assert updated is not None
        assert updated.enabled is False
        assert updated.cron_expression == "0 */2 * * *"

    def test_update_collection_task_not_found(self, service):
        """测试更新不存在的采集任务"""
        update_data = CollectionTaskUpdate(enabled=False)
        result = service.update_collection_task(99999, update_data)

        assert result is None

    def test_delete_collection_task_success(self, service, db_session, mock_instance):
        """测试删除采集任务成功"""
        # 先创建任务
        task_data = CollectionTaskCreate(
            instance_id=mock_instance.id,
            enabled=True,
            cron_expression="0 */1 * * *"
        )
        task = service.create_collection_task(task_data, current_user=Mock(id=1))

        # 删除任务
        result = service.delete_collection_task(task.id)

        assert result is True

        # 确认已删除
        deleted = db_session.get(SlowQueryCollectionTask, task.id)
        assert deleted is None

    def test_delete_collection_task_not_found(self, service):
        """测试删除不存在的采集任务"""
        result = service.delete_collection_task(99999)

        assert result is False

    def test_get_suggestion_success(self, service, db_session, mock_instance):
        """测试获取优化建议详情"""
        # 创建建议
        suggestion = OptimizationSuggestion(
            instance_id=mock_instance.id,
            sql_fingerprint="SELECT * FROM users WHERE id = ?",
            sql_sample="SELECT * FROM users WHERE id = 1",
            issues=[{"type": "missing_index", "description": "缺少索引"}],
            suggestions=[{"action": "add_index", "sql": "CREATE INDEX idx ON users(id)"}],
            risk_level="high",
            status="pending"
        )
        db_session.add(suggestion)
        db_session.commit()

        # 获取建议
        result = service.get_suggestion(suggestion.id)

        assert result is not None
        assert result.sql_fingerprint == "SELECT * FROM users WHERE id = ?"
        assert result.risk_level == "high"

    def test_get_suggestion_not_found(self, service):
        """测试获取不存在的优化建议"""
        result = service.get_suggestion(99999)

        assert result is None

    def test_create_suggestion_success(self, service, db_session, mock_instance):
        """测试创建优化建议"""
        from app.schemas import OptimizationSuggestionCreate

        suggestion_data = OptimizationSuggestionCreate(
            instance_id=mock_instance.id,
            sql_fingerprint="SELECT * FROM users WHERE id = ?",
            sql_sample="SELECT * FROM users WHERE id = 1",
            issues=[{"type": "missing_index", "description": "缺少索引"}],
            suggestions=[{"action": "add_index", "sql": "CREATE INDEX idx_users_id ON users(id)"}],
            risk_level="medium"
        )

        suggestion = service.create_suggestion(suggestion_data)

        assert suggestion is not None
        assert suggestion.instance_id == mock_instance.id
        assert suggestion.sql_fingerprint == "SELECT * FROM users WHERE id = ?"
        assert suggestion.status == "pending"

    def test_adopt_suggestion_success(self, service, db_session, mock_instance):
        """测试采用优化建议成功"""
        # 创建建议
        suggestion = OptimizationSuggestion(
            instance_id=mock_instance.id,
            sql_fingerprint="SELECT * FROM users WHERE id = ?",
            suggested_sql="SELECT id, name FROM users WHERE id = ?",
            index_ddl="CREATE INDEX idx_users_id ON users(id)",
            issues=[{"type": "missing_index", "description": "缺少索引"}],
            suggestions=[{"action": "add_index", "sql": "CREATE INDEX idx_users_id ON users(id)"}],
            risk_level="medium",
            status="pending"
        )
        db_session.add(suggestion)
        db_session.commit()

        # 采用建议
        user = Mock(id=1, real_name="测试用户", username="testuser")
        result = service.adopt_suggestion(suggestion.id, current_user=user)

        assert result is not None
        assert "approval_id" in result

    def test_adopt_suggestion_not_found(self, service):
        """测试采用不存在的优化建议"""
        user = Mock(id=1, real_name="测试用户", username="testuser")

        with pytest.raises(ValueError, match="建议不存在"):
            service.adopt_suggestion(99999, current_user=user)

    def test_adopt_suggestion_wrong_status(self, service, db_session, mock_instance):
        """测试采用状态不正确的优化建议"""
        # 创建已采用的 建议
        suggestion = OptimizationSuggestion(
            instance_id=mock_instance.id,
            sql_fingerprint="SELECT * FROM users",
            status="adopted"
        )
        db_session.add(suggestion)
        db_session.commit()

        user = Mock(id=1, real_name="测试用户", username="testuser")

        with pytest.raises(ValueError, match="建议状态不是 pending"):
            service.adopt_suggestion(suggestion.id, current_user=user)

    def test_adopt_suggestion_no_sql(self, service, db_session, mock_instance):
        """测试采用无可执行SQL的优化建议"""
        # 创建没有SQL的建议
        suggestion = OptimizationSuggestion(
            instance_id=mock_instance.id,
            sql_fingerprint="SELECT * FROM users",
            suggested_sql=None,
            index_ddl=None,
            status="pending"
        )
        db_session.add(suggestion)
        db_session.commit()

        user = Mock(id=1, real_name="测试用户", username="testuser")

        with pytest.raises(ValueError, match="没有可执行的 SQL 语句"):
            service.adopt_suggestion(suggestion.id, current_user=user)

    def test_adopt_suggestion_instance_not_found(self, service, db_session):
        """测试采用建议时实例不存在"""
        # 创建建议（关联不存在的实例）
        suggestion = OptimizationSuggestion(
            instance_id=99999,  # 不存在的实例
            sql_fingerprint="SELECT * FROM users",
            index_ddl="CREATE INDEX idx ON users(id)",
            status="pending"
        )
        db_session.add(suggestion)
        db_session.commit()

        user = Mock(id=1, real_name="测试用户", username="testuser")

        with pytest.raises(ValueError, match="实例不存在"):
            service.adopt_suggestion(suggestion.id, current_user=user)

    def test_reject_suggestion_success(self, service, db_session, mock_instance):
        """测试拒绝优化建议"""
        # 创建建议
        suggestion = OptimizationSuggestion(
            instance_id=mock_instance.id,
            sql_fingerprint="SELECT * FROM users",
            status="pending"
        )
        db_session.add(suggestion)
        db_session.commit()

        # 拒绝建议
        user = Mock(id=1, real_name="测试用户", username="testuser")
        result = service.reject_suggestion(suggestion.id, reason="不需要优化", current_user=user)

        assert result.status == "rejected"

    def test_reject_suggestion_not_found(self, service):
        """测试拒绝不存在的优化建议"""
        user = Mock(id=1, real_name="测试用户", username="testuser")

        with pytest.raises(ValueError, match="建议不存在"):
            service.reject_suggestion(99999, reason="不需要", current_user=user)
