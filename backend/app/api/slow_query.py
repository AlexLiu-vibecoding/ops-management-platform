"""
慢查询监控API
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import pymysql
from pymysql.cursors import DictCursor
import logging

from app.database import get_db
from app.models import (
    SlowQuery, Instance, MonitorSwitch, 
    MonitorType, User
)
from app.schemas import SlowQueryResponse, MessageResponse
from app.deps import get_current_user
from app.utils.auth import aes_cipher

router = APIRouter(prefix="/slow-query", tags=["慢查询监控"])
logger = logging.getLogger(__name__)


@router.get("/{instance_id}", response_model=List[SlowQueryResponse])
async def list_slow_queries(
    instance_id: int,
    min_time: Optional[float] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取慢查询列表"""
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
    """获取Top N慢查询"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # 按执行时间或执行次数排序
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
    """获取慢查询统计"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # 统计
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """分析慢查询"""
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
    
    # 执行 EXPLAIN 分析
    explain_result = await execute_explain(instance, slow_query.sql_sample, slow_query.database_name)
    
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
        "suggestions": generate_suggestions(explain_result, slow_query)
    }


async def execute_explain(instance: Instance, sql: str, database_name: str = None) -> Dict[str, Any]:
    """
    执行 EXPLAIN 分析
    
    Args:
        instance: 数据库实例
        sql: SQL语句
        database_name: 数据库名
    
    Returns:
        EXPLAIN 结果
    """
    if not sql:
        return {"error": "SQL语句为空"}
    
    # 清理 SQL（去掉可能导致问题的部分）
    sql = sql.strip()
    if sql.endswith(';'):
        sql = sql[:-1]
    
    # 对于 INSERT/UPDATE/DELETE，使用 EXPLAIN ANALYZE 可能需要更谨慎
    sql_upper = sql.upper().strip()
    is_dml = any(sql_upper.startswith(kw) for kw in ['INSERT', 'UPDATE', 'DELETE', 'REPLACE'])
    
    result = {
        "explain": [],
        "explain_json": None,
        "warnings": [],
        "error": None
    }
    
    connection = None
    try:
        # 解密密码
        password = aes_cipher.decrypt(instance.password_encrypted)
        
        # 连接数据库
        connection = pymysql.connect(
            host=instance.host,
            port=instance.port,
            user=instance.username,
            password=password,
            database=database_name if database_name else None,
            connect_timeout=10,
            read_timeout=30,
            cursorclass=DictCursor
        )
        
        with connection.cursor() as cursor:
            # 执行 EXPLAIN
            explain_sql = f"EXPLAIN {sql}"
            cursor.execute(explain_sql)
            explain_rows = cursor.fetchall()
            
            # 转换为列表并处理特殊类型
            result["explain"] = []
            for row in explain_rows:
                row_dict = {}
                for key, value in row.items():
                    if isinstance(value, bytes):
                        row_dict[key] = value.decode('utf-8', errors='replace')
                    else:
                        row_dict[key] = value
                result["explain"].append(row_dict)
            
            # 尝试获取 JSON 格式的 EXPLAIN（MySQL 5.6.5+）
            try:
                cursor.execute(f"EXPLAIN FORMAT=JSON {sql}")
                json_result = cursor.fetchone()
                if json_result and 'EXPLAIN' in json_result:
                    import json
                    result["explain_json"] = json.loads(json_result['EXPLAIN'])
            except Exception as e:
                logger.debug(f"获取 JSON 格式 EXPLAIN 失败: {e}")
            
            # 检查警告
            cursor.execute("SHOW WARNINGS")
            warnings = cursor.fetchall()
            if warnings:
                result["warnings"] = [
                    {"level": w.get('Level', ''), "code": w.get('Code', ''), "message": w.get('Message', '')}
                    for w in warnings
                ]
        
    except pymysql.err.OperationalError as e:
        error_code, error_msg = e.args
        result["error"] = f"数据库连接错误: {error_msg}"
        logger.error(f"连接数据库失败: {e}")
    except pymysql.err.ProgrammingError as e:
        error_code, error_msg = e.args
        result["error"] = f"SQL语法错误: {error_msg}"
        logger.error(f"SQL 执行错误: {e}")
    except Exception as e:
        result["error"] = str(e)
        logger.error(f"执行 EXPLAIN 失败: {e}")
    finally:
        if connection:
            try:
                connection.close()
            except:
                pass
    
    return result


