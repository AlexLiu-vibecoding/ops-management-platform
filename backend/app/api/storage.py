"""
存储配置管理 API
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps import get_current_user
from app.models import User
from app.config.storage import get_storage_settings, StorageConfig
from app.services.storage import storage_manager

router = APIRouter(prefix="/storage", tags=["存储管理"])


class StorageConfigResponse(BaseModel):
    """存储配置响应"""
    storage_type: str
    retention_days: int
    size_threshold: int
    local_path: str = None
    s3_bucket: str = None
    oss_bucket: str = None


class StorageTestRequest(BaseModel):
    """存储测试请求"""
    storage_type: str


class StorageTestResponse(BaseModel):
    """存储测试响应"""
    success: bool
    message: str


@router.get("/config", response_model=StorageConfigResponse)
async def get_storage_config(
    current_user: User = Depends(get_current_user)
):
    """
    获取存储配置
    
    只有管理员可以查看完整配置
    """
    settings = get_storage_settings()
    
    return StorageConfigResponse(
        storage_type=settings.TYPE,
        retention_days=settings.FILE_RETENTION_DAYS,
        size_threshold=settings.FILE_SIZE_THRESHOLD,
        local_path=settings.LOCAL_PATH if settings.TYPE == "local" else None,
        s3_bucket=settings.S3_BUCKET if settings.TYPE == "s3" else None,
        oss_bucket=settings.OSS_BUCKET if settings.TYPE == "oss" else None
    )


@router.post("/test", response_model=StorageTestResponse)
async def test_storage(
    request: StorageTestRequest,
    current_user: User = Depends(get_current_user)
):
    """
    测试存储连接
    
    验证存储配置是否正确
    """
    try:
        # 尝试写入和读取测试文件
        test_content = f"Storage test at {__import__('datetime').datetime.now().isoformat()}"
        test_path = "test/test_connection.txt"
        
        # 保存测试文件
        success = await storage_manager.backend.save(test_path, test_content, {"test": True})
        
        if not success:
            return StorageTestResponse(
                success=False,
                message="写入测试文件失败"
            )
        
        # 读取测试文件
        content = await storage_manager.backend.read(test_path)
        
        if content != test_content:
            return StorageTestResponse(
                success=False,
                message="读取内容与写入内容不匹配"
            )
        
        # 删除测试文件
        await storage_manager.backend.delete(test_path)
        
        return StorageTestResponse(
            success=True,
            message=f"{request.storage_type.upper()} 存储连接测试成功"
        )
        
    except Exception as e:
        return StorageTestResponse(
            success=False,
            message=f"测试失败: {str(e)}"
        )


@router.get("/stats")
async def get_storage_stats(
    current_user: User = Depends(get_current_user)
):
    """
    获取存储统计信息
    
    返回文件数量、总大小等信息
    """
    try:
        files = await storage_manager.backend.list_files("approvals/")
        
        total_files = len(files)
        sql_files = [f for f in files if f.endswith('.sql') and not f.endswith('_rollback.sql')]
        rollback_files = [f for f in files if f.endswith('_rollback.sql')]
        
        return {
            "storage_type": storage_manager.settings.TYPE,
            "total_files": total_files,
            "sql_files": len(sql_files),
            "rollback_files": len(rollback_files),
            "retention_days": storage_manager.settings.FILE_RETENTION_DAYS
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")
