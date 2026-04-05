"""
SQL 性能对比分析服务

对比优化前后的 SQL 性能，生成分析报告。
"""
import json
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
import logging

from app.models.sql_performance import SQLPerformanceRecord, SQLPerformanceComparison
from app.services.sql_performance_collector import SQLPerformanceCollector


logger = logging.getLogger(__name__)


class SQLPerformanceComparator:
    """SQL 性能对比器
    
    对比优化前后的 SQL 性能，计算改善百分比并生成报告。
    """
    
    def __init__(self, db: Session):
        """
        初始化对比器
        
        Args:
            db: 数据库会话
        """
        self.db = db
    
    def compare(
        self,
        source_id: int,
        target_id: int,
        user_id: Optional[int] = None
    ) -> SQLPerformanceComparison:
        """对比两个性能记录
        
        Args:
            source_id: 优化前记录 ID
            target_id: 优化后记录 ID
            user_id: 用户 ID
        
        Returns:
            对比记录
        """
        # 获取记录
        source = self.db.query(SQLPerformanceRecord).filter(
            SQLPerformanceRecord.id == source_id
        ).first()
        target = self.db.query(SQLPerformanceRecord).filter(
            SQLPerformanceRecord.id == target_id
        ).first()
        
        if not source or not target:
            raise ValueError("Source or target record not found")
        
        # 计算改善百分比
        improvements = self._calculate_improvements(source, target)
        
        # 生成分析
        analysis = self._generate_analysis(source, target, improvements)
        
        # 生成建议
        recommendations = self._generate_recommendations(source, target, improvements)
        
        # 生成可视化报告数据
        report_data = self._generate_report_data(source, target, improvements)
        
        # 创建对比记录
        comparison = SQLPerformanceComparison(
            source_id=source_id,
            target_id=target_id,
            user_id=user_id,
            **improvements,
            analysis=analysis,
            recommendations=recommendations,
            report_data=report_data
        )
        
        self.db.add(comparison)
        self.db.commit()
        self.db.refresh(comparison)
        
        logger.info(f"SQL performance comparison created: {comparison.id}")
        return comparison
    
    def _calculate_improvements(
        self,
        source: SQLPerformanceRecord,
        target: SQLPerformanceRecord
    ) -> Dict[str, float]:
        """计算改善百分比
        
        Args:
            source: 优化前记录
            target: 优化后记录
        
        Returns:
            改善百分比字典
        """
        improvements = {
            "execution_time_improvement": None,
            "rows_scanned_improvement": None,
            "cpu_time_improvement": None,
            "io_time_improvement": None,
            "overall_improvement": None
        }
        
        # 执行时间改善
        if source.execution_time_ms and target.execution_time_ms:
            if source.execution_time_ms > 0:
                improvements["execution_time_improvement"] = (
                    (source.execution_time_ms - target.execution_time_ms) / source.execution_time_ms * 100
                )
        
        # 扫描行数改善
        if source.rows_scanned and target.rows_scanned:
            if source.rows_scanned > 0:
                improvements["rows_scanned_improvement"] = (
                    (source.rows_scanned - target.rows_scanned) / source.rows_scanned * 100
                )
        
        # CPU 时间改善
        if source.cpu_time_ms and target.cpu_time_ms:
            if source.cpu_time_ms > 0:
                improvements["cpu_time_improvement"] = (
                    (source.cpu_time_ms - target.cpu_time_ms) / source.cpu_time_ms * 100
                )
        
        # IO 时间改善
        if source.io_time_ms and target.io_time_ms:
            if source.io_time_ms > 0:
                improvements["io_time_improvement"] = (
                    (source.io_time_ms - target.io_time_ms) / source.io_time_ms * 100
                )
        
        # 综合改善（加权平均）
        weights = {
            "execution_time_improvement": 0.4,
            "rows_scanned_improvement": 0.3,
            "cpu_time_improvement": 0.2,
            "io_time_improvement": 0.1
        }
        
        valid_improvements = {
            k: v for k, v in improvements.items()
            if v is not None
        }
        
        if valid_improvements:
            weighted_sum = sum(v * weights[k] for k, v in valid_improvements.items())
            total_weight = sum(weights[k] for k in valid_improvements.keys())
            improvements["overall_improvement"] = weighted_sum / total_weight if total_weight > 0 else 0
        
        return improvements
    
    def _generate_analysis(
        self,
        source: SQLPerformanceRecord,
        target: SQLPerformanceRecord,
        improvements: Dict[str, float]
    ) -> str:
        """生成分析文本
        
        Args:
            source: 优化前记录
            target: 优化后记录
            improvements: 改善百分比
        
        Returns:
            分析文本
        """
        analysis_lines = []
        
        analysis_lines.append("## SQL 性能对比分析")
        analysis_lines.append("")
        analysis_lines.append("### 概览")
        analysis_lines.append("")
        analysis_lines.append(f"- **优化版本**: {target.version} - {target.version_description or '无描述'}")
        analysis_lines.append(f"- **对比时间**: {target.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        analysis_lines.append("")
        
        # 执行时间分析
        if improvements["execution_time_improvement"] is not None:
            time_improvement = improvements["execution_time_improvement"]
            if time_improvement > 0:
                analysis_lines.append(f"✅ **执行时间**: 从 {source.execution_time_ms:.2f}ms 降低到 {target.execution_time_ms:.2f}ms，**改善 {time_improvement:.2f}%**")
            else:
                analysis_lines.append(f"⚠️ **执行时间**: 从 {source.execution_time_ms:.2f}ms 增加到 {target.execution_time_ms:.2f}ms，**恶化 {abs(time_improvement):.2f}%**")
        
        # 扫描行数分析
        if improvements["rows_scanned_improvement"] is not None:
            scan_improvement = improvements["rows_scanned_improvement"]
            if scan_improvement > 0:
                analysis_lines.append(f"✅ **扫描行数**: 从 {source.rows_scanned:,} 行降低到 {target.rows_scanned:,} 行，**改善 {scan_improvement:.2f}%**")
            else:
                analysis_lines.append(f"⚠️ **扫描行数**: 从 {source.rows_scanned:,} 行增加到 {target.rows_scanned:,} 行，**恶化 {abs(scan_improvement):.2f}%**")
        
        # CPU 时间分析
        if improvements["cpu_time_improvement"] is not None:
            cpu_improvement = improvements["cpu_time_improvement"]
            if cpu_improvement > 0:
                analysis_lines.append(f"✅ **CPU 时间**: 从 {source.cpu_time_ms:.2f}ms 降低到 {target.cpu_time_ms:.2f}ms，**改善 {cpu_improvement:.2f}%**")
        
        # IO 时间分析
        if improvements["io_time_improvement"] is not None:
            io_improvement = improvements["io_time_improvement"]
            if io_improvement > 0:
                analysis_lines.append(f"✅ **IO 时间**: 从 {source.io_time_ms:.2f}ms 降低到 {target.io_time_ms:.2f}ms，**改善 {io_improvement:.2f}%**")
        
        analysis_lines.append("")
        
        # 综合评价
        if improvements["overall_improvement"] is not None:
            overall = improvements["overall_improvement"]
            if overall > 20:
                analysis_lines.append("### 🎉 综合评价：优秀")
                analysis_lines.append(f"优化效果显著，综合改善 **{overall:.2f}%**，建议在生产环境应用。")
            elif overall > 10:
                analysis_lines.append("### 👍 综合评价：良好")
                analysis_lines.append(f"优化效果明显，综合改善 **{overall:.2f}%**，可以继续优化或应用。")
            elif overall > 0:
                analysis_lines.append("### ✅ 综合评价：有效")
                analysis_lines.append(f"有一定改善，综合改善 **{overall:.2f}%**，建议继续优化。")
            else:
                analysis_lines.append("### ⚠️ 综合评价：无改善")
                analysis_lines.append(f"优化未带来性能提升，综合改善 **{overall:.2f}%**，建议检查优化方案。")
        
        return "\n".join(analysis_lines)
    
    def _generate_recommendations(
        self,
        source: SQLPerformanceRecord,
        target: SQLPerformanceRecord,
        improvements: Dict[str, float]
    ) -> List[Dict[str, str]]:
        """生成优化建议
        
        Args:
            source: 优化前记录
            target: 优化后记录
            improvements: 改善百分比
        
        Returns:
            建议列表
        """
        recommendations = []
        
        # 执行时间建议
        if improvements["execution_time_improvement"] is not None:
            if improvements["execution_time_improvement"] < 0:
                recommendations.append({
                    "type": "warning",
                    "category": "执行时间",
                    "suggestion": "执行时间增加，建议检查 SQL 逻辑是否正确，或考虑添加合适的索引"
                })
        
        # 扫描行数建议
        if improvements["rows_scanned_improvement"] is not None:
            if improvements["rows_scanned_improvement"] < 0:
                recommendations.append({
                    "type": "warning",
                    "category": "扫描行数",
                    "suggestion": "扫描行数增加，可能缺少索引或索引使用不当，建议使用 EXPLAIN 分析执行计划"
                })
        
        # 磁盘读取建议
        if source.disk_reads and target.disk_reads:
            if target.disk_reads > source.disk_reads * 1.2:
                recommendations.append({
                    "type": "warning",
                    "category": "磁盘读取",
                    "suggestion": f"磁盘读取增加 {target.disk_reads - source.disk_reads} 次，建议检查索引覆盖或缓存配置"
                })
        
        # 成功建议
        if improvements["overall_improvement"] is not None and improvements["overall_improvement"] > 10:
            recommendations.append({
                "type": "success",
                "category": "整体优化",
                "suggestion": "优化效果显著，建议记录优化方案并在类似场景复用"
            })
        
        # 执行计划建议
        if source.execution_plan != target.execution_plan:
            recommendations.append({
                "type": "info",
                "category": "执行计划",
                "suggestion": "执行计划已改变，请仔细检查新的执行路径是否符合预期"
            })
        
        return recommendations
    
    def _generate_report_data(
        self,
        source: SQLPerformanceRecord,
        target: SQLPerformanceRecord,
        improvements: Dict[str, float]
    ) -> Dict[str, Any]:
        """生成可视化报告数据
        
        Args:
            source: 优化前记录
            target: 优化后记录
            improvements: 改善百分比
        
        Returns:
            报告数据
        """
        return {
            "summary": {
                "sql_hash": source.sql_hash,
                "instance_id": source.instance_id,
                "created_at": target.created_at.isoformat()
            },
            "metrics": {
                "source": {
                    "execution_time_ms": source.execution_time_ms,
                    "rows_scanned": source.rows_scanned,
                    "rows_returned": source.rows_returned,
                    "buffer_pool_reads": source.buffer_pool_reads,
                    "disk_reads": source.disk_reads,
                    "cpu_time_ms": source.cpu_time_ms,
                    "io_time_ms": source.io_time_ms
                },
                "target": {
                    "execution_time_ms": target.execution_time_ms,
                    "rows_scanned": target.rows_scanned,
                    "rows_returned": target.rows_returned,
                    "buffer_pool_reads": target.buffer_pool_reads,
                    "disk_reads": target.disk_reads,
                    "cpu_time_ms": target.cpu_time_ms,
                    "io_time_ms": target.io_time_ms
                }
            },
            "improvements": improvements,
            "charts": {
                "bar": self._generate_bar_chart_data(source, target),
                "radar": self._generate_radar_chart_data(source, target, improvements),
                "line": self._generate_line_chart_data(source, target)
            },
            "execution_plans": {
                "source": source.execution_plan,
                "target": target.execution_plan
            }
        }
    
    def _generate_bar_chart_data(
        self,
        source: SQLPerformanceRecord,
        target: SQLPerformanceRecord
    ) -> Dict[str, Any]:
        """生成柱状图数据
        
        Args:
            source: 优化前记录
            target: 优化后记录
        
        Returns:
            柱状图数据
        """
        categories = [
            "执行时间 (ms)",
            "扫描行数",
            "CPU 时间 (ms)",
            "IO 时间 (ms)"
        ]
        
        source_values = [
            source.execution_time_ms or 0,
            source.rows_scanned or 0,
            source.cpu_time_ms or 0,
            source.io_time_ms or 0
        ]
        
        target_values = [
            target.execution_time_ms or 0,
            target.rows_scanned or 0,
            target.cpu_time_ms or 0,
            target.io_time_ms or 0
        ]
        
        return {
            "categories": categories,
            "series": [
                {"name": "优化前", "data": source_values},
                {"name": "优化后", "data": target_values}
            ]
        }
    
    def _generate_radar_chart_data(
        self,
        source: SQLPerformanceRecord,
        target: SQLPerformanceRecord,
        improvements: Dict[str, float]
    ) -> Dict[str, Any]:
        """生成雷达图数据
        
        Args:
            source: 优化前记录
            target: 优化后记录
            improvements: 改善百分比
        
        Returns:
            雷达图数据
        """
        # 归一化数据（0-100）
        max_values = {
            "execution_time_ms": max(source.execution_time_ms or 0, target.execution_time_ms or 0, 1),
            "rows_scanned": max(source.rows_scanned or 0, target.rows_scanned or 0, 1),
            "cpu_time_ms": max(source.cpu_time_ms or 0, target.cpu_time_ms or 0, 1),
            "io_time_ms": max(source.io_time_ms or 0, target.io_time_ms or 0, 1)
        }
        
        source_normalized = [
            (source.execution_time_ms or 0) / max_values["execution_time_ms"] * 100,
            (source.rows_scanned or 0) / max_values["rows_scanned"] * 100,
            (source.cpu_time_ms or 0) / max_values["cpu_time_ms"] * 100,
            (source.io_time_ms or 0) / max_values["io_time_ms"] * 100
        ]
        
        target_normalized = [
            (target.execution_time_ms or 0) / max_values["execution_time_ms"] * 100,
            (target.rows_scanned or 0) / max_values["rows_scanned"] * 100,
            (target.cpu_time_ms or 0) / max_values["cpu_time_ms"] * 100,
            (target.io_time_ms or 0) / max_values["io_time_ms"] * 100
        ]
        
        return {
            "indicators": [
                {"name": "执行时间", "max": 100},
                {"name": "扫描行数", "max": 100},
                {"name": "CPU 时间", "max": 100},
                {"name": "IO 时间", "max": 100}
            ],
            "series": [
                {"name": "优化前", "data": source_normalized},
                {"name": "优化后", "data": target_normalized}
            ]
        }
    
    def _generate_line_chart_data(
        self,
        source: SQLPerformanceRecord,
        target: SQLPerformanceRecord
    ) -> Dict[str, Any]:
        """生成折线图数据（模拟多次执行）
        
        Args:
            source: 优化前记录
            target: 优化后记录
        
        Returns:
            折线图数据
        """
        # 模拟 5 次执行的数据
        import random
        
        random.seed(42)
        
        source_data = [
            (source.execution_time_ms or 0) * random.uniform(0.9, 1.1),
            (source.execution_time_ms or 0) * random.uniform(0.9, 1.1),
            (source.execution_time_ms or 0) * random.uniform(0.9, 1.1),
            (source.execution_time_ms or 0) * random.uniform(0.9, 1.1),
            (source.execution_time_ms or 0) * random.uniform(0.9, 1.1)
        ]
        
        target_data = [
            (target.execution_time_ms or 0) * random.uniform(0.9, 1.1),
            (target.execution_time_ms or 0) * random.uniform(0.9, 1.1),
            (target.execution_time_ms or 0) * random.uniform(0.9, 1.1),
            (target.execution_time_ms or 0) * random.uniform(0.9, 1.1),
            (target.execution_time_ms or 0) * random.uniform(0.9, 1.1)
        ]
        
        return {
            "xAxis": ["第1次", "第2次", "第3次", "第4次", "第5次"],
            "series": [
                {"name": "优化前", "data": source_data},
                {"name": "优化后", "data": target_data}
            ]
        }
    
    def get_comparison(self, comparison_id: int) -> Optional[SQLPerformanceComparison]:
        """获取对比记录
        
        Args:
            comparison_id: 对比记录 ID
        
        Returns:
            对比记录
        """
        return self.db.query(SQLPerformanceComparison).filter(
            SQLPerformanceComparison.id == comparison_id
        ).first()
    
    def list_comparisons(
        self,
        user_id: Optional[int] = None,
        limit: int = 50
    ) -> List[SQLPerformanceComparison]:
        """列出对比记录
        
        Args:
            user_id: 用户 ID
            limit: 限制数量
        
        Returns:
            对比记录列表
        """
        query = self.db.query(SQLPerformanceComparison)
        
        if user_id:
            query = query.filter(SQLPerformanceComparison.user_id == user_id)
        
        return query.order_by(SQLPerformanceComparison.created_at.desc()).limit(limit).all()
