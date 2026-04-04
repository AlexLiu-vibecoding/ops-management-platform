"""
巡检报告API - 巡检指标管理、巡检执行、报告生成
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pydantic import BaseModel, Field
import json

from app.database import get_db
from app.models import (
    InspectMetric, InspectResult, InspectionReport,
    RDBInstance, User, SlowQuery, IndexAnalysis,
    ReplicationStatus, LongTransaction, LockWait
)
from app.schemas import MessageResponse
from app.deps import get_current_user, get_super_admin
from app.services.db_connection import db_manager

router = APIRouter(prefix="/inspection", tags=["巡检报告"])


# ==================== Schemas ====================

class InspectMetricCreate(BaseModel):
    """创建巡检指标"""
    module: str = Field(..., description="模块: slow_query/index/lock/transaction/repl/capacity")
    metric_name: str = Field(..., description="指标名称")
    metric_code: str = Field(..., description="指标编码")
    check_freq: str = Field("daily", description="检查频率")
    warn_threshold: Optional[str] = Field(None, description="告警阈值")
    critical_threshold: Optional[str] = Field(None, description="严重阈值")
    collect_sql: Optional[str] = Field(None, description="采集SQL")
    auto_fix_sql: Optional[str] = Field(None, description="自动修复SQL")
    description: Optional[str] = Field(None, description="描述")


class InspectMetricUpdate(BaseModel):
    """更新巡检指标"""
    metric_name: Optional[str] = None
    check_freq: Optional[str] = None
    warn_threshold: Optional[str] = None
    critical_threshold: Optional[str] = None
    collect_sql: Optional[str] = None
    auto_fix_sql: Optional[str] = None
    is_enabled: Optional[bool] = None
    description: Optional[str] = None


class InspectionRunRequest(BaseModel):
    """执行巡检请求"""
    instance_id: int = Field(..., description="实例ID")
    modules: Optional[list[str]] = Field(None, description="检查模块列表，为空则检查全部")


# ==================== Constants ====================

MODULE_LABELS = {
    "slow_query": "慢查询",
    "index": "索引分析",
    "lock": "锁等待",
    "transaction": "长事务",
    "repl": "主从复制",
    "capacity": "容量分析"
}

STATUS_LABELS = {
    "normal": "正常",
    "warning": "警告",
    "critical": "严重",
    "error": "错误"
}


# ==================== 巡检指标管理 ====================

@router.get("/metrics", response_model=dict)
async def list_metrics(
    module: Optional[str] = None,
    is_enabled: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取巡检指标列表"""
    query = db.query(InspectMetric)
    
    if module:
        query = query.filter(InspectMetric.module == module)
    if is_enabled is not None:
        query = query.filter(InspectMetric.is_enabled == is_enabled)
    
    metrics = query.order_by(InspectMetric.module, InspectMetric.id).all()
    
    return {
        "total": len(metrics),
        "items": [{
            "id": m.id,
            "module": m.module,
            "module_label": MODULE_LABELS.get(m.module, m.module),
            "metric_name": m.metric_name,
            "metric_code": m.metric_code,
            "check_freq": m.check_freq,
            "warn_threshold": m.warn_threshold,
            "critical_threshold": m.critical_threshold,
            "collect_sql": m.collect_sql,
            "auto_fix_sql": m.auto_fix_sql,
            "is_enabled": m.is_enabled,
            "description": m.description,
            "created_at": m.created_at.isoformat() if m.created_at else None
        } for m in metrics]
    }


@router.post("/metrics", response_model=MessageResponse)
async def create_metric(
    data: InspectMetricCreate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """创建巡检指标"""
    # 检查编码是否已存在
    if db.query(InspectMetric).filter(InspectMetric.metric_code == data.metric_code).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="指标编码已存在")
    
    metric = InspectMetric(
        module=data.module,
        metric_name=data.metric_name,
        metric_code=data.metric_code,
        check_freq=data.check_freq,
        warn_threshold=data.warn_threshold,
        critical_threshold=data.critical_threshold,
        collect_sql=data.collect_sql,
        auto_fix_sql=data.auto_fix_sql,
        description=data.description
    )
    
    db.add(metric)
    db.commit()
    
    return MessageResponse(message="巡检指标创建成功")


