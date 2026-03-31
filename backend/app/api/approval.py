"""
变更审批API
"""
import re
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
import pymysql
import psycopg2
import redis as redis_client

from app.database import get_db
from app.models import (
    ApprovalRecord, ApprovalStatus, RDBInstance, RedisInstance, User, AuditLog
)
from app.schemas import (
    ApprovalCreate, ApprovalAction, ApprovalResponse,
    MessageResponse
)
from app.deps import get_approval_admin, get_current_user
from app.services.notification import notification_service
from app.services.scheduler import approval_scheduler
from app.services.rollback_generator import rollback_generator
from app.services.enhanced_rollback_generator import (
    EnhancedRollbackGenerator, enhanced_rollback_generator
)
from app.services.storage import storage_manager
from app.services.sql_executor import sql_executor, redis_executor
from app.utils.auth import decrypt_instance_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvals", tags=["变更审批"])

# 大文件预览行数限制
PREVIEW_LINES = 100


def _get_instance_type(instance: RDBInstance) -> str:
    """判断实例类型：mysql 或 postgresql"""
    if instance.port == 5432:
        return "postgresql"
    elif instance.port == 3306:
        return "mysql"
    if "pg" in instance.host.lower() or "postgres" in instance.host.lower():
        return "postgresql"
    return "mysql"


def _get_rdb_connection(instance: RDBInstance, database: str = None):
    """获取关系型数据库连接"""
    db_type = _get_instance_type(instance)
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


def _get_redis_connection(instance: RedisInstance):
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


async def _generate_sql_rollback_with_data(
    instance: RDBInstance, 
    sql_content: str, 
    database: str = None
) -> tuple[str, int]:
    """
    连接数据库生成真实的回滚SQL
    
    Args:
        instance: RDB实例
        sql_content: SQL内容
        database: 数据库名
    
    Returns:
        (回滚SQL, 受影响行数)
    """
    conn = None
    try:
        conn, db_type = _get_rdb_connection(instance, database)
        
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
                rollback_parts.append(f"-- ================================")
                rollback_parts.append(f"-- SQL类型: {result.sql_type.value}")
                rollback_parts.append(f"-- 受影响表: {result.affected_table or '未知'}")
                if result.affected_rows:
                    rollback_parts.append(f"-- 受影响行数: {result.affected_rows}")
                    total_affected += result.affected_rows
                rollback_parts.append(f"-- ================================")
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
            except:
                pass


async def _generate_redis_rollback_with_data(
    instance: RedisInstance, 
    commands: str
) -> tuple[str, list]:
    """
    连接Redis生成真实的回滚命令
    
    Args:
        instance: Redis实例
        commands: Redis命令
    
    Returns:
        (回滚命令, 受影响键列表)
    """
    r = None
    try:
        r = _get_redis_connection(instance)
        
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
            except:
                pass


