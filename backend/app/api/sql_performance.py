"""
SQL 性能对比 API

提供 SQL 性能采集、对比和报告导出的 API 接口。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.services.sql_performance_collector import SQLPerformanceCollector
from app.services.sql_performance_comparator import SQLPerformanceComparator
from app.models.sql_performance import SQLPerformanceRecord, SQLPerformanceComparison
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sql-performance", tags=["SQL性能对比"])


# ========== Pydantic Schemas ==========

class ExecuteSQLRequest(BaseModel):
    """执行 SQL 请求"""
    instance_id: int = Field(..., description="数据库实例 ID")
    sql_text: str = Field(..., description="SQL 语句")
    version: str = Field(default="original", description="版本标识")
    version_description: str = Field(default="", description="版本描述")


class SQLPerformanceRecordSchema(BaseModel):
    """SQL 性能记录响应"""
    id: int
    instance_id: int
    sql_text: str
    sql_hash: str
    version: str
    version_description: Optional[str]
    execution_time_ms: Optional[float]
    rows_scanned: Optional[int]
    rows_returned: Optional[int]
    buffer_pool_reads: Optional[int]
    disk_reads: Optional[int]
    cpu_time_ms: Optional[float]
    io_time_ms: Optional[float]
    memory_mb: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


class CompareRequest(BaseModel):
    """对比请求"""
    source_id: int = Field(..., description="优化前记录 ID")
    target_id: int = Field(..., description="优化后记录 ID")


class ComparisonSummarySchema(BaseModel):
    """对比摘要"""
    id: int
    overall_improvement: Optional[float]
    execution_time_improvement: Optional[float]
    analysis: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ComparisonDetailSchema(BaseModel):
    """对比详情"""
    id: int
    source_id: int
    target_id: int
    overall_improvement: Optional[float]
    execution_time_improvement: Optional[float]
    rows_scanned_improvement: Optional[float]
    cpu_time_improvement: Optional[float]
    io_time_improvement: Optional[float]
    analysis: str
    recommendations: Optional[List[dict]]
    report_data: Optional[dict]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ========== API Endpoints ==========

@router.post("/execute", response_model=SQLPerformanceRecordSchema, status_code=status.HTTP_201_CREATED)
async def execute_sql(
    request: ExecuteSQLRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """执行 SQL 并采集性能数据
    
    执行 SQL 并收集详细的性能指标，包括执行时间、扫描行数、CPU/IO 占用等。
    """
    try:
        collector = SQLPerformanceCollector(db)
        record = collector.collect(
            instance_id=request.instance_id,
            sql_text=request.sql_text,
            version=request.version,
            version_description=request.version_description,
            user_id=current_user.id
        )
        return record
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to execute SQL: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/records", response_model=List[SQLPerformanceRecordSchema])
async def list_records(
    instance_id: Optional[int] = None,
    sql_hash: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列出性能记录
    
    根据条件筛选 SQL 性能记录。
    """
    try:
        collector = SQLPerformanceCollector(db)
        records = collector.list_records(
            instance_id=instance_id,
            sql_hash=sql_hash,
            limit=limit
        )
        return records
    except Exception as e:
        logger.error(f"Failed to list records: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/records/{record_id}", response_model=SQLPerformanceRecordSchema)
async def get_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取性能记录详情
    
    获取指定记录的详细性能指标。
    """
    try:
        collector = SQLPerformanceCollector(db)
        record = collector.get_record(record_id)
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
        return record
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get record: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/compare", response_model=ComparisonDetailSchema, status_code=status.HTTP_201_CREATED)
async def compare_performance(
    request: CompareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """对比性能记录
    
    对比优化前后的 SQL 性能，生成分析报告和可视化数据。
    """
    try:
        comparator = SQLPerformanceComparator(db)
        comparison = comparator.compare(
            source_id=request.source_id,
            target_id=request.target_id,
            user_id=current_user.id
        )
        return comparison
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to compare: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/comparisons", response_model=List[ComparisonSummarySchema])
async def list_comparisons(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列出对比记录
    
    列出当前用户的所有对比记录。
    """
    try:
        comparator = SQLPerformanceComparator(db)
        comparisons = comparator.list_comparisons(user_id=current_user.id)
        return comparisons
    except Exception as e:
        logger.error(f"Failed to list comparisons: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/comparisons/{comparison_id}", response_model=ComparisonDetailSchema)
async def get_comparison(
    comparison_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取对比详情
    
    获取指定对比的详细分析报告和可视化数据。
    """
    try:
        comparator = SQLPerformanceComparator(db)
        comparison = comparator.get_comparison(comparison_id)
        if not comparison:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comparison not found")
        return comparison
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get comparison: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/comparisons/{comparison_id}/report")
async def export_report(
    comparison_id: int,
    format: str = "html",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """导出性能报告
    
    导出性能对比报告，支持 HTML 和 PDF 格式。
    
    Args:
        comparison_id: 对比记录 ID
        format: 导出格式（html/pdf）
    """
    try:
        comparator = SQLPerformanceComparator(db)
        comparison = comparator.get_comparison(comparison_id)
        if not comparison:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comparison not found")
        
        if format == "html":
            from app.services.report_generator import ReportGenerator
            generator = ReportGenerator()
            html_report = generator.generate_html_report(comparison)
            return {"report": html_report}
        elif format == "pdf":
            from app.services.report_generator import ReportGenerator
            generator = ReportGenerator()
            pdf_report = generator.generate_pdf_report(comparison)
            return {"report": pdf_report}
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported format: {format}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export report: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
