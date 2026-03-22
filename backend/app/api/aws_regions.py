"""
AWS 区域配置 API
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AWSRegion
from app.deps import get_current_user
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
    
    class Config:
        from_attributes = True


class AWSRegionGrouped(BaseModel):
    """分组的 AWS 区域响应"""
    geo_group: str
    regions: List[AWSRegionResponse]


@router.get("", response_model=List[AWSRegionResponse])
async def get_aws_regions(
    enabled_only: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取 AWS 区域列表
    
    - enabled_only: 是否只返回启用的区域
    """
    query = db.query(AWSRegion)
    if enabled_only:
        query = query.filter(AWSRegion.is_enabled == True)
    
    regions = query.order_by(AWSRegion.geo_group, AWSRegion.display_order).all()
    return regions


@router.get("/grouped", response_model=List[AWSRegionGrouped])
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
        query = query.filter(AWSRegion.is_enabled == True)
    
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
