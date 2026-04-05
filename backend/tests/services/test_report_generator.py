"""
报告生成器单元测试

使用 mock 测试报告生成器的核心功能，避免依赖真实的文件系统或外部服务。
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json

from app.services.report_generator import ReportGenerator


@pytest.fixture
def mock_comparison_data():
    """创建模拟的对比数据"""
    return {
        "before": {
            "query": "SELECT * FROM users",
            "execution_time": 0.100,
            "rows_sent": 10,
            "rows_examined": 100
        },
        "after": {
            "query": "SELECT * FROM users WHERE id > 0",
            "execution_time": 0.050,
            "rows_sent": 10,
            "rows_examined": 50
        },
        "metrics": {
            "execution_time": {
                "before": 0.100,
                "after": 0.050,
                "improvement": 50.0,
                "direction": "decrease"
            },
            "rows_examined": {
                "before": 100,
                "after": 50,
                "improvement": 50.0,
                "direction": "decrease"
            }
        },
        "overall_improvement": {
            "score": 50.0,
            "rating": "良好"
        }
    }


@pytest.fixture
def generator():
    """创建报告生成器实例"""
    return ReportGenerator()


class TestReportGenerator:
    """报告生成器测试"""

    def test_init(self, generator):
        """测试初始化"""
        assert generator is not None

    def test_generate_html_report(self, generator, mock_comparison_data):
        """测试生成 HTML 报告"""
        html = generator.generate_html_report(
            mock_comparison_data,
            title="SQL 性能对比报告"
        )

        assert isinstance(html, str)
        assert "<html" in html
        assert "</html>" in html
        assert "SQL 性能对比报告" in html

    def test_generate_html_report_with_timestamp(self, generator, mock_comparison_data):
        """测试生成带时间戳的 HTML 报告"""
        timestamp = datetime.now().isoformat()
        html = generator.generate_html_report(
            mock_comparison_data,
            title="SQL 性能对比报告",
            timestamp=timestamp
        )

        assert timestamp in html

    def test_generate_html_report_section_header(self, generator, mock_comparison_data):
        """测试生成报告头部"""
        html = generator.generate_html_report(
            mock_comparison_data,
            title="SQL 性能对比报告"
        )

        assert "<h1>" in html
        assert "执行时间对比" in html or "execution_time" in html

    def test_generate_html_report_metrics_table(self, generator, mock_comparison_data):
        """测试生成指标表格"""
        html = generator.generate_html_report(
            mock_comparison_data,
            title="SQL 性能对比报告"
        )

        assert "<table" in html
        assert "50.0" in html  # 改进百分比

    def test_generate_json_report(self, generator, mock_comparison_data):
        """测试生成 JSON 报告"""
        json_str = generator.generate_json_report(
            mock_comparison_data,
            title="SQL 性能对比报告"
        )

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["title"] == "SQL 性能对比报告"
        assert "metrics" in data
        assert "overall_improvement" in data

    def test_generate_summary_text(self, generator, mock_comparison_data):
        """测试生成摘要文本"""
        summary = generator.generate_summary_text(mock_comparison_data)

        assert isinstance(summary, str)
        assert "改进" in summary or "improvement" in summary
        assert "50.0" in summary

    def test_format_percentage(self, generator):
        """测试格式化百分比"""
        formatted = generator._format_percentage(50.0)
        assert formatted == "50.00%"

        formatted = generator._format_percentage(-10.5)
        assert formatted == "-10.50%"

    def test_format_time(self, generator):
        """测试格式化时间"""
        formatted = generator._format_time(0.12345)
        assert "0.123" in formatted or "123" in formatted

    def test_determine_rating_color(self, generator):
        """测试确定评级颜色"""
        color = generator._determine_rating_color("优秀")
        assert color == "#52C41A"  # 绿色

        color = generator._determine_rating_color("良好")
        assert color == "#1890FF"  # 蓝色

        color = generator._determine_rating_color("一般")
        assert color == "#FAAD14"  # 黄色

        color = generator._determine_rating_color("较差")
        assert color == "#FF4D4F"  # 红色

    def test_create_chart_placeholder(self, generator):
        """测试创建图表占位符"""
        chart_html = generator._create_chart_placeholder(
            "执行时间对比",
            {"before": 0.100, "after": 0.050}
        )

        assert "<div" in chart_html
        assert "执行时间对比" in chart_html

    @patch('builtins.open', create=True)
    def test_save_html_report(self, mock_open, generator, mock_comparison_data):
        """测试保存 HTML 报告"""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        html_content = generator.generate_html_report(
            mock_comparison_data,
            title="SQL 性能对比报告"
        )

        generator.save_report(html_content, "/tmp/test_report.html")

        mock_open.assert_called_once_with("/tmp/test_report.html", "w", encoding="utf-8")
        mock_file.write.assert_called_once()

    @patch('builtins.open', create=True)
    def test_save_json_report(self, mock_open, generator, mock_comparison_data):
        """测试保存 JSON 报告"""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        json_content = generator.generate_json_report(
            mock_comparison_data,
            title="SQL 性能对比报告"
        )

        generator.save_report(json_content, "/tmp/test_report.json")

        mock_open.assert_called_once_with("/tmp/test_report.json", "w", encoding="utf-8")
        mock_file.write.assert_called_once()

    def test_generate_multiple_comparisons_report(self, generator, mock_comparison_data):
        """测试生成多个对比的报告"""
        comparisons = [mock_comparison_data, mock_comparison_data]

        html = generator.generate_multiple_comparisons_report(
            comparisons,
            title="SQL 性能对比报告集合"
        )

        assert "<html" in html
        assert "SQL 性能对比报告集合" in html

    def test_add_recommendations_section(self, generator):
        """测试添加建议部分"""
        recommendations = [
            "建议 1: 添加索引",
            "建议 2: 优化查询条件"
        ]

        html = generator._add_recommendations_section(recommendations)

        assert "建议 1" in html
        assert "建议 2" in html

    def test_generate_performance_trend_html(self, generator):
        """测试生成性能趋势图 HTML"""
        trend_data = [
            {"timestamp": "2024-01-01", "execution_time": 0.100},
            {"timestamp": "2024-01-02", "execution_time": 0.080},
            {"timestamp": "2024-01-03", "execution_time": 0.050}
        ]

        html = generator._generate_performance_trend_html(trend_data)

        assert "<div" in html
        assert "趋势" in html or "trend" in html

    def test_validate_comparison_data(self, generator):
        """测试验证对比数据"""
        valid_data = {
            "before": {"execution_time": 0.100},
            "after": {"execution_time": 0.050},
            "metrics": {}
        }

        assert generator._validate_comparison_data(valid_data) is True

        invalid_data = {}
        assert generator._validate_comparison_data(invalid_data) is False

    def test_extract_key_metrics(self, generator, mock_comparison_data):
        """测试提取关键指标"""
        metrics = generator._extract_key_metrics(mock_comparison_data)

        assert "execution_time" in metrics
        assert "rows_sent" in metrics
        assert "rows_examined" in metrics

    def test_generate_improvement_badge(self, generator):
        """测试生成改进徽章"""
        badge = generator._generate_improvement_badge(50.0, "decrease")

        assert "50.00%" in badge
        assert "decrease" in badge or "green" in badge

    @patch('app.services.report_generator.ReportGenerator.generate_html_report')
    def test_create_comparison_with_custom_styles(self, mock_generate, generator, mock_comparison_data):
        """测试创建带自定义样式的对比报告"""
        mock_generate.return_value = "<html>test</html>"

        custom_styles = {
            "primary_color": "#1890FF",
            "secondary_color": "#52C41A"
        }

        result = generator.create_comparison_with_custom_styles(
            mock_comparison_data,
            title="SQL 性能对比报告",
            styles=custom_styles
        )

        assert mock_generate.called
