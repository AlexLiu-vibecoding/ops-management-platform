"""
性能报告生成服务

生成 HTML 和 PDF 格式的性能对比报告。
"""
from typing import Dict, Any
import json
import logging

from app.models.sql_performance import SQLPerformanceComparison


logger = logging.getLogger(__name__)


class ReportGenerator:
    """报告生成器
    
    生成 HTML 和 PDF 格式的 SQL 性能对比报告。
    """
    
    def __init__(self):
        """初始化报告生成器"""
        pass
    
    def generate_html_report(self, comparison: SQLPerformanceComparison) -> str:
        """生成 HTML 报告
        
        Args:
            comparison: 对比记录
        
        Returns:
            HTML 报告字符串
        """
        report_data = comparison.report_data or {}
        improvements = {
            "execution_time_improvement": comparison.execution_time_improvement,
            "rows_scanned_improvement": comparison.rows_scanned_improvement,
            "cpu_time_improvement": comparison.cpu_time_improvement,
            "io_time_improvement": comparison.io_time_improvement,
            "overall_improvement": comparison.overall_improvement
        }
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SQL 性能对比报告 - {comparison.id}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 40px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 2px solid #409eff;
        }}
        .header h1 {{
            color: #333;
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .header .meta {{
            color: #666;
            font-size: 14px;
        }}
        .summary {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .summary h2 {{
            font-size: 24px;
            margin-bottom: 20px;
        }}
        .summary .improvement {{
            font-size: 48px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .summary .description {{
            font-size: 16px;
            opacity: 0.9;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #409eff;
        }}
        .metric-card h3 {{
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }}
        .metric-card .value {{
            font-size: 28px;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}
        .metric-card .improvement {{
            font-size: 14px;
        }}
        .metric-card .improvement.positive {{
            color: #67c23a;
        }}
        .metric-card .improvement.negative {{
            color: #f56c6c;
        }}
        .charts {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
            margin-bottom: 30px;
        }}
        .chart-container {{
            background: #f9f9f9;
            padding: 20px;
            border-radius: 8px;
        }}
        .chart-container h3 {{
            color: #333;
            font-size: 18px;
            margin-bottom: 20px;
            padding-left: 10px;
            border-left: 4px solid #409eff;
        }}
        .chart {{
            width: 100%;
            height: 400px;
        }}
        .analysis {{
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 30px;
            margin-bottom: 30px;
        }}
        .analysis h2 {{
            color: #333;
            font-size: 24px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .analysis .content {{
            white-space: pre-wrap;
            color: #555;
            line-height: 1.8;
        }}
        .recommendations {{
            background: #fff;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 30px;
        }}
        .recommendations h2 {{
            color: #333;
            font-size: 24px;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .recommendation-item {{
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 4px;
            border-left: 4px solid #409eff;
            background: #f9f9f9;
        }}
        .recommendation-item.success {{
            border-left-color: #67c23a;
            background: #f0f9ff;
        }}
        .recommendation-item.warning {{
            border-left-color: #e6a23c;
            background: #fdf6ec;
        }}
        .recommendation-item.info {{
            border-left-color: #909399;
            background: #f4f4f5;
        }}
        .recommendation-item .category {{
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }}
        .recommendation-item .suggestion {{
            color: #666;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            color: #999;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 SQL 性能对比报告</h1>
            <div class="meta">
                对比 ID: {comparison.id} | 
                生成时间: {comparison.created_at.strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>

        {self._generate_summary_section(improvements)}

        {self._generate_metrics_section(report_data, improvements)}

        <div class="charts">
            <div class="chart-container">
                <h3>📈 性能指标对比（柱状图）</h3>
                <div id="barChart" class="chart"></div>
            </div>
            <div class="chart-container">
                <h3>🎯 综合性能评估（雷达图）</h3>
                <div id="radarChart" class="chart"></div>
            </div>
        </div>

        {self._generate_analysis_section(comparison.analysis)}

        {self._generate_recommendations_section(comparison.recommendations)}

        <div class="footer">
            <p>本报告由 OpsCenter 自动生成 | 仅供参考</p>
        </div>
    </div>

    <script>
        // 柱状图
        const barData = {json.dumps(report_data.get('charts', {}).get('bar', {}), ensure_ascii=False)};
        const barChart = echarts.init(document.getElementById('barChart'));
        barChart.setOption({{
            title: {{
                text: '',
                left: 'center'
            }},
            tooltip: {{
                trigger: 'axis',
                axisPointer: {{
                    type: 'shadow'
                }}
            }},
            legend: {{
                data: barData.series.map(s => s.name),
                top: 10
            }},
            grid: {{
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            }},
            xAxis: {{
                type: 'category',
                data: barData.categories,
                axisLabel: {{
                    rotate: 0
                }}
            }},
            yAxis: {{
                type: 'value',
                name: '数值'
            }},
            series: barData.series.map(s => ({{
                name: s.name,
                type: 'bar',
                data: s.data,
                barWidth: '40%',
                itemStyle: {{
                    color: function(params) {{
                        return params.seriesName === '优化前' ? '#ff6b6b' : '#51cf66';
                    }}
                }}
            }}))
        }});

        // 雷达图
        const radarData = {json.dumps(report_data.get('charts', {}).get('radar', {}), ensure_ascii=False)};
        const radarChart = echarts.init(document.getElementById('radarChart'));
        radarChart.setOption({{
            title: {{
                text: '',
                left: 'center'
            }},
            legend: {{
                data: radarData.series.map(s => s.name),
                top: 10
            }},
            radar: {{
                indicator: radarData.indicators,
                center: ['50%', '55%'],
                radius: '70%'
            }},
            series: [{{
                type: 'radar',
                data: radarData.series.map(s => ({{
                    value: s.data,
                    name: s.name,
                    areaStyle: {{
                        opacity: 0.3
                    }}
                }}))
            }}]
        }});

        // 响应式
        window.addEventListener('resize', function() {{
            barChart.resize();
            radarChart.resize();
        }});
    </script>
</body>
</html>
"""
        return html
    
    def _generate_summary_section(self, improvements: Dict[str, float]) -> str:
        """生成摘要部分"""
        overall = improvements.get("overall_improvement", 0)
        
        if overall > 20:
            emoji = "🎉"
            description = "优化效果显著，建议在生产环境应用！"
        elif overall > 10:
            emoji = "👍"
            description = "优化效果明显，可以继续优化或应用。"
        elif overall > 0:
            emoji = "✅"
            description = "有一定改善，建议继续优化。"
        else:
            emoji = "⚠️"
            description = "优化未带来性能提升，建议检查优化方案。"
        
        return f"""
        <div class="summary">
            <h2>{emoji} 综合性能评价</h2>
            <div class="improvement">{overall:.2f}%</div>
            <div class="description">{description}</div>
        </div>
        """
    
    def _generate_metrics_section(self, report_data: Dict[str, Any], improvements: Dict[str, float]) -> str:
        """生成指标部分"""
        metrics = report_data.get("metrics", {})
        source = metrics.get("source", {})
        target = metrics.get("target", {})
        
        cards = []
        
        # 执行时间
        exec_time_imp = improvements.get("execution_time_improvement")
        if exec_time_imp is not None:
            cards.append(self._generate_metric_card(
                "执行时间",
                f"{target.get('execution_time_ms', 0):.2f} ms",
                exec_time_imp,
                f"优化前: {source.get('execution_time_ms', 0):.2f} ms"
            ))
        
        # 扫描行数
        scan_imp = improvements.get("rows_scanned_improvement")
        if scan_imp is not None:
            cards.append(self._generate_metric_card(
                "扫描行数",
                f"{target.get('rows_scanned', 0):,} 行",
                scan_imp,
                f"优化前: {source.get('rows_scanned', 0):,} 行"
            ))
        
        # CPU 时间
        cpu_imp = improvements.get("cpu_time_improvement")
        if cpu_imp is not None:
            cards.append(self._generate_metric_card(
                "CPU 时间",
                f"{target.get('cpu_time_ms', 0):.2f} ms",
                cpu_imp,
                f"优化前: {source.get('cpu_time_ms', 0):.2f} ms"
            ))
        
        # IO 时间
        io_imp = improvements.get("io_time_improvement")
        if io_imp is not None:
            cards.append(self._generate_metric_card(
                "IO 时间",
                f"{target.get('io_time_ms', 0):.2f} ms",
                io_imp,
                f"优化前: {source.get('io_time_ms', 0):.2f} ms"
            ))
        
        return f"""
        <div class="metrics">
            {"".join(cards)}
        </div>
        """
    
    def _generate_metric_card(self, title: str, value: str, improvement: float, subtitle: str) -> str:
        """生成指标卡片"""
        improvement_class = "positive" if improvement > 0 else "negative"
        improvement_text = f"改善 {improvement:.2f}%" if improvement > 0 else f"恶化 {abs(improvement):.2f}%"
        
        return f"""
        <div class="metric-card">
            <h3>{title}</h3>
            <div class="value">{value}</div>
            <div class="improvement {improvement_class}">{improvement_text}</div>
            <div style="color: #999; font-size: 12px; margin-top: 5px;">{subtitle}</div>
        </div>
        """
    
    def _generate_analysis_section(self, analysis: str) -> str:
        """生成分析部分"""
        return f"""
        <div class="analysis">
            <h2>📝 详细分析</h2>
            <div class="content">{analysis}</div>
        </div>
        """
    
    def _generate_recommendations_section(self, recommendations: list) -> str:
        """生成建议部分"""
        if not recommendations:
            return ""
        
        items = []
        for rec in recommendations:
            item_type = rec.get("type", "info")
            category = rec.get("category", "")
            suggestion = rec.get("suggestion", "")
            
            items.append(f"""
            <div class="recommendation-item {item_type}">
                <div class="category">{category}</div>
                <div class="suggestion">{suggestion}</div>
            </div>
            """)
        
        return f"""
        <div class="recommendations">
            <h2>💡 优化建议</h2>
            {"".join(items)}
        </div>
        """
    
    def generate_pdf_report(self, comparison: SQLPerformanceComparison) -> str:
        """生成 PDF 报告
        
        注意：需要安装 weasyprint 库
        pip install weasyprint
        
        Args:
            comparison: 对比记录
        
        Returns:
            PDF 报告 base64 字符串
        """
        try:
            from weasyprint import HTML
            import base64
            
            # 生成 HTML 报告
            html_report = self.generate_html_report(comparison)
            
            # 转换为 PDF
            pdf_bytes = HTML(string=html_report).write_pdf()
            
            # 转换为 base64
            pdf_base64 = base64.b64encode(pdf_bytes).decode()
            
            return pdf_base64
        except ImportError:
            logger.warning("weasyprint not installed, returning HTML instead")
            html_report = self.generate_html_report(comparison)
            return html_report
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise
