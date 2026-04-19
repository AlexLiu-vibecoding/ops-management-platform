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
import psycopg2
import psycopg2.extras
from app.database import get_db
from app.models import RDBInstance, RedisInstance, AuditLog, OperationSnapshot, User
from app.schemas import (
    SQLExecuteRequest, SQLExecuteResponse, MessageResponse
)
from app.utils.auth import decrypt_instance_password, encrypt_instance_password
from app.deps import require_permission, get_current_user

router = APIRouter(prefix="/sql", tags=["SQL执行"])


def get_instance_type(instance: RDBInstance) -> str:
    """判断实例类型：mysql 或 postgresql"""
    # 通过端口判断：MySQL 默认 3306，PostgreSQL 默认 5432
    if instance.port == 5432:
        return "postgresql"
    elif instance.port == 3306:
        return "mysql"
    # 通过 host 判断
    if "pg" in instance.host.lower() or "postgres" in instance.host.lower():
        return "postgresql"
    return "mysql"


def check_sql_risk(sql: str) -> dict[str, Any]:
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


def get_mysql_connection(instance: RDBInstance, database: str = None):
    """获取MySQL连接"""
    try:
        password = decrypt_instance_password(instance.password_encrypted)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password decryption failed, please re-save instance password: {str(e)}"
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


def get_postgresql_connection(instance: RDBInstance, database: str = None):
    """获取PostgreSQL连接"""
    try:
        password = decrypt_instance_password(instance.password_encrypted)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password decryption failed, please re-save instance password: {str(e)}"
        )
    
    conn = psycopg2.connect(
        host=instance.host,
        port=instance.port,
        user=instance.username,
        password=password,
        database=database or 'postgres',
        connect_timeout=10
    )
    return conn


def get_db_connection(instance: RDBInstance, database: str = None):
    """根据实例类型获取数据库连接"""
    db_type = get_instance_type(instance)
    if db_type == "postgresql":
        return get_postgresql_connection(instance, database), "postgresql"
    return get_mysql_connection(instance, database), "mysql"


@router.post("/execute", response_model=SQLExecuteResponse)
async def execute_sql(
    request: SQLExecuteRequest,
    current_user: User = Depends(require_permission("sql:execute")),
    db: Session = Depends(get_db)
):
    """执行SQL"""
    # 检查实例
    instance = db.query(RDBInstance).filter(RDBInstance.id == request.instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
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
        conn, db_type = get_db_connection(instance, request.database_name)
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
                data=[dict(zip(columns, row, strict=False)) for row in data] if data else [],
                execution_time=(datetime.now() - start_time).total_seconds(),
                snapshot_id=snapshot_id
            )
        else:
            # 修改操作
            affected_rows = cursor.rowcount
            conn.commit()
            
            result = SQLExecuteResponse(
                success=True,
                message=f"执行成功，影响{affected_rows}lines",
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
        operation_detail=f"Execute SQL: {request.sql[:500]}...",
        request_ip="",
        request_method="POST",
        request_path="/api/sql/execute",
        response_code=200 if result.success else 500,
        response_message=result.message
    )
    db.add(audit_log)
    db.commit()
    
    return result


@router.get("/databases/{instance_id}", response_model=list[str])
async def list_databases(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例的数据库列表"""
    instance = db.query(RDBInstance).filter(RDBInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    # Redis 实例没有数据库列表概念，返回空列表
    if instance.db_type == "redis":
        return []
    
    try:
        conn, db_type = get_db_connection(instance)
        cursor = conn.cursor()
        
        if db_type == "postgresql":
            # PostgreSQL: 查询所有数据库
            cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname")
        else:
            # MySQL: SHOW DATABASES
            cursor.execute("SHOW DATABASES")
        
        databases = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return databases
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get database list: {str(e)}"
        )


@router.get("/tables/{instance_id}/{database}", response_model=list[str])
async def list_tables(
    instance_id: int,
    database: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取数据库的表列表"""
    instance = db.query(RDBInstance).filter(RDBInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    try:
        conn, db_type = get_db_connection(instance, database)
        cursor = conn.cursor()
        
        if db_type == "postgresql":
            # PostgreSQL: 查询 public schema 下的表
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
        else:
            # MySQL: SHOW TABLES
            cursor.execute("SHOW TABLES")
        
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        return tables
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get table list: {str(e)}"
        )
