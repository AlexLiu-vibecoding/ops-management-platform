"""
SQL 优化闭环 API

提供 SQL 性能优化闭环的接口：
- 采集任务管理
- 优化建议管理
- 手动分析
- 一键提交变更
- 效果验证
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.database import get_db
from app.deps import get_current_user, get_operator
from app.models import User
from app.schemas import (
    CollectionTaskCreate, CollectionTaskUpdate,
    CollectionTaskResponse, CollectionTaskListResponse,
    OptimizationSuggestionResponse, SuggestionListResponse,
    AdoptSuggestionResponse, RejectSuggestionRequest,
    VerifySuggestionResponse, ManualAnalyzeRequest,
    ManualCollectionResponse
)
from app.services.sql_optimization_service import SQLOptimizationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sql-optimization", tags=["SQL优化闭环"])


# ==================== 采集任务管理 ====================

@router.get("/tasks", response_model=CollectionTaskListResponse)
def list_collection_tasks(
    instance_id: Optional[int] = Query(None, description="实例ID"),
    enabled: Optional[bool] = Query(None, description="启用状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取采集任务列表"""
    service = SQLOptimizationService(db)
    tasks, total = service.list_collection_tasks(
        instance_id=instance_id,
        enabled=enabled,
        page=page,
        page_size=page_size
    )

    # 补充实例名称
    items = []
    for task in tasks:
        task_dict = {
            "id": task.id,
            "instance_id": task.instance_id,
            "instance_name": task.rdb_instance.name if task.rdb_instance else None,
            "enabled": task.enabled,
            "cron_expression": task.cron_expression,
            "min_exec_time": float(task.min_exec_time) if task.min_exec_time else 1.0,
            "top_n": task.top_n,
            "auto_analyze": task.auto_analyze,
            "analyze_threshold": task.analyze_threshold,
            "llm_analysis": task.llm_analysis,
            "last_run_at": task.last_run_at,
            "last_run_status": task.last_run_status,
            "last_collected_count": task.last_collected_count,
            "total_collected_count": task.total_collected_count,
            "created_at": task.created_at
        }
        items.append(CollectionTaskResponse(**task_dict))

    return CollectionTaskListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/tasks", response_model=CollectionTaskResponse, status_code=201)