@router.get("/preview-databases/{instance_id}")
async def preview_matched_databases(
    instance_id: int,
    pattern: Optional[str] = None,
    mode: str = "pattern",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    预览匹配的数据库列表
    
    - mode=pattern: 通配符匹配
    - mode=all: 返回所有数据库
    """
    # 检查实例是否存在
    instance = db.query(RDBInstance).filter(RDBInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    # TODO: 实际连接数据库获取数据库列表
    # 这里模拟返回一些数据库用于演示
    # 实际实现需要使用 pymysql 连接到目标实例
    
    # 模拟数据库列表（实际应从实例查询）
    mock_databases = [
        "db_users", "db_orders", "db_products", "db_payments",
        "user_db_master", "user_db_slave1", "user_db_slave2",
        "order_db_2023", "order_db_2024", "order_db_2025",
        "information_schema", "mysql", "performance_schema", "sys"
    ]
    
    if mode == "all":
        # 返回所有数据库（排除系统库）
        filtered = [db for db in mock_databases if db not in ["information_schema", "mysql", "performance_schema", "sys"]]
        return {
            "mode": "all",
            "databases": filtered,
            "total": len(filtered)
        }
    
    if mode == "pattern" and pattern:
        # 通配符匹配
        import fnmatch
        # 将 SQL LIKE 模式转换为 fnmatch 模式
        # % -> *, _ -> ?
        fnmatch_pattern = pattern.replace("%", "*").replace("_", "?")
        matched = [db for db in mock_databases if fnmatch.fnmatch(db, fnmatch_pattern)]
        return {
            "mode": "pattern",
            "pattern": pattern,
            "databases": matched,
            "total": len(matched)
        }
    
    return {
        "mode": mode,
        "databases": [],
        "total": 0
    }


@router.post("/parse-sql-databases")
async def parse_sql_databases(
    sql_content: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    从SQL中解析数据库引用
    
    支持的格式：
    - db.table
    - `db`.table
    - db.`table`
    - `db`.`table`
    """
    # 正则匹配 db.table 格式
    # 支持反引号包裹的数据库名和表名
    patterns = [
        r'`?(\w+)`?\.`?(\w+)`?',  # db.table 或 `db`.`table`
        r'FROM\s+`?(\w+)`?\.`?(\w+)`?',  # FROM db.table
        r'JOIN\s+`?(\w+)`?\.`?(\w+)`?',  # JOIN db.table
        r'INTO\s+`?(\w+)`?\.`?(\w+)`?',  # INTO db.table
        r'UPDATE\s+`?(\w+)`?\.`?(\w+)`?',  # UPDATE db.table
    ]
    
    databases = set()
    for pattern in patterns:
        matches = re.findall(pattern, sql_content, re.IGNORECASE)
        for match in matches:
            db_name = match[0] if isinstance(match, tuple) else match
            # 排除一些常见的非数据库名
            if db_name.lower() not in ['select', 'from', 'where', 'and', 'or', 'join', 'left', 'right', 'inner', 'outer']:
                databases.add(db_name)
    
    return {
        "databases": list(databases),
        "total": len(databases)
    }


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
                ) if not loop.is_running() else None
        except Exception as e:
            logger.warning(f"读取SQL文件失败: {e}")
            sql_content = None
    
    # 获取回滚SQL
    rollback_sql = approval.rollback_sql
    rollback_file_path = approval.rollback_file_path
    rollback_download_url = None
    
    if rollback_file_path and not rollback_sql:
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                rollback_sql = loop.run_until_complete(storage_manager.read_sql_file(rollback_file_path))
                rollback_download_url = loop.run_until_complete(
                    storage_manager.get_download_url(rollback_file_path)
                )
        except Exception as e:
            logger.warning(f"读取回滚SQL文件失败: {e}")
            rollback_sql = None
    
    # 获取SQL预览
    if sql_content:
        sql_preview = get_sql_preview(sql_content)
        total_lines = approval.sql_line_count or len(sql_content.split('\n'))
    else:
        sql_preview = None
        total_lines = approval.sql_line_count or 0
    
    # 构建数据库目标描述
    database_target = ""
    if approval.database_mode == "all":
        database_target = "全部数据库"
    elif approval.database_mode == "pattern":
        database_target = approval.database_pattern
    elif approval.database_mode == "multiple":
        database_target = f"{len(approval.database_list or [])} 个数据库"
    elif approval.database_mode == "auto":
        database_target = "SQL自动解析"
    else:
        database_target = approval.database_name
    
    response = {
        "id": approval.id,
        "title": approval.title,
        "change_type": approval.change_type,
        "instance_id": approval.rdb_instance_id or approval.redis_instance_id,
        "rdb_instance_id": approval.rdb_instance_id,
        "redis_instance_id": approval.redis_instance_id,
        "database_mode": approval.database_mode,
        "database_name": approval.database_name,
        "database_list": approval.database_list,
        "database_pattern": approval.database_pattern,
        "matched_database_count": approval.matched_database_count,
        "database_target": database_target,
        "sql_content": sql_content if include_full_sql else None,
        "sql_content_preview": sql_preview if total_lines > PREVIEW_LINES else None,
        "sql_file_path": sql_file_path,
        "sql_download_url": sql_download_url,
        "sql_line_count": total_lines,
        "sql_risk_level": approval.sql_risk_level,
        "rollback_sql": rollback_sql if include_full_sql else None,
        "rollback_file_path": rollback_file_path,
        "rollback_download_url": rollback_download_url,
        "rollback_generated": approval.rollback_generated,
        "file_storage_type": approval.file_storage_type,
        "affected_rows_estimate": approval.affected_rows_estimate,
        "affected_rows_actual": approval.affected_rows_actual,
        "auto_execute": approval.auto_execute,
        "is_emergency": approval.is_emergency,
        "status": approval.status,
        "requester_id": approval.requester_id,
        "requester_name": approval.requester.real_name if approval.requester else None,
        "approver_id": approval.approver_id,
        "approver_name": approval.approver.real_name if approval.approver else None,
        "approve_comment": approval.approve_comment,
        # 多人审批相关字段
        "min_approvers": approval.min_approvers or 1,
        "approval_count": approval.approval_count or 0,
        "approver_ids": approval.approver_ids or [],
        "scheduled_time": approval.scheduled_time,
        "execute_time": approval.execute_time,
        "execute_result": approval.execute_result,
        "created_at": approval.created_at,
        "approved_at": approval.approve_time,
        "instance_name": (approval.rdb_instance.name if approval.rdb_instance else None) or 
                         (approval.redis_instance.name if approval.redis_instance else None)
    }
    
    return response


