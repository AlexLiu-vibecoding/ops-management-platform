"""
MySQL实例管理API
"""
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import pymysql
from app.database import get_db
from app.models import Instance, InstanceGroup, Environment, MonitorSwitch, MonitorType
from app.schemas import (
    InstanceCreate, InstanceUpdate, InstanceResponse, 
    InstanceTestResult, MessageResponse
)
from app.utils.auth import encrypt_instance_password, decrypt_instance_password
from app.deps import get_operator, get_current_user
from app.models import User

router = APIRouter(prefix="/instances", tags=["实例管理"])


async def test_mysql_connection(host: str, port: int, username: str, password: str) -> dict:
    """测试MySQL连接"""
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            connect_timeout=5
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
        conn.close()
        return {
            "success": True,
            "message": "连接成功",
            "version": version
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"连接失败: {str(e)}",
            "version": None
        }


@router.get("", response_model=List[InstanceResponse])
async def list_instances(
    environment_id: Optional[int] = None,
    group_id: Optional[int] = None,
    status: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例列表"""
    query = db.query(Instance)
    
    if environment_id:
        query = query.filter(Instance.environment_id == environment_id)
    if group_id:
        query = query.filter(Instance.group_id == group_id)
    if status is not None:
        query = query.filter(Instance.status == status)
    
    instances = query.offset(skip).limit(limit).all()
    return [InstanceResponse.from_orm(i) for i in instances]


@router.get("/{instance_id}", response_model=InstanceResponse)
async def get_instance(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例详情"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    return InstanceResponse.from_orm(instance)


@router.post("/test", response_model=InstanceTestResult)
async def test_instance_connection(
    instance_data: InstanceCreate,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """测试实例连接"""
    result = await test_mysql_connection(
        instance_data.host,
        instance_data.port,
        instance_data.username,
        instance_data.password
    )
    return InstanceTestResult(**result)


@router.post("", response_model=InstanceResponse)
async def create_instance(
    instance_data: InstanceCreate,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """创建实例"""
    # 检查名称是否已存在
    if db.query(Instance).filter(Instance.name == instance_data.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="实例名称已存在"
        )
    
    # 测试连接
    conn_result = await test_mysql_connection(
        instance_data.host,
        instance_data.port,
        instance_data.username,
        instance_data.password
    )
    
    if not conn_result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"连接测试失败: {conn_result['message']}"
        )
    
    # 创建实例
    instance = Instance(
        name=instance_data.name,
        host=instance_data.host,
        port=instance_data.port,
        username=instance_data.username,
        password_encrypted=encrypt_instance_password(instance_data.password),
        environment_id=instance_data.environment_id,
        group_id=instance_data.group_id,
        description=instance_data.description,
        status=True
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)
    
    # 创建默认监控开关（全部启用）
    for monitor_type in MonitorType:
        switch = MonitorSwitch(
            instance_id=instance.id,
            monitor_type=monitor_type,
            enabled=True
        )
        db.add(switch)
    db.commit()
    
    return InstanceResponse.from_orm(instance)


@router.put("/{instance_id}", response_model=InstanceResponse)
async def update_instance(
    instance_id: int,
    instance_data: InstanceUpdate,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """更新实例"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 更新字段
    update_data = instance_data.dict(exclude_unset=True)
    
    # 如果更新了密码，需要加密
    if 'password' in update_data:
        update_data['password_encrypted'] = encrypt_instance_password(update_data.pop('password'))
    
    for key, value in update_data.items():
        setattr(instance, key, value)
    
    db.commit()
    db.refresh(instance)
    
    return InstanceResponse.from_orm(instance)


@router.delete("/{instance_id}", response_model=MessageResponse)
async def delete_instance(
    instance_id: int,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """删除实例"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    db.delete(instance)
    db.commit()
    
    return MessageResponse(message="实例删除成功")


@router.post("/{instance_id}/check", response_model=InstanceTestResult)
async def check_instance_status(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """检查实例状态"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 尝试解密密码
    try:
        password = decrypt_instance_password(instance.password_encrypted)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"密码解密失败，请重新保存实例密码: {str(e)}"
        )
    
    result = await test_mysql_connection(
        instance.host,
        instance.port,
        instance.username,
        password
    )
    
    # 更新实例状态
    from datetime import datetime
    instance.status = result["success"]
    instance.last_check_time = datetime.now()
    db.commit()
    
    return InstanceTestResult(**result)


# ============ 实例分组相关 ============

@router.get("/groups/", response_model=List[dict])
async def list_instance_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例分组列表"""
    groups = db.query(InstanceGroup).all()
    return [{"id": g.id, "name": g.name, "description": g.description} for g in groups]


@router.post("/groups/", response_model=MessageResponse)
async def create_instance_group(
    name: str,
    description: str = "",
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """创建实例分组"""
    if db.query(InstanceGroup).filter(InstanceGroup.name == name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="分组名称已存在"
        )
    
    group = InstanceGroup(name=name, description=description)
    db.add(group)
    db.commit()
    
    return MessageResponse(message="分组创建成功")


# ============ 实例参数相关 ============

@router.get("/{instance_id}/variables", response_model=dict)
async def get_instance_variables(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例参数"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    try:
        password = decrypt_instance_password(instance.password_encrypted)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"密码解密失败，请重新保存实例密码: {str(e)}"
        )
    
    try:
        conn = pymysql.connect(
            host=instance.host,
            port=instance.port,
            user=instance.username,
            password=password,
            connect_timeout=5
        )
        with conn.cursor() as cursor:
            cursor.execute("SHOW VARIABLES")
            variables = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return variables
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取参数失败: {str(e)}"
        )


# ============ 数据库列表相关 ============

@router.get("/{instance_id}/databases", response_model=List[dict])
async def get_instance_databases(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例数据库列表"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    try:
        password = decrypt_instance_password(instance.password_encrypted)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"密码解密失败，请重新保存实例密码: {str(e)}"
        )
    
    try:
        conn = pymysql.connect(
            host=instance.host,
            port=instance.port,
            user=instance.username,
            password=password,
            connect_timeout=10
        )
        databases = []
        with conn.cursor() as cursor:
            # 获取数据库列表
            cursor.execute("SHOW DATABASES")
            db_list = cursor.fetchall()
            
            for db_row in db_list:
                db_name = db_row[0]
                # 过滤系统库
                if db_name in ('information_schema', 'mysql', 'performance_schema', 'sys'):
                    continue
                
                # 获取数据库大小和表数量
                try:
                    cursor.execute(f"""
                        SELECT COUNT(*), 
                               COALESCE(SUM(data_length + index_length) / 1024 / 1024, 0) as size_mb
                        FROM information_schema.tables 
                        WHERE table_schema = %s
                    """, (db_name,))
                    result = cursor.fetchone()
                    databases.append({
                        "name": db_name,
                        "tables": result[0] if result else 0,
                        "size_mb": round(result[1], 2) if result else 0
                    })
                except Exception:
                    databases.append({
                        "name": db_name,
                        "tables": 0,
                        "size_mb": 0
                    })
        
        conn.close()
        
        # 按名称排序
        databases.sort(key=lambda x: x["name"])
        return databases
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据库列表失败: {str(e)}"
        )


@router.get("/{instance_id}/databases/{database_name}/tables", response_model=List[dict])
async def get_database_tables(
    instance_id: int,
    database_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取数据库表列表"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    try:
        password = decrypt_instance_password(instance.password_encrypted)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"密码解密失败，请重新保存实例密码: {str(e)}"
        )
    
    try:
        conn = pymysql.connect(
            host=instance.host,
            port=instance.port,
            user=instance.username,
            password=password,
            database=database_name,
            connect_timeout=10
        )
        tables = []
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    table_name,
                    table_type,
                    table_rows,
                    COALESCE((data_length + index_length) / 1024 / 1024, 0) as size_mb,
                    table_comment
                FROM information_schema.tables 
                WHERE table_schema = %s
                ORDER BY table_name
            """, (database_name,))
            
            for row in cursor.fetchall():
                tables.append({
                    "name": row[0],
                    "type": row[1],
                    "rows": row[2] or 0,
                    "size_mb": round(row[3], 2),
                    "comment": row[4] or ""
                })
        
        conn.close()
        return tables
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表列表失败: {str(e)}"
        )
