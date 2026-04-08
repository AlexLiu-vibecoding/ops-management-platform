"""
RDB 实例管理 API（MySQL/PostgreSQL）

提供关系型数据库实例的增删改查、连接测试、监控配置等功能
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

from app.database import get_db
from app.models import RDBInstance, InstanceGroup, Environment, MonitorSwitch, MonitorType, RDBType, GlobalConfig
from app.services.instance_service import RDBInstanceService
from app.utils.auth import encrypt_instance_password, decrypt_instance_password
from app.utils.db_helpers import test_mysql_connection, test_postgresql_connection
from app.deps import get_operator, get_current_user, require_permission
from app.models import User
from app.utils.aws_rds_collector import parse_aws_region_from_host, is_rds_endpoint

router = APIRouter(prefix="/rdb-instances", tags=["RDB实例管理"])
logger = logging.getLogger(__name__)


def check_db_type_enabled(db: Session, db_type: str) -> bool:
    """检查数据库类型是否启用"""
    config = db.query(GlobalConfig).filter(
        GlobalConfig.config_key == f"db_type_{db_type}_enabled"
    ).first()

    if config:
        return config.config_value.lower() == "true"
    return True  # 默认启用


# ============ Schema 定义 ============

class RDBInstanceCreate(BaseModel):
    """创建 RDB 实例请求"""
    name: str
    db_type: str = "mysql"  # mysql / postgresql
    host: str
    port: int = 3306
    username: Optional[str] = None
    password: Optional[str] = None
    environment_id: Optional[int] = None
    group_id: Optional[int] = None
    description: Optional[str] = None
    status: bool = True
    # AWS RDS 相关
    is_rds: bool = False
    rds_instance_id: Optional[str] = None
    aws_region: Optional[str] = None
    # 监控配置
    slow_query_threshold: int = 3
    enable_monitoring: bool = True


class RDBInstanceUpdate(BaseModel):
    """更新 RDB 实例请求"""
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    environment_id: Optional[int] = None
    group_id: Optional[int] = None
    description: Optional[str] = None
    status: Optional[bool] = None
    is_rds: Optional[bool] = None
    rds_instance_id: Optional[str] = None
    aws_region: Optional[str] = None
    slow_query_threshold: Optional[int] = None
    enable_monitoring: Optional[bool] = None


class RDBInstanceResponse(BaseModel):
    """RDB 实例响应"""
    id: int
    name: str
    db_type: str
    host: str
    port: int
    username: Optional[str]
    environment_id: Optional[int]
    group_id: Optional[int]
    description: Optional[str]
    status: bool
    is_rds: bool
    rds_instance_id: Optional[str]
    aws_region: Optional[str]
    slow_query_threshold: int
    enable_monitoring: bool
    last_check_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InstanceTestResult(BaseModel):
    """实例连接测试结果"""
    success: bool
    message: str
    version: Optional[str] = None


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str


# ============ 辅助函数 ============

async def test_rdb_connection(db_type: str, host: str, port: int, username: str, password: str) -> dict:
    """测试 RDB 连接（包装函数，同步调用）"""
    if db_type == "postgresql":
        return test_postgresql_connection(host, port, username, password)
    else:
        return test_mysql_connection(host, port, username, password)


# ============ API 路由 ============

@router.get("")
async def list_rdb_instances(
    environment_id: Optional[int] = None,
    group_id: Optional[int] = None,
    db_type: Optional[str] = None,
    status: Optional[bool] = None,
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(require_permission("instance:view")),
    db: Session = Depends(get_db)
):
    """获取 RDB 实例列表"""
    service = RDBInstanceService(db)
    instances, total = service.get_multi_with_environment(
        skip=skip,
        limit=limit,
        environment_id=environment_id,
        group_id=group_id,
        db_type=db_type,
        status=status
    )

    # 构建返回数据，包含 environment 信息
    items = []
    for i in instances:
        # 使用预加载的 environment 关系，避免 N+1 查询
        env_data = None
        if i.environment:
            env_data = {"id": i.environment.id, "name": i.environment.name, "color": i.environment.color}

        items.append({
            "id": i.id,
            "name": i.name,
            "db_type": i.db_type.value if hasattr(i.db_type, 'value') else str(i.db_type),
            "host": i.host,
            "port": i.port,
            "username": i.username,
            "environment_id": i.environment_id,
            "environment": env_data,
            "group_id": i.group_id,
            "description": i.description,
            "status": i.status,
            "is_rds": i.is_rds,
            "rds_instance_id": i.rds_instance_id,
            "aws_region": i.aws_region,
            "slow_query_threshold": i.slow_query_threshold,
            "enable_monitoring": i.enable_monitoring,
            "last_check_time": i.last_check_time,
            "created_at": i.created_at,
            "updated_at": i.updated_at,
        })

    return {
        "total": total,
        "items": items
    }


@router.get("/{instance_id}")
async def get_rdb_instance(
    instance_id: int,
    current_user: User = Depends(require_permission("instance:view")),
    db: Session = Depends(get_db)
):
    """获取 RDB 实例详情"""
    service = RDBInstanceService(db)
    instance = service.get_with_environment(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )

    # 使用预加载的 environment 关系
    env_data = None
    if instance.environment:
        env_data = {"id": instance.environment.id, "name": instance.environment.name, "color": instance.environment.color}

    return {
        "id": instance.id,
        "name": instance.name,
        "db_type": instance.db_type.value if hasattr(instance.db_type, 'value') else str(instance.db_type),
        "host": instance.host,
        "port": instance.port,
        "username": instance.username,
        "environment_id": instance.environment_id,
        "environment": env_data,
        "group_id": instance.group_id,
        "description": instance.description,
        "status": instance.status,
        "is_rds": instance.is_rds,
        "rds_instance_id": instance.rds_instance_id,
        "aws_region": instance.aws_region,
        "slow_query_threshold": instance.slow_query_threshold,
        "enable_monitoring": instance.enable_monitoring,
        "last_check_time": instance.last_check_time,
        "created_at": instance.created_at,
        "updated_at": instance.updated_at,
    }


@router.post("/test", response_model=InstanceTestResult)
async def test_rdb_instance_connection(
    instance_data: RDBInstanceCreate,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """测试 RDB 实例连接"""
    result = await test_rdb_connection(
        instance_data.db_type or "mysql",
        instance_data.host,
        instance_data.port or 3306,
        instance_data.username or "",
        instance_data.password or ""
    )
    return InstanceTestResult(**result)


@router.post("/{instance_id}/check", response_model=InstanceTestResult)
async def check_rdb_instance_status(
    instance_id: int,
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """检查 RDB 实例连接状态"""
    service = RDBInstanceService(db)
    instance = service.get(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 解密密码
    decrypted_password = ""
    if instance.password_encrypted:
        try:
            decrypted_password = decrypt_instance_password(instance.password_encrypted)
        except Exception as e:
            logger.warning(f"密码解密失败: {e}")
            decrypted_password = ""
    
    result = await test_rdb_connection(
        instance.db_type.value if hasattr(instance.db_type, 'value') else str(instance.db_type),
        instance.host,
        instance.port,
        instance.username or "",
        decrypted_password
    )
    return InstanceTestResult(**result)


@router.post("", response_model=RDBInstanceResponse)
async def create_rdb_instance(
    instance_data: RDBInstanceCreate,
    current_user: User = Depends(require_permission("instance:create")),
    db: Session = Depends(get_db)
):
    """创建 RDB 实例"""
    service = RDBInstanceService(db)

    # 检查数据库类型是否启用
    db_type = instance_data.db_type.lower() if instance_data.db_type else "mysql"
    if not check_db_type_enabled(db, db_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{db_type.upper()} 实例类型已被禁用，无法创建新实例"
        )

    # 检查名称是否已存在
    if service.get_by_name(instance_data.name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="实例名称已存在"
        )

    # 检测是否为 RDS endpoint
    detected_is_rds = instance_data.is_rds or (instance_data.host and is_rds_endpoint(instance_data.host))

    # RDS 实例不需要测试连接（可能无法从当前网络访问）
    if not detected_is_rds:
        # 非RDS实例必须有连接信息
        if not instance_data.host:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="主机地址不能为空"
            )

        # MySQL/PostgreSQL 需要用户名和密码
        if not instance_data.username or not instance_data.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MySQL/PostgreSQL 实例需要用户名和密码"
            )

        # 测试连接
        conn_result = await test_rdb_connection(
            instance_data.db_type or "mysql",
            instance_data.host,
            instance_data.port or 3306,
            instance_data.username or "",
            instance_data.password or ""
        )

        if not conn_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"连接测试失败: {conn_result['message']}"
            )

    # 创建实例
    # 自动检测是否为 RDS 实例并解析区域
    is_rds = instance_data.is_rds
    aws_region = instance_data.aws_region

    if instance_data.host:
        # 如果 host 是 RDS endpoint，自动设置 is_rds
        if is_rds_endpoint(instance_data.host):
            if not is_rds:
                is_rds = True
                logger.info(f"检测到 RDS endpoint，自动设置 is_rds=True: {instance_data.host}")

            # 如果用户没有指定区域，自动解析
            if not aws_region:
                aws_region = parse_aws_region_from_host(instance_data.host)
                if aws_region:
                    logger.info(f"从 host 自动解析出 AWS 区域: {aws_region}")

    instance = service.create({
        "name": instance_data.name,
        "db_type": instance_data.db_type or "mysql",
        "host": instance_data.host or "",
        "port": instance_data.port or 3306,
        "username": instance_data.username or "",
        "password_encrypted": encrypt_instance_password(instance_data.password) if instance_data.password else "",
        "environment_id": instance_data.environment_id,
        "group_id": instance_data.group_id,
        "description": instance_data.description,
        "status": instance_data.status if instance_data.status is not None else True,
        "is_rds": is_rds,
        "rds_instance_id": instance_data.rds_instance_id,
        "aws_region": aws_region,
        "slow_query_threshold": instance_data.slow_query_threshold,
        "enable_monitoring": instance_data.enable_monitoring
    })
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

    logger.info(f"创建 RDB 实例: {instance.name} (ID: {instance.id})")
    return RDBInstanceResponse.model_validate(instance)


@router.put("/{instance_id}", response_model=RDBInstanceResponse)
async def update_rdb_instance(
    instance_id: int,
    instance_data: RDBInstanceUpdate,
    current_user: User = Depends(require_permission("instance:update")),
    db: Session = Depends(get_db)
):
    """更新 RDB 实例"""
    service = RDBInstanceService(db)
    instance = service.get(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )

    # 更新字段
    update_data = instance_data.model_dump(exclude_unset=True)

    # 如果更新了密码，需要加密
    if 'password' in update_data:
        update_data['password_encrypted'] = encrypt_instance_password(update_data.pop('password'))

    # 如果更新了 host，自动检测 RDS 并解析区域
    if 'host' in update_data:
        host = update_data['host']
        if host and is_rds_endpoint(host):
            # 自动设置 is_rds
            if 'is_rds' not in update_data:
                update_data['is_rds'] = True
                logger.info(f"检测到 RDS endpoint，自动设置 is_rds=True: {host}")

            # 自动解析区域
            if 'aws_region' not in update_data:
                parsed_region = parse_aws_region_from_host(host)
                if parsed_region:
                    update_data['aws_region'] = parsed_region
                    logger.info(f"从 host 自动解析出 AWS 区域: {parsed_region}")

    instance = service.update(instance_id, update_data)

    logger.info(f"更新 RDB 实例: {instance.name} (ID: {instance.id})")
    return RDBInstanceResponse.model_validate(instance)


@router.post("/sync-aws-regions")
async def sync_aws_regions(
    current_user: User = Depends(get_operator),
    db: Session = Depends(get_db)
):
    """
    批量同步 AWS 区域

    自动从 RDS endpoint 解析区域并更新到数据库
    适用于已有实例的区域信息补充
    """
    service = RDBInstanceService(db)
    instances = service.get_all()
    updated_count = 0

    for instance in instances:
        if instance.host and is_rds_endpoint(instance.host):
            # 解析区域
            region = parse_aws_region_from_host(instance.host)
            if region and instance.aws_region != region:
                # 更新实例
                instance.aws_region = region
                db.commit()
                updated_count += 1
                logger.info(f"同步实例 {instance.name} 的 AWS 区域: {region}")

    return {
        "message": f"同步完成，更新了 {updated_count} 个实例的 AWS 区域",
        "updated_count": updated_count
    }
