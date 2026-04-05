"""
SQL 性能采集服务

执行 SQL 并收集详细的性能指标（EXPLAIN ANALYZE）。
"""
import hashlib
import json
import time
import re
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

from app.models.sql_performance import SQLPerformanceRecord
from app.models import RDBInstance as Instance
from app.services.db_connection import DatabaseConnectionManager


logger = logging.getLogger(__name__)


class SQLPerformanceCollector:
    """SQL 性能采集器
    
    执行 SQL 并收集性能指标，支持多种数据库类型。
    """
    
    def __init__(self, db: Session):
        """
        初始化采集器
        
        Args:
            db: 数据库会话
        """
        self.db = db
        self.connection_manager = DatabaseConnectionManager()
    
    def collect(
        self,
        instance_id: int,
        sql_text: str,
        version: str = "original",
        version_description: str = "",
        user_id: Optional[int] = None
    ) -> SQLPerformanceRecord:
        """采集 SQL 性能数据
        
        Args:
            instance_id: 实例 ID
            sql_text: SQL 语句
            version: 版本标识
            version_description: 版本描述
            user_id: 用户 ID
        
        Returns:
            性能记录对象
        """
        # 获取实例信息
        instance = self.db.query(Instance).filter(Instance.id == instance_id).first()
        if not instance:
            raise ValueError(f"Instance not found: {instance_id}")
        
        # 计算 SQL Hash
        sql_hash = self._calculate_hash(sql_text)
        
        # 执行 EXPLAIN ANALYZE
        explain_result = self._execute_explain_analyze(instance, sql_text)
        
        # 执行 SQL 收集性能
        performance_metrics = self._execute_with_metrics(instance, sql_text)
        
        # 创建记录
        record = SQLPerformanceRecord(
            instance_id=instance_id,
            sql_text=sql_text,
            sql_hash=sql_hash,
            version=version,
            version_description=version_description,
            user_id=user_id,
            **performance_metrics,
            execution_plan=explain_result.get("plan"),
            execution_plan_json=explain_result.get("plan_json")
        )
        
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        
        logger.info(f"SQL performance record created: {record.id}")
        return record
    
    def _calculate_hash(self, sql_text: str) -> str:
        """计算 SQL Hash（去除空格和注释后）"""
        # 标准化 SQL（去除多余空格、注释）
        normalized_sql = re.sub(r'\s+', ' ', sql_text).strip()
        normalized_sql = re.sub(r'--.*?\n', '', normalized_sql)
        normalized_sql = re.sub(r'/\*.*?\*/', '', normalized_sql)
        
        return hashlib.sha256(normalized_sql.encode()).hexdigest()
    
    def _execute_explain_analyze(self, instance: Instance, sql_text: str) -> Dict[str, Any]:
        """执行 EXPLAIN ANALYZE
        
        Args:
            instance: 数据库实例
            sql_text: SQL 语句
        
        Returns:
            执行计划信息
        """
        connection = self.connection_manager.get_connection(instance.id)
        
        try:
            if instance.db_type in ["mysql", "mariadb"]:
                # MySQL: EXPLAIN FORMAT=JSON
                explain_sql = f"EXPLAIN FORMAT=JSON {sql_text}"
                result = connection.execute(text(explain_sql))
                plan = result.fetchone()[0] if result.fetchone() else {}
                
                # EXPLAIN ANALYZE (MySQL 8.0.18+)
                try:
                    analyze_sql = f"EXPLAIN ANALYZE {sql_text}"
                    analyze_result = connection.execute(text(analyze_sql))
                    analyze_rows = analyze_result.fetchall()
                except Exception as e:
                    logger.warning(f"EXPLAIN ANALYZE not supported: {e}")
                    analyze_rows = []
                
                return {
                    "plan": plan,
                    "plan_json": json.dumps(plan, ensure_ascii=False, indent=2),
                    "analyze_rows": [dict(row._mapping) for row in analyze_rows]
                }
            
            elif instance.db_type == "postgresql":
                # PostgreSQL: EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
                explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql_text}"
                result = connection.execute(text(explain_sql))
                plan = result.fetchone()[0]
                
                return {
                    "plan": plan,
                    "plan_json": json.dumps(plan, ensure_ascii=False, indent=2)
                }
            
            else:
                # 其他数据库：普通 EXPLAIN
                explain_sql = f"EXPLAIN {sql_text}"
                result = connection.execute(text(explain_sql))
                rows = result.fetchall()
                
                return {
                    "plan": [dict(row._mapping) for row in rows],
                    "plan_json": json.dumps([dict(row._mapping) for row in rows], ensure_ascii=False, indent=2)
                }
        
        except Exception as e:
            logger.error(f"Failed to execute EXPLAIN: {e}")
            return {
                "plan": {},
                "plan_json": json.dumps({"error": str(e)})
            }
    
    def _execute_with_metrics(self, instance: Instance, sql_text: str) -> Dict[str, Any]:
        """执行 SQL 并收集性能指标
        
        Args:
            instance: 数据库实例
            sql_text: SQL 语句
        
        Returns:
            性能指标
        """
        connection = self.connection_manager.get_connection(instance.id)
        
        metrics = {
            "execution_time_ms": None,
            "rows_scanned": None,
            "rows_returned": None,
            "buffer_pool_reads": None,
            "disk_reads": None,
            "cpu_time_ms": None,
            "io_time_ms": None,
            "memory_mb": None
        }
        
        try:
            # 执行前记录
            start_time = time.time()
            
            # 执行 SQL
            result = connection.execute(text(sql_text))
            rows = result.fetchall()
            
            # 执行后记录
            execution_time = (time.time() - start_time) * 1000  # 毫秒
            
            metrics["execution_time_ms"] = execution_time
            metrics["rows_returned"] = len(rows)
            
            # 从 EXPLAIN 解析扫描行数
            metrics.update(self._parse_explain_metrics(instance, sql_text, connection))
            
            # 获取系统性能指标（如果有权限）
            metrics.update(self._get_system_metrics(instance, connection))
            
        except Exception as e:
            logger.error(f"Failed to execute SQL: {e}")
            metrics["error"] = str(e)
        
        return metrics
    
    def _parse_explain_metrics(self, instance: Instance, sql_text: str, connection) -> Dict[str, Any]:
        """从 EXPLAIN 解析扫描行数
        
        Args:
            instance: 数据库实例
            sql_text: SQL 语句
            connection: 数据库连接
        
        Returns:
            指标
        """
        metrics = {
            "rows_scanned": None,
            "buffer_pool_reads": None,
            "disk_reads": None
        }
        
        try:
            if instance.db_type == "postgresql":
                # 从 EXPLAIN ANALYZE 解析
                explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql_text}"
                result = connection.execute(text(explain_sql))
                plan = result.fetchone()[0]
                
                # 解析 JSON 提取指标
                if isinstance(plan, list) and len(plan) > 0:
                    self._extract_postgres_metrics(plan[0], metrics)
            
            elif instance.db_type in ["mysql", "mariadb"]:
                # MySQL 8.0+ 使用 EXPLAIN FORMAT=JSON
                try:
                    explain_sql = f"EXPLAIN FORMAT=JSON {sql_text}"
                    result = connection.execute(text(explain_sql))
                    plan = result.fetchone()[0]
                    
                    if plan and "query_block" in plan:
                        self._extract_mysql_metrics(plan["query_block"], metrics)
                except Exception as e:
                    logger.warning(f"Failed to parse MySQL EXPLAIN: {e}")
        
        except Exception as e:
            logger.warning(f"Failed to parse EXPLAIN metrics: {e}")
        
        return metrics
    
    def _extract_postgres_metrics(self, plan: Dict, metrics: Dict):
        """提取 PostgreSQL 指标"""
        if "Actual Rows" in plan:
            metrics["rows_scanned"] = (metrics["rows_scanned"] or 0) + plan["Actual Rows"]
        
        if "Shared Hit Blocks" in plan:
            metrics["buffer_pool_reads"] = (metrics["buffer_pool_reads"] or 0) + plan["Shared Hit Blocks"]
        
        if "Shared Read Blocks" in plan:
            metrics["disk_reads"] = (metrics["disk_reads"] or 0) + plan["Shared Read Blocks"]
        
        # 递归处理子计划
        for key in ["Plans", "Subplans"]:
            if key in plan:
                for sub_plan in plan[key]:
                    self._extract_postgres_metrics(sub_plan, metrics)
    
    def _extract_mysql_metrics(self, plan: Dict, metrics: Dict):
        """提取 MySQL 指标"""
        if "rows_examined_per_scan" in plan:
            metrics["rows_scanned"] = (metrics["rows_scanned"] or 0) + plan["rows_examined_per_scan"]
        
        # 递归处理子节点
        if "nested_loop" in plan:
            for child in plan["nested_loop"]:
                if isinstance(child, dict):
                    self._extract_mysql_metrics(child, metrics)
    
    def _get_system_metrics(self, instance: Instance, connection) -> Dict[str, Any]:
        """获取系统性能指标
        
        Args:
            instance: 数据库实例
            connection: 数据库连接
        
        Returns:
            系统指标
        """
        metrics = {
            "cpu_time_ms": None,
            "io_time_ms": None,
            "memory_mb": None
        }
        
        try:
            if instance.db_type == "postgresql":
                # PostgreSQL: pg_stat_statements
                try:
                    result = connection.execute(text("""
                        SELECT 
                            total_exec_time,
                            total_cpu_time,
                            shared_blks_hit,
                            shared_blks_read
                        FROM pg_stat_statements
                        ORDER BY total_exec_time DESC
                        LIMIT 1
                    """))
                    row = result.fetchone()
                    if row:
                        metrics["cpu_time_ms"] = row[1] * 1000 if row[1] else None
                        metrics["io_time_ms"] = (row[0] - row[1]) * 1000 if row[0] and row[1] else None
                except Exception as e:
                    logger.warning(f"pg_stat_statements not available: {e}")
            
            elif instance.db_type in ["mysql", "mariadb"]:
                # MySQL: information_schema.PROCESSLIST
                try:
                    result = connection.execute(text("""
                        SELECT TIME_MS
                        FROM information_schema.PROCESSLIST
                        WHERE INFO IS NOT NULL
                        ORDER BY TIME_MS DESC
                        LIMIT 1
                    """))
                    row = result.fetchone()
                    if row:
                        metrics["cpu_time_ms"] = row[0]
                except Exception as e:
                    logger.warning(f"Failed to get MySQL metrics: {e}")
        
        except Exception as e:
            logger.warning(f"Failed to get system metrics: {e}")
        
        return metrics
    
    def get_record(self, record_id: int) -> Optional[SQLPerformanceRecord]:
        """获取性能记录
        
        Args:
            record_id: 记录 ID
        
        Returns:
            性能记录对象
        """
        return self.db.query(SQLPerformanceRecord).filter(
            SQLPerformanceRecord.id == record_id
        ).first()
    
    def list_records(
        self,
        instance_id: Optional[int] = None,
        sql_hash: Optional[str] = None,
        limit: int = 50
    ) -> List[SQLPerformanceRecord]:
        """列出性能记录
        
        Args:
            instance_id: 实例 ID
            sql_hash: SQL Hash
            limit: 限制数量
        
        Returns:
            性能记录列表
        """
        query = self.db.query(SQLPerformanceRecord)
        
        if instance_id:
            query = query.filter(SQLPerformanceRecord.instance_id == instance_id)
        
        if sql_hash:
            query = query.filter(SQLPerformanceRecord.sql_hash == sql_hash)
        
        return query.order_by(SQLPerformanceRecord.created_at.desc()).limit(limit).all()
