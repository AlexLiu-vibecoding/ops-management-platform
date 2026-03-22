"""
存储后端抽象层
支持本地存储、AWS S3、阿里云 OSS
"""
import os
import json
import logging
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass

from app.config.storage import get_storage_settings

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """文件信息"""
    path: str
    size: int
    created_at: datetime
    content_type: str = "text/plain"
    metadata: Dict[str, Any] = None


class StorageBackend(ABC):
    """存储后端抽象基类"""
    
    @abstractmethod
    async def save(self, path: str, content: str, metadata: Dict = None) -> bool:
        """保存文件"""
        pass
    
    @abstractmethod
    async def read(self, path: str) -> Optional[str]:
        """读取文件内容"""
        pass
    
    @abstractmethod
    async def delete(self, path: str) -> bool:
        """删除文件"""
        pass
    
    @abstractmethod
    async def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        pass
    
    @abstractmethod
    async def get_info(self, path: str) -> Optional[FileInfo]:
        """获取文件信息"""
        pass
    
    @abstractmethod
    async def list_files(self, prefix: str = "") -> List[str]:
        """列出文件"""
        pass
    
    @abstractmethod
    async def get_signed_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """获取临时访问URL（用于下载）"""
        pass


class LocalStorage(StorageBackend):
    """本地文件存储"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self._ensure_base_path()
    
    def _ensure_base_path(self):
        """确保基础目录存在"""
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_full_path(self, path: str) -> Path:
        """获取完整路径"""
        return self.base_path / path
    
    async def save(self, path: str, content: str, metadata: Dict = None) -> bool:
        """保存文件到本地"""
        try:
            full_path = self._get_full_path(path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 写入内容
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 如果有元数据，保存到同名的 .meta 文件
            if metadata:
                meta_path = full_path.with_suffix(full_path.suffix + '.meta')
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        **metadata,
                        'created_at': datetime.now().isoformat()
                    }, f)
            
            logger.info(f"文件已保存到本地: {path}")
            return True
        except Exception as e:
            logger.error(f"保存文件失败: {path}, 错误: {e}")
            return False
    
    async def read(self, path: str) -> Optional[str]:
        """读取本地文件"""
        try:
            full_path = self._get_full_path(path)
            if not full_path.exists():
                return None
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取文件失败: {path}, 错误: {e}")
            return None
    
    async def delete(self, path: str) -> bool:
        """删除本地文件"""
        try:
            full_path = self._get_full_path(path)
            if full_path.exists():
                full_path.unlink()
            
            # 同时删除元数据文件
            meta_path = full_path.with_suffix(full_path.suffix + '.meta')
            if meta_path.exists():
                meta_path.unlink()
            
            logger.info(f"文件已删除: {path}")
            return True
        except Exception as e:
            logger.error(f"删除文件失败: {path}, 错误: {e}")
            return False
    
    async def exists(self, path: str) -> bool:
        """检查文件是否存在"""
        return self._get_full_path(path).exists()
    
    async def get_info(self, path: str) -> Optional[FileInfo]:
        """获取文件信息"""
        try:
            full_path = self._get_full_path(path)
            if not full_path.exists():
                return None
            
            stat = full_path.stat()
            created_at = datetime.fromtimestamp(stat.st_ctime)
            
            # 读取元数据
            metadata = None
            meta_path = full_path.with_suffix(full_path.suffix + '.meta')
            if meta_path.exists():
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            return FileInfo(
                path=path,
                size=stat.st_size,
                created_at=created_at,
                metadata=metadata
            )
        except Exception as e:
            logger.error(f"获取文件信息失败: {path}, 错误: {e}")
            return None
    
    async def list_files(self, prefix: str = "") -> List[str]:
        """列出文件"""
        try:
            full_prefix = self._get_full_path(prefix)
            if not full_prefix.exists():
                return []
            
            files = []
            for f in full_prefix.rglob("*"):
                if f.is_file() and not f.suffix.endswith('.meta'):
                    rel_path = f.relative_to(self.base_path)
                    files.append(str(rel_path))
            return files
        except Exception as e:
            logger.error(f"列出文件失败: {prefix}, 错误: {e}")
            return []
    
    async def get_signed_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """本地存储不支持签名URL，返回 None"""
        return None
    
    async def cleanup_old_files(self, days: int) -> int:
        """清理过期文件"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            for f in self.base_path.rglob("*"):
                if f.is_file() and not f.suffix.endswith('.meta'):
                    stat = f.stat()
                    created_at = datetime.fromtimestamp(stat.st_ctime)
                    
                    if created_at < cutoff_date:
                        # 删除文件
                        f.unlink()
                        # 删除元数据文件
                        meta_path = f.with_suffix(f.suffix + '.meta')
                        if meta_path.exists():
                            meta_path.unlink()
                        deleted_count += 1
                        logger.info(f"已清理过期文件: {f.relative_to(self.base_path)}")
            
            return deleted_count
        except Exception as e:
            logger.error(f"清理过期文件失败: {e}")
            return 0


