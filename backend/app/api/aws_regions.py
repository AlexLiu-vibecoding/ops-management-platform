"""
AWS 区域配置 API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AWSRegion
from app.deps import get_current_user, get_super_admin
from app.models import User

router = APIRouter(prefix="/aws-regions", tags=["AWS区域配置"])


class AWSRegionResponse(BaseModel):
    """AWS 区域响应模型"""
    id: int
    region_code: str
    region_name: str
    geo_group: str
    display_order: int
    is_enabled: bool
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class AWSRegionGrouped(BaseModel):
    """分组的 AWS 区域响应"""
    geo_group: str
    regions: list[AWSRegionResponse]


class AWSRegionUpdate(BaseModel):
    """更新 AWS 区域请求"""
    is_enabled: Optional[bool] = None
    region_name: Optional[str] = None
    description: Optional[str] = None


class AWSRegionCreate(BaseModel):
    """创建 AWS 区域请求"""
    region_code: str
    region_name: str
    geo_group: str
    display_order: int = 0
    is_enabled: bool = True
    description: Optional[str] = None


@router.get("", response_model=list[AWSRegionResponse])
async def get_aws_regions(
    enabled_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取 AWS 区域列表
    
    - enabled_only: 是否只返回启用的区域（默认返回所有）
    """
    query = db.query(AWSRegion)
    if enabled_only:
        query = query.filter(AWSRegion.is_enabled)
    
    regions = query.order_by(AWSRegion.geo_group, AWSRegion.display_order).all()
    return regions


@router.get("/grouped", response_model=list[AWSRegionGrouped])
async def get_aws_regions_grouped(
    enabled_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取按地理区域分组的 AWS 区域列表
    
    - enabled_only: 是否只返回启用的区域
    """
    query = db.query(AWSRegion)
    if enabled_only:
        query = query.filter(AWSRegion.is_enabled)
    
    regions = query.order_by(AWSRegion.geo_group, AWSRegion.display_order).all()
    
    # 按地理区域分组
    grouped = {}
    geo_order = ["美国", "美洲其他", "欧洲", "亚太", "中东", "非洲", "中国"]
    
    for region in regions:
        geo = region.geo_group
        if geo not in grouped:
            grouped[geo] = []
        grouped[geo].append(AWSRegionResponse.model_validate(region))
    
    # 按预定义顺序返回
    result = []
    for geo in geo_order:
        if geo in grouped:
            result.append(AWSRegionGrouped(geo_group=geo, regions=grouped[geo]))
    
    return result


@router.put("/{region_id}", response_model=AWSRegionResponse)
async def update_aws_region(
    region_id: int,
    data: AWSRegionUpdate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """
    更新 AWS 区域配置（仅超级管理员）
    
    可用于启用/禁用区域、修改区域名称或描述
    """
    region = db.query(AWSRegion).filter(AWSRegion.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="区域不存在")
    
    if data.is_enabled is not None:
        region.is_enabled = data.is_enabled
    if data.region_name is not None:
        region.region_name = data.region_name
    if data.description is not None:
        region.description = data.description
    
    db.commit()
    db.refresh(region)
    return AWSRegionResponse.model_validate(region)


@router.post("", response_model=AWSRegionResponse)
async def create_aws_region(
    data: AWSRegionCreate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """
    添加自定义 AWS 区域（仅超级管理员）
    
    用于添加 AWS 新发布的区域或私有区域
    """
    # 检查区域代码是否已存在
    existing = db.query(AWSRegion).filter(AWSRegion.region_code == data.region_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"区域代码 {data.region_code} 已存在")
    
    region = AWSRegion(
        region_code=data.region_code,
        region_name=data.region_name,
        geo_group=data.geo_group,
        display_order=data.display_order,
        is_enabled=data.is_enabled,
        description=data.description
    )
    db.add(region)
    db.commit()
    db.refresh(region)
    return AWSRegionResponse.model_validate(region)


@router.delete("/{region_id}")
async def delete_aws_region(
    region_id: int,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """
    删除 AWS 区域（仅超级管理员）
    
    注意：正在使用的区域无法删除
    """
    region = db.query(AWSRegion).filter(AWSRegion.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="区域不存在")
    
    # 检查是否有环境或实例使用该区域
    from app.models import Environment, RDBInstance
    
    env_count = db.query(Environment).filter(Environment.aws_region == region.region_code).count()
    rdb_count = db.query(RDBInstance).filter(RDBInstance.aws_region == region.region_code).count()
    
    if env_count > 0 or rdb_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"无法删除：有 {env_count} 个环境和 {rdb_count} 个实例正在使用该区域"
        )
    
    db.delete(region)
    db.commit()
    return {"message": "区域删除成功"}
