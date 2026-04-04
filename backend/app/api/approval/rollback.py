"""
变更审批API - 回滚生成
"""
import logging
from typing import Optional

from app.models import RDBInstance, RedisInstance
from app.services.enhanced_rollback_generator import EnhancedRollbackGenerator
from .helpers import get_rdb_connection, get_redis_connection

logger = logging.getLogger(__name__)


async def generate_sql_rollback_with_data(
    instance: RDBInstance,
    sql_content: str,
    database: Optional[str] = None
) -> Optional[tuple[str, int]]:
    """
    连接数据库生成真实的回滚SQL

    Args:
        instance: RDB实例
        sql_content: SQL内容
        database: 数据库名

    Returns:
        (回滚SQL, 受影响行数) 或 None
    """
    from datetime import datetime

    conn = None
    try:
        conn, db_type = get_rdb_connection(instance, database)

        # 使用增强版回滚生成器
        generator = EnhancedRollbackGenerator(db_connection=conn, db_type=db_type)
        results = generator.generate_rollback_sql(sql_content)

        if not results:
            return None, 0

        # 合并所有回滚SQL
        rollback_parts = []
        total_affected = 0

        for result in results:
            if result.success and result.rollback_sql:
                rollback_parts.append("-- ================================")
                rollback_parts.append(f"-- SQL类型: {result.sql_type.value}")
                rollback_parts.append(f"-- 受影响表: {result.affected_table or '未知'}")
                if result.affected_rows:
                    rollback_parts.append(f"-- 受影响行数: {result.affected_rows}")
                    total_affected += result.affected_rows
                rollback_parts.append("-- ================================")
                rollback_parts.append("")
                rollback_parts.append(result.rollback_sql)
                if result.warning:
                    rollback_parts.append(f"-- 警告: {result.warning}")
                rollback_parts.append("")

        if rollback_parts:
            header = f"""-- ============================================
-- 自动生成的回滚SQL
-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 实例: {instance.name}
-- 数据库: {database or '默认'}
-- 总受影响行数: {total_affected}
-- ============================================

"""
            return header + "\n".join(rollback_parts), total_affected

        return None, 0

    except Exception as e:
        logger.error(f"连接数据库生成回滚SQL失败: {e}")
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


async def generate_redis_rollback_with_data(
    instance: RedisInstance,
    commands: str
) -> Optional[tuple[str, list]]:
    """
    连接Redis生成真实的回滚命令

    Args:
        instance: Redis实例
        commands: Redis命令

    Returns:
        (回滚命令, 受影响键列表) 或 None
    """
    from datetime import datetime

    r = None
    try:
        r = get_redis_connection(instance)

        # 使用增强版回滚生成器
        generator = EnhancedRollbackGenerator()
        result = generator.generate_redis_rollback(commands, redis_connection=r)

        if not result.success:
            if result.error:
                logger.warning(f"Redis回滚生成失败: {result.error}")
            return None, []

        if not result.rollback_commands:
            return None, []

        # 构建回滚命令
        header = f"""-- ============================================
-- 自动生成的Redis回滚命令
-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- 实例: {instance.name}
-- 受影响键数量: {len(result.affected_keys)}
-- ============================================

"""
        rollback_content = "\n".join(result.rollback_commands)

        if result.warning:
            rollback_content += f"\n\n-- 警告: {result.warning}"

        return header + rollback_content, result.affected_keys

    except Exception as e:
        logger.error(f"连接Redis生成回滚命令失败: {e}")
        raise
    finally:
        if r:
            try:
                r.close()
            except Exception:
                pass
