"""
密钥轮换 API - 支持动态多版本

提供 AES 密钥轮换、数据迁移和自动轮换配置功能
"""

import os
import secrets
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.deps import get_current_user, get_super_admin
from app.models import User
from app.models.key_rotation import KeyRotationConfig, KeyRotationKey
from app.database import SessionLocal
from app.config import settings
from app.services.key_rotation_service import KeyRotationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/key-rotation", tags=["密钥轮换"])


# ==================== Schema ====================

class KeyVersionInfo(BaseModel):
    """密钥版本信息"""
    current_version: str
    total_versions: int
    versions: List[dict]


class KeyRotationStatus(BaseModel):
    """密钥轮换状态"""
    can_rotate: bool
    reason: Optional[str] = None
    migration_needed: bool
    unrotated_count: int
    current_version: str
    total_versions: int
    current_key_preview: str
    has_pending_key: bool


class RotationConfig(BaseModel):
    """轮换配置"""
    id: int
    enabled: bool
    schedule_type: str
    schedule_day: int
    schedule_time: str
    current_key_id: str
    auto_switch: bool
    last_rotation_at: Optional[str] = None
    next_rotation_at: Optional[str] = None


class RotationConfigUpdate(BaseModel):
    """轮换配置更新"""
    enabled: Optional[bool] = None
    schedule_type: Optional[str] = None
    schedule_day: Optional[int] = None
    schedule_time: Optional[str] = None
    auto_switch: Optional[bool] = None


class MigrationPreviewItem(BaseModel):
    """迁移预览项"""
    description: str
    table: Optional[str] = None
    field: Optional[str] = None
    total: int
    migrated: int
    pending: int
    target_version: str


class MigrationPreviewResponse(BaseModel):
    """迁移预览响应"""
    can_migrate: bool
    preview: List[MigrationPreviewItem]
    total_records: int
    total_pending: int
    target_version: Optional[str] = None


class MigrationResult(BaseModel):
    """迁移结果"""
    table: str
    field: str
    total: int
    migrated: int
    failed: int
    errors: List[str]


class MigrationResponse(BaseModel):
    """迁移响应"""
    success: bool
    message: str
    results: List[MigrationResult]
    total_migrated: int
    total_failed: int
    target_version: Optional[str] = None


class RotationLog(BaseModel):
    """轮换日志"""
    id: int
    action: str
    from_version: Optional[str] = None
    to_version: Optional[str] = None
    status: str
    total_records: int
    migrated_records: int
    failed_records: int
    error_message: Optional[str] = None
    created_at: str


class RotationHistoryResponse(BaseModel):
    """轮换历史响应"""
    logs: List[RotationLog]
    total: int
    page: int
    page_size: int


class SwitchVersionRequest(BaseModel):
    """切换版本请求"""
    target_version: str


class GenerateKeyResponse(BaseModel):
    """生成密钥响应"""
    success: bool
    new_version: str
    key_preview: str


class FullRotationResponse(BaseModel):
    """一键轮换响应"""
    success: bool
    new_key_version: str
    migration_result: dict
    auto_switched: bool


# ==================== 端点 ====================

@router.get("/overview")
async def get_key_rotation_overview(
    current_user: User = Depends(get_super_admin)
):
    """获取密钥轮换概览"""
    db = SessionLocal()
    try:
        service = KeyRotationService(db, operator_id=current_user.id)
        return service.get_overview()
    finally:
        db.close()


@router.get("/status", response_model=KeyRotationStatus)
async def get_key_rotation_status(
    current_user: User = Depends(get_super_admin)
):
    """获取密钥轮换状态"""
    db = SessionLocal()
    try:
        service = KeyRotationService(db, operator_id=current_user.id)
        status = service.get_status()
        return KeyRotationStatus(**status)
    finally:
        db.close()


@router.get("/versions", response_model=KeyVersionInfo)
async def get_key_versions(
    current_user: User = Depends(get_super_admin)
):
    """获取所有密钥版本"""
    db = SessionLocal()
    try:
        service = KeyRotationService(db, operator_id=current_user.id)
        config = service.get_config()
        keys = service.get_all_keys()
        
        return KeyVersionInfo(
            current_version=config.current_key_id,
            total_versions=len(keys),
            versions=[k.to_dict() for k in keys]
        )
    finally:
        db.close()


@router.get("/config", response_model=RotationConfig)
async def get_rotation_config(
    current_user: User = Depends(get_super_admin)
):
    """获取轮换配置"""
    db = SessionLocal()
    try:
        service = KeyRotationService(db, operator_id=current_user.id)
        config = service.get_config()
        
        # 计算下次轮换时间
        next_rotation = service.calculate_next_rotation()
        config.next_rotation_at = next_rotation
        
        return RotationConfig(**config.to_dict())
    finally:
        db.close()


@router.put("/config", response_model=RotationConfig)
async def update_rotation_config(
    config_update: RotationConfigUpdate,
    current_user: User = Depends(get_super_admin)
):
    """更新轮换配置"""
    db = SessionLocal()
    try:
        service = KeyRotationService(db, operator_id=current_user.id)
        config = service.update_config(
            enabled=config_update.enabled,
            schedule_type=config_update.schedule_type,
            schedule_day=config_update.schedule_day,
            schedule_time=config_update.schedule_time,
            auto_switch=config_update.auto_switch
        )
        
        # 重新加载定时任务
        try:
            from app.services.task_scheduler import task_scheduler
            task_scheduler.reload_key_rotation_task()
        except Exception as e:
            logger.warning(f"重新加载密钥轮换任务失败: {e}")
        
        # 计算下次轮换时间
        next_rotation = service.calculate_next_rotation()
        config.next_rotation_at = next_rotation
        
        return RotationConfig(**config.to_dict())
    finally:
        db.close()


