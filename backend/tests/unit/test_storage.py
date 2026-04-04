"""
测试存储服务 - Storage Service Tests
"""

import pytest
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from pydantic import BaseModel


class MockSettings(BaseModel):
    """Mock settings for testing"""
    TYPE: str = "local"
    LOCAL_PATH: str = "/tmp/test_storage"
    FILE_SIZE_THRESHOLD: int = 1000
    FILE_RETENTION_DAYS: int = 30
    S3_BUCKET: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_REGION: str = "us-east-1"
    S3_ENDPOINT: str = ""
    OSS_BUCKET: str = ""
    OSS_ACCESS_KEY: str = ""
    OSS_SECRET_KEY: str = ""
    OSS_ENDPOINT: str = ""


@pytest.fixture(autouse=True)
def mock_settings_module():
    """Mock 存储设置模块"""
    with patch('app.services.storage.get_effective_storage_settings') as mock:
        mock.return_value = MockSettings()
        yield mock


class TestFileInfo:
    """测试 FileInfo 数据类"""
    
    def test_file_info_creation(self):
        """测试 FileInfo 创建"""
        from app.services.storage import FileInfo
        
        now = datetime.now()
        info = FileInfo(
            path="test/path/file.txt",
            size=1024,
            created_at=now,
            content_type="text/plain",
            metadata={"key": "value"}
        )
        
        assert info.path == "test/path/file.txt"
        assert info.size == 1024
        assert info.created_at == now
        assert info.content_type == "text/plain"
        assert info.metadata == {"key": "value"}


class TestLocalStorage:
    """测试本地存储后端"""
    
    @pytest.fixture
    def local_storage(self, tmp_path):
        from app.services.storage import LocalStorage
        return LocalStorage(str(tmp_path))
    
    @pytest.mark.asyncio
    async def test_save_file(self, local_storage, tmp_path):
        """测试保存文件"""
        path = "test/query.sql"
        content = "SELECT * FROM users;"
        metadata = {"author": "test"}
        
        result = await local_storage.save(path, content, metadata)
        
        assert result is True
        file_path = tmp_path / path
        assert file_path.exists()
        assert file_path.read_text() == content
    
    @pytest.mark.asyncio
    async def test_read_existing_file(self, local_storage, tmp_path):
        """测试读取存在的文件"""
        path = "test/read.sql"
        content = "SELECT 1;"
        
        file_path = tmp_path / path
        file_path.parent.mkdir(parents=True)
        file_path.write_text(content)
        
        result = await local_storage.read(path)
        assert result == content
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, local_storage):
        """测试读取不存在的文件"""
        result = await local_storage.read("nonexistent.sql")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_delete_file(self, local_storage, tmp_path):
        """测试删除文件"""
        path = "test/delete.sql"
        file_path = tmp_path / path
        file_path.parent.mkdir(parents=True)
        file_path.write_text("content")
        
        result = await local_storage.delete(path)
        assert result is True
        assert not file_path.exists()
    
    @pytest.mark.asyncio
    async def test_exists_true(self, local_storage, tmp_path):
        """测试文件存在"""
        path = "test/exists.sql"
        file_path = tmp_path / path
        file_path.parent.mkdir(parents=True)
        file_path.write_text("content")
        
        result = await local_storage.exists(path)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_exists_false(self, local_storage):
        """测试文件不存在"""
        result = await local_storage.exists("not_exists.sql")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_info(self, local_storage, tmp_path):
        """测试获取文件信息"""
        path = "test/info.sql"
        content = "SELECT 1;"
        
        file_path = tmp_path / path
        file_path.parent.mkdir(parents=True)
        file_path.write_text(content)
        
        result = await local_storage.get_info(path)
        
        assert result is not None
        assert result.path == path
        assert result.size == len(content)


class TestStorageManager:
    """测试存储管理器"""
    
    @pytest.fixture
    def storage_manager(self):
        from app.services.storage import StorageManager
        return StorageManager()
    
    def test_settings_property(self, storage_manager):
        """测试 settings 属性"""
        settings = storage_manager.settings
        assert settings.TYPE == "local"
    
    def test_backend_property(self, storage_manager):
        """测试 backend 属性"""
        backend = storage_manager.backend
        assert backend is not None
    
    def test_reload_backend(self, storage_manager):
        """测试重新加载后端"""
        backend = storage_manager.backend
        storage_manager.reload_backend()
        assert storage_manager._backend is None
    
    @pytest.mark.asyncio
    async def test_save_sql_file(self, storage_manager, tmp_path, mock_settings_module):
        """测试保存SQL文件"""
        mock_settings_module.return_value = MockSettings(LOCAL_PATH=str(tmp_path))
        storage_manager.reload_backend()
        
        content = "SELECT * FROM users;"
        path = await storage_manager.save_sql_file(approval_id=123, sql_type="sql", content=content)
        
        assert path.startswith("approvals/")
        assert "123_sql.sql" in path
    
    def test_should_store_as_file(self, storage_manager):
        """测试判断是否应该存储为文件"""
        small = "SELECT 1;"
        large = "SELECT 1;" * 200
        
        assert storage_manager.should_store_as_file(small) is False
        assert storage_manager.should_store_as_file(large) is True


class TestStorageEdgeCases:
    """测试边界情况"""
    
    @pytest.mark.asyncio
    async def test_save_empty_content(self, tmp_path):
        """测试保存空内容"""
        from app.services.storage import LocalStorage
        storage = LocalStorage(str(tmp_path))
        
        result = await storage.save("empty.sql", "", None)
        assert result is True
        
        content = await storage.read("empty.sql")
        assert content == ""
    
    @pytest.mark.asyncio
    async def test_save_unicode(self, tmp_path):
        """测试保存 Unicode 内容"""
        from app.services.storage import LocalStorage
        storage = LocalStorage(str(tmp_path))
        
        content = "SELECT '中文测试' FROM users;"
        result = await storage.save("unicode.sql", content, None)
        assert result is True
        
        read = await storage.read("unicode.sql")
        assert read == content


class TestGlobalStorage:
    """测试全局实例"""
    
    def test_global_instance(self):
        """测试全局实例存在"""
        from app.services.storage import storage_manager, StorageManager
        assert isinstance(storage_manager, StorageManager)