@router.get("")
async def list_approvals(
    status_filter: Optional[ApprovalStatus] = None,
    except_status: Optional[ApprovalStatus] = None,
    requester_id: Optional[int] = None,
    approver_id: Optional[int] = None,
    environment_id: Optional[int] = None,
    change_type: Optional[str] = None,
    exclude_change_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审批列表"""
    query = db.query(ApprovalRecord)
    
    if status_filter:
        query = query.filter(ApprovalRecord.status == status_filter)
    if except_status:
        query = query.filter(ApprovalRecord.status != except_status)
    if requester_id:
        query = query.filter(ApprovalRecord.requester_id == requester_id)
    if approver_id:
        query = query.filter(ApprovalRecord.approver_id == approver_id)
    if environment_id:
        query = query.filter(ApprovalRecord.environment_id == environment_id)
    if change_type:
        query = query.filter(ApprovalRecord.change_type == change_type)
    if exclude_change_type:
        query = query.filter(ApprovalRecord.change_type != exclude_change_type)
        # 如果排除 Redis 类型，只查询 rdb_instance_id 不为空的记录
        if exclude_change_type.upper() == 'REDIS':
            query = query.filter(ApprovalRecord.rdb_instance_id.isnot(None))
    
    # 普通用户只能看自己的申请
    if current_user.role.value == "readonly":
        query = query.filter(ApprovalRecord.requester_id == current_user.id)
    
    total = query.count()
    approvals = query.order_by(ApprovalRecord.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": [format_approval_response(a) for a in approvals]
    }


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审批详情"""
    approval = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval record not found"
        )
    
    # 权限检查：只能查看自己的申请或作为审批人查看
    if (approval.requester_id != current_user.id and 
        current_user.role.value not in ["super_admin", "approval_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to view this approval"
        )
    
    # 详情返回完整SQL内容
    return format_approval_response(approval, include_full_sql=True)


@router.post("", response_model=ApprovalResponse)
async def create_approval(
    approval_data: ApprovalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """提交审批申请"""
    # 根据 change_type 检查实例是否存在
    instance = None
    instance_name = ""
    environment_id = None
    
    if approval_data.change_type == "REDIS":
        # Redis 变更 - 查询 Redis 实例
        instance = db.query(RedisInstance).filter(RedisInstance.id == approval_data.instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Redis instance not found"
            )
        instance_name = instance.name
        environment_id = instance.environment_id
        # Redis 命令风险分析
        risk_level = analyze_redis_risk(approval_data.sql_content, environment_id, db)
    else:
        # SQL 变更 - 查询 RDB 实例
        instance = db.query(RDBInstance).filter(RDBInstance.id == approval_data.instance_id).first()
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="RDB instance not found"
            )
        instance_name = instance.name
        environment_id = instance.environment_id
        # SQL 风险分析
        risk_level = analyze_sql_risk(approval_data.sql_content, environment_id, db)
    
    # 极高风险直接拒绝
    if risk_level == "critical":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Critical risk detected, submission rejected"
        )
    
    # 获取变更窗口配置（用于多人审批）
    min_approvers = 1
    if environment_id:
        from app.models import ChangeWindow
        windows = db.query(ChangeWindow).filter(
            ChangeWindow.is_enabled == True,
            ChangeWindow.allow_emergency == True
        ).all()
        # 找到适用于该环境的窗口
        for w in windows:
            if w.environment_ids is None or len(w.environment_ids) == 0 or environment_id in (w.environment_ids or []):
                if w.min_approvers and w.min_approvers > min_approvers:
                    min_approvers = w.min_approvers
                    break
    
    # 如果是紧急变更，min_approvers 至少为 2
    if approval_data.is_emergency and min_approvers < 2:
        min_approvers = 2
    
    # 计算SQL/命令行数（如果前端没传）
    sql_line_count = approval_data.sql_line_count
    if not sql_line_count:
        sql_line_count = len(approval_data.sql_content.split('\n'))
    
    # 生成回滚SQL（连接数据库查询真实数据）
    rollback_sql = None
    rollback_generated = False
    affected_rows_estimate = approval_data.affected_rows_estimate or 0
    
    if approval_data.change_type != "REDIS":
        # SQL 变更 - 连接数据库生成回滚SQL
        try:
            rollback_sql, affected_rows = await _generate_sql_rollback_with_data(
                instance, 
                approval_data.sql_content, 
                approval_data.database_name
            )
            if rollback_sql:
                rollback_generated = True
                # 更新预估影响行数
                if affected_rows > 0:
                    affected_rows_estimate = affected_rows
        except Exception as e:
            logger.warning(f"生成回滚SQL失败（将使用基础版本）: {e}")
            # 降级：使用基础版本生成器
            try:
                rollback_results = rollback_generator.generate_rollback_sql(approval_data.sql_content)
                if rollback_results:
                    rollback_parts = []
                    for result in rollback_results:
                        if result.success and result.rollback_sql:
                            rollback_parts.append(f"-- 原SQL类型: {result.sql_type.value}")
                            rollback_parts.append(result.rollback_sql)
                            if result.warning:
                                rollback_parts.append(f"-- 警告: {result.warning}")
                            rollback_parts.append("")
                    if rollback_parts:
                        rollback_sql = "\n".join(rollback_parts)
                        rollback_generated = True
            except Exception as e2:
                logger.warning(f"基础版本生成回滚SQL也失败: {e2}")
    else:
        # Redis 命令回滚生成
        try:
            rollback_sql, affected_keys = await _generate_redis_rollback_with_data(
                instance, 
                approval_data.sql_content
            )
            if rollback_sql:
                rollback_generated = True
                affected_rows_estimate = len(affected_keys) if affected_keys else 0
        except Exception as e:
            logger.warning(f"生成Redis回滚命令失败（将使用基础版本）: {e}")
            # 降级：使用基础版本
            try:
                rollback_results = rollback_generator.generate_redis_rollback(approval_data.sql_content)
                if rollback_results and rollback_results.success and rollback_results.rollback_sql:
                    rollback_sql = rollback_results.rollback_sql
                    rollback_generated = True
            except Exception as e2:
                logger.warning(f"基础版本生成Redis回滚也失败: {e2}")
    
    # 判断是否需要存储到文件
    sql_content = approval_data.sql_content
    sql_file_path = None
    rollback_file_path = None
    file_storage_type = "database"
    
    if storage_manager.should_store_as_file(sql_content):
        file_storage_type = storage_manager.settings.STORAGE_TYPE
        # 先创建记录获取ID
        approval = ApprovalRecord(
            title=approval_data.title,
            change_type=approval_data.change_type,
            rdb_instance_id=approval_data.instance_id if approval_data.change_type != "REDIS" else None,
            redis_instance_id=approval_data.instance_id if approval_data.change_type == "REDIS" else None,
            database_mode=approval_data.database_mode,
            database_name=approval_data.database_name,
            database_list=approval_data.database_list,
            database_pattern=approval_data.database_pattern,
            matched_database_count=approval_data.matched_database_count,
            sql_content=None,  # 大文件不存数据库
            sql_line_count=sql_line_count,
            sql_risk_level=risk_level,
            rollback_sql=None,  # 大文件不存数据库
            rollback_generated=rollback_generated,
            file_storage_type=file_storage_type,
            affected_rows_estimate=affected_rows_estimate,
            auto_execute=approval_data.auto_execute or False,
            is_emergency=approval_data.is_emergency or False,
            min_approvers=min_approvers,
            environment_id=environment_id,
            requester_id=current_user.id,
            scheduled_time=approval_data.scheduled_time
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)
        
        # 保存SQL到文件
        try:
            sql_file_path = await storage_manager.save_sql_file(
                approval_id=approval.id,
                sql_type="sql",
                content=sql_content,
                metadata={
                    'title': approval_data.title,
                    'change_type': approval_data.change_type,
                    'risk_level': risk_level
                }
            )
            approval.sql_file_path = sql_file_path
            
            # 如果有回滚SQL，也保存到文件
            if rollback_sql:
                rollback_file_path = await storage_manager.save_sql_file(
                    approval_id=approval.id,
                    sql_type="rollback",
                    content=rollback_sql,
                    metadata={
                        'generated': rollback_generated
                    }
                )
                approval.rollback_file_path = rollback_file_path
            
            db.commit()
            logger.info(f"SQL已存储到文件: {sql_file_path}")
        except Exception as e:
            logger.error(f"保存SQL文件失败: {e}")
            # 降级处理：存入数据库
            approval.sql_content = sql_content
            approval.rollback_sql = rollback_sql
            approval.file_storage_type = "database"
            db.commit()
    else:
        # 小文件直接存数据库
        approval = ApprovalRecord(
            title=approval_data.title,
            change_type=approval_data.change_type,
            rdb_instance_id=approval_data.instance_id if approval_data.change_type != "REDIS" else None,
            redis_instance_id=approval_data.instance_id if approval_data.change_type == "REDIS" else None,
            database_mode=approval_data.database_mode,
            database_name=approval_data.database_name,
            database_list=approval_data.database_list,
            database_pattern=approval_data.database_pattern,
            matched_database_count=approval_data.matched_database_count,
            sql_content=sql_content,
            sql_line_count=sql_line_count,
            sql_risk_level=risk_level,
            rollback_sql=rollback_sql,
            rollback_generated=rollback_generated,
            file_storage_type="database",
            affected_rows_estimate=affected_rows_estimate,
            auto_execute=approval_data.auto_execute or False,
            is_emergency=approval_data.is_emergency or False,
            min_approvers=min_approvers,
            environment_id=instance.environment_id,
            requester_id=current_user.id,
            scheduled_time=approval_data.scheduled_time
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)
    
    # 构建数据库目标描述
    db_target_desc = ""
    if approval_data.database_mode == "all":
        db_target_desc = "全部数据库"
    elif approval_data.database_mode == "pattern":
        db_target_desc = f"通配符模式: {approval_data.database_pattern}"
    elif approval_data.database_mode == "multiple":
        db_target_desc = f"{len(approval_data.database_list or [])} 个数据库"
    elif approval_data.database_mode == "auto":
        db_target_desc = "SQL自动解析"
    else:
        db_target_desc = approval_data.database_name
    
    # 记录审计日志
    audit_log = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        instance_id=approval_data.instance_id,
        instance_name=instance_name,
        environment_id=environment_id,
        operation_type="submit_approval",
        operation_detail=f"Submit approval: {approval_data.title}\nDatabase: {db_target_desc}\nSQL lines: {sql_line_count}lines",
        request_ip="",
        request_method="POST",
        request_path=f"/api/approvals",
        response_code=200
    )
    db.add(audit_log)
    db.commit()
    
    # 发送钉钉通知
    try:
        await notification_service.send_approval_notification(db, approval, "pending")
    except Exception as e:
        # 通知失败不影响创建，记录日志即可
        logger.warning(f"发送审批通知失败: {e}")
    
    return format_approval_response(approval, include_full_sql=True)


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_or_reject(
    approval_id: int,
    action_data: ApprovalAction,
    current_user: User = Depends(get_approval_admin),
    db: Session = Depends(get_db)
):
    """审批通过或拒绝（支持多人审批）"""
    from app.models import ApprovalFlow
    
    approval = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval record not found"
        )
    
    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This approval has already been processed"
        )
    
    # 检查是否已审批过（防止重复审批）
    approver_ids = approval.approver_ids or []
    if current_user.id in approver_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已审批过此申请，请勿重复操作"
        )
    
    # 记录审批流程
    flow = ApprovalFlow(
        approval_id=approval.id,
        approver_id=current_user.id,
        action="approve" if action_data.approved else "reject",
        comment=action_data.comment
    )
    db.add(flow)
    
    # 如果是拒绝，直接拒绝
    if not action_data.approved:
        approval.status = ApprovalStatus.REJECTED
        approval.approver_id = current_user.id
        approval.approve_time = datetime.now()
        approval.approve_comment = action_data.comment
        db.commit()
        
        # 记录审计日志
        _add_audit_log(db, current_user, approval, "reject")
        db.commit()
        
        # 发送通知
        try:
            await notification_service.send_approval_notification(db, approval, "rejected")
        except Exception as e:
            logger.warning(f"发送审批结果通知失败: {e}")
        
        return format_approval_response(approval, include_full_sql=True)
    
    # 通过审批 - 更新审批计数
    approver_ids.append(current_user.id)
    approval.approver_ids = approver_ids
    approval.approval_count = len(approver_ids)
    
    # 获取最小审批人数
    min_approvers = approval.min_approvers or 1
    
    # 获取系统中所有有审批权限的用户数量（用于兜底判断）
    approver_count = db.query(User).filter(
        User.role.in_(["super_admin", "approval_admin"]),
        User.status == True
    ).count()
    
    # 判断是否达到审批条件
    # 条件1：已审批人数 >= 最小审批人数
    # 条件2：系统中审批人不足时，所有审批人都已审批
    all_approvers_voted = approval.approval_count >= approver_count
    min_approvers_reached = approval.approval_count >= min_approvers
    
    if min_approvers_reached or all_approvers_voted:
        # 审批通过
        approval.status = ApprovalStatus.APPROVED
        approval.approver_id = current_user.id  # 最后一个审批人
        approval.approve_time = datetime.now()
        approval.approve_comment = action_data.comment
        
        db.commit()
        
        # 记录审计日志
        _add_audit_log(db, current_user, approval, "approve")
        db.commit()
        
        # 发送通知
        try:
            await notification_service.send_approval_notification(db, approval, "approved")
        except Exception as e:
            logger.warning(f"发送审批结果通知失败: {e}")
        
        # 如果通过，处理执行逻辑
        if approval.scheduled_time:
            try:
                approval_scheduler.schedule_approval_execution(
                    approval.id, 
                    approval.scheduled_time
                )
                logger.info(f"已添加定时执行任务: 审批ID={approval.id}, 执行时间={approval.scheduled_time}")
            except Exception as e:
                logger.error(f"添加定时执行任务失败: {e}")
        elif approval.auto_execute:
            try:
                logger.info(f"审批通过且启用自动执行，开始执行: 审批ID={approval.id}")
                await approval_scheduler.execute_approval(approval.id, db)
            except Exception as e:
                logger.error(f"自动执行审批失败: {e}")
    else:
        # 还需要继续审批
        db.commit()
        logger.info(f"审批进度: {approval.approval_count}/{min_approvers}，等待更多审批人")
    
    return format_approval_response(approval, include_full_sql=True)


