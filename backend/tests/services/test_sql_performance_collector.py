"""
SQL 性能采集器单元测试

使用 mock 测试 SQL 性能采集器的核心功能，避免依赖真实的数据库连接。
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from app.services.sql_performance_collector import SQLPerformanceCollector
from app.models import RDBInstance, RDBType


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.add.return_value = None
    db.commit.return_value = None
    db.refresh.return_value = None
    return db


@pytest.fixture
def test_instance():
    """创建测试实例"""
    instance = RDBInstance(
        id=1,
        name="test-instance",
        db_type=RDBType.MYSQL,
        host="localhost",
        port=3306,
        username="root",
        password_encrypted="encrypted_password"
    )
    return instance


@pytest.fixture
def collector():
    """创建性能采集器实例"""
    return SQLPerformanceCollector()


class TestSQLPerformanceCollector:
    """SQL 性能采集器测试"""

    @patch('app.services.sql_performance_collector.SQLPerformanceCollector._get_adapter')
    async def test_collect_performance_success(self, mock_get_adapter, collector, mock_db_session, test_instance):
        """测试成功采集性能数据"""
        # 模拟适配器
        mock_adapter = Mock()
        mock_adapter.execute_query.return_value = [
            {"query_time": 0.123, "lock_time": 0.001, "rows_sent": 10, "rows_examined": 100}
        ]
        mock_get_adapter.return_value = mock_adapter

        result = await collector.collect_performance(
            mock_db_session,
            test_instance,
            "SELECT * FROM users LIMIT 10"
        )

        assert result["success"] is True
        assert "metrics" in result
        assert result["metrics"]["execution_time"] > 0
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

    @patch('app.services.sql_performance_collector.SQLPerformanceCollector._get_adapter')
    async def test_collect_performance_failure(self, mock_get_adapter, collector, mock_db_session, test_instance):
        """测试采集性能数据失败"""
        # 模拟适配器失败
        mock_adapter = Mock()
        mock_adapter.connect.side_effect = Exception("Connection failed")
        mock_get_adapter.return_value = mock_adapter

        result = await collector.collect_performance(
            mock_db_session,
            test_instance,
            "SELECT * FROM users LIMIT 10"
        )

        assert result["success"] is False
        assert "error" in result

    @patch('app.services.sql_performance_collector.SQLPerformanceCollector._get_adapter')
    async def test_collect_performance_with_params(self, mock_get_adapter, collector, mock_db_session, test_instance):
        """测试带参数的查询采集"""
        mock_adapter = Mock()
        mock_adapter.execute_query.return_value = [{"query_time": 0.123}]
        mock_get_adapter.return_value = mock_adapter

        result = await collector.collect_performance(
            mock_db_session,
            test_instance,
            "SELECT * FROM users WHERE id = %(id)s",
            {"id": 1}
        )

        assert result["success"] is True

    @patch('app.services.sql_performance_collector.SQLPerformanceCollector._get_adapter')
    async def test_collect_multiple_queries(self, mock_get_adapter, collector, mock_db_session, test_instance):
        """测试采集多个查询的性能"""
        mock_adapter = Mock()
        mock_adapter.execute_query.side_effect = [
            [{"query_time": 0.123, "rows_sent": 10}],
            [{"query_time": 0.234, "rows_sent": 20}]
        ]
        mock_get_adapter.return_value = mock_adapter

        queries = [
            "SELECT * FROM users LIMIT 10",
            "SELECT * FROM orders LIMIT 20"
        ]

        results = []
        for query in queries:
            result = await collector.collect_performance(
                mock_db_session,
                test_instance,
                query
            )
            results.append(result)

        assert all(r["success"] for r in results)
        assert len(results) == 2

    def test_parse_query_time(self, collector):
        """测试解析查询时间"""
        mock_result = {"query_time": 0.12345}
        query_time = collector._parse_query_time(mock_result)
        assert query_time == 0.12345

    def test_parse_rows_sent(self, collector):
        """测试解析返回行数"""
        mock_result = {"rows_sent": 10}
        rows_sent = collector._parse_rows_sent(mock_result)
        assert rows_sent == 10

    def test_parse_rows_examined(self, collector):
        """测试解析扫描行数"""
        mock_result = {"rows_examined": 100}
        rows_examined = collector._parse_rows_examined(mock_result)
        assert rows_examined == 100

    def test_calculate_metrics(self, collector):
        """测试计算性能指标"""
        mock_data = {
            "query_time": 0.123,
            "rows_sent": 10,
            "rows_examined": 100
        }

        metrics = collector._calculate_metrics(mock_data)

        assert "execution_time" in metrics
        assert "rows_sent" in metrics
        assert "rows_examined" in metrics
        assert "scan_ratio" in metrics

    def test_calculate_scan_ratio(self, collector):
        """测试计算扫描比率"""
        mock_data = {
            "rows_sent": 10,
            "rows_examined": 100
        }

        scan_ratio = collector._calculate_scan_ratio(mock_data)
        assert scan_ratio == 10.0  # 100 / 10

    @patch('app.adapters.datasource.factory.DataSourceAdapterFactory.create')
    def test_get_adapter_mysql(self, mock_factory_create, collector, test_instance):
        """测试获取 MySQL 适配器"""
        mock_adapter = Mock()
        mock_factory_create.return_value = mock_adapter

        test_instance.db_type = RDBType.MYSQL
        adapter = collector._get_adapter(test_instance)

        assert adapter == mock_adapter
        mock_factory_create.assert_called_once_with("mysql", test_instance.to_config())

    @patch('app.adapters.datasource.factory.DataSourceAdapterFactory.create')
    def test_get_adapter_postgresql(self, mock_factory_create, collector, test_instance):
        """测试获取 PostgreSQL 适配器"""
        mock_adapter = Mock()
        mock_factory_create.return_value = mock_adapter

        test_instance.db_type = RDBType.POSTGRESQL
        adapter = collector._get_adapter(test_instance)

        assert adapter == mock_adapter
        mock_factory_create.assert_called_once_with("postgresql", test_instance.to_config())

    def test_validate_query(self, collector):
        """测试验证 SQL 查询"""
        valid_query = "SELECT * FROM users"
        assert collector._validate_query(valid_query) is True

    def test_validate_query_invalid(self, collector):
        """测试验证无效 SQL 查询"""
        invalid_query = "DROP TABLE users"
        assert collector._validate_query(invalid_query) is False

    @patch('app.services.sql_performance_collector.SQLPerformanceCollector._get_adapter')
    async def test_save_performance_record(self, mock_get_adapter, collector, mock_db_session, test_instance):
        """测试保存性能记录"""
        mock_adapter = Mock()
        mock_adapter.execute_query.return_value = [{"query_time": 0.123}]
        mock_get_adapter.return_value = mock_adapter

        result = await collector.collect_performance(
            mock_db_session,
            test_instance,
            "SELECT * FROM users LIMIT 10"
        )

        # 验证数据库操作被调用
        assert mock_db_session.add.called
        assert mock_db_session.commit.called

    @patch('app.services.sql_performance_collector.SQLPerformanceCollector._get_adapter')
    async def test_get_performance_summary(self, mock_get_adapter, collector, mock_db_session, test_instance):
        """测试获取性能摘要"""
        mock_adapter = Mock()
        mock_adapter.execute_query.return_value = [{"query_time": 0.123}]
        mock_get_adapter.return_value = mock_adapter

        # 采集多条记录
        for i in range(3):
            await collector.collect_performance(
                mock_db_session,
                test_instance,
                f"SELECT * FROM users LIMIT {i+1}"
            )

        # 获取摘要
        summary = collector.get_performance_summary(mock_db_session, test_instance.id)

        assert "total_queries" in summary
        assert "avg_execution_time" in summary
        assert "max_execution_time" in summary
        assert "min_execution_time" in summary
