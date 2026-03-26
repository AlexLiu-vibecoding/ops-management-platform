"""
慢查询采集服务

从数据库实例采集慢查询数据：
- performance_schema 采集
- sys.statement_analysis 采集
- 性能模式检查
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import text, create_engine

from app.models import RDBInstance
from app.utils.auth import aes_cipher

logger = logging.getLogger(__name__)


class SlowQueryCollector:
    """慢查询采集器"""

    async def fetch_from_performance_schema(
        self,
        instance: RDBInstance,
        limit: int = 100,
        min_exec_time: float = 1.0,
        database_name: Optional[str] = None
    ) -> list[dict]:
        """
        从 performance_schema.events_statements_summary_by_digest 抓取慢查询

        Args:
            instance: 数据库实例
            limit: 返回记录数限制
            min_exec_time: 最小执行时间（秒）
            database_name: 过滤特定数据库

        Returns:
            慢查询列表
        """
        engine = None
        try:
            if instance.db_type != "mysql":
                raise ValueError("仅支持 MySQL 实例")

            # 构建连接字符串
            password = aes_cipher.decrypt(instance.password_encrypted)
            connection_url = f"mysql+pymysql://{instance.username}:{password}@{instance.host}:{instance.port}/performance_schema"

            engine = create_engine(connection_url, connect_args={"connect_timeout": 10})

            # 查询 events_statements_summary_by_digest
            query = text("""
                SELECT
                    DIGEST_TEXT as digest_text,
                    DIGEST as digest,
                    SCHEMA_NAME as schema_name,
                    COUNT_STAR as exec_count,
                    SUM_TIMER_WAIT/1000000000000 as total_exec_time_sec,
                    AVG_TIMER_WAIT/1000000000000 as avg_exec_time_sec,
                    MAX_TIMER_WAIT/1000000000000 as max_exec_time_sec,
                    MIN_TIMER_WAIT/1000000000000 as min_exec_time_sec,
                    SUM_ROWS_EXAMINED as rows_examined,
                    SUM_ROWS_SENT as rows_sent,
                    SUM_ROWS_AFFECTED as rows_affected,
                    SUM_CREATED_TMP_TABLES as created_tmp_tables,
                    SUM_CREATED_TMP_DISK_TABLES as created_tmp_disk_tables,
                    SUM_SELECT_SCAN as select_scan,
                    SUM_SELECT_FULL_JOIN as select_full_join,
                    SUM_NO_INDEX_USED as no_index_used,
                    SUM_NO_GOOD_INDEX_USED as no_good_index_used,
                    FIRST_SEEN as first_seen,
                    LAST_SEEN as last_seen,
                    QUERY_SAMPLE_TEXT as sample_query,
                    QUERY_SAMPLE_SEEN as sample_seen,
                    QUERY_SAMPLE_TIMER_WAIT/1000000000000 as sample_exec_time_sec
                FROM events_statements_summary_by_digest
                WHERE DIGEST_TEXT IS NOT NULL
                AND AVG_TIMER_WAIT/1000000000000 >= :min_exec_time
            """)

            params = {"min_exec_time": min_exec_time}

            if database_name:
                query = text(str(query) + " AND SCHEMA_NAME = :db_name")
                params["db_name"] = database_name

            query = text(str(query) + " ORDER BY SUM_TIMER_WAIT DESC LIMIT :limit")
            params["limit"] = limit

            with engine.connect() as conn:
                result = conn.execute(query, params)
                rows = result.fetchall()

            return [self._parse_performance_schema_row(row) for row in rows]

        except Exception as e:
            logger.error(f"从 performance_schema 抓取慢查询失败: {str(e)}")
            raise
        finally:
            if engine:
                engine.dispose()

    def _parse_performance_schema_row(self, row) -> dict:
        """解析 performance_schema 行数据"""
        return {
            "digest_text": row.digest_text,
            "digest": row.digest,
            "schema_name": row.schema_name,
            "exec_count": row.exec_count,
            "total_exec_time_sec": float(row.total_exec_time_sec) if row.total_exec_time_sec else 0,
            "avg_exec_time_sec": float(row.avg_exec_time_sec) if row.avg_exec_time_sec else 0,
            "max_exec_time_sec": float(row.max_exec_time_sec) if row.max_exec_time_sec else 0,
            "min_exec_time_sec": float(row.min_exec_time_sec) if row.min_exec_time_sec else 0,
            "rows_examined": row.rows_examined or 0,
            "rows_sent": row.rows_sent or 0,
            "rows_affected": row.rows_affected or 0,
            "created_tmp_tables": row.created_tmp_tables or 0,
            "created_tmp_disk_tables": row.created_tmp_disk_tables or 0,
            "select_scan": row.select_scan or 0,
            "select_full_join": row.select_full_join or 0,
            "no_index_used": row.no_index_used or 0,
            "no_good_index_used": row.no_good_index_used or 0,
            "first_seen": row.first_seen.isoformat() if row.first_seen else None,
            "last_seen": row.last_seen.isoformat() if row.last_seen else None,
            "sample_query": row.sample_query,
            "sample_seen": row.sample_seen.isoformat() if row.sample_seen else None,
            "sample_exec_time_sec": float(row.sample_exec_time_sec) if row.sample_exec_time_sec else 0
        }

    async def fetch_from_statement_analysis(
        self,
        instance: RDBInstance,
        limit: int = 100,
        database_name: Optional[str] = None
    ) -> list[dict]:
        """
        从 sys.statement_analysis 获取分析数据

        Args:
            instance: 数据库实例
            limit: 返回记录数限制
            database_name: 过滤特定数据库

        Returns:
            语句分析列表
        """
        engine = None
        try:
            if instance.db_type != "mysql":
                raise ValueError("仅支持 MySQL 实例")

            # 构建连接字符串
            password = aes_cipher.decrypt(instance.password_encrypted)
            connection_url = f"mysql+pymysql://{instance.username}:{password}@{instance.host}:{instance.port}/sys"

            engine = create_engine(connection_url, connect_args={"connect_timeout": 10})

            # 检查 sys.statement_analysis 是否存在
            if not await self._check_statement_analysis_exists(engine):
                logger.warning("sys.statement_analysis 视图不存在")
                return []

            # 查询 statement_analysis
            query = text("""
                SELECT
                    query as query_text,
                    db as schema_name,
                    full_scan,
                    exec_count,
                    err_count,
                    warn_count,
                    total_latency_sec,
                    max_latency_sec,
                    avg_latency_sec,
                    lock_latency_sec,
                    rows_sent,
                    rows_sent_avg,
                    rows_examined,
                    rows_examined_avg,
                    rows_affected,
                    rows_affected_avg,
                    tmp_tables,
                    tmp_disk_tables,
                    rows_sorted,
                    sort_merge_passes,
                    digest,
                    first_seen,
                    last_seen
                FROM statement_analysis
                WHERE 1=1
            """)

            params = {}

            if database_name:
                query = text(str(query) + " AND db = :db_name")
                params["db_name"] = database_name

            query = text(str(query) + " ORDER BY total_latency_sec DESC LIMIT :limit")
            params["limit"] = limit

            with engine.connect() as conn:
                result = conn.execute(query, params)
                rows = result.fetchall()

            return [self._parse_statement_analysis_row(row) for row in rows]

        except Exception as e:
            logger.error(f"从 sys.statement_analysis 获取数据失败: {str(e)}")
            raise
        finally:
            if engine:
                engine.dispose()

    async def _check_statement_analysis_exists(self, engine) -> bool:
        """检查 sys.statement_analysis 视图是否存在"""
        check_query = text("""
            SELECT COUNT(*) FROM information_schema.VIEWS
            WHERE TABLE_SCHEMA = 'sys' AND TABLE_NAME = 'statement_analysis'
        """)

        with engine.connect() as conn:
            result = conn.execute(check_query)
            return result.scalar() > 0

    def _parse_statement_analysis_row(self, row) -> dict:
        """解析 statement_analysis 行数据"""
        return {
            "query_text": row.query_text,
            "schema_name": row.schema_name,
            "full_scan": row.full_scan == "*",
            "exec_count": row.exec_count or 0,
            "err_count": row.err_count or 0,
            "warn_count": row.warn_count or 0,
            "total_latency_sec": float(row.total_latency_sec) if row.total_latency_sec else 0,
            "max_latency_sec": float(row.max_latency_sec) if row.max_latency_sec else 0,
            "avg_latency_sec": float(row.avg_latency_sec) if row.avg_latency_sec else 0,
            "lock_latency_sec": float(row.lock_latency_sec) if row.lock_latency_sec else 0,
            "rows_sent": row.rows_sent or 0,
            "rows_sent_avg": row.rows_sent_avg or 0,
            "rows_examined": row.rows_examined or 0,
            "rows_examined_avg": row.rows_examined_avg or 0,
            "rows_affected": row.rows_affected or 0,
            "rows_affected_avg": row.rows_affected_avg or 0,
            "tmp_tables": row.tmp_tables or 0,
            "tmp_disk_tables": row.tmp_disk_tables or 0,
            "rows_sorted": row.rows_sorted or 0,
            "sort_merge_passes": row.sort_merge_passes or 0,
            "digest": row.digest,
            "first_seen": row.first_seen.isoformat() if row.first_seen else None,
            "last_seen": row.last_seen.isoformat() if row.last_seen else None
        }

    async def check_performance_schema_enabled(self, instance: RDBInstance) -> dict:
        """
        检查 performance_schema 是否启用

        Args:
            instance: 数据库实例

        Returns:
            包含启用状态和配置的字典
        """
        engine = None
        try:
            if instance.db_type != "mysql":
                return {
                    "enabled": False,
                    "message": "仅支持 MySQL 实例"
                }

            password = aes_cipher.decrypt(instance.password_encrypted)
            connection_url = f"mysql+pymysql://{instance.username}:{password}@{instance.host}:{instance.port}/information_schema"

            engine = create_engine(connection_url, connect_args={"connect_timeout": 10})

            with engine.connect() as conn:
                # 检查 performance_schema 是否启用
                result = conn.execute(text("SHOW VARIABLES LIKE 'performance_schema'"))
                perf_schema_var = result.fetchone()

                if not perf_schema_var or perf_schema_var[1] != 'ON':
                    return {
                        "enabled": False,
                        "message": "performance_schema 未启用，请在 RDS 参数组中开启"
                    }

                # 检查 consumers 是否启用
                result = conn.execute(text("""
                    SELECT NAME, ENABLED
                    FROM performance_schema.setup_consumers
                    WHERE NAME IN ('events_statements_current', 'events_statements_history', 'events_statements_history_long')
                """))
                consumers = {row[0]: row[1] for row in result.fetchall()}

                # 检查 instruments 是否启用
                result = conn.execute(text("""
                    SELECT COUNT(*) as total,
                           SUM(CASE WHEN ENABLED = 'YES' THEN 1 ELSE 0 END) as enabled_count
                    FROM performance_schema.setup_instruments
                    WHERE NAME LIKE 'statement/%'
                """))
                instruments = result.fetchone()

                return {
                    "enabled": True,
                    "consumers": consumers,
                    "instruments": {
                        "total": instruments[0],
                        "enabled": instruments[1]
                    },
                    "message": "performance_schema 已启用"
                }

        except Exception as e:
            logger.error(f"检查 performance_schema 状态失败: {e}")
            return {
                "enabled": False,
                "message": f"检查失败: {str(e)}"
            }
        finally:
            if engine:
                engine.dispose()

    async def get_instance_databases(
        self,
        instance: RDBInstance
    ) -> list[str]:
        """
        获取实例的数据库列表

        Args:
            instance: 数据库实例

        Returns:
            数据库名称列表
        """
        engine = None
        try:
            password = aes_cipher.decrypt(instance.password_encrypted)
            connection_url = f"mysql+pymysql://{instance.username}:{password}@{instance.host}:{instance.port}/"

            engine = create_engine(connection_url, connect_args={"connect_timeout": 10})

            with engine.connect() as conn:
                result = conn.execute(text("SHOW DATABASES"))
                return [row[0] for row in result.fetchall()]

        except Exception as e:
            logger.error(f"获取数据库列表失败: {e}")
            return []
        finally:
            if engine:
                engine.dispose()

    async def sync_slow_queries_to_db(
        self,
        instance: RDBInstance,
        db_session,
        limit: int = 100
    ) -> dict[str, Any]:
        """
        从 performance_schema 同步慢查询到本地数据库

        Args:
            instance: 数据库实例
            db_session: 数据库会话
            limit: 同步记录数限制

        Returns:
            同步结果
        """
        from app.models import SlowQuery

        try:
            # 获取慢查询数据
            slow_queries = await self.fetch_from_performance_schema(instance, limit=limit)

            synced_count = 0
            skipped_count = 0

            for sq_data in slow_queries:
                # 检查是否已存在
                existing = db_session.query(SlowQuery).filter(
                    SlowQuery.instance_id == instance.id,
                    SlowQuery.sql_fingerprint == sq_data["digest_text"]
                ).first()

                if existing:
                    # 更新现有记录
                    existing.execution_count = sq_data["exec_count"]
                    existing.query_time = sq_data["avg_exec_time_sec"]
                    existing.rows_examined = sq_data["rows_examined"]
                    existing.rows_sent = sq_data["rows_sent"]
                    existing.last_seen = datetime.now()
                    skipped_count += 1
                else:
                    # 创建新记录
                    new_query = SlowQuery(
                        instance_id=instance.id,
                        sql_fingerprint=sq_data["digest_text"],
                        sql_sample=sq_data["sample_query"],
                        database_name=sq_data["schema_name"],
                        query_time=sq_data["avg_exec_time_sec"],
                        lock_time=0,
                        rows_sent=sq_data["rows_sent"],
                        rows_examined=sq_data["rows_examined"],
                        execution_count=sq_data["exec_count"],
                        first_seen=datetime.now(),
                        last_seen=datetime.now()
                    )
                    db_session.add(new_query)
                    synced_count += 1

            db_session.commit()

            return {
                "success": True,
                "synced": synced_count,
                "skipped": skipped_count,
                "total": len(slow_queries)
            }

        except Exception as e:
            logger.error(f"同步慢查询失败: {e}")
            db_session.rollback()
            return {
                "success": False,
                "error": str(e)
            }


# 单例实例
slow_query_collector = SlowQueryCollector()
