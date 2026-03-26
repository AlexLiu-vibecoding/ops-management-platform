"""
监控扩展API - 主从复制监控、锁等待监控、长事务监控
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pydantic import BaseModel, Field

from app.database import get_db
from app.models import ReplicationStatus, LockWait, LongTransaction, RDBInstance, RedisInstance, User
from app.schemas import MessageResponse
from app.deps import get_current_user, get_super_admin
from app.services.db_connection import db_manager

router = APIRouter(prefix="/monitor-ext", tags=["监控扩展"])


# ==================== Schemas ====================

class ReplicationStatusResponse(BaseModel):
    """主从复制状态响应"""
    id: int
    instance_id: int
    instance_name: Optional[str]
    slave_host: Optional[str]
    slave_port: Optional[int]
    slave_io_running: Optional[str]
    slave_sql_running: Optional[str]
    seconds_behind_master: Optional[int]
    last_io_error: Optional[str]
    last_sql_error: Optional[str]
    check_time: Optional[datetime]
    
    class Config:
        from_attributes = True


class LockWaitResponse(BaseModel):
    """锁等待响应"""
    id: int
    instance_id: int
    instance_name: Optional[str]
    database_name: Optional[str]
    wait_type: Optional[str]
    waiting_thread_id: Optional[int]
    waiting_sql: Optional[str]
    waiting_time: Optional[int]
    blocking_thread_id: Optional[int]
    blocking_sql: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class LongTransactionResponse(BaseModel):
    """长事务响应"""
    id: int
    instance_id: int
    instance_name: Optional[str]
    database_name: Optional[str]
    trx_thread_id: Optional[int]
    trx_started: Optional[datetime]
    trx_duration: Optional[int]
    trx_state: Optional[str]
    trx_query: Optional[str]
    user: Optional[str]
    host: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ==================== 主从复制监控 ====================

@router.get("/replication", response_model=dict)
async def list_replication_status(
    instance_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取主从复制状态列表"""
    query = db.query(ReplicationStatus)
    
    if instance_id:
        query = query.filter(ReplicationStatus.instance_id == instance_id)
    
    total = query.count()
    # 获取每个实例最新的复制状态
    subquery = db.query(
        ReplicationStatus.instance_id,
        func.max(ReplicationStatus.check_time).label('max_time')
    ).group_by(ReplicationStatus.instance_id).subquery()
    
    records = query.join(
        subquery,
        (ReplicationStatus.instance_id == subquery.c.instance_id) &
        (ReplicationStatus.check_time == subquery.c.max_time)
    ).order_by(desc(ReplicationStatus.check_time)).offset((page - 1) * limit).limit(limit).all()
    
    # 获取实例名称
    instance_ids = [r.instance_id for r in records]
    instances = {i.id: i.name for i in db.query(RDBInstance).filter(RDBInstance.id.in_(instance_ids)).all()} if instance_ids else {}
    
    items = []
    for r in records:
        items.append({
            "id": r.id,
            "instance_id": r.instance_id,
            "instance_name": instances.get(r.instance_id),
            "slave_host": r.slave_host,
            "slave_port": r.slave_port,
            "slave_io_running": r.slave_io_running,
            "slave_sql_running": r.slave_sql_running,
            "seconds_behind_master": r.seconds_behind_master,
            "master_log_file": r.master_log_file,
            "read_master_log_pos": r.read_master_log_pos,
            "relay_master_log_file": r.relay_master_log_file,
            "exec_master_log_pos": r.exec_master_log_pos,
            "last_io_error": r.last_io_error,
            "last_sql_error": r.last_sql_error,
            "check_time": r.check_time.isoformat() if r.check_time else None,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    
    return {"total": total, "items": items}


@router.post("/replication/check/{instance_id}", response_model=dict)
async def check_replication_status(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查实例的主从复制状态"""
    instance = db.query(RDBInstance).filter(RDBInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="实例不存在")
    
    if instance.db_type != "mysql":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持MySQL实例")
    
    try:
        # 执行 SHOW SLAVE STATUS
        result = db_manager.execute_query(
            host=instance.host,
            port=instance.port,
            username=instance.username,
            password=db_manager.decrypt_password(instance.password_encrypted) if instance.password_encrypted else None,
            database="information_schema",
            query="SHOW SLAVE STATUS"
        )
        
        if not result:
            return {"message": "该实例未配置主从复制", "is_slave": False}
        
        slave_status = result[0]
        
        # 保存到数据库
        repl_record = ReplicationStatus(
            instance_id=instance_id,
            slave_host=slave_status.get("Master_Host"),
            slave_port=slave_status.get("Master_Port"),
            slave_io_running=slave_status.get("Slave_IO_Running"),
            slave_sql_running=slave_status.get("Slave_SQL_Running"),
            seconds_behind_master=slave_status.get("Seconds_Behind_Master"),
            master_log_file=slave_status.get("Master_Log_File"),
            read_master_log_pos=slave_status.get("Read_Master_Log_Pos"),
            relay_master_log_file=slave_status.get("Relay_Master_Log_File"),
            exec_master_log_pos=slave_status.get("Exec_Master_Log_Pos"),
            last_io_error=slave_status.get("Last_IO_Error"),
            last_sql_error=slave_status.get("Last_SQL_Error"),
            check_time=datetime.now()
        )
        db.add(repl_record)
        db.commit()
        
        return {
            "message": "复制状态已检查",
            "is_slave": True,
            "status": {
                "slave_io_running": slave_status.get("Slave_IO_Running"),
                "slave_sql_running": slave_status.get("Slave_SQL_Running"),
                "seconds_behind_master": slave_status.get("Seconds_Behind_Master"),
                "last_io_error": slave_status.get("Last_IO_Error"),
                "last_sql_error": slave_status.get("Last_SQL_Error")
            }
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"检查失败: {str(e)}")


# ==================== 锁等待监控 ====================

@router.get("/locks", response_model=dict)
async def list_lock_waits(
    instance_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取锁等待列表"""
    query = db.query(LockWait)
    
    if instance_id:
        query = query.filter(LockWait.instance_id == instance_id)
    if status:
        query = query.filter(LockWait.status == status)
    
    total = query.count()
    records = query.order_by(desc(LockWait.created_at)).offset((page - 1) * limit).limit(limit).all()
    
    # 获取实例名称
    instance_ids = [r.instance_id for r in records]
    instances = {i.id: i.name for i in db.query(RDBInstance).filter(RDBInstance.id.in_(instance_ids)).all()} if instance_ids else {}
    
    items = []
    for r in records:
        items.append({
            "id": r.id,
            "instance_id": r.instance_id,
            "instance_name": instances.get(r.instance_id),
            "database_name": r.database_name,
            "wait_type": r.wait_type,
            "waiting_thread_id": r.waiting_thread_id,
            "waiting_sql": r.waiting_sql,
            "waiting_time": r.waiting_time,
            "blocking_thread_id": r.blocking_thread_id,
            "blocking_sql": r.blocking_sql,
            "blocking_time": r.blocking_time,
            "status": r.status,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    
    return {"total": total, "items": items}


@router.post("/locks/check/{instance_id}", response_model=dict)
async def check_lock_waits(
    instance_id: int,
    threshold: int = Query(5, description="锁等待时间阈值(秒)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查实例的锁等待情况"""
    instance = db.query(RDBInstance).filter(RDBInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="实例不存在")
    
    if instance.db_type != "mysql":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持MySQL实例")
    
    try:
        # 查询锁等待
        lock_query = """
        SELECT 
            r.trx_id AS waiting_trx_id,
            r.trx_mysql_thread_id AS waiting_thread_id,
            r.trx_query AS waiting_query,
            r.trx_wait_started AS wait_started,
            b.trx_id AS blocking_trx_id,
            b.trx_mysql_thread_id AS blocking_thread_id,
            b.trx_query AS blocking_query,
            TIMESTAMPDIFF(SECOND, r.trx_wait_started, NOW()) AS wait_time
        FROM information_schema.innodb_lock_waits w
        INNER JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
        INNER JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id
        WHERE TIMESTAMPDIFF(SECOND, r.trx_wait_started, NOW()) > %s
        """
        
        results = db_manager.execute_query(
            host=instance.host,
            port=instance.port,
            username=instance.username,
            password=db_manager.decrypt_password(instance.password_encrypted) if instance.password_encrypted else None,
            database="information_schema",
            query=lock_query,
            params=(threshold,)
        )
        
        lock_records = []
        for row in results:
            lock_record = LockWait(
                instance_id=instance_id,
                wait_type="Row_Lock",
                waiting_thread_id=row.get("waiting_thread_id"),
                waiting_sql=row.get("waiting_query"),
                waiting_time=row.get("wait_time"),
                blocking_thread_id=row.get("blocking_thread_id"),
                blocking_sql=row.get("blocking_query"),
                status="active"
            )
            db.add(lock_record)
            lock_records.append({
                "waiting_thread_id": row.get("waiting_thread_id"),
                "waiting_sql": row.get("waiting_query"),
                "waiting_time": row.get("wait_time"),
                "blocking_thread_id": row.get("blocking_thread_id"),
                "blocking_sql": row.get("blocking_query")
            })
        
        db.commit()
        
        return {
            "message": f"检测到 {len(lock_records)} 个锁等待",
            "count": len(lock_records),
            "locks": lock_records
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"检查失败: {str(e)}")


# ==================== 长事务监控 ====================

@router.get("/transactions", response_model=dict)
async def list_long_transactions(
    instance_id: Optional[int] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取长事务列表"""
    query = db.query(LongTransaction)
    
    if instance_id:
        query = query.filter(LongTransaction.instance_id == instance_id)
    if status:
        query = query.filter(LongTransaction.status == status)
    
    total = query.count()
    records = query.order_by(desc(LongTransaction.created_at)).offset((page - 1) * limit).limit(limit).all()
    
    # 获取实例名称
    instance_ids = [r.instance_id for r in records]
    instances = {i.id: i.name for i in db.query(RDBInstance).filter(RDBInstance.id.in_(instance_ids)).all()} if instance_ids else {}
    
    items = []
    for r in records:
        items.append({
            "id": r.id,
            "instance_id": r.instance_id,
            "instance_name": instances.get(r.instance_id),
            "database_name": r.database_name,
            "trx_id": r.trx_id,
            "trx_thread_id": r.trx_thread_id,
            "trx_started": r.trx_started.isoformat() if r.trx_started else None,
            "trx_duration": r.trx_duration,
            "trx_state": r.trx_state,
            "trx_query": r.trx_query,
            "trx_rows_locked": r.trx_rows_locked,
            "trx_tables_locked": r.trx_tables_locked,
            "user": r.user,
            "host": r.host,
            "status": r.status,
            "killed_at": r.killed_at.isoformat() if r.killed_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None
        })
    
    return {"total": total, "items": items}


@router.post("/transactions/check/{instance_id}", response_model=dict)
async def check_long_transactions(
    instance_id: int,
    threshold: int = Query(60, description="事务持续时间阈值(秒)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查实例的长事务"""
    instance = db.query(RDBInstance).filter(RDBInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="实例不存在")
    
    if instance.db_type != "mysql":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持MySQL实例")
    
    try:
        # 查询长事务
        trx_query = """
        SELECT 
            trx_id,
            trx_mysql_thread_id,
            trx_started,
            TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS duration,
            trx_state,
            trx_query,
            trx_rows_locked,
            trx_tables_locked,
            USER,
            HOST
        FROM information_schema.innodb_trx
        WHERE TIMESTAMPDIFF(SECOND, trx_started, NOW()) > %s
        ORDER BY duration DESC
        """
        
        results = db_manager.execute_query(
            host=instance.host,
            port=instance.port,
            username=instance.username,
            password=db_manager.decrypt_password(instance.password_encrypted) if instance.password_encrypted else None,
            database="information_schema",
            query=trx_query,
            params=(threshold,)
        )
        
        trx_records = []
        for row in results:
            trx_record = LongTransaction(
                instance_id=instance_id,
                trx_id=str(row.get("trx_id")),
                trx_thread_id=row.get("trx_mysql_thread_id"),
                trx_started=row.get("trx_started"),
                trx_duration=row.get("duration"),
                trx_state=row.get("trx_state"),
                trx_query=row.get("trx_query"),
                trx_rows_locked=row.get("trx_rows_locked"),
                trx_tables_locked=row.get("trx_tables_locked"),
                user=row.get("USER"),
                host=row.get("HOST"),
                status="active"
            )
            db.add(trx_record)
            trx_records.append({
                "trx_id": str(row.get("trx_id")),
                "thread_id": row.get("trx_mysql_thread_id"),
                "started": row.get("trx_started").isoformat() if row.get("trx_started") else None,
                "duration": row.get("duration"),
                "state": row.get("trx_state"),
                "query": row.get("trx_query"),
                "rows_locked": row.get("trx_rows_locked")
            })
        
        db.commit()
        
        return {
            "message": f"检测到 {len(trx_records)} 个长事务",
            "count": len(trx_records),
            "transactions": trx_records
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"检查失败: {str(e)}")


@router.post("/transactions/kill/{trx_id}", response_model=MessageResponse)
async def kill_transaction(
    trx_id: int,
    instance_id: int = Query(..., description="实例ID"),
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """Kill长事务"""
    instance = db.query(RDBInstance).filter(RDBInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="实例不存在")
    
    try:
        # 执行 KILL QUERY
        db_manager.execute_query(
            host=instance.host,
            port=instance.port,
            username=instance.username,
            password=db_manager.decrypt_password(instance.password_encrypted) if instance.password_encrypted else None,
            database="information_schema",
            query=f"KILL {trx_id}"
        )
        
        # 更新记录状态
        trx_record = db.query(LongTransaction).filter(
            LongTransaction.instance_id == instance_id,
            LongTransaction.trx_thread_id == trx_id,
            LongTransaction.status == "active"
        ).first()
        
        if trx_record:
            trx_record.status = "killed"
            trx_record.killed_at = datetime.now()
            db.commit()
        
        return MessageResponse(message=f"事务 {trx_id} 已被Kill")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Kill失败: {str(e)}")