class S3Storage(StorageBackend):
    """AWS S3 存储"""
    
    def __init__(
        self,
        bucket_name: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None
    ):
        self.bucket_name = bucket_name
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.endpoint_url = endpoint_url
        self._client = None
    
    def _get_client(self):
        """获取 S3 客户端（延迟加载）"""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    's3',
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region,
                    endpoint_url=self.endpoint_url
                )
            except ImportError:
                raise ImportError("请安装 boto3: pip install boto3")
        return self._client
    
    async def save(self, path: str, content: str, metadata: Dict = None) -> bool:
        """保存到 S3"""
        try:
            client = self._get_client()
            extra_args = {
                'ContentType': 'text/plain',
                'Metadata': metadata or {}
            }
            client.put_object(
                Bucket=self.bucket_name,
                Key=path,
                Body=content.encode('utf-8'),
                **extra_args
            )
            logger.info(f"文件已保存到S3: {path}")
            return True
        except Exception as e:
            logger.error(f"S3保存失败: {path}, 错误: {e}")
            return False
    
    async def read(self, path: str) -> Optional[str]:
        """从 S3 读取"""
        try:
            client = self._get_client()
            response = client.get_object(
                Bucket=self.bucket_name,
                Key=path
            )
            return response['Body'].read().decode('utf-8')
        except client.exceptions.NoSuchKey:
            return None
        except Exception as e:
            logger.error(f"S3读取失败: {path}, 错误: {e}")
            return None
    
    async def delete(self, path: str) -> bool:
        """从 S3 删除"""
        try:
            client = self._get_client()
            client.delete_object(
                Bucket=self.bucket_name,
                Key=path
            )
            logger.info(f"文件已从S3删除: {path}")
            return True
        except Exception as e:
            logger.error(f"S3删除失败: {path}, 错误: {e}")
            return False
    
    async def exists(self, path: str) -> bool:
        """检查 S3 文件是否存在"""
        try:
            client = self._get_client()
            client.head_object(Bucket=self.bucket_name, Key=path)
            return True
        except client.exceptions.NoSuchKey:
            return False
        except Exception:
            return False
    
    async def get_info(self, path: str) -> Optional[FileInfo]:
        """获取 S3 文件信息"""
        try:
            client = self._get_client()
            response = client.head_object(
                Bucket=self.bucket_name,
                Key=path
            )
            return FileInfo(
                path=path,
                size=response['ContentLength'],
                created_at=response['LastModified'],
                content_type=response.get('ContentType', 'text/plain'),
                metadata=response.get('Metadata', {})
            )
        except Exception as e:
            logger.error(f"获取S3文件信息失败: {path}, 错误: {e}")
            return None
    
    async def list_files(self, prefix: str = "") -> List[str]:
        """列出 S3 文件"""
        try:
            client = self._get_client()
            files = []
            paginator = client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                for obj in page.get('Contents', []):
                    files.append(obj['Key'])
            
            return files
        except Exception as e:
            logger.error(f"列出S3文件失败: {prefix}, 错误: {e}")
            return []
    
    async def get_signed_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """生成 S3 签名URL"""
        try:
            client = self._get_client()
            url = client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': path},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"生成签名URL失败: {path}, 错误: {e}")
            return None


