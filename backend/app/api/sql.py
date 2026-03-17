"""
SQL执行API
"""
import re
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import pymysql
from app.database import get_db
from app.models import Instance, AuditLog, OperationSnapshot, User
from app.schemas import (
    SQLExecuteRequest, SQLExecuteResponse, MessageResponse
)
from app.utils.auth import decrypt_instance_password, encrypt_instance_password
from app.deps import get_operator, get_current_user

router = APIRouter(prefix="/sql", tags=["SQL执行"])


def check_sql_risk(sql: str) -> Dict[str, Any]:
    """
    检查SQL风险
    返回风险等级和是否允许执行
    """
    sql_upper = sql.upper().strip()
    
    # 检测高危操作
    forbidden_patterns = [
        (r'\bDROP\s+DATABASE\b', "禁止删除数据库"),
        (r'\bDROP\s+SCHEMA\b', "禁止删除Schema"),
        (r'\bTRUNCATE\b', "禁止TRUNCATE操作"),
    ]
    
    for pattern, message in forbidden_patterns:
        if re.search(pattern, sql_upper, re.IGNORECASE):
            return {
                "risk_level": "critical",
                "allowed": False,
                "message": message
            }
    
    # 检查是否是无WHERE的DELETE/UPDATE
    if 'DELETE' in sql_upper or 'UPDATE' in sql_upper:
        if 'WHERE' not in sql_upper:
            return {
                "risk_level": "high",
                "allowed": True,
                "message": "警告: DELETE/UPDATE操作无WHERE条件，将影响全表"
            }
    
    return {
        "risk_level": "low",
        "allowed": True,
        "message": "SQL风险检测通过"
    }


def get_mysql_connection(instance: Instance, database: str = None):
    """获取MySQL连接"""
    try:
        password = decrypt_instance_password(instance.password_encrypted)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"密码解密失败，请重新保存实例密码: {str(e)}"
        )
    
    conn = pymysql.connect(
        host=instance.host,
        port=instance.port,
        user=instance.username,
        password=password,
        database=database,
        connect_timeout=10,
        charset='utf8mb4'
    )
    return conn


@router.post("/execute", response_model=SQLExecuteResponse)
async def execute_sql(
    request: SQLExecuteRequest,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """执行SQL"""
    # 检查实例
    instance = db.query(Instance).filter(Instance.id == request.instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 风险检测
    risk_check = check_sql_risk(request.sql)
    if not risk_check["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=risk_check["message"]
        )
    
    # 生产环境需要额外检查
    if instance.environment and instance.environment.code == "production":
        # 生产环境禁止执行无WHERE的DELETE/UPDATE
        sql_upper = request.sql.upper()
        if ('DELETE' in sql_upper or 'UPDATE' in sql_upper) and 'WHERE' not in sql_upper:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="生产环境禁止执行无WHERE条件的DELETE/UPDATE操作"
            )
    
    snapshot_id = None
    start_time = datetime.now()
    
    try:
        conn = get_mysql_connection(instance, request.database_name)
        cursor = conn.cursor()
        
        # 如果是DML操作且需要快照，先保存快照
        sql_upper = request.sql.upper().strip()
        if request.need_snapshot and (sql_upper.startswith('UPDATE') or sql_upper.startswith('DELETE')):
            # 提取表名
            table_match = re.search(r'(?:UPDATE|DELETE\s+FROM)\s+`?(\w+)`?', request.sql, re.IGNORECASE)
            if table_match:
                table_name = table_match.group(1)
                
                # 构建查询SQL获取受影响的数据
                # 从原SQL中提取WHERE条件
                where_match = re.search(r'\bWHERE\b(.+)', request.sql, re.IGNORECASE)
                if where_match:
                    where_clause = where_match.group(1)
                    select_sql = f"SELECT * FROM {table_name} WHERE {where_clause}"
                else:
                    select_sql = f"SELECT * FROM {table_name}"
                
                try:
                    cursor.execute(select_sql)
                    snapshot_data = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    
                    # 保存快照
                    snapshot = OperationSnapshot(
                        instance_id=instance.id,
                        database_name=request.database_name,
                        table_name=table_name,
                        operation_type="UPDATE" if sql_upper.startswith('UPDATE') else "DELETE",
                        original_sql=request.sql,
                        snapshot_data=json.dumps({
                            "columns": columns,
                            "data": snapshot_data
                        }, ensure_ascii=False),
                        row_count=len(snapshot_data)
                    )
                    db.add(snapshot)
                    db.commit()
                    db.refresh(snapshot)
                    snapshot_id = snapshot.id
                except Exception as e:
                    # 快照失败不影响执行
                    print(f"快照保存失败: {e}")
        
        # 执行SQL
        cursor.execute(request.sql)
        
        # 判断是查询还是修改
        if sql_upper.startswith('SELECT') or sql_upper.startswith('SHOW') or sql_upper.startswith('DESC') or sql_upper.startswith('EXPLAIN'):
            # 查询操作
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            affected_rows = len(data)
            
            result = SQLExecuteResponse(
                success=True,
                message="查询成功",
                affected_rows=affected_rows,
                columns=columns,
                data=[dict(zip(columns, row)) for row in data] if data else [],
                execution_time=(datetime.now() - start_time).total_seconds(),
                snapshot_id=snapshot_id
            )
        else:
            # 修改操作
            affected_rows = cursor.rowcount
            conn.commit()
            
            result = SQLExecuteResponse(
                success=True,
                message=f"执行成功，影响{affected_rows}行",
                affected_rows=affected_rows,
                execution_time=(datetime.now() - start_time).total_seconds(),
                snapshot_id=snapshot_id
            )
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        result = SQLExecuteResponse(
            success=False,
            message=f"执行失败: {str(e)}",
            execution_time=(datetime.now() - start_time).total_seconds()
        )
    
    # 记录审计日志
    audit_log = AuditLog(
        user_id=current_user.id,
        username=current_user.username,
        instance_id=instance.id,
        instance_name=instance.name,
        environment_id=instance.environment_id,
        operation_type="execute_sql",
        operation_detail=f"执行SQL: {request.sql[:500]}...",
        request_ip="",
        request_method="POST",
        request_path="/api/sql/execute",
        response_code=200 if result.success else 500,
        response_message=result.message
    )
    db.add(audit_log)
    db.commit()
    
    return result


@router.get("/databases/{instance_id}", response_model=List[str])
async def list_databases(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例的数据库列表"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    try:
        conn = get_mysql_connection(instance)
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES")
        databases = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return databases
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据库列表失败: {str(e)}"
        )


@router.get("/tables/{instance_id}/{database}", response_model=List[str])
async def list_tables(
    instance_id: int,
    database: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取数据库的表列表"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    try:
        conn = get_mysql_connection(instance, database)
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表列表失败: {str(e)}"
        )
