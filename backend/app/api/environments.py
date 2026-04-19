"""
环境管理API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import Environment
from app.schemas import EnvironmentCreate, EnvironmentUpdate, EnvironmentResponse, MessageResponse
from app.deps import require_permission, get_current_user
from app.models import User
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/environments", tags=["环境管理"])


# ==================== AWS 连接测试 ====================

class AwsConfigTest(BaseModel):
    """AWS 配置测试请求"""
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"


class AwsConfigTestResponse(BaseModel):
    """AWS 配置测试响应"""
    success: bool
    message: str
    rds_instances_count: Optional[int] = None


@router.post("/{env_id}/test-aws", response_model=AwsConfigTestResponse)
async def test_environment_aws(
    env_id: int,
    request: AwsConfigTest,
    current_user: User = Depends(require_permission("environment:update")),
    db: Session = Depends(get_db)
):
    """测试环境的 AWS 连接"""
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, EndpointConnectionError
    
    try:
        session = boto3.Session(
            aws_access_key_id=request.aws_access_key_id,
            aws_secret_access_key=request.aws_secret_access_key,
            region_name=request.aws_region
        )
        rds_client = session.client("rds")
        
        # 测试连接：列出 RDS 实例
        response = rds_client.describe_db_instances(MaxRecords=100)
        instances_count = len(response.get("DBInstances", []))
        
        return AwsConfigTestResponse(
            success=True,
            message=f"AWS 连接成功，区域: {request.aws_region}，发现 {instances_count} 个 RDS 实例",
            rds_instances_count=instances_count
        )
        
    except NoCredentialsError:
        return AwsConfigTestResponse(success=False, message="AWS 凭证无效")
    except EndpointConnectionError:
        return AwsConfigTestResponse(success=False, message=f"无法连接到 AWS 端点 ({request.aws_region})")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code == "UnauthorizedOperation":
            return AwsConfigTestResponse(success=False, message="AWS 凭证无权限访问 RDS 服务")
        elif error_code == "InvalidClientTokenId":
            return AwsConfigTestResponse(success=False, message="AWS Access Key ID 无效")
        elif error_code == "SignatureDoesNotMatch":
            return AwsConfigTestResponse(success=False, message="AWS Secret Access Key 不正确")
        return AwsConfigTestResponse(success=False, message=f"AWS 错误: {error_code}")
    except Exception as e:
        return AwsConfigTestResponse(success=False, message=f"连接测试失败: {str(e)}")


# ==================== 环境 CRUD ====================

@router.get("")
async def list_environments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取环境列表（根据用户角色过滤）"""
    from app.models.permissions import RoleEnvironment
    
    # 获取用户可访问的环境ID列表
    permission_service = PermissionService(db)
    accessible_env_ids = permission_service.get_user_environment_ids(current_user)
    
    # 根据环境ID过滤
    if accessible_env_ids:
        environments = db.query(Environment).filter(Environment.id.in_(accessible_env_ids)).all()
    else:
        environments = []
    
    return {
        "total": len(environments),
        "items": [EnvironmentResponse.model_validate(e) for e in environments]
    }


@router.get("/{env_id}", response_model=EnvironmentResponse)
async def get_environment(
    env_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取环境详情"""
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Environment not found"
        )
    return EnvironmentResponse.model_validate(env)


@router.post("", response_model=EnvironmentResponse)
async def create_environment(
    env_data: EnvironmentCreate,
    current_user: User = Depends(require_permission("environment:create")),
    db: Session = Depends(get_db)
):
    """创建环境"""
    # 检查功能权限
    permission_service = PermissionService(db)
    permission_service.check_permission(current_user, "environment:create")
    
    # 检查名称是否已存在
    if db.query(Environment).filter(Environment.name == env_data.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Environment name already exists"
        )
    
    # 检查编码是否已存在
    if db.query(Environment).filter(Environment.code == env_data.code).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Environment code already exists"
        )
    
    # 创建环境
    data = env_data.dict()
    
    # 检查是否配置了 AWS 凭证
    aws_configured = bool(data.get("aws_access_key_id") and data.get("aws_secret_access_key"))
    data["aws_configured"] = aws_configured
    
    # 加密存储 AWS Secret Access Key（使用简单加密，生产环境应使用更强加密）
    if data.get("aws_secret_access_key"):
        from app.utils.auth import encrypt_instance_password
        data["aws_secret_access_key"] = encrypt_instance_password(data["aws_secret_access_key"])
    
    env = Environment(**data)
    db.add(env)
    db.commit()
    db.refresh(env)
    
    return EnvironmentResponse.model_validate(env)


@router.put("/{env_id}", response_model=EnvironmentResponse)
async def update_environment(
    env_id: int,
    env_data: EnvironmentUpdate,
    current_user: User = Depends(require_permission("environment:update")),
    db: Session = Depends(get_db)
):
    """更新环境"""
    # 检查功能权限
    permission_service = PermissionService(db)
    permission_service.check_permission(current_user, "environment:update")
    
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Environment not found"
        )
    
    # 更新字段
    update_data = env_data.dict(exclude_unset=True)
    
    # 处理 AWS 凭证更新
    if "aws_secret_access_key" in update_data and update_data["aws_secret_access_key"]:
        from app.utils.auth import encrypt_instance_password
        update_data["aws_secret_access_key"] = encrypt_instance_password(update_data["aws_secret_access_key"])
    
    # 更新 AWS 配置状态
    if "aws_access_key_id" in update_data or "aws_secret_access_key" in update_data:
        new_key = update_data.get("aws_access_key_id", env.aws_access_key_id)
        new_secret = update_data.get("aws_secret_access_key", env.aws_secret_access_key)
        update_data["aws_configured"] = bool(new_key and new_secret)
    
    for key, value in update_data.items():
        setattr(env, key, value)
    
    db.commit()
    db.refresh(env)
    
    return EnvironmentResponse.model_validate(env)


@router.delete("/{env_id}", response_model=MessageResponse)
async def delete_environment(
    env_id: int,
    current_user: User = Depends(require_permission("environment:delete")),
    db: Session = Depends(get_db)
):
    """删除环境"""
    # 检查功能权限
    permission_service = PermissionService(db)
    permission_service.check_permission(current_user, "environment:delete")
    
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Environment not found"
        )
    
    # 检查是否有关联的实例
    from app.models import RDBInstance, RedisInstance
    rdb_count = db.query(RDBInstance).filter(RDBInstance.environment_id == env_id).count()
    redis_count = db.query(RedisInstance).filter(RedisInstance.environment_id == env_id).count()
    
    if rdb_count > 0 or redis_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无法删除：环境下有 {rdb_count} 个 RDB 实例和 {redis_count} 个 Redis 实例"
        )
    
    db.delete(env)
    db.commit()
    
    return MessageResponse(message="环境删除成功")
