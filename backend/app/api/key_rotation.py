"""
密钥轮换 API

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
from app.models.key_rotation import KeyRotationConfig
from app.database import SessionLocal
from app.config import settings
from app.services.key_rotation_service import KeyRotationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/key-rotation", tags=["密钥轮换"])


# ==================== Schema ====================

class KeyVersionInfo(BaseModel):
    """密钥版本信息"""
    current_version: str
    v1_configured: bool
    v2_configured: bool
    v2_key_preview: str


class EncryptionStatistics(BaseModel):
    """加密数据统计"""
    total: int
    v1_count: int
    v2_count: int
    legacy_count: int
    needs_migration: int


class KeyRotationStatus(BaseModel):
    """密钥轮换状态"""
    can_rotate: bool
    reason: Optional[str] = None
    migration_needed: bool
    unrotated_count: int
    v1_configured: bool
    v2_configured: bool
    current_version: str


class RotationConfig(BaseModel):
    """轮换配置"""
    id: int
    enabled: bool
    schedule_type: str
    schedule_day: int
    schedule_time: str
    current_key_id: str
    v2_key: Optional[str] = None
    has_v2_key: bool = False
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


class MigrationPreview(BaseModel):
    """迁移预览"""
    table_name: str
    field_name: str
    description: str
    total: int
    v1_or_legacy: int
    v2: int


class MigrationPreviewResponse(BaseModel):
    """迁移预览响应"""
    can_migrate: bool
    preview_tables: List[MigrationPreview]
    total_records: int
    total_needs_migration: int


class MigrationResult(BaseModel):
    """迁移结果"""
    table_name: str
    field_name: str
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
    operator_id: Optional[int] = None
    created_at: str


class RotationHistoryResponse(BaseModel):
    """轮换历史响应"""
    logs: List[RotationLog]
    total: int
    page: int
    page_size: int


class SwitchVersionRequest(BaseModel):
    """切换版本请求"""
    target_version: str = Field(..., pattern="^(v1|v2)$")


# ==================== 端点 ====================

@router.get("/status", response_model=KeyRotationStatus)
async def get_key_rotation_status(
    current_user: User = Depends(get_super_admin)
):
    """
    获取密钥轮换状态
    """
    db = SessionLocal()
    try:
        # 检查数据库中的 v2_key
        config = db.query(KeyRotationConfig).first()
        has_v2_key = bool(config and config.v2_key)
        
        service = KeyRotationService(db)
        stats = service.get_statistics()
        
        return KeyRotationStatus(
            can_rotate=has_v2_key,
            reason=None if has_v2_key else "V2 密钥未生成，请点击「生成新密钥」按钮",
            migration_needed=stats["needs_migration"] > 0,
            unrotated_count=stats["needs_migration"],
            v1_configured=bool(settings.security.AES_KEY),
            v2_configured=has_v2_key,
            current_version=settings.security.AES_CURRENT_VERSION
        )
    finally:
        db.close()


@router.get("/versions", response_model=KeyVersionInfo)
async def get_key_versions(
    current_user: User = Depends(get_super_admin)
):
    """
    获取密钥版本信息
    """
    db = SessionLocal()
    try:
        config = db.query(KeyRotationConfig).first()
        v2_key = config.v2_key if config else None
        
        return KeyVersionInfo(
            current_version=settings.security.AES_CURRENT_VERSION,
            v1_configured=bool(settings.security.AES_KEY),
            v2_configured=bool(v2_key),
            v2_key_preview=v2_key[:4] + "***" if v2_key else ""
        )
    finally:
        db.close()


@router.get("/statistics", response_model=EncryptionStatistics)
async def get_encryption_statistics(
    current_user: User = Depends(get_super_admin)
):
    """
    获取加密数据统计
    """
    db = SessionLocal()
    try:
        service = KeyRotationService(db)
        stats = service.get_statistics()
        return EncryptionStatistics(**stats)
    finally:
        db.close()


@router.get("/config", response_model=RotationConfig)
async def get_rotation_config(
    current_user: User = Depends(get_super_admin)
):
    """
    获取轮换配置
    """
    db = SessionLocal()
    try:
        service = KeyRotationService(db)
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
    """
    更新轮换配置
    """
    # 验证 schedule_type
    if config_update.schedule_type and config_update.schedule_type not in ["weekly", "monthly", "quarterly"]:
        raise HTTPException(status_code=400, detail="schedule_type 必须是 weekly/monthly/quarterly")
    
    # 验证 schedule_day
    if config_update.schedule_day is not None:
        if config_update.schedule_type == "weekly" and (config_update.schedule_day < 0 or config_update.schedule_day > 6):
            raise HTTPException(status_code=400, detail="weekly 模式下 schedule_day 必须是 0-6 (周日到周六)")
        if config_update.schedule_type in ["monthly", "quarterly"] and (config_update.schedule_day < 1 or config_update.schedule_day > 31):
            raise HTTPException(status_code=400, detail="monthly/quarterly 模式下 schedule_day 必须是 1-31")
    
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
    """
    预览数据迁移
    """
    db = SessionLocal()
    try:
        config = db.query(KeyRotationConfig).first()
        if not config or not config.v2_key:
            raise HTTPException(status_code=400, detail="V2 密钥未生成，请先点击「生成新密钥」按钮")
        
        service = KeyRotationService(db, operator_id=current_user.id)
        preview_tables = service.preview_migration()
        
        total_records = sum(p["total"] for p in preview_tables)
        total_needs_migration = sum(p["v1_or_legacy"] for p in preview_tables)
        
        return MigrationPreviewResponse(
            can_migrate=total_needs_migration > 0,
            preview_tables=[MigrationPreview(**p) for p in preview_tables],
            total_records=total_records,
            total_needs_migration=total_needs_migration
        )
    finally:
        db.close()


@router.post("/migrate", response_model=MigrationResponse)
async def execute_migration(
    batch_size: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_super_admin)
):
    """
    执行数据迁移
    """
    db = SessionLocal()
    try:
        config = db.query(KeyRotationConfig).first()
        if not config or not config.v2_key:
            raise HTTPException(status_code=400, detail="V2 密钥未生成，请先点击「生成新密钥」按钮")
        
        service = KeyRotationService(db, operator_id=current_user.id)
        result = service.execute_migration(batch_size=batch_size)
        
        return MigrationResponse(
            success=result["success"],
            message="迁移完成" if result["success"] else f"迁移完成，但有 {result['total_failed']} 条记录失败",
            results=[MigrationResult(**r) for r in result["results"]],
            total_migrated=result["total_migrated"],
            total_failed=result["total_failed"]
        )
    finally:
        db.close()


@router.post("/switch-version", response_model=dict)
async def switch_key_version(
    request: SwitchVersionRequest,
    current_user: User = Depends(get_super_admin)
):
    """
    切换密钥版本
    """
    db = SessionLocal()
    try:
        config = db.query(KeyRotationConfig).first()
        if request.target_version == "v2" and (not config or not config.v2_key):
            raise HTTPException(status_code=400, detail="V2 密钥未生成，请先点击「生成新密钥」按钮")
        
        service = KeyRotationService(db, operator_id=current_user.id)
        success = service.switch_version(request.target_version)
        
        if not success:
            raise HTTPException(status_code=400, detail="切换版本失败")
        
        return {
            "success": True,
            "message": f"密钥版本切换到 {request.target_version}",
            "warning": "请重启服务使配置生效。重启后，新加密的数据将使用新密钥。",
            "note": "旧版本加密的数据仍可自动解密"
        }
    finally:
        db.close()


@router.get("/history", response_model=RotationHistoryResponse)
async def get_rotation_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_super_admin)
):
    """
    获取轮换历史记录
    """
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


@router.post("/auto-rotate", response_model=dict)
async def trigger_auto_rotation(
    current_user: User = Depends(get_super_admin)
):
    """
    手动触发自动轮换
    """
    db = SessionLocal()
    try:
        service = KeyRotationService(db, operator_id=current_user.id)
        config = service.get_config()
        
        # 如果没有 v2_key，自动生成
        if not config.v2_key:
            logger.info("自动生成 V2 密钥...")
            config.v2_key = secrets.token_hex(16)  # 生成32字符密钥
            db.commit()
        
        # 执行迁移
        migration_result = service.execute_migration()
        
        # 如果配置了自动切换，则切换版本
        if config.auto_switch and migration_result["success"]:
            current_ver = settings.security.AES_CURRENT_VERSION
            target_ver = "v2" if current_ver == "v1" else "v1"
            service.switch_version(target_ver)
        
        # 更新配置中的轮换时间
        config.last_rotation_at = db.query(KeyRotationConfig).first().last_rotation_at
        db.commit()
        
        return {
            "success": migration_result["success"],
            "message": "自动轮换执行完成",
            "migrated": migration_result["total_migrated"],
            "failed": migration_result["total_failed"]
        }
    finally:
        db.close()


@router.post("/generate-v2-key", response_model=dict)
async def generate_v2_key(
    current_user: User = Depends(get_super_admin)
):
    """
    生成新的 V2 密钥
    """
    db = SessionLocal()
    try:
        service = KeyRotationService(db, operator_id=current_user.id)
        config = service.get_config()
        
        # 生成安全的随机密钥（32字符）
        new_key = secrets.token_hex(16)
        config.v2_key = new_key
        db.commit()
        
        logger.info(f"用户 {current_user.username} 生成了新的 V2 密钥")
        
        return {
            "success": True,
            "message": "V2 密钥已生成",
            "key_preview": new_key[:4] + "***" + new_key[-4:],
            "warning": "请尽快完成数据迁移并切换版本"
        }
    finally:
        db.close()