@router.get("/migration-preview", response_model=MigrationPreviewResponse)
async def get_migration_preview(
    current_user: User = Depends(get_super_admin)
):
    """预览数据迁移"""
    db = SessionLocal()
    try:
        service = KeyRotationService(db, operator_id=current_user.id)
        preview = service.preview_migration()
        
        total_records = sum(p.get("total", 0) for p in preview)
        total_pending = sum(p.get("pending", 0) for p in preview)
        target_version = preview[0].get("target_version") if preview else None
        
        return MigrationPreviewResponse(
            can_migrate=total_pending > 0,
            preview=[MigrationPreviewItem(**p) for p in preview],
            total_records=total_records,
            total_pending=total_pending,
            target_version=target_version
        )
    finally:
        db.close()


@router.post("/migrate", response_model=MigrationResponse)
async def execute_migration(
    batch_size: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_super_admin)
):
    """执行数据迁移"""
    db = SessionLocal()
    try:
        service = KeyRotationService(db, operator_id=current_user.id)
        result = service.execute_migration(batch_size=batch_size)
        
        return MigrationResponse(
            success=result["success"],
            message=result.get("message", ""),
            results=[MigrationResult(**r) for r in result.get("results", [])],
            total_migrated=result["total_migrated"],
            total_failed=result["total_failed"],
            target_version=result.get("target_version")
        )
    finally:
        db.close()


@router.post("/switch-version")
async def switch_key_version(
    request: SwitchVersionRequest,
    current_user: User = Depends(get_super_admin)
):
    """切换密钥版本"""
    db = SessionLocal()
    try:
        service = KeyRotationService(db, operator_id=current_user.id)
        success = service.switch_version(request.target_version)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"切换到 {request.target_version} 失败，密钥可能不存在")
        
        return {
            "success": True,
            "message": f"已切换到 {request.target_version}",
            "note": "新加密的数据将使用新密钥，旧密钥加密的数据仍可自动解密"
        }
    finally:
        db.close()


@router.post("/generate-key", response_model=GenerateKeyResponse)
async def generate_new_key(
    current_user: User = Depends(get_super_admin)
):
    """生成新的密钥版本"""
    db = SessionLocal()
    try:
        service = KeyRotationService(db, operator_id=current_user.id)
        new_key = service.generate_new_key()
        
        logger.info(f"用户 {current_user.username} 生成了新密钥: {new_key.key_id}")
        
        return GenerateKeyResponse(
            success=True,
            new_version=new_key.key_id,
            key_preview=new_key.key_value[:4] + "***" + new_key.key_value[-4:]
        )
    finally:
        db.close()


@router.get("/history", response_model=RotationHistoryResponse)
async def get_rotation_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_super_admin)
):
    """获取轮换历史记录"""
    db = SessionLocal()
    try:
        service = KeyRotationService(db)
        offset = (page - 1) * page_size
        
        logs = service.get_history(limit=page_size, offset=offset)
        total = service.count_history()
        
        return RotationHistoryResponse(
            logs=[RotationLog(**log.to_dict()) for log in logs],
            total=total,
            page=page,
            page_size=page_size
        )
    finally:
        db.close()


@router.post("/full-rotation", response_model=FullRotationResponse)
async def full_rotation(
    current_user: User = Depends(get_super_admin)
):
    """一键完成轮换：生成密钥 -> 迁移数据 -> 切换版本"""
    db = SessionLocal()
    try:
        service = KeyRotationService(db, operator_id=current_user.id)
        result = service.full_rotation()
        
        return FullRotationResponse(
            success=result["migration_result"]["success"] if result["migration_result"] else True,
            new_key_version=result["new_key_version"],
            migration_result=result["migration_result"],
            auto_switched=result["auto_switched"]
        )
    finally:
        db.close()


@router.post("/auto-rotate")
async def trigger_auto_rotation(
    current_user: User = Depends(get_super_admin)
):
    """触发自动轮换"""
    db = SessionLocal()
    try:
        service = KeyRotationService(db, operator_id=current_user.id)
        config = service.get_config()
        
        if not config.enabled:
            raise HTTPException(status_code=400, detail="自动轮换未启用")
        
        result = service.full_rotation()
        
        return {
            "success": result["migration_result"]["success"] if result["migration_result"] else True,
            "message": "自动轮换执行完成",
            "new_key_version": result["new_key_version"],
            "migrated": result["migration_result"].get("total_migrated", 0),
            "failed": result["migration_result"].get("total_failed", 0)
        }
    finally:
        db.close()


@router.delete("/keys/{key_id}")
async def delete_key_version(
    key_id: str,
    current_user: User = Depends(get_super_admin)
):
    """删除密钥版本（不能删除当前激活版本）"""
    db = SessionLocal()
    try:
        from app.services.key_rotation_service import KeyRotationService
        service = KeyRotationService(db, operator_id=current_user.id)
        
        # 获取要删除的密钥
        key = service.get_key_by_id(key_id)
        if not key:
            raise HTTPException(status_code=404, detail="密钥版本不存在")
        
        # 不能删除当前激活版本
        if key.is_active:
            raise HTTPException(status_code=400, detail="不能删除当前使用的密钥版本")
        
        # 删除密钥
        db.delete(key)
        db.commit()
        
        # 记录日志
        service.add_log(
            action="delete",
            status="success",
            from_version=key_id,
            to_version=None
        )
        
        return {"success": True, "message": f"密钥版本 {key_id.upper()} 已删除"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
    finally:
        db.close()