class OSSStorage(StorageBackend):
    """阿里云 OSS 存储"""
    
    def __init__(
        self,
        bucket_name: str,
        access_key: str,
        secret_key: str,
        endpoint: str
    ):
        self.bucket_name = bucket_name
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint = endpoint
        self._bucket = None
    
    def _get_bucket(self):
        """获取 OSS Bucket（延迟加载）"""
        if self._bucket is None:
            try:
                import oss2
                auth = oss2.Auth(self.access_key, self.secret_key)
                self._bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            except ImportError:
                raise ImportError("请安装 oss2: pip install oss2")
        return self._bucket
    
    async def save(self, path: str, content: str, metadata: Dict = None) -> bool:
        """保存到 OSS"""
        try:
            bucket = self._get_bucket()
            headers = {}
            if metadata:
                for k, v in metadata.items():
                    headers[f'x-oss-meta-{k}'] = str(v)
            bucket.put_object(path, content.encode('utf-8'), headers=headers)
            logger.info(f"文件已保存到OSS: {path}")
            return True
        except Exception as e:
            logger.error(f"OSS保存失败: {path}, 错误: {e}")
            return False
    
    async def read(self, path: str) -> Optional[str]:
        """从 OSS 读取"""
        try:
            bucket = self._get_bucket()
            result = bucket.get_object(path)
            return result.read().decode('utf-8')
        except oss2.exceptions.NoSuchKey:
            return None
        except Exception as e:
            logger.error(f"OSS读取失败: {path}, 错误: {e}")
            return None
    
    async def delete(self, path: str) -> bool:
        """从 OSS 删除"""
        try:
            bucket = self._get_bucket()
            bucket.delete_object(path)
            logger.info(f"文件已从OSS删除: {path}")
            return True
        except Exception as e:
            logger.error(f"OSS删除失败: {path}, 错误: {e}")
            return False
    
    async def exists(self, path: str) -> bool:
        """检查 OSS 文件是否存在"""
        try:
            bucket = self._get_bucket()
            return bucket.object_exists(path)
        except Exception:
            return False
    
    async def get_info(self, path: str) -> Optional[FileInfo]:
        """获取 OSS 文件信息"""
        try:
            bucket = self._get_bucket()
            meta = bucket.head_object(path)
            return FileInfo(
                path=path,
                size=meta.content_length,
                created_at=meta.last_modified,
                content_type=meta.content_type or 'text/plain',
                metadata=meta.headers.get('x-oss-meta-', {})
            )
        except Exception as e:
            logger.error(f"获取OSS文件信息失败: {path}, 错误: {e}")
            return None
    
    async def list_files(self, prefix: str = "") -> List[str]:
        """列出 OSS 文件"""
        try:
            bucket = self._get_bucket()
            files = []
            for obj in oss2.ObjectIterator(bucket, prefix=prefix):
                files.append(obj.key)
            return files
        except Exception as e:
            logger.error(f"列出OSS文件失败: {prefix}, 错误: {e}")
            return []
    
    async def get_signed_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """生成 OSS 签名URL"""
        try:
            bucket = self._get_bucket()
            url = bucket.sign_url('GET', path, expires_in)
            return url
        except Exception as e:
            logger.error(f"生成签名URL失败: {path}, 错误: {e}")
            return None


# ==================== 存储管理器 ====================

