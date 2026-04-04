"""
变更审批API - 辅助函数
"""
import re
import logging
from typing import Optional
from datetime import datetime
import pymysql
import psycopg2
import redis as redis_client
from sqlalchemy.orm import Session

from app.models import (
    ApprovalRecord, RDBInstance, RedisInstance
)
from app.services.enhanced_rollback_generator import EnhancedRollbackGenerator
from app.services.storage import storage_manager
from app.utils.auth import decrypt_instance_password

logger = logging.getLogger(__name__)

# 大文件预览行数限制
PREVIEW_LINES = 100


def get_instance_type(instance: RDBInstance) -> str:
    """判断实例类型：mysql 或 postgresql"""
    if instance.port == 5432:
        return "postgresql"
    elif instance.port == 3306:
        return "mysql"
    if "pg" in instance.host.lower() or "postgres" in instance.host.lower():
        return "postgresql"
    return "mysql"


def get_rdb_connection(instance: RDBInstance, database: str = None):
    """获取关系型数据库连接"""
    db_type = get_instance_type(instance)
    try:
        password = decrypt_instance_password(instance.password_encrypted)
    except ValueError as e:
        raise ValueError(f"密码解密失败: {str(e)}")

    if db_type == "postgresql":
        conn = psycopg2.connect(
            host=instance.host,
            port=instance.port,
            user=instance.username,
            password=password,
            database=database or 'postgres',
            connect_timeout=5
        )
        return conn, "postgresql"
    else:
        conn = pymysql.connect(
            host=instance.host,
            port=instance.port,
            user=instance.username,
            password=password,
            database=database,
            connect_timeout=5,
            charset='utf8mb4'
        )
        return conn, "mysql"