def _add_audit_log(db, current_user, approval, action):
    """添加审计日志"""
    audit_log = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        instance_id=approval.rdb_instance_id or approval.redis_instance_id,
        instance_name=(approval.rdb_instance.name if approval.rdb_instance else None) or 
                      (approval.redis_instance.name if approval.redis_instance else None),
        environment_id=approval.environment_id,
        operation_type=action,
        operation_detail=f"{'Approved' if action == 'approve' else 'Rejected'} approval: {approval.title}",
        request_ip="",
        request_method="POST",
        request_path=f"/api/approvals/{approval.id}/approve",
        response_code=200
    )
    db.add(audit_log)


@router.post("/{approval_id}/execute", response_model=MessageResponse)
async def execute_approval(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """执行已通过的审批"""
    approval = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval record not found"
        )
    
    if approval.status != ApprovalStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This approval was not approved, cannot execute"
        )
    
    # 只有申请人可以执行
    if approval.requester_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the applicant can execute this approval"
        )
    
    try:
        # 获取实例 - 根据变更类型选择正确的实例表
        instance = None
        if approval.change_type == "REDIS":
            instance = db.query(RedisInstance).filter(RedisInstance.id == approval.redis_instance_id).first()
            # 执行 Redis 命令
            execute_result = await redis_executor.execute_for_approval(approval, instance)
            execution_success = sql_executor.check_execution_success(execute_result)
        else:
            instance = db.query(RDBInstance).filter(RDBInstance.id == approval.rdb_instance_id).first()
            # 执行 SQL
            success, execute_result, affected_rows = await sql_executor.execute_for_approval(approval, instance)
            approval.affected_rows_actual = affected_rows
            execution_success = sql_executor.check_execution_success(execute_result)
        
        # 更新状态
        if execution_success:
            approval.status = ApprovalStatus.EXECUTED
        else:
            approval.status = ApprovalStatus.FAILED
        approval.execute_time = datetime.now()
        approval.execute_result = execute_result
        
        db.commit()
        
        message = "审批执行成功" if execution_success else f"审批执行失败: {execute_result}"
        
    except Exception as e:
        # 执行异常，记录失败
        approval.status = ApprovalStatus.FAILED
        approval.execute_time = datetime.now()
        approval.execute_result = f"执行异常: {str(e)}"
        db.commit()
        message = f"审批执行失败: {str(e)}"
    
    # 发送执行完成通知（无论成功失败都发送）
    try:
        await notification_service.send_approval_notification(db, approval, "executed")
    except Exception as e:
        logger.warning(f"发送执行完成通知失败: {e}")
    
    # 记录审计日志
    audit_log = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        instance_id=approval.rdb_instance_id or approval.redis_instance_id,
        instance_name=instance.name if instance else None,
        environment_id=approval.environment_id,
        operation_type="execute_approval",
        operation_detail=f"Execute approval: {approval.title}\nResult: {approval.execute_result}",
        request_ip="",
        request_method="POST",
        request_path=f"/api/approvals/{approval_id}/execute",
        response_code=200
    )
    db.add(audit_log)
    db.commit()
    
    return MessageResponse(message=message)


