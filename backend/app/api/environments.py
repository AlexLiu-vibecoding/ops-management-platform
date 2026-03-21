"""
环境管理API
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Environment
from app.schemas import EnvironmentCreate, EnvironmentUpdate, EnvironmentResponse, MessageResponse
from app.deps import get_super_admin, get_current_user
from app.models import User

router = APIRouter(prefix="/environments", tags=["环境管理"])


@router.get("")
async def list_environments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取环境列表"""
    environments = db.query(Environment).all()
    return {
        "total": len(environments),
        "items": [EnvironmentResponse.from_orm(e) for e in environments]
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
    return EnvironmentResponse.from_orm(env)


@router.post("", response_model=EnvironmentResponse)
async def create_environment(
    env_data: EnvironmentCreate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """创建环境（仅超级管理员）"""
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
    
    env = Environment(**env_data.dict())
    db.add(env)
    db.commit()
    db.refresh(env)
    
    return EnvironmentResponse.from_orm(env)


@router.put("/{env_id}", response_model=EnvironmentResponse)
async def update_environment(
    env_id: int,
    env_data: EnvironmentUpdate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """更新环境（仅超级管理员）"""
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Environment not found"
        )
    
    # 更新字段
    update_data = env_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(env, key, value)
    
    db.commit()
    db.refresh(env)
    
    return EnvironmentResponse.from_orm(env)


@router.delete("/{env_id}", response_model=MessageResponse)
async def delete_environment(
    env_id: int,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """删除环境（仅超级管理员）"""
    env = db.query(Environment).filter(Environment.id == env_id).first()
    if not env:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Environment not found"
        )
    
    # 检查是否有关联的实例
    if env.instances:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete environment with instances"
        )
    
    db.delete(env)
    db.commit()
    
    return MessageResponse(message="环境删除成功")