@router.put("/metrics/{metric_id}", response_model=MessageResponse)
async def update_metric(
    metric_id: int,
    data: InspectMetricUpdate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """更新巡检指标"""
    metric = db.query(InspectMetric).filter(InspectMetric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="巡检指标不存在")
    
    if data.metric_name is not None:
        metric.metric_name = data.metric_name
    if data.check_freq is not None:
        metric.check_freq = data.check_freq
    if data.warn_threshold is not None:
        metric.warn_threshold = data.warn_threshold
    if data.critical_threshold is not None:
        metric.critical_threshold = data.critical_threshold
    if data.collect_sql is not None:
        metric.collect_sql = data.collect_sql
    if data.auto_fix_sql is not None:
        metric.auto_fix_sql = data.auto_fix_sql
    if data.is_enabled is not None:
        metric.is_enabled = data.is_enabled
    if data.description is not None:
        metric.description = data.description
    
    db.commit()
    return MessageResponse(message="巡检指标更新成功")


@router.delete("/metrics/{metric_id}", response_model=MessageResponse)
async def delete_metric(
    metric_id: int,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """删除巡检指标"""
    metric = db.query(InspectMetric).filter(InspectMetric.id == metric_id).first()
    if not metric:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="巡检指标不存在")
    
    db.delete(metric)
    db.commit()
    return MessageResponse(message="巡检指标删除成功")


# ==================== 巡检执行 ====================

@router.post("/run", response_model=dict)
async def run_inspection(
    data: InspectionRunRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """执行巡检"""
    instance = db.query(RDBInstance).filter(RDBInstance.id == data.instance_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="实例不存在")
    
    # 获取启用的巡检指标
    query = db.query(InspectMetric).filter(InspectMetric.is_enabled)
    if data.modules:
        query = query.filter(InspectMetric.module.in_(data.modules))
    
    metrics = query.all()
    
    results = []
    check_time = datetime.now()
    
    for metric in metrics:
        try:
            result = await _run_single_check(instance, metric, db, check_time)
            results.append(result)
        except Exception as e:
            results.append({
                "metric_id": metric.id,
                "metric_name": metric.metric_name,
                "module": metric.module,
                "status": "error",
                "error": str(e)
            })
    
    # 汇总统计
    normal_count = sum(1 for r in results if r.get("status") == "normal")
    warning_count = sum(1 for r in results if r.get("status") == "warning")
    critical_count = sum(1 for r in results if r.get("status") == "critical")
    error_count = sum(1 for r in results if r.get("status") == "error")
    
    return {
        "instance_id": instance.id,
        "instance_name": instance.name,
        "check_time": check_time.isoformat(),
        "total_checks": len(results),
        "normal_count": normal_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "error_count": error_count,
        "results": results
    }


async def _run_single_check(instance: RDBInstance, metric: InspectMetric, db: Session, check_time: datetime) -> dict[str, Any]:
    """执行单个巡检检查"""
    
    status = "normal"
    actual_value = None
    result_detail = {}
    suggestion = None
    
    # 根据模块执行不同的检查逻辑
    if metric.module == "slow_query":
        # 检查慢查询
        slow_query_count = db.query(SlowQuery).filter(
            SlowQuery.instance_id == instance.id,
            SlowQuery.last_seen >= check_time - timedelta(hours=24)
        ).count()
        
        actual_value = str(slow_query_count)
        
        warn_threshold = int(metric.warn_threshold) if metric.warn_threshold else 10
        critical_threshold = int(metric.critical_threshold) if metric.critical_threshold else 50
        
        if slow_query_count >= critical_threshold:
            status = "critical"
            suggestion = f"24小时内慢查询数量({slow_query_count})超过严重阈值({critical_threshold})，建议优化高频慢查询"
        elif slow_query_count >= warn_threshold:
            status = "warning"
            suggestion = f"24小时内慢查询数量({slow_query_count})超过警告阈值({warn_threshold})，建议关注慢查询情况"
        
        result_detail = {"slow_query_count": slow_query_count}
    
    elif metric.module == "index":
        # 检查索引问题
        index_issues = db.query(IndexAnalysis).filter(
            IndexAnalysis.instance_id == instance.id
        ).count()
        
        redundant_count = db.query(IndexAnalysis).filter(
            IndexAnalysis.instance_id == instance.id,
            IndexAnalysis.issue_type == "redundant"
        ).count()
        
        unused_count = db.query(IndexAnalysis).filter(
            IndexAnalysis.instance_id == instance.id,
            IndexAnalysis.issue_type == "unused"
        ).count()
        
        actual_value = str(index_issues)
        
        warn_threshold = int(metric.warn_threshold) if metric.warn_threshold else 5
        critical_threshold = int(metric.critical_threshold) if metric.critical_threshold else 20
        
        if index_issues >= critical_threshold:
            status = "critical"
            suggestion = f"发现{index_issues}个索引问题(冗余:{redundant_count}, 未使用:{unused_count})，建议清理冗余和未使用索引"
        elif index_issues >= warn_threshold:
            status = "warning"
            suggestion = f"发现{index_issues}个索引问题，建议关注并优化"
        
        result_detail = {"total_issues": index_issues, "redundant": redundant_count, "unused": unused_count}
    
    elif metric.module == "lock":
        # 检查锁等待
        lock_count = db.query(LockWait).filter(
            LockWait.instance_id == instance.id,
            LockWait.status == "active",
            LockWait.created_at >= check_time - timedelta(hours=1)
        ).count()
        
        actual_value = str(lock_count)
        
        warn_threshold = int(metric.warn_threshold) if metric.warn_threshold else 3
        critical_threshold = int(metric.critical_threshold) if metric.critical_threshold else 10
        
        if lock_count >= critical_threshold:
            status = "critical"
            suggestion = f"发现{lock_count}个活跃锁等待，建议排查阻塞事务"
        elif lock_count >= warn_threshold:
            status = "warning"
            suggestion = f"发现{lock_count}个锁等待，建议关注"
        
        result_detail = {"lock_wait_count": lock_count}
    
    elif metric.module == "transaction":
        # 检查长事务
        long_trx_count = db.query(LongTransaction).filter(
            LongTransaction.instance_id == instance.id,
            LongTransaction.status == "active"
        ).count()
        
        actual_value = str(long_trx_count)
        
        warn_threshold = int(metric.warn_threshold) if metric.warn_threshold else 1
        critical_threshold = int(metric.critical_threshold) if metric.critical_threshold else 5
        
        if long_trx_count >= critical_threshold:
            status = "critical"
            suggestion = f"发现{long_trx_count}个活跃长事务，建议Kill或优化"
        elif long_trx_count >= warn_threshold:
            status = "warning"
            suggestion = f"发现{long_trx_count}个长事务，建议关注"
        
        result_detail = {"long_transaction_count": long_trx_count}
    
    elif metric.module == "repl":
        # 检查主从复制
        repl_status = db.query(ReplicationStatus).filter(
            ReplicationStatus.instance_id == instance.id
        ).order_by(desc(ReplicationStatus.check_time)).first()
        
        if repl_status:
            delay = repl_status.seconds_behind_master or 0
            io_running = repl_status.slave_io_running == "Yes"
            sql_running = repl_status.slave_sql_running == "Yes"
            
            actual_value = f"IO:{io_running}, SQL:{sql_running}, Delay:{delay}s"
            
            if not io_running or not sql_running:
                status = "critical"
                suggestion = "主从复制线程异常，请立即检查"
            elif delay > (int(metric.critical_threshold) if metric.critical_threshold else 60):
                status = "critical"
                suggestion = f"主从延迟{delay}秒，超过严重阈值"
            elif delay > (int(metric.warn_threshold) if metric.warn_threshold else 10):
                status = "warning"
                suggestion = f"主从延迟{delay}秒，建议关注"
            
            result_detail = {
                "io_running": io_running,
                "sql_running": sql_running,
                "seconds_behind": delay
            }
        else:
            status = "error"
            actual_value = "无复制状态数据"
            result_detail = {"error": "未找到复制状态记录"}
    
    else:
        # 默认检查
        status = "normal"
        actual_value = "未实现检查逻辑"
    
    # 保存结果
    inspect_result = InspectResult(
        instance_id=instance.id,
        metric_id=metric.id,
        check_time=check_time,
        status=status,
        actual_value=actual_value,
        result_detail=result_detail,
        suggestion=suggestion
    )
    db.add(inspect_result)
    db.commit()
    
    return {
        "metric_id": metric.id,
        "metric_name": metric.metric_name,
        "module": metric.module,
        "module_label": MODULE_LABELS.get(metric.module, metric.module),
        "status": status,
        "status_label": STATUS_LABELS.get(status, status),
        "actual_value": actual_value,
        "result_detail": result_detail,
        "suggestion": suggestion,
        "check_time": check_time.isoformat()
    }


# ==================== 巡检结果查询 ====================

@router.get("/results", response_model=dict)
async def list_results(
    instance_id: Optional[int] = None,
    module: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取巡检结果列表"""
    query = db.query(InspectResult)
    
    if instance_id:
        query = query.filter(InspectResult.instance_id == instance_id)
    if status:
        query = query.filter(InspectResult.status == status)
    if start_time:
        query = query.filter(InspectResult.check_time >= start_time)
    if end_time:
        query = query.filter(InspectResult.check_time <= end_time)
    
    if module:
        query = query.join(InspectMetric).filter(InspectMetric.module == module)
    
    total = query.count()
    results = query.order_by(desc(InspectResult.check_time)).offset((page - 1) * limit).limit(limit).all()
    
    # 获取实例和指标信息
    instance_ids = [r.instance_id for r in results]
    instances = {i.id: i.name for i in db.query(RDBInstance).filter(RDBInstance.id.in_(instance_ids)).all()} if instance_ids else {}
    
    metric_ids = [r.metric_id for r in results]
    metrics = {m.id: {"name": m.metric_name, "module": m.module} for m in db.query(InspectMetric).filter(InspectMetric.id.in_(metric_ids)).all()} if metric_ids else {}
    
    items = []
    for r in results:
        metric_info = metrics.get(r.metric_id, {})
        items.append({
            "id": r.id,
            "instance_id": r.instance_id,
            "instance_name": instances.get(r.instance_id),
            "metric_id": r.metric_id,
            "metric_name": metric_info.get("name"),
            "module": metric_info.get("module"),
            "module_label": MODULE_LABELS.get(metric_info.get("module"), metric_info.get("module")),
            "status": r.status,
            "status_label": STATUS_LABELS.get(r.status, r.status),
            "actual_value": r.actual_value,
            "result_detail": r.result_detail,
            "suggestion": r.suggestion,
            "is_fixed": r.is_fixed,
            "fixed_at": r.fixed_at.isoformat() if r.fixed_at else None,
            "check_time": r.check_time.isoformat() if r.check_time else None
        })
    
    return {"total": total, "items": items}


# ==================== 巡检报告 ====================

@router.get("/reports", response_model=dict)
async def list_reports(
    instance_id: Optional[int] = None,
    report_type: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取巡检报告列表"""
    query = db.query(InspectionReport)
    
    if instance_id:
        query = query.filter(InspectionReport.instance_id == instance_id)
    if report_type:
        query = query.filter(InspectionReport.report_type == report_type)
    
    total = query.count()
    reports = query.order_by(desc(InspectionReport.created_at)).offset((page - 1) * limit).limit(limit).all()
    
    # 获取实例名称
    instance_ids = [r.instance_id for r in reports]
    instances = {i.id: i.name for i in db.query(RDBInstance).filter(RDBInstance.id.in_(instance_ids)).all()} if instance_ids else {}
    
    items = []
    for r in reports:
        items.append({
            "id": r.id,
            "instance_id": r.instance_id,
            "instance_name": instances.get(r.instance_id),
            "report_type": r.report_type,
            "status": r.status,
            "summary": r.summary,
            "risk_count_high": r.risk_count_high,
            "risk_count_medium": r.risk_count_medium,
            "risk_count_low": r.risk_count_low,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    
    return {"total": total, "items": items}


@router.get("/modules/list")
async def get_modules():
    """获取巡检模块列表"""
    return [
        {"value": "slow_query", "label": "慢查询"},
        {"value": "index", "label": "索引分析"},
        {"value": "lock", "label": "锁等待"},
        {"value": "transaction", "label": "长事务"},
        {"value": "repl", "label": "主从复制"},
        {"value": "capacity", "label": "容量分析"}
    ]