def get_redis_connection(instance: RedisInstance):
    """获取Redis连接"""
    try:
        password = decrypt_instance_password(instance.password_encrypted) if instance.password_encrypted else None
    except ValueError:
        password = instance.password_encrypted

    r = redis_client.Redis(
        host=instance.host,
        port=instance.port,
        password=password,
        db=0,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    return r


def get_sql_preview(sql_content: str, max_lines: int = PREVIEW_LINES) -> str:
    """
    获取SQL预览内容（截取前N行）
    """
    lines = sql_content.split('\n')
    if len(lines) <= max_lines:
        return sql_content
    return '\n'.join(lines[:max_lines])


def analyze_sql_risk(sql: str, environment_id: int, db: Session) -> str:
    """
    分析SQL风险等级
    返回: critical/high/medium/low
    """
    sql_upper = sql.upper().strip()

    # 极高风险：删除数据库、截断表
    critical_patterns = [
        r'\bDROP\s+DATABASE\b',
        r'\bDROP\s+SCHEMA\b',
        r'\bTRUNCATE\s+TABLE\b',
        r'\bTRUNCATE\b',
    ]

    # 高风险：删除表、删除数据无WHERE
    high_patterns = [
        r'\bDROP\s+TABLE\b',
        r'\bDELETE\s+FROM\b.*(?<!WHERE\b)',  # DELETE无WHERE
        r'\bUPDATE\b.*(?<!WHERE\b)',  # UPDATE无WHERE
        r'\bALTER\s+TABLE\b.*\bDROP\b',
        r'\bALTER\s+TABLE\b.*\bMODIFY\b',
    ]

    # 中风险：ALTER、CREATE
    medium_patterns = [
        r'\bALTER\s+TABLE\b',
        r'\bCREATE\s+TABLE\b',
        r'\bCREATE\s+INDEX\b',
        r'\bDROP\s+INDEX\b',
        r'\bDELETE\s+FROM\b.*\bWHERE\b',
        r'\bUPDATE\b.*\bWHERE\b',
    ]

    # 检查极高风险
    for pattern in critical_patterns:
        if re.search(pattern, sql_upper, re.IGNORECASE):
            return "critical"

    # 检查高风险
    for pattern in high_patterns:
        if re.search(pattern, sql_upper, re.IGNORECASE):
            # 特殊检查：是否有WHERE条件
            if 'DELETE' in sql_upper or 'UPDATE' in sql_upper:
                if 'WHERE' not in sql_upper:
                    return "critical"
            return "high"

    # 检查中风险
    for pattern in medium_patterns:
        if re.search(pattern, sql_upper, re.IGNORECASE):
            return "medium"

    return "low"


def analyze_redis_risk(commands: str, environment_id: int, db: Session) -> str:
    """
    分析 Redis 命令风险等级
    返回: critical/high/medium/low
    """
    commands_upper = commands.upper().strip()

    # 极高风险：删除所有数据、关闭服务器
    critical_patterns = [
        r'\bFLUSHALL\b',
        r'\bFLUSHDB\b',
        r'\bSHUTDOWN\b',
        r'\bDEBUG\s+RELOAD\b',
        r'\bDEBUG\s+SEGFAULT\b',
    ]

    # 高风险：删除键、重命名
    high_patterns = [
        r'\bDEL\b',
        r'\bUNLINK\b',
        r'\bRENAME\b',
        r'\bRENAMENX\b',
        r'\bMOVE\b',
        r'\bMIGRATE\b',
        r'\bRESTORE\b',
    ]

    # 中风险：修改数据
    medium_patterns = [
        r'\bSET\b',
        r'\bSETEX\b',
        r'\bSETNX\b',
        r'\bMSET\b',
        r'\bINCR\b',
        r'\bDECR\b',
        r'\bINCRBY\b',
        r'\bDECRBY\b',
        r'\bAPPEND\b',
        r'\bLPUSH\b',
        r'\bRPUSH\b',
        r'\bLPOP\b',
        r'\bRPOP\b',
        r'\bSADD\b',
        r'\bSREM\b',
        r'\bZADD\b',
        r'\bZREM\b',
        r'\bHSET\b',
        r'\bHDEL\b',
        r'\bEXPIRE\b',
        r'\bPEXPIRE\b',
        r'\bPERSIST\b',
    ]

    # 检查极高风险
    for pattern in critical_patterns:
        if re.search(pattern, commands_upper, re.IGNORECASE):
            return "critical"

    # 检查高风险
    for pattern in high_patterns:
        if re.search(pattern, commands_upper, re.IGNORECASE):
            return "high"

    # 检查中风险
    for pattern in medium_patterns:
        if re.search(pattern, commands_upper, re.IGNORECASE):
            return "medium"

    # 只读命令为低风险
    return "low"


def format_approval_response(approval: ApprovalRecord, include_full_sql: bool = False) -> dict:
    """
    格式化审批响应，处理大SQL文件的预览
    支持从文件存储读取SQL内容
    """
    import asyncio

    # 获取SQL内容
    sql_content = approval.sql_content
    sql_file_path = approval.sql_file_path
    sql_download_url = None

    # 如果存储在文件中，从文件读取
    if sql_file_path and not sql_content:
        try:
            # 尝试从文件读取
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果在异步上下文中，使用缓存的内容
                sql_content = None
            else:
                sql_content = loop.run_until_complete(storage_manager.read_sql_file(sql_file_path))

            # 生成下载URL
            if include_full_sql:
                sql_download_url = loop.run_until_complete(
                    storage_manager.get_download_url(sql_file_path)
                )
        except Exception as e:
            logger.error(f"读取SQL文件失败: {e}")
            sql_content = None

    # 如果没有内容，返回占位符
    if not sql_content:
        sql_preview = "(无SQL内容或从文件读取失败)"
    else:
        sql_preview = get_sql_preview(sql_content)

    # 确定实例ID和类型
    instance_id = approval.rdb_instance_id or approval.redis_instance_id

    # 构建响应
    response = {
        "id": approval.id,
        "title": approval.title,
        "change_type": approval.change_type,
        "instance_id": instance_id,
        "rdb_instance_id": approval.rdb_instance_id,
        "redis_instance_id": approval.redis_instance_id,
        "status": approval.status,
        "environment_id": approval.environment_id,
        "sql_risk_level": approval.sql_risk_level,
        "sql_preview": sql_preview,
        "sql_download_url": sql_download_url,
        "database_mode": approval.database_mode,
        "database_name": approval.database_name,
        "database_list": approval.database_list or [],
        "sql_line_count": approval.sql_line_count,
        "affected_rows_estimate": approval.affected_rows_estimate,
        "auto_execute": approval.auto_execute,
        "is_emergency": approval.is_emergency,
        "rollback_generated": approval.rollback_generated,
        "approve_comment": approval.approve_comment,
        "created_at": approval.created_at.isoformat() if approval.created_at else None,
        "updated_at": approval.updated_at.isoformat() if approval.updated_at else None,
        "requester_id": approval.requester_id,
        "approver_id": approval.approver_id,
        "approve_time": approval.approve_time.isoformat() if approval.approve_time else None,
        "execute_time": approval.execute_time.isoformat() if approval.execute_time else None,
        "scheduled_time": approval.scheduled_time.isoformat() if approval.scheduled_time else None,
    }

    # 如果需要完整SQL且内容较短，直接包含
    if include_full_sql and sql_content and len(sql_content) < 10000:
        response["sql_content"] = sql_content

    return response


def add_audit_log(db, current_user, approval, action):
    """添加审计日志"""
    from app.models import AuditLog

    audit_log = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        operation_type=action,
        operation_detail={
            "approval_id": approval.id,
            "title": approval.title,
            "status": approval.status,
        }
    )
    db.add(audit_log)
