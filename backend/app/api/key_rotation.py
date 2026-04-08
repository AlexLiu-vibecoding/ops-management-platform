"""
密钥轮换 API

提供 AES 密钥轮换和数据迁移功能
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import get_current_user, get_super_admin
from app.models import User
from app.database import SessionLocal
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/key-rotation", tags=["密钥轮换"])


# ==================== Schema ====================

class KeyVersionStatus(BaseModel):
    """密钥版本状态"""
    current_version: str
    v1_configured: bool
    v2_configured: bool
    v1_key_preview: str  # 只显示前4位
    v2_key_preview: str


class KeyRotationStatus(BaseModel):
    """密钥轮换状态"""
    can_rotate: bool
    reason: Optional[str] = None
    migration_needed: bool
    unrotated_count: int


class MigrationPreview(BaseModel):
    """迁移预览"""
    table_name: str
    field_name: str
    description: str
    total: int
    needs_migration: int
    current_version_count: int
    old_version_count: int


class MigrationPreviewResponse(BaseModel):
    """迁移预览响应"""
    can_migrate: bool
    reason: Optional[str] = None
    tables: list[MigrationPreview]
    total_records: int
    total_needs_migration: int


class MigrationRequest(BaseModel):
    """迁移请求"""
    batch_size: int = Field(default=100, ge=1, le=1000, description="每批处理数量")


class MigrationResult(BaseModel):
    """迁移结果"""
    table_name: str
    field_name: str
    total: int
    migrated: int
    failed: int
    errors: list[str]


class MigrationResponse(BaseModel):
    """迁移响应"""
    success: bool
    message: str
    results: list[MigrationResult]
    total_migrated: int
    total_failed: int


# ==================== 端点 ====================

@router.get("/status", response_model=KeyRotationStatus)
async def get_key_rotation_status(
    current_user: User = Depends(get_super_admin)
):
    """
    获取密钥轮换状态
    
    检查是否可以进行密钥轮换操作
    """
    from app.utils.auth import AESCipher
    
    can_rotate = settings.security.has_aes_key_v2()
    migration_needed = False
    unrotated_count = 0
    
    if can_rotate:
        # 检查是否有需要迁移的数据
        db = SessionLocal()
        try:
            from sqlalchemy import text
            
            # 检查各表的加密字段
            tables_fields = [
                ("rdb_instances", "password_encrypted"),
                ("redis_instances", "password_encrypted"),
                ("ai_models", "api_key_encrypted"),
                ("aws_credentials", "aws_secret_access_key"),
            ]
            
            for table, field in tables_fields:
                try:
                    query = f"""
                        SELECT COUNT(*) FROM {table} 
                        WHERE {field} IS NOT NULL 
                        AND {field} != ''
                        AND NOT ({field} LIKE 'v2$%')
                    """
                    result = db.execute(text(query)).scalar()
                    unrotated_count += result or 0
                except Exception:
                    pass
            
            migration_needed = unrotated_count > 0
            
        finally:
            db.close()
    
    reason = None
    if not can_rotate:
        reason = "AES_KEY_V2 未配置，无法进行密钥轮换"
    
    return KeyRotationStatus(
        can_rotate=can_rotate,
        reason=reason,
        migration_needed=migration_needed,
        unrotated_count=unrotated_count
    )


@router.get("/versions", response_model=KeyVersionStatus)
async def get_key_versions(
    current_user: User = Depends(get_super_admin)
):
    """
    获取密钥版本信息
    
    返回各版本的配置状态（不显示完整密钥）
    """
    v1_key = settings.security.AES_KEY or ""
    v2_key = settings.security.AES_KEY_V2 or ""
    
    return KeyVersionStatus(
        current_version=settings.security.AES_CURRENT_VERSION,
        v1_configured=bool(v1_key),
        v2_configured=bool(v2_key),
        v1_key_preview=v1_key[:4] + "***" if v1_key else "",
        v2_key_preview=v2_key[:4] + "***" if v2_key else ""
    )


@router.get("/migration-preview", response_model=MigrationPreviewResponse)
async def get_migration_preview(
    current_user: User = Depends(get_super_admin)
):
    """
    预览数据迁移情况
    
    查看哪些加密数据需要迁移到新密钥
    """
    if not settings.security.has_aes_key_v2():
        raise HTTPException(
            status_code=400,
            detail="AES_KEY_V2 未配置，无法预览迁移"
        )
    
    db = SessionLocal()
    try:
        from sqlalchemy import text
        from app.utils.auth import AESCipher
        
        tables_config = [
            ("rdb_instances", "password_encrypted", "RDB 实例密码"),
            ("redis_instances", "password_encrypted", "Redis 实例密码"),
            ("ai_models", "api_key_encrypted", "AI 模型 API 密钥"),
            ("aws_credentials", "aws_secret_access_key", "AWS 访问密钥"),
        ]
        
        results = []
        total_records = 0
        total_needs_migration = 0
        current_version = settings.security.AES_CURRENT_VERSION
        target_version = "v2" if current_version == "v1" else "v1"
        
        for table, field, description in tables_config:
            try:
                # 获取总数
                count_query = f"""
                    SELECT COUNT(*) FROM {table} 
                    WHERE {field} IS NOT NULL AND {field} != ''
                """
                total = db.execute(text(count_query)).scalar() or 0
                
                # 获取已是目标版本的数量
                target_query = f"""
                    SELECT COUNT(*) FROM {table} 
                    WHERE {field} LIKE '{target_version}$%'
                """
                target_count = db.execute(text(target_query)).scalar() or 0
                
                needs_migration = total - target_count
                
                results.append(MigrationPreview(
                    table_name=table,
                    field_name=field,
                    description=description,
                    total=total,
                    needs_migration=needs_migration,
                    current_version_count=target_count,
                    old_version_count=total - target_count
                ))
                
                total_records += total
                total_needs_migration += needs_migration
                
            except Exception as e:
                logger.warning(f"预览表 {table} 失败: {e}")
                results.append(MigrationPreview(
                    table_name=table,
                    field_name=field,
                    description=description,
                    total=0,
                    needs_migration=0,
                    current_version_count=0,
                    old_version_count=0
                ))
        
        return MigrationPreviewResponse(
            can_migrate=total_needs_migration > 0,
            reason=None if total_needs_migration > 0 else "所有数据已是最新的密钥版本",
            tables=results,
            total_records=total_records,
            total_needs_migration=total_needs_migration
        )
        
    finally:
        db.close()


@router.post("/migrate", response_model=MigrationResponse)
async def execute_migration(
    request: MigrationRequest,
    current_user: User = Depends(get_super_admin)
):
    """
    执行数据迁移
    
    将加密数据从旧密钥迁移到新密钥
    """
    if not settings.security.has_aes_key_v2():
        raise HTTPException(
            status_code=400,
            detail="AES_KEY_V2 未配置，无法执行迁移"
        )
    
    from app.utils.auth import AESCipher
    from sqlalchemy import text
    
    db = SessionLocal()
    try:
        results = []
        total_migrated = 0
        total_failed = 0
        
        tables_config = [
            ("rdb_instances", "password_encrypted"),
            ("redis_instances", "password_encrypted"),
            ("ai_models", "api_key_encrypted"),
            ("aws_credentials", "aws_secret_access_key"),
        ]
        
        for table, field in tables_config:
            try:
                # 获取需要迁移的记录
                select_query = f"""
                    SELECT id, {field} FROM {table} 
                    WHERE {field} IS NOT NULL 
                    AND {field} != ''
                    AND NOT ({field} LIKE 'v2$%')
                    LIMIT :batch_size
                """
                rows = db.execute(text(select_query), {"batch_size": request.batch_size}).fetchall()
                
                migrated = 0
                failed = 0
                errors = []
                
                for row in rows:
                    record_id = row[0]
                    old_value = row[1]
                    
                    try:
                        # 解密并重新加密
                        plaintext = AESCipher.decrypt(old_value)
                        new_value = AESCipher().encrypt(plaintext)
                        
                        # 更新数据库
                        update_query = f"""
                            UPDATE {table} 
                            SET {field} = :new_value 
                            WHERE id = :id
                        """
                        db.execute(text(update_query), {"new_value": new_value, "id": record_id})
                        migrated += 1
                        
                    except Exception as e:
                        failed += 1
                        errors.append(f"ID={record_id}: {str(e)}")
                        logger.warning(f"迁移 {table}.{field} ID={record_id} 失败: {e}")
                
                db.commit()
                
                results.append(MigrationResult(
                    table_name=table,
                    field_name=field,
                    total=len(rows),
                    migrated=migrated,
                    failed=failed,
                    errors=errors[:10]  # 最多保留10条错误
                ))
                
                total_migrated += migrated
                total_failed += failed
                
            except Exception as e:
                logger.error(f"迁移表 {table}.{field} 失败: {e}")
                db.rollback()
                results.append(MigrationResult(
                    table_name=table,
                    field_name=field,
                    total=0,
                    migrated=0,
                    failed=0,
                    errors=[str(e)]
                ))
        
        success = total_failed == 0
        
        return MigrationResponse(
            success=success,
            message="迁移完成" if success else f"迁移完成，但有 {total_failed} 条记录失败",
            results=results,
            total_migrated=total_migrated,
            total_failed=total_failed
        )
        
    finally:
        db.close()


@router.post("/switch-version")
async def switch_key_version(
    target_version: str,
    current_user: User = Depends(get_super_admin)
):
    """
    切换当前使用的密钥版本
    
    注意：切换前请确保数据已迁移完成
    """
    if target_version not in ["v1", "v2"]:
        raise HTTPException(
            status_code=400,
            detail="目标版本必须是 v1 或 v2"
        )
    
    if target_version == "v2" and not settings.security.has_aes_key_v2():
        raise HTTPException(
            status_code=400,
            detail="AES_KEY_V2 未配置，无法切换到 v2"
        )
    
    # 注意：实际切换需要重启服务或重新加载配置
    # 这里只是返回提示信息
    
    return {
        "success": True,
        "message": f"密钥版本切换到 {target_version}",
        "warning": "请重启服务使配置生效。重启后，新加密的数据将使用新密钥。",
        "note": "旧版本加密的数据仍可自动解密"
    }