def create_collection_task(
    task_data: CollectionTaskCreate,
    db=Depends(get_db),
    current_user: User = Depends(get_operator)
):
    """创建采集任务"""
    service = SQLOptimizationService(db)

    try:
        task = service.create_collection_task(task_data, current_user)

        return CollectionTaskResponse(
            id=task.id,
            instance_id=task.instance_id,
            instance_name=task.rdb_instance.name if task.rdb_instance else None,
            enabled=task.enabled,
            cron_expression=task.cron_expression,
            min_exec_time=float(task.min_exec_time) if task.min_exec_time else 1.0,
            top_n=task.top_n,
            auto_analyze=task.auto_analyze,
            analyze_threshold=task.analyze_threshold,
            llm_analysis=task.llm_analysis,
            last_run_at=task.last_run_at,
            last_run_status=task.last_run_status,
            last_collected_count=task.last_collected_count,
            total_collected_count=task.total_collected_count,
            created_at=task.created_at
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tasks/{task_id}", response_model=CollectionTaskResponse)
def get_collection_task(
    task_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取采集任务详情"""
    service = SQLOptimizationService(db)
    task = service._get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return CollectionTaskResponse(
        id=task.id,
        instance_id=task.instance_id,
        instance_name=task.rdb_instance.name if task.rdb_instance else None,
        enabled=task.enabled,
        cron_expression=task.cron_expression,
        min_exec_time=float(task.min_exec_time) if task.min_exec_time else 1.0,
        top_n=task.top_n,
        auto_analyze=task.auto_analyze,
        analyze_threshold=task.analyze_threshold,
        llm_analysis=task.llm_analysis,
        last_run_at=task.last_run_at,
        last_run_status=task.last_run_status,
        last_collected_count=task.last_collected_count,
        total_collected_count=task.total_collected_count,
        created_at=task.created_at
    )


@router.put("/tasks/{task_id}", response_model=CollectionTaskResponse)
def update_collection_task(
    task_id: int,
    task_data: CollectionTaskUpdate,
    db=Depends(get_db),
    current_user: User = Depends(get_operator)
):
    """更新采集任务"""
    service = SQLOptimizationService(db)

    task = service.update_collection_task(task_id, task_data)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return CollectionTaskResponse(
        id=task.id,
        instance_id=task.instance_id,
        instance_name=task.rdb_instance.name if task.rdb_instance else None,
        enabled=task.enabled,
        cron_expression=task.cron_expression,
        min_exec_time=float(task.min_exec_time) if task.min_exec_time else 1.0,
        top_n=task.top_n,
        auto_analyze=task.auto_analyze,
        analyze_threshold=task.analyze_threshold,
        llm_analysis=task.llm_analysis,
        last_run_at=task.last_run_at,
        last_run_status=task.last_run_status,
        last_collected_count=task.last_collected_count,
        total_collected_count=task.total_collected_count,
        created_at=task.created_at
    )


@router.delete("/tasks/{task_id}")
def delete_collection_task(
    task_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_operator)
):
    """删除采集任务"""
    service = SQLOptimizationService(db)

    success = service.delete_collection_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {"message": "删除成功"}


@router.post("/tasks/{task_id}/run", response_model=ManualCollectionResponse)
def run_collection_task(
    task_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_operator)
):
    """手动触发采集"""
    service = SQLOptimizationService(db)

    try:
        result = service.run_collection(task_id)

        return ManualCollectionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 优化建议管理 ====================

@router.get("/suggestions", response_model=SuggestionListResponse)
def list_suggestions(
    instance_id: Optional[int] = Query(None, description="实例ID"),
    status: Optional[str] = Query(None, description="状态: pending/adopted/rejected/expired"),
    risk_level: Optional[str] = Query(None, description="风险等级: low/medium/high"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取优化建议列表"""
    service = SQLOptimizationService(db)
    suggestions, total = service.list_suggestions(
        instance_id=instance_id,
        status=status,
        risk_level=risk_level,
        page=page,
        page_size=page_size
    )

    # 补充实例名称
    items = []
    for s in suggestions:
        s_dict = {
            "id": s.id,
            "instance_id": s.instance_id,
            "instance_name": s.rdb_instance.name if s.rdb_instance else None,
            "database_name": s.database_name,
            "slow_query_id": s.slow_query_id,
            "sql_fingerprint": s.sql_fingerprint,
            "sql_sample": s.sql_sample,
            "issues": s.issues or [],
            "suggestions": s.suggestions or [],
            "suggested_sql": s.suggested_sql,
            "index_ddl": s.index_ddl,
            "rollback_sql": s.rollback_sql,
            "risk_level": s.risk_level,
            "confidence": float(s.confidence) if s.confidence else None,
            "expected_improvement": s.expected_improvement,
            "status": s.status,
            "approval_id": s.approval_id,
            "adopted_by": s.adopted_by,
            "adopted_at": s.adopted_at,
            "before_avg_time": float(s.before_avg_time) if s.before_avg_time else None,
            "after_avg_time": float(s.after_avg_time) if s.after_avg_time else None,
            "actual_improvement": float(s.actual_improvement) if s.actual_improvement else None,
            "created_at": s.created_at
        }
        items.append(OptimizationSuggestionResponse(**s_dict))

    return SuggestionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/suggestions/{suggestion_id}", response_model=OptimizationSuggestionResponse)
def get_suggestion(
    suggestion_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取优化建议详情"""
    service = SQLOptimizationService(db)
    s = service.get_suggestion(suggestion_id)

    if not s:
        raise HTTPException(status_code=404, detail="建议不存在")

    return OptimizationSuggestionResponse(
        id=s.id,
        instance_id=s.instance_id,
        instance_name=s.rdb_instance.name if s.rdb_instance else None,
        database_name=s.database_name,
        slow_query_id=s.slow_query_id,
        sql_fingerprint=s.sql_fingerprint,
        sql_sample=s.sql_sample,
        issues=s.issues or [],
        suggestions=s.suggestions or [],
        suggested_sql=s.suggested_sql,
        index_ddl=s.index_ddl,
        rollback_sql=s.rollback_sql,
        risk_level=s.risk_level,
        confidence=float(s.confidence) if s.confidence else None,
        expected_improvement=s.expected_improvement,
        status=s.status,
        approval_id=s.approval_id,
        adopted_by=s.adopted_by,
        adopted_at=s.adopted_at,
        before_avg_time=float(s.before_avg_time) if s.before_avg_time else None,
        after_avg_time=float(s.after_avg_time) if s.after_avg_time else None,
        actual_improvement=float(s.actual_improvement) if s.actual_improvement else None,
        created_at=s.created_at
    )


@router.post("/suggestions/{suggestion_id}/adopt", response_model=AdoptSuggestionResponse)
def adopt_suggestion(
    suggestion_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_operator)
):
    """采用建议，创建变更申请"""
    service = SQLOptimizationService(db)

    try:
        result = service.adopt_suggestion(suggestion_id, current_user)
        return AdoptSuggestionResponse(**result)

    except ValueError as e:
        error_msg = str(e)

        # 返回更友好的错误信息
        if "状态不是 pending" in error_msg:
            return JSONResponse(
                status_code=400,
                content={"error": "ALREADY_ADOPTED", "message": "该建议已被采用"}
            )
        elif "没有可执行" in error_msg:
            return JSONResponse(
                status_code=400,
                content={"error": "NO_INDEX_DDL", "message": "该建议没有可执行的DDL语句"}
            )
        else:
            raise HTTPException(status_code=400, detail=error_msg)


@router.post("/suggestions/{suggestion_id}/reject", response_model=OptimizationSuggestionResponse)
def reject_suggestion(
    suggestion_id: int,
    request: RejectSuggestionRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_operator)
):
    """拒绝建议"""
    service = SQLOptimizationService(db)

    try:
        s = service.reject_suggestion(suggestion_id, request.reason, current_user)

        return OptimizationSuggestionResponse(
            id=s.id,
            instance_id=s.instance_id,
            instance_name=s.rdb_instance.name if s.rdb_instance else None,
            database_name=s.database_name,
            slow_query_id=s.slow_query_id,
            sql_fingerprint=s.sql_fingerprint,
            sql_sample=s.sql_sample,
            issues=s.issues or [],
            suggestions=s.suggestions or [],
            suggested_sql=s.suggested_sql,
            index_ddl=s.index_ddl,
            rollback_sql=s.rollback_sql,
            risk_level=s.risk_level,
            confidence=float(s.confidence) if s.confidence else None,
            expected_improvement=s.expected_improvement,
            status=s.status,
            approval_id=s.approval_id,
            adopted_by=s.adopted_by,
            adopted_at=s.adopted_at,
            before_avg_time=float(s.before_avg_time) if s.before_avg_time else None,
            after_avg_time=float(s.after_avg_time) if s.after_avg_time else None,
            actual_improvement=float(s.actual_improvement) if s.actual_improvement else None,
            created_at=s.created_at
        )

    except ValueError as e:
        error_msg = str(e)

        if "状态不是 pending" in error_msg:
            return JSONResponse(
                status_code=400,
                content={"error": "ALREADY_PROCESSED", "message": "该建议已被处理"}
            )
        else:
            raise HTTPException(status_code=400, detail=error_msg)


@router.post("/suggestions/{suggestion_id}/verify", response_model=VerifySuggestionResponse)
def verify_suggestion(
    suggestion_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_operator)
):
    """验证优化效果"""
    service = SQLOptimizationService(db)

    try:
        result = service.verify_suggestion(suggestion_id)
        return VerifySuggestionResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/suggestions/analyze")
def manual_analyze(
    request: ManualAnalyzeRequest,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动分析 SQL"""
    service = SQLOptimizationService(db)

    try:
        result = service.manual_analyze(
            instance_id=request.instance_id,
            sql_text=request.sql_text,
            database_name=request.database_name
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
