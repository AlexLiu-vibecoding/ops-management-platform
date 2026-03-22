"""
慢查询监控 API

提供慢查询的查询、分析和优化建议接口
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging

from app.database import get_db
from app.models import (
    SlowQuery, Instance, MonitorSwitch, 
    MonitorType, User
)
from app.schemas import SlowQueryResponse, MessageResponse
from app.deps import get_current_user
from app.services.slow_query_analyzer import slow_query_analyzer
from app.services.slow_query_collector import slow_query_collector

router = APIRouter(prefix="/slow-query", tags=["慢查询监控"])
logger = logging.getLogger(__name__)


# ============ API 路由 ============

@router.get("/{instance_id}", response_model=List[SlowQueryResponse])
async def list_slow_queries(
    instance_id: int,
    limit: int = 100,
    min_time: float = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取实例的慢查询列表
    
    Args:
        instance_id: 实例ID
        limit: 返回记录数
        min_time: 最小执行时间（秒）
    """
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 检查监控开关
    switch = db.query(MonitorSwitch).filter(
        MonitorSwitch.instance_id == instance_id,
        MonitorSwitch.monitor_type == MonitorType.SLOW_QUERY
    ).first()
    
    if not switch or not switch.enabled:
        return []
    
    # 查询慢查询
    query = db.query(SlowQuery).filter(
        SlowQuery.instance_id == instance_id
    )
    
    if min_time:
        query = query.filter(SlowQuery.query_time >= min_time)
    
    queries = query.order_by(SlowQuery.query_time.desc()).limit(limit).all()
    return [SlowQueryResponse.from_orm(q) for q in queries]


