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
from datetime import datetime
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


# ==================== 分析历史管理 ====================

class AnalysisHistoryItem(BaseModel):
    """分析历史项"""
    id: int
    instance_id: int
    instance_name: str
    database_name: Optional[str] = None
    sql_fingerprint: str
    sql_sample: Optional[str] = None
    analysis_type: str
    analysis_content: Optional[str] = None
    issues: list = []
    issues_count: int = 0
    suggestions: list = []
    suggestions_count: int = 0
    analyzed_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisHistoryListResponse(BaseModel):
    """分析历史列表响应"""
    items: list
    total: int


class AnalysisDetailResponse(BaseModel):
    """分析详情响应"""
    id: int
    instance_id: int
    instance_name: str
    database_name: Optional[str] = None
    sql_fingerprint: str
    sql_sample: Optional[str] = None
    analysis_type: str
    analysis_content: Optional[str] = None
    issues: list = []
    issues_count: int = 0
    suggestions: list = []
    suggestions_count: int = 0
    explain_result: Optional[list] = None
    analyzed_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/analysis-history", response_model=AnalysisHistoryListResponse)
def list_analysis_history(
    instance_id: Optional[int] = Query(None, description="实例ID"),
    analysis_type: Optional[str] = Query(None, description="分析类型"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取分析历史列表"""
    service = SQLOptimizationService(db)
    history, total = service.list_analysis_history(
        instance_id=instance_id,
        analysis_type=analysis_type,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size
    )
    
    return AnalysisHistoryListResponse(items=history, total=total)


@router.get("/analysis-history/{history_id}", response_model=AnalysisDetailResponse)
def get_analysis_detail(
    history_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取分析历史详情"""
    service = SQLOptimizationService(db)
    detail = service.get_analysis_detail(history_id)
    
    if not detail:
        raise HTTPException(status_code=404, detail="分析历史不存在")
    
    return AnalysisDetailResponse(**detail)


# ==================== 慢日志文件上传 ====================

import os
import hashlib
from datetime import datetime, timedelta
from fastapi import UploadFile, File
from pathlib import Path

# 文件存储目录
UPLOAD_DIR = Path("/tmp/slow_log_files")


class SlowLogFileResponse(BaseModel):
    """慢日志文件响应"""
    id: int
    instance_id: int
    instance_name: str
    file_name: str
    file_size: int
    file_hash: str
    parse_status: str
    parse_error: Optional[str] = None
    parsed_count: int
    analyze_status: str
    analyzed_count: int
    suggestion_count: int
    uploaded_by: Optional[str] = None
    expire_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class SlowLogFileListResponse(BaseModel):
    """慢日志文件列表响应"""
    items: list
    total: int


@router.post("/upload-slow-log", response_model=SlowLogFileResponse, status_code=201)
async def upload_slow_log_file(
    instance_id: int = Query(..., description="实例ID"),
    file: UploadFile = File(..., description="慢日志文件"),
    auto_analyze: bool = Query(True, description="是否自动分析"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    上传慢日志文件进行分析
    
    支持的文件格式：
    - MySQL 慢查询日志 (.log, .txt)
    - PostgreSQL 慢查询日志 (.log, .txt)
    
    文件保留策略：30天后自动删除
    """
    service = SQLOptimizationService(db)
    
    try:
        result = await service.upload_slow_log_file(
            instance_id=instance_id,
            file=file,
            auto_analyze=auto_analyze,
            current_user=current_user
        )
        return SlowLogFileResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/slow-log-files", response_model=SlowLogFileListResponse)
def list_slow_log_files(
    instance_id: Optional[int] = Query(None, description="实例ID"),
    parse_status: Optional[str] = Query(None, description="解析状态"),
    analyze_status: Optional[str] = Query(None, description="分析状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取慢日志文件列表"""
    service = SQLOptimizationService(db)
    files, total = service.list_slow_log_files(
        instance_id=instance_id,
        parse_status=parse_status,
        analyze_status=analyze_status,
        page=page,
        page_size=page_size
    )
    return SlowLogFileListResponse(items=files, total=total)


@router.get("/slow-log-files/{file_id}", response_model=SlowLogFileResponse)
def get_slow_log_file(
    file_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取慢日志文件详情"""
    service = SQLOptimizationService(db)
    file_info = service.get_slow_log_file(file_id)
    
    if not file_info:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return SlowLogFileResponse(**file_info)


@router.post("/slow-log-files/{file_id}/analyze")
def analyze_slow_log_file(
    file_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """手动触发分析慢日志文件"""
    service = SQLOptimizationService(db)
    
    try:
        result = service.analyze_slow_log_file(file_id, current_user)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/slow-log-files/{file_id}")
def delete_slow_log_file(
    file_id: int,
    db=Depends(get_db),
    current_user: User = Depends(get_operator)
):
    """删除慢日志文件"""
    service = SQLOptimizationService(db)
    
    success = service.delete_slow_log_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return {"message": "删除成功"}