@router.get("/dingtalk-action", response_class=HTMLResponse)
async def dingtalk_approval_action(
    token: str,
    db: Session = Depends(get_db)
):
    """
    钉钉审批链接处理
    
    通过 token 验证并执行审批操作
    """
    # 验证 token
    token_data = notification_service.verify_approval_token(token)
    
    if not token_data:
        return HTMLResponse(content="""
        <html>
        <head><title>审批失败</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #f56c6c;">❌ 操作失败</h1>
            <p>链接无效或已过期，请登录系统进行审批</p>
        </body>
        </html>
        """)
    
    approval_id = token_data["approval_id"]
    action = token_data["action"]
    
    # 获取审批记录
    approval = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
    
    if not approval:
        return HTMLResponse(content="""
        <html>
        <head><title>审批失败</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #f56c6c;">❌ 审批记录不存在</h1>
        </body>
        </html>
        """)
    
    if approval.status != ApprovalStatus.PENDING:
        status_text = {
            ApprovalStatus.APPROVED: "已通过",
            ApprovalStatus.REJECTED: "已拒绝",
            ApprovalStatus.EXECUTED: "已执lines",
            ApprovalStatus.FAILED: "执行失败"
        }.get(approval.status, "未知状态")
        
        return HTMLResponse(content=f"""
        <html>
        <head><title>审批已处理</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #e6a23c;">⚠️ 该审批已处理</h1>
            <p>当前状态: {status_text}</p>
        </body>
        </html>
        """)
    
    # 执行审批操作
    if action == "approve":
        approval.status = ApprovalStatus.APPROVED
        approval.approver_id = 0  # 钉钉审批，标记为系统
        approval.approve_time = datetime.now()
        approval.approve_comment = "通过钉钉链接审批"
        
        # 如果有定时执行时间，添加到调度器
        if approval.scheduled_time:
            approval_scheduler.schedule_approval_execution(
                approval.id, 
                approval.scheduled_time
            )
        
        db.commit()
        
        # 发送通知
        await notification_service.send_approval_notification(db, approval, "approved")
        
        return HTMLResponse(content="""
        <html>
        <head><title>审批通过</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #67c23a;">✅ 审批已通过</h1>
            <p>审批人: 钉钉审批</p>
        </body>
        </html>
        """)
    
    elif action == "reject":
        approval.status = ApprovalStatus.REJECTED
        approval.approver_id = 0
        approval.approve_time = datetime.now()
        approval.approve_comment = "通过钉钉链接拒绝"
        
        db.commit()
        
        # 发送通知
        await notification_service.send_approval_notification(db, approval, "rejected")
        
        return HTMLResponse(content="""
        <html>
        <head><title>审批拒绝</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #f56c6c;">❌ 审批已拒绝</h1>
            <p>审批人: 钉钉审批</p>
        </body>
        </html>
        """)
    
    else:
        return HTMLResponse(content="""
        <html>
        <head><title>操作无效</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
            <h1 style="color: #f56c6c;">❌ 无效的操作</h1>
        </body>
        </html>
        """)