def generate_suggestions(explain_result: Dict[str, Any], slow_query: SlowQuery) -> List[Dict[str, str]]:
    """
    根据EXPLAIN结果生成优化建议
    
    Args:
        explain_result: EXPLAIN 分析结果
        slow_query: 慢查询记录
    
    Returns:
        优化建议列表
    """
    suggestions = []
    
    if explain_result.get("error"):
        suggestions.append({
            "type": "error",
            "title": "分析失败",
            "description": explain_result["error"],
            "action": "请检查SQL语法是否正确，或数据库连接是否正常"
        })
        return suggestions
    
    explain_rows = explain_result.get("explain", [])
    
    for idx, row in enumerate(explain_rows):
        # 检查扫描类型
        select_type = row.get("select_type", "")
        type_ = row.get("type", "")
        key = row.get("key", "")
        rows_examined = row.get("rows", 0)
        extra = row.get("Extra", "")
        
        # 全表扫描
        if type_ == "ALL":
            suggestions.append({
                "type": "warning",
                "title": f"表 {row.get('table', '未知')} 全表扫描",
                "description": f"type={type_}，正在扫描全表，这是最慢的访问方式",
                "action": f"建议为 WHERE/JOIN 条件中的列添加索引，当前表扫描约 {rows_examined:,} 行"
            })
        
        # 索引效率低
        elif type_ in ["index", "range"] and rows_examined and rows_examined > 10000:
            suggestions.append({
                "type": "warning", 
                "title": f"表 {row.get('table', '未知')} 扫描行数过多",
                "description": f"type={type_}，扫描约 {rows_examined:,} 行，可能索引选择不佳",
                "action": "检查索引是否覆盖了查询条件，考虑创建更合适的复合索引"
            })
        
        # 使用了临时表
        if "Using temporary" in str(extra):
            suggestions.append({
                "type": "info",
                "title": "使用临时表",
                "description": "查询需要创建临时表来处理结果",
                "action": "检查 GROUP BY 或 ORDER BY 是否可以使用索引，避免临时表"
            })
        
        # 使用了文件排序
        if "Using filesort" in str(extra):
            suggestions.append({
                "type": "info",
                "title": "使用文件排序",
                "description": "查询需要额外的排序操作",
                "action": "为 ORDER BY 列添加索引，避免额外排序"
            })
        
        # 没有使用索引
        if not key or key == "NULL":
            if type_ != "ALL":  # 全表扫描已经有建议了
                suggestions.append({
                    "type": "warning",
                    "title": f"表 {row.get('table', '未知')} 未使用索引",
                    "description": f"当前访问类型为 {type_}，未使用任何索引",
                    "action": "检查查询条件，为相关列创建合适的索引"
                })
        
        # 索引失效
        if "Using index condition" in str(extra) or "Using where" in str(extra):
            pass  # 这是正常的
        
        # DERIVED 子查询
        if select_type == "DERIVED":
            suggestions.append({
                "type": "info",
                "title": "派生表（子查询）",
                "description": "使用了派生表，可能导致性能问题",
                "action": "考虑将子查询改写为 JOIN，或确保子查询使用了索引"
            })
    
    # 基于慢查询统计数据的建议
    if slow_query.rows_examined and slow_query.rows_sent:
        ratio = slow_query.rows_examined / slow_query.rows_sent if slow_query.rows_sent > 0 else 0
        if ratio > 100:
            suggestions.append({
                "type": "warning",
                "title": "扫描行数与返回行数比例过高",
                "description": f"扫描了 {slow_query.rows_examined:,} 行但只返回了 {slow_query.rows_sent:,} 行（比例: {ratio:.0f}:1）",
                "action": "查询效率低，建议优化 WHERE 条件或添加更精确的索引"
            })
    
    if slow_query.lock_time and slow_query.lock_time > 0.1:
        suggestions.append({
            "type": "warning",
            "title": "锁等待时间较长",
            "description": f"锁等待时间: {slow_query.lock_time:.3f} 秒",
            "action": "检查是否有长事务阻塞，考虑优化事务范围或使用乐观锁"
        })
    
    # 如果没有建议，给出正面反馈
    if not suggestions:
        suggestions.append({
            "type": "success",
            "title": "查询计划看起来不错",
            "description": "EXPLAIN 结果显示查询使用了索引，没有明显的性能问题",
            "action": "如果仍然较慢，可能是数据量过大或网络延迟导致，考虑分库分表"
        })
    
    return suggestions


@router.post("/{instance_id}/explain", response_model=dict)
async def run_explain(
    instance_id: int,
    sql: str,
    database_name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    手动执行 EXPLAIN 分析
    
    Args:
        instance_id: 实例ID
        sql: SQL语句
        database_name: 数据库名（可选）
    """
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    explain_result = await execute_explain(instance, sql, database_name)
    
    # 构建简单的建议
    suggestions = []
    for row in explain_result.get("explain", []):
        if row.get("type") == "ALL":
            suggestions.append(f"表 {row.get('table')} 全表扫描，建议添加索引")
        if "Using temporary" in str(row.get("Extra", "")):
            suggestions.append(f"表 {row.get('table')} 使用临时表，考虑优化 GROUP BY/ORDER BY")
    
    return {
        "sql": sql,
        "database_name": database_name,
        "explain": explain_result.get("explain"),
        "explain_json": explain_result.get("explain_json"),
        "warnings": explain_result.get("warnings", []),
        "error": explain_result.get("error"),
        "suggestions": suggestions
    }
