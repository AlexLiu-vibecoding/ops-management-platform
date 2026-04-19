"""
变更审批API - 端点定义
"""
import re
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload
import asyncio

from app.database import get_db
from app.models import (
    ApprovalRecord, ApprovalStatus, RDBInstance, RedisInstance, User
)
from app.schemas import (
    ApprovalCreate, ApprovalAction, ApprovalResponse,
    MessageResponse
)
from app.deps import get_current_user, require_permission
from app.services.notification import notification_service
from app.services.scheduler import approval_scheduler
from app.services.rollback_generator import rollback_generator
from app.services.storage import storage_manager
from app.services.sql_executor import sql_executor, redis_executor

from .helpers import (
    analyze_sql_risk, analyze_redis_risk,
    format_approval_response, add_audit_log,
    PREVIEW_LINES
)
from .rollback import generate_sql_rollback_with_data, generate_redis_rollback_with_data

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvals", tags=["变更审批"])


@router.get("/preview-databases/{instance_id}")
async def preview_matched_databases(
    instance_id: int,
    pattern: Optional[str] = None,
    mode: str = "pattern",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """预览匹配的数据库列表"""
    # 检查实例是否存在
    instance = db.query(RDBInstance).filter(RDBInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )

    # 模拟数据库列表（实际应从实例查询）
    mock_databases = [
        "db_users", "db_orders", "db_products", "db_payments",
        "user_db_master", "user_db_slave1", "user_db_slave2",
        "order_db_2023", "order_db_2024", "order_db_2025",
        "information_schema", "mysql", "performance_schema", "sys"
    ]

    if mode == "all":
        filtered = [db for db in mock_databases if db not in ["information_schema", "mysql", "performance_schema", "sys"]]
        return {"mode": "all", "databases": filtered, "total": len(filtered)}

    if mode == "pattern" and pattern:
        import fnmatch
        fnmatch_pattern = pattern.replace("%", "*").replace("_", "?")
        matched = [db for db in mock_databases if fnmatch.fnmatch(db, fnmatch_pattern)]
        return {"mode": "pattern", "pattern": pattern, "databases": matched, "total": len(matched)}

    return {"mode": mode, "databases": [], "total": 0}


@router.post("/parse-sql-databases")
async def parse_sql_databases(
    sql_content: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """从SQL中解析数据库引用"""
    patterns = [
        r'`?(\w+)`?\.`?(\w+)`?',
        r'FROM\s+`?(\w+)`?\.`?(\w+)`?',
        r'JOIN\s+`?(\w+)`?\.`?(\w+)`?',
        r'INTO\s+`?(\w+)`?\.`?(\w+)`?',
        r'UPDATE\s+`?(\w+)`?\.`?(\w+)`?',
    ]

    databases = set()
    for pattern in patterns:
        matches = re.findall(pattern, sql_content, re.IGNORECASE)
        for match in matches:
            db_name = match[0] if isinstance(match, tuple) else match
            if db_name.lower() not in ['select', 'from', 'where', 'and', 'or', 'join', 'left', 'right', 'inner', 'outer']:
                databases.add(db_name)

    return {"databases": list(databases), "total": len(databases)}


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
    query = db.query(ApprovalRecord).options(
        joinedload(ApprovalRecord.requester),
        joinedload(ApprovalRecord.approver),
        joinedload(ApprovalRecord.rdb_instance),
        joinedload(ApprovalRecord.redis_instance)
    )

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
        if exclude_change_type.upper() == 'REDIS':
            query = query.filter(ApprovalRecord.rdb_instance_id.isnot(None))

    if current_user.role.value == "readonly":
        query = query.filter(ApprovalRecord.requester_id == current_user.id)

    total = query.count()
    approvals = query.order_by(ApprovalRecord.created_at.desc()).offset(skip).limit(limit).all()

    return {"total": total, "items": [format_approval_response(a) for a in approvals]}


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(
    approval_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取审批详情"""
    approval = db.query(ApprovalRecord).options(
        joinedload(ApprovalRecord.requester),
        joinedload(ApprovalRecord.approver),
        joinedload(ApprovalRecord.rdb_instance),
        joinedload(ApprovalRecord.redis_instance)
    ).filter(ApprovalRecord.id == approval_id).first()
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval record not found"
        )

    if (approval.requester_id != current_user.id and
        current_user.role.value not in ["super_admin", "approval_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No permission to view this approval"
        )

    return format_approval_response(approval, include_full_sql=True)


@router.post("", response_model=ApprovalResponse)
async def create_approval(
    approval_data: ApprovalCreate,
    current_user: User = Depends(require_permission("approval:create")),
    db: Session = Depends(get_db)
):
    """提交审批申请"""
    # 根据 change_type 检查实例是否存在
    instance = None
    instance_name = ""
    environment_id = None

    if approval_data.change_type == "REDIS":
        instance = db.query(RedisInstance).filter(RedisInstance.id == approval_data.instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail="Redis instance not found")
        instance_name = instance.name
        environment_id = instance.environment_id
        risk_level = analyze_redis_risk(approval_data.sql_content, environment_id, db)
    else:
        instance = db.query(RDBInstance).filter(RDBInstance.id == approval_data.instance_id).first()
        if not instance:
            raise HTTPException(status_code=404, detail="RDB instance not found")
        instance_name = instance.name
        environment_id = instance.environment_id
        risk_level = analyze_sql_risk(approval_data.sql_content, environment_id, db)

    if risk_level == "critical":
        raise HTTPException(status_code=400, detail="Critical risk detected, submission rejected")

    # 计算SQL/命令行数
    sql_line_count = approval_data.sql_line_count or len(approval_data.sql_content.split('\n'))

    # 生成回滚SQL
    rollback_sql = None
    rollback_generated = False
    affected_rows_estimate = approval_data.affected_rows_estimate or 0

    if approval_data.change_type != "REDIS":
        try:
            rollback_sql, affected_rows = await generate_sql_rollback_with_data(
                instance,
                approval_data.sql_content,
                approval_data.database_name
            )
            if rollback_sql:
                rollback_generated = True
                if affected_rows > 0:
                    affected_rows_estimate = affected_rows
        except Exception as e:
            logger.warning(f"生成回滚SQL失败: {e}")
    else:
        try:
            rollback_sql, affected_keys = await generate_redis_rollback_with_data(
                instance,
                approval_data.sql_content
            )
            if rollback_sql:
                rollback_generated = True
                affected_rows_estimate = len(affected_keys) if affected_keys else 0
        except Exception as e:
            logger.warning(f"生成Redis回滚命令失败: {e}")

    # 判断是否需要存储到文件
    sql_content = approval_data.sql_content
    sql_file_path = None
    rollback_file_path = None
    file_storage_type = "database"

    if storage_manager.should_store_as_file(sql_content):
        file_storage_type = storage_manager.settings.TYPE
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
            sql_content=None,
            sql_line_count=sql_line_count,
            sql_risk_level=risk_level,
            rollback_sql=None,
            rollback_generated=rollback_generated,
            file_storage_type=file_storage_type,
            affected_rows_estimate=affected_rows_estimate,
            auto_execute=approval_data.auto_execute or False,
            is_emergency=approval_data.is_emergency or False,
            min_approvers=1,
            environment_id=environment_id,
            requester_id=current_user.id,
            scheduled_time=approval_data.scheduled_time
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        try:
            sql_file_path = await storage_manager.save_sql_file(
                approval_id=approval.id,
                sql_type="sql",
                content=sql_content,
                metadata={'title': approval_data.title, 'change_type': approval_data.change_type}
            )
            approval.sql_file_path = sql_file_path

            if rollback_sql:
                rollback_file_path = await storage_manager.save_sql_file(
                    approval_id=approval.id,
                    sql_type="rollback",
                    content=rollback_sql,
                    metadata={'generated': rollback_generated}
                )
                approval.rollback_file_path = rollback_file_path

            db.commit()
            logger.info(f"SQL已存储到文件: {sql_file_path}")
        except Exception as e:
            logger.error(f"保存SQL文件失败: {e}")
            approval.sql_content = sql_content
            approval.rollback_sql = rollback_sql
            approval.file_storage_type = "database"
            db.commit()
    else:
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
            file_storage_type=file_storage_type,
            affected_rows_estimate=affected_rows_estimate,
            auto_execute=approval_data.auto_execute or False,
            is_emergency=approval_data.is_emergency or False,
            min_approvers=1,
            environment_id=environment_id,
            requester_id=current_user.id,
            scheduled_time=approval_data.scheduled_time
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

    # 添加审计日志
    add_audit_log(db, current_user, approval, "APPROVAL_CREATE")

    return format_approval_response(approval, include_full_sql=True)


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_or_reject(
    approval_id: int,
    action: ApprovalAction,
    current_user: User = Depends(require_permission("approval:approve")),
    db: Session = Depends(get_db)
):
    """审批或拒绝"""
    approval = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.status != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="Approval already processed")

    if action.action == "approve":
        approval.status = ApprovalStatus.APPROVED
        approval.approver_id = current_user.id
        approval.approved_at = datetime.utcnow()
        approval.approver_comment = action.comment

        # 检查是否自动执行
        if approval.auto_execute:
            try:
                # 这里应该异步执行，但为了简化，先同步执行
                success, message, affected = await sql_executor.execute_for_approval(approval, approval.rdb_instance)
                if success:
                    approval.status = ApprovalStatus.EXECUTED
                    approval.execution_result = message
                    approval.executed_at = datetime.utcnow()
                else:
                    approval.status = ApprovalStatus.FAILED
                    approval.execution_result = f"执行失败: {message}"
            except Exception as e:
                logger.error(f"自动执行失败: {e}")
                approval.status = ApprovalStatus.FAILED
                approval.execution_result = f"执行异常: {str(e)}"

        # 发送通知
        try:
            await notification_service.send_approval_notification(
                approval_id=approval.id,
                action="approved",
                user_id=current_user.id
            )
        except Exception as e:
            logger.error(f"发送通知失败: {e}")

    elif action.action == "reject":
        approval.status = ApprovalStatus.REJECTED
        approval.approver_id = current_user.id
        approval.rejected_at = datetime.utcnow()
        approval.rejection_reason = action.comment

        # 发送通知
        try:
            await notification_service.send_approval_notification(
                approval_id=approval.id,
                action="rejected",
                user_id=current_user.id
            )
        except Exception as e:
            logger.error(f"发送通知失败: {e}")

    db.commit()
    db.refresh(approval)

    add_audit_log(db, current_user, approval, f"APPROVAL_{action.action.upper()}")

    return format_approval_response(approval, include_full_sql=True)


@router.post("/{approval_id}/execute", response_model=MessageResponse)
async def execute_approval(
    approval_id: int,
    current_user: User = Depends(require_permission("approval:execute")),
    db: Session = Depends(get_db)
):
    """手动执行审批"""
    approval = db.query(ApprovalRecord).filter(ApprovalRecord.id == approval_id).first()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    if approval.status != ApprovalStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Approval must be approved before execution")

    approval.status = ApprovalStatus.EXECUTING
    approval.executed_by = current_user.id
    approval.executed_at = datetime.utcnow()
    db.commit()

    try:
        if approval.change_type == "REDIS":
            success, message, affected = await redis_executor.execute_for_approval(approval, approval.redis_instance)
        else:
            success, message, affected = await sql_executor.execute_for_approval(approval, approval.rdb_instance)

        if success:
            approval.status = ApprovalStatus.EXECUTED
            approval.execution_result = message
        else:
            approval.status = ApprovalStatus.FAILED
            approval.execution_result = f"执行失败: {message}"

        db.commit()
        add_audit_log(db, current_user, approval, "APPROVAL_EXECUTE")

        return {"message": f"执行{'成功' if success else '失败'}", "success": success}
    except Exception as e:
        approval.status = ApprovalStatus.FAILED
        approval.execution_result = f"执行异常: {str(e)}"
        db.commit()
        logger.error(f"执行审批失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dingtalk-action", response_class=HTMLResponse)
async def dingtalk_approval_action(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """钉钉审批操作页面"""
    # 简化的钉钉操作页面
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>钉钉审批操作</title>
    </head>
    <body>
        <h1>钉钉审批操作</h1>
        <p>功能开发中...</p>
    </body>
    </html>
    """
    return html
