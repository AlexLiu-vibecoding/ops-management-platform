"""
SQL优化服务测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.services.sql_optimization_service import SQLOptimizationService
from app.models import (
    RDBInstance, SlowQueryCollectionTask, SlowQuery,
    OptimizationSuggestion, User
)


class TestSQLOptimizationService:
    """SQL优化服务测试类"""

    @pytest.fixture
    def mock_db(self):
        """创建模拟数据库会话"""
        return Mock()

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return SQLOptimizationService(mock_db)

    @pytest.fixture
    def mock_user(self):
        """创建模拟用户"""
        user = Mock(spec=User)
        user.id = 1
        user.username = "test_user"
        return user

    @pytest.fixture
    def mock_instance(self):
        """创建模拟实例"""
        instance = Mock(spec=RDBInstance)
        instance.id = 1
        instance.name = "test_mysql"
        instance.host = "localhost"
        instance.port = 3306
        return instance

    # ==================== 采集任务管理测试 ====================

    def test_get_instance_found(self, service, mock_db, mock_instance):
        """测试获取实例成功"""
        # SQLAlchemy 2.0 风格查询
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_instance
        mock_db.execute.return_value = mock_result

        result = service._get_instance(1)

        assert result is not None
        mock_db.execute.assert_called_once()

    def test_get_instance_not_found(self, service, mock_db):
        """测试获取实例不存在"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = service._get_instance(999)

        assert result is None

    def test_get_task_found(self, service, mock_db):
        """测试获取任务成功"""
        mock_task = Mock(spec=SlowQueryCollectionTask)
        mock_task.id = 1
        mock_task.instance_id = 1

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_task
        mock_db.execute.return_value = mock_result

        result = service._get_task(1)

        assert result is not None

    def test_get_task_not_found(self, service, mock_db):
        """测试获取任务不存在"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = service._get_task(999)

        assert result is None

    def test_get_task_by_instance_found(self, service, mock_db):
        """测试通过实例获取任务"""
        mock_task = Mock(spec=SlowQueryCollectionTask)
        mock_task.id = 1
        mock_task.instance_id = 1

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_task
        mock_db.execute.return_value = mock_result

        result = service._get_task_by_instance(1)

        assert result is not None

    def test_get_task_by_instance_not_found(self, service, mock_db):
        """测试通过实例获取任务不存在"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = service._get_task_by_instance(999)

        assert result is None

    def test_has_suggestion_true(self, service, mock_db):
        """测试存在优化建议"""
        mock_suggestion = Mock(spec=OptimizationSuggestion)
        mock_suggestion.id = 1

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_suggestion
        mock_db.execute.return_value = mock_result

        result = service._has_suggestion(1)

        assert result is True

    def test_has_suggestion_false(self, service, mock_db):
        """测试不存在优化建议"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = service._has_suggestion(999)

        assert result is False

    def test_get_instance_name_found(self, service, mock_db):
        """测试获取实例名称成功"""
        # _get_instance_name 查询的是 RDBInstance.name 而不是整个对象
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = "test_mysql"
        mock_db.execute.return_value = mock_result

        result = service._get_instance_name(1)

        assert result == "test_mysql"

    def test_get_instance_name_not_found(self, service, mock_db):
        """测试获取实例名称失败"""
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = service._get_instance_name(999)

        assert result == "未知实例"


class TestSQLOptimizationHelperMethods:
    """SQL优化辅助方法测试类"""

    @pytest.fixture
    def mock_db(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_db):
        return SQLOptimizationService(mock_db)

    def test_generate_sql_fingerprint(self, service):
        """测试生成SQL指纹"""
        sql = "SELECT * FROM users WHERE id = 123"
        fingerprint = service._generate_sql_fingerprint(sql)

        assert fingerprint is not None
        assert isinstance(fingerprint, str)

    def test_generate_same_fingerprint(self, service):
        """测试相同SQL生成相同指纹"""
        sql1 = "SELECT * FROM users WHERE id = 123"
        sql2 = "SELECT * FROM users WHERE id = 456"

        fp1 = service._generate_sql_fingerprint(sql1)
        fp2 = service._generate_sql_fingerprint(sql2)

        # 结构相同，指纹应该相同
        assert fp1 == fp2

    def test_detect_rule_issues(self, service):
        """测试检测规则问题"""
        explain_result = {
            "rows": 10000,
            "type": "ALL",
            "key": None,
            "extra": "Using where"
        }

        issues = service._detect_rule_issues(explain_result)

        assert isinstance(issues, list)

    def test_analyze_sql_rules(self, service):
        """测试分析SQL规则"""
        sql = "SELECT * FROM users WHERE name = 'test'"
        query_data = {
            "exec_time": 2.5,
            "rows_sent": 1000
        }

        issues = service._analyze_sql_rules(sql, query_data)

        assert isinstance(issues, list)

    def test_generate_suggestions(self, service):
        """测试生成优化建议"""
        issues = [
            {"type": "full_table_scan", "description": "全表扫描"},
            {"type": "missing_index", "description": "缺少索引"}
        ]

        suggestions = service._generate_suggestions(issues)

        assert isinstance(suggestions, list)
        assert len(suggestions) == 2

