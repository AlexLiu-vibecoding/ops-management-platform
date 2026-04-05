"""
SQL 性能对比器单元测试

使用 mock 测试 SQL 性能对比器的核心功能，避免依赖真实的数据库连接。
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.sql_performance_comparator import SQLPerformanceComparator


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    db = Mock()
    db.query.return_value.all.return_value = []
    db.query.return_value.filter.return_value.all.return_value = []
    db.add.return_value = None
    db.commit.return_value = None
    return db


@pytest.fixture
def comparator():
    """创建性能对比器实例"""
    return SQLPerformanceComparator()


@pytest.fixture
def mock_record1():
    """创建模拟的性能记录"""
    record = Mock()
    record.id = 1
    record.query = "SELECT * FROM users"
    record.execution_time = 0.100
    record.rows_sent = 10
    record.rows_examined = 100
    record.timestamp = datetime.now()
    return record


@pytest.fixture
def mock_record2():
    """创建模拟的性能记录（优化后）"""
    record = Mock()
    record.id = 2
    record.query = "SELECT * FROM users WHERE id > 0"
    record.execution_time = 0.050
    record.rows_sent = 10
    record.rows_examined = 50
    record.timestamp = datetime.now()
    return record


class TestSQLPerformanceComparator:
    """SQL 性能对比器测试"""

    def test_init(self, comparator):
        """测试初始化"""
        assert comparator is not None

    def test_compare_single_metrics(self, comparator):
        """测试对比单个指标"""
        record1 = Mock()
        record1.execution_time = 0.100

        record2 = Mock()
        record2.execution_time = 0.050

        result = comparator._compare_single_metrics(
            record1,
            record2,
            "execution_time"
        )

        assert result["before"] == 0.100
        assert result["after"] == 0.050
        assert result["improvement"] == 50.0  # (0.100 - 0.050) / 0.100 * 100
        assert result["direction"] == "decrease"  # 越小越好

    def test_compare_records(self, comparator, mock_record1, mock_record2):
        """测试对比两条记录"""
        result = comparator.compare_records(mock_record1, mock_record2)

        assert "execution_time" in result
        assert "rows_sent" in result
        assert "rows_examined" in result
        assert "scan_ratio" in result
        assert "overall_improvement" in result

    def test_calculate_improvement(self, comparator):
        """测试计算改进百分比"""
        # 执行时间减少 50%
        improvement = comparator._calculate_improvement(0.100, 0.050)
        assert improvement == 50.0

        # 执行时间增加（负改进）
        improvement = comparator._calculate_improvement(0.050, 0.100)
        assert improvement == -100.0

        # 无变化
        improvement = comparator._calculate_improvement(0.100, 0.100)
        assert improvement == 0.0

    def test_determine_direction(self, comparator):
        """测试确定改进方向"""
        assert comparator._determine_direction("execution_time") == "decrease"
        assert comparator._determine_direction("rows_sent") == "neutral"
        assert comparator._determine_direction("rows_examined") == "decrease"

    def test_calculate_scan_ratio(self, comparator, mock_record1, mock_record2):
        """测试计算扫描比率"""
        ratio1 = comparator._calculate_scan_ratio(mock_record1)
        assert ratio1 == 10.0  # 100 / 10

        ratio2 = comparator._calculate_scan_ratio(mock_record2)
        assert ratio2 == 5.0  # 50 / 10

    def test_calculate_overall_improvement(self, comparator, mock_record1, mock_record2):
        """测试计算总体改进"""
        comparison = comparator.compare_records(mock_record1, mock_record2)
        overall = comparator._calculate_overall_improvement(comparison)

        assert "score" in overall
        assert "rating" in overall
        assert isinstance(overall["score"], float)

    def test_get_rating(self, comparator):
        """测试获取评级"""
        assert comparator._get_rating(80.0) == "优秀"
        assert comparator._get_rating(50.0) == "良好"
        assert comparator._get_rating(20.0) == "一般"
        assert comparator._get_rating(-10.0) == "较差"

    def test_compare_multiple_records(self, comparator):
        """测试对比多条记录"""
        records = [
            Mock(id=i, execution_time=0.100 - i*0.01, rows_sent=10, rows_examined=100)
            for i in range(3)
        ]

        results = comparator.compare_multiple_records(records)

        assert len(results) == 2  # 3条记录，2个对比
        assert all("before" in r for r in results)
        assert all("after" in r for r in results)

    def test_create_comparison_report(self, comparator, mock_record1, mock_record2):
        """测试创建对比报告"""
        comparison = comparator.compare_records(mock_record1, mock_record2)
        report = comparator.create_comparison_report(comparison)

        assert "before" in report
        assert "after" in report
        assert "metrics" in report
        assert "summary" in report
        assert "recommendations" in report

    def test_generate_recommendations(self, comparator, mock_record1, mock_record2):
        """测试生成优化建议"""
        comparison = comparator.compare_records(mock_record1, mock_record2)
        recommendations = comparator._generate_recommendations(comparison)

        assert isinstance(recommendations, list)

    def test_check_scan_ratio_issue(self, comparator):
        """测试检查扫描比率问题"""
        mock_record = Mock()
        mock_record.rows_sent = 10
        mock_record.rows_examined = 1000  # 高扫描比率

        issues = comparator._check_scan_ratio_issue(mock_record)
        assert len(issues) > 0

    def test_check_index_usage(self, comparator):
        """测试检查索引使用"""
        mock_record = Mock()
        mock_record.rows_examined = 1000
        mock_record.rows_sent = 10

        index_issue = comparator._check_index_usage(mock_record)
        assert "suggestion" in index_issue

    @patch('app.services.sql_performance_comparator.SQLPerformanceComparator.compare_records')
    def test_compare_query_before_after(self, mock_compare, comparator, mock_db_session):
        """测试对比查询的优化前后"""
        mock_compare.return_value = {
            "execution_time": {"before": 0.100, "after": 0.050, "improvement": 50.0}
        }

        result = comparator.compare_query_before_after(
            mock_db_session,
            instance_id=1,
            query_id=1,
            before_record_id=1,
            after_record_id=2
        )

        assert mock_compare.called
        assert "comparison" in result

    def test_sort_by_improvement(self, comparator):
        """测试按改进程度排序"""
        comparisons = [
            {"overall_improvement": {"score": 30.0}},
            {"overall_improvement": {"score": 80.0}},
            {"overall_improvement": {"score": 50.0}},
        ]

        sorted_results = comparator.sort_by_improvement(comparisons)

        assert sorted_results[0]["overall_improvement"]["score"] == 80.0
        assert sorted_results[2]["overall_improvement"]["score"] == 30.0

    def test_get_top_improvements(self, comparator):
        """测试获取最佳改进"""
        comparisons = [
            {"overall_improvement": {"score": 30.0}},
            {"overall_improvement": {"score": 80.0}},
            {"overall_improvement": {"score": 50.0}},
        ]

        top_2 = comparator.get_top_improvements(comparisons, limit=2)

        assert len(top_2) == 2
        assert top_2[0]["overall_improvement"]["score"] == 80.0
        assert top_2[1]["overall_improvement"]["score"] == 50.0

    def test_export_comparison_to_dict(self, comparator, mock_record1, mock_record2):
        """测试导出对比结果为字典"""
        comparison = comparator.compare_records(mock_record1, mock_record2)
        exported = comparator.export_comparison_to_dict(comparison)

        assert isinstance(exported, dict)
        assert "metrics" in exported
        assert "overall_improvement" in exported