@router.get("/{instance_id}/top", response_model=List[SlowQueryResponse])
async def get_top_slow_queries(
    instance_id: int,
    hours: int = 24,
    top_n: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取Top N慢查询
    
    Args:
        instance_id: 实例ID
        hours: 时间范围（小时）
        top_n: 返回记录数
    """
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    queries = db.query(SlowQuery).filter(
        SlowQuery.instance_id == instance_id,
        SlowQuery.last_seen >= start_time
    ).order_by(SlowQuery.query_time.desc()).limit(top_n).all()
    
    return [SlowQueryResponse.from_orm(q) for q in queries]


@router.get("/{instance_id}/statistics", response_model=dict)
async def get_slow_query_statistics(
    instance_id: int,
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取慢查询统计
    
    Args:
        instance_id: 实例ID
        hours: 时间范围（小时）
    """
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    stats = db.query(
        func.count(SlowQuery.id).label('total_count'),
        func.sum(SlowQuery.execution_count).label('total_executions'),
        func.max(SlowQuery.query_time).label('max_time'),
        func.avg(SlowQuery.query_time).label('avg_time')
    ).filter(
        SlowQuery.instance_id == instance_id,
        SlowQuery.last_seen >= start_time
    ).first()
    
    return {
        "total_count": stats.total_count or 0,
        "total_executions": stats.total_executions or 0,
        "max_time": float(stats.max_time) if stats.max_time else 0,
        "avg_time": float(stats.avg_time) if stats.avg_time else 0
    }


@router.get("/{instance_id}/analysis/{query_id}", response_model=dict)
async def analyze_slow_query(
    instance_id: int,
    query_id: int,
    use_llm: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    分析慢查询
    
    Args:
        instance_id: 实例ID
        query_id: 慢查询ID
        use_llm: 是否使用大模型分析（默认True）
    """
    slow_query = db.query(SlowQuery).filter(
        SlowQuery.id == query_id,
        SlowQuery.instance_id == instance_id
    ).first()
    
    if not slow_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="慢查询记录不存在"
        )
    
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 执行 EXPLAIN 分析（使用服务）
    explain_result = await slow_query_analyzer.execute_explain(
        instance=instance,
        sql=slow_query.sql_sample,
        database_name=slow_query.database_name
    )
    
    # 基础建议（使用服务）
    basic_suggestions = slow_query_analyzer.generate_suggestions(
        explain_result=explain_result,
        slow_query=slow_query
    )
    
    # LLM 分析（使用服务）
    llm_analysis = None
    if use_llm and slow_query.sql_sample:
        llm_analysis = await slow_query_analyzer.analyze_with_llm(
            sql=slow_query.sql_sample,
            explain_result=explain_result,
            slow_query=slow_query
        )
    
    return {
        "query_id": slow_query.id,
        "sql_fingerprint": slow_query.sql_fingerprint,
        "sql_sample": slow_query.sql_sample,
        "database_name": slow_query.database_name,
        "query_time": slow_query.query_time,
        "lock_time": slow_query.lock_time,
        "rows_sent": slow_query.rows_sent,
        "rows_examined": slow_query.rows_examined,
        "execution_count": slow_query.execution_count,
        "explain": explain_result.get("explain"),
        "explain_json": explain_result.get("explain_json"),
        "warnings": explain_result.get("warnings", []),
        "suggestions": basic_suggestions,
        "llm_analysis": llm_analysis
    }


@router.post("/{instance_id}/run-explain", response_model=dict)
async def run_explain(
    instance_id: int,
    sql: str,
    database_name: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    执行 EXPLAIN 分析指定 SQL
    
    Args:
        instance_id: 实例ID
        sql: SQL语句
        database_name: 数据库名
    """
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 执行 EXPLAIN 分析（使用服务）
    explain_result = await slow_query_analyzer.execute_explain(
        instance=instance,
        sql=sql,
        database_name=database_name
    )
    
    # 生成建议（使用服务）
    suggestions = slow_query_analyzer.generate_suggestions(explain_result)
    
    return {
        "explain": explain_result.get("explain"),
        "explain_json": explain_result.get("explain_json"),
        "warnings": explain_result.get("warnings", []),
        "error": explain_result.get("error"),
        "suggestions": suggestions
    }


@router.get("/{instance_id}/performance-schema-status", response_model=dict)
async def check_performance_schema_status(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    检查 performance_schema 状态
    
    Args:
        instance_id: 实例ID
    """
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 使用服务检查性能模式状态
    return await slow_query_collector.check_performance_schema_enabled(instance)


@router.post("/{instance_id}/sync", response_model=dict)
async def sync_slow_queries(
    instance_id: int,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    从 performance_schema 同步慢查询
    
    Args:
        instance_id: 实例ID
        limit: 同步记录数限制
    """
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 使用服务同步慢查询
    result = await slow_query_collector.sync_slow_queries_to_db(
        instance=instance,
        db_session=db,
        limit=limit
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "同步失败")
        )
    
    return result


@router.get("/{instance_id}/databases", response_model=List[str])
async def get_instance_databases(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取实例的数据库列表
    
    Args:
        instance_id: 实例ID
    """
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 使用服务获取数据库列表
    return await slow_query_collector.get_instance_databases(instance)


@router.get("/{instance_id}/realtime", response_model=List[dict])
async def get_realtime_slow_queries(
    instance_id: int,
    limit: int = 50,
    min_exec_time: float = 1.0,
    database_name: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    从 performance_schema 获取实时慢查询
    
    Args:
        instance_id: 实例ID
        limit: 返回记录数
        min_exec_time: 最小执行时间（秒）
        database_name: 过滤特定数据库
    """
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 使用服务获取实时慢查询
    return await slow_query_collector.fetch_from_performance_schema(
        instance=instance,
        limit=limit,
        min_exec_time=min_exec_time,
        database_name=database_name
    )


@router.get("/{instance_id}/statement-analysis", response_model=List[dict])
async def get_statement_analysis(
    instance_id: int,
    limit: int = 100,
    database_name: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    从 sys.statement_analysis 获取分析数据
    
    Args:
        instance_id: 实例ID
        limit: 返回记录数
        database_name: 过滤特定数据库
    """
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 使用服务获取语句分析
    return await slow_query_collector.fetch_from_statement_analysis(
        instance=instance,
        limit=limit,
        database_name=database_name
    )


@router.delete("/{query_id}", response_model=MessageResponse)
async def delete_slow_query(
    query_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除慢查询记录
    
    Args:
        query_id: 慢查询ID
    """
    slow_query = db.query(SlowQuery).filter(SlowQuery.id == query_id).first()
    if not slow_query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="慢查询记录不存在"
        )
    
    db.delete(slow_query)
    db.commit()
    
    return MessageResponse(message="删除成功")