class StorageManager:
    """存储管理器 - 统一管理存储后端"""
    
    def __init__(self):
        self._backend: Optional[StorageBackend] = None
        self._settings = get_storage_settings()
    
    @property
    def backend(self) -> StorageBackend:
        """获取存储后端（延迟初始化）"""
        if self._backend is None:
            self._backend = self._create_backend()
        return self._backend
    
    def _create_backend(self) -> StorageBackend:
        """创建存储后端"""
        storage_type = self._settings.STORAGE_TYPE
        
        if storage_type == "local":
            logger.info(f"使用本地存储: {self._settings.LOCAL_STORAGE_PATH}")
            return LocalStorage(self._settings.LOCAL_STORAGE_PATH)
        
        elif storage_type == "s3":
            if not all([self._settings.S3_BUCKET_NAME, self._settings.AWS_ACCESS_KEY_ID]):
                raise ValueError("S3存储需要配置 S3_BUCKET_NAME 和 AWS_ACCESS_KEY_ID")
            logger.info(f"使用AWS S3存储: {self._settings.S3_BUCKET_NAME}")
            return S3Storage(
                bucket_name=self._settings.S3_BUCKET_NAME,
                access_key=self._settings.AWS_ACCESS_KEY_ID,
                secret_key=self._settings.AWS_SECRET_ACCESS_KEY,
                region=self._settings.AWS_REGION or "us-east-1",
                endpoint_url=self._settings.S3_ENDPOINT_URL
            )
        
        elif storage_type == "oss":
            if not all([self._settings.OSS_BUCKET_NAME, self._settings.OSS_ACCESS_KEY_ID]):
                raise ValueError("OSS存储需要配置 OSS_BUCKET_NAME 和 OSS_ACCESS_KEY_ID")
            logger.info(f"使用阿里云OSS存储: {self._settings.OSS_BUCKET_NAME}")
            return OSSStorage(
                bucket_name=self._settings.OSS_BUCKET_NAME,
                access_key=self._settings.OSS_ACCESS_KEY_ID,
                secret_key=self._settings.OSS_ACCESS_KEY_SECRET,
                endpoint=self._settings.OSS_ENDPOINT
            )
        
        else:
            raise ValueError(f"不支持的存储类型: {storage_type}")
    
    async def save_sql_file(
        self,
        approval_id: int,
        sql_type: str,  # 'sql' or 'rollback'
        content: str,
        metadata: Dict = None
    ) -> str:
        """
        保存SQL文件
        
        Returns:
            文件路径
        """
        # 生成文件路径: approvals/2024/01/123_sql.sql
        now = datetime.now()
        date_path = now.strftime("%Y/%m")
        filename = f"{approval_id}_{sql_type}.sql"
        path = f"approvals/{date_path}/{filename}"
        
        # 默认元数据
        default_metadata = {
            'approval_id': approval_id,
            'sql_type': sql_type,
            'content_hash': hashlib.md5(content.encode()).hexdigest()[:16],
            'line_count': content.count('\n') + 1,
            'size': len(content)
        }
        
        if metadata:
            default_metadata.update(metadata)
        
        await self.backend.save(path, content, default_metadata)
        return path
    
    async def read_sql_file(self, path: str) -> Optional[str]:
        """读取SQL文件"""
        return await self.backend.read(path)
    
    async def delete_sql_file(self, path: str) -> bool:
        """删除SQL文件"""
        return await self.backend.delete(path)
    
    async def get_download_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """获取下载URL"""
        return await self.backend.get_signed_url(path, expires_in)
    
    async def cleanup_expired_files(self) -> int:
        """清理过期文件"""
        retention_days = self._settings.SQL_FILE_RETENTION_DAYS
        
        if isinstance(self.backend, LocalStorage):
            return await self.backend.cleanup_old_files(retention_days)
        else:
            # S3/OSS 通过生命周期规则管理，这里只记录日志
            logger.info(f"云存储通过生命周期规则管理过期文件，保留天数: {retention_days}")
            return 0
    
    def should_store_as_file(self, content: str) -> bool:
        """判断是否应该存储为文件"""
        return len(content) > self._settings.SQL_FILE_SIZE_THRESHOLD


# 全局存储管理器实例
storage_manager = StorageManager()
