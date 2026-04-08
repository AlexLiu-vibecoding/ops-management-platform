"""
JWT 轮换 API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db, SessionLocal
from app.models import User
from app.deps import get_current_user, get_super_admin
from app.services.jwt_rotation_service import JWTRotationService

router = APIRouter(prefix="/jwt-rotation", tags=["JWT轮换"])


# Schema
class KeyVersionInfo(BaseModel):
    id: int
    key_id: str
    key_value_preview: str
    is_active: bool
    created_at: Optional[str] = None


class JWTRotationStatus(BaseModel):
    enabled: bool
    current_version: str
    total_keys: int
    keys: List[KeyVersionInfo]
    last_rotation_at: Optional[str] = None


class GenerateKeyRequest(BaseModel):
    key_id: Optional[str] = None  # 可选指定版本号


class GenerateKeyResponse(BaseModel):
    success: bool
    new_version: str
    key_preview: str


class SwitchVersionRequest(BaseModel):
    target_version: str


class MessageResponse(BaseModel):
    success: bool
    message: str
    note: Optional[str] = None


# API
@router.get("/status", response_model=JWTRotationStatus)
async def get_jwt_rotation_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 JWT 轮换状态"""
    service = JWTRotationService(db)
    return service.get_status()


@router.get("/versions", response_model=List[KeyVersionInfo])
async def get_jwt_versions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有 JWT 密钥版本"""
    service = JWTRotationService(db)
    keys = service.get_all_keys()
    return [k.to_dict() for k in keys]


@router.post("/generate-key", response_model=GenerateKeyResponse)
async def generate_jwt_key(
    request: GenerateKeyRequest,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """生成新的 JWT 密钥"""
    service = JWTRotationService(db, operator_id=current_user.id)
    
    try:
        key = service.generate_key(request.key_id)
        return GenerateKeyResponse(
            success=True,
            new_version=key.key_id,
            key_preview=key.key_value[:4] + "***" + key.key_value[-4:]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/switch-version", response_model=MessageResponse)
async def switch_jwt_version(
    request: SwitchVersionRequest,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """切换 JWT 密钥版本"""
    service = JWTRotationService(db, operator_id=current_user.id)
    success = service.switch_version(request.target_version)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"切换到 {request.target_version} 失败，密钥可能不存在"
        )
    
    return MessageResponse(
        success=True,
        message=f"已切换到 {request.target_version}",
        note="新登录的用户将使用新密钥签发，旧密钥签发的 token 在过期前仍可验证"
    )


@router.post("/full-rotation", response_model=GenerateKeyResponse)
async def full_jwt_rotation(
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """一键轮换 JWT 密钥（生成新密钥并切换）"""
    service = JWTRotationService(db, operator_id=current_user.id)
    result = service.full_rotation()
    
    return GenerateKeyResponse(
        success=result["success"],
        new_version=result["new_version"],
        key_preview=result["key_preview"]
    )


@router.delete("/keys/{key_id}", response_model=MessageResponse)
async def delete_jwt_key(
    key_id: str,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """删除指定的 JWT 密钥版本"""
    service = JWTRotationService(db, operator_id=current_user.id)
    
    try:
        success = service.delete_key(key_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"密钥版本 {key_id} 不存在")
        
        return MessageResponse(
            success=True,
            message=f"密钥版本 {key_id} 已删除",
            note="删除后无法恢复"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
