"""
存储服务单元测试
"""
import pytest
import os
import tempfile
import asyncio
from datetime import datetime
from pathlib import Path

from app.services.storage import (
    LocalStorage, FileInfo, StorageBackend
)


class TestFileInfo:
    """文件信息类测试"""

    def test_file_info_creation(self):
        """测试创建文件信息"""
        info = FileInfo(
            path="/test/file.txt",
            size=1024,
            created_at=datetime.now(),
            content_type="text/plain",
            metadata={"key": "value"}
        )
        
        assert info.path == "/test/file.txt"
        assert info.size == 1024
        assert info.content_type == "text/plain"
        assert info.metadata["key"] == "value"

    def test_file_info_defaults(self):
        """测试文件信息默认值"""
        info = FileInfo(
            path="/test/file.txt",
            size=100,
            created_at=datetime.now()
        )
        
        assert info.content_type == "text/plain"
        assert info.metadata is None


class TestLocalStorage:
    """本地存储测试"""

    @pytest.fixture
    def temp_storage(self):
        """创建临时存储目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield LocalStorage(tmpdir)

    @pytest.mark.asyncio
    async def test_save_file(self, temp_storage):
        """测试保存文件"""
        result = await temp_storage.save(
            path="test/file.txt",
            content="Hello World",
            metadata={"author": "test"}
        )
        
        assert result is True
        
        # 验证文件存在
        full_path = temp_storage._get_full_path("test/file.txt")
        assert full_path.exists()
        assert full_path.read_text() == "Hello World"

    @pytest.mark.asyncio
    async def test_read_file(self, temp_storage):
        """测试读取文件"""
        # 先保存文件
        await temp_storage.save("read/test.txt", "File content")
        
        # 读取文件
        content = await temp_storage.read("read/test.txt")
        
        assert content == "File content"

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, temp_storage):
        """测试读取不存在的文件"""
        content = await temp_storage.read("nonexistent.txt")
        
        assert content is None

    @pytest.mark.asyncio
    async def test_exists(self, temp_storage):
        """测试文件存在检查"""
        await temp_storage.save("exists.txt", "content")
        
        assert await temp_storage.exists("exists.txt") is True
        assert await temp_storage.exists("not_exists.txt") is False

    @pytest.mark.asyncio
    async def test_delete_file(self, temp_storage):
        """测试删除文件"""
        await temp_storage.save("delete/me.txt", "content")
        
        result = await temp_storage.delete("delete/me.txt")
        
        assert result is True
        assert await temp_storage.exists("delete/me.txt") is False

    @pytest.mark.asyncio
    async def test_get_info(self, temp_storage):
        """测试获取文件信息"""
        await temp_storage.save("info/test.txt", "Hello World")
        
        info = await temp_storage.get_info("info/test.txt")
        
        assert info is not None
        assert info.path == "info/test.txt"
        assert info.size == 11  # "Hello World" 的长度

    @pytest.mark.asyncio
    async def test_get_info_nonexistent(self, temp_storage):
        """测试获取不存在文件的信息"""
        info = await temp_storage.get_info("nonexistent.txt")
        
        assert info is None

    @pytest.mark.asyncio
    async def test_list_files(self, temp_storage):
        """测试列出文件"""
        await temp_storage.save("dir/file1.txt", "content1")
        await temp_storage.save("dir/file2.txt", "content2")
        
        files = await temp_storage.list_files("dir")
        
        assert len(files) >= 2

    @pytest.mark.asyncio
    async def test_get_signed_url_returns_none(self, temp_storage):
        """测试本地存储返回 None 签名 URL"""
        await temp_storage.save("signed.txt", "content")
        
        url = await temp_storage.get_signed_url("signed.txt")
        
        # 本地存储不支持签名URL，返回 None
        assert url is None

    def test_ensure_base_path(self, temp_storage):
        """测试确保基础目录存在"""
        assert temp_storage.base_path.exists()

    def test_get_full_path(self, temp_storage):
        """测试获取完整路径"""
        full_path = temp_storage._get_full_path("subdir/file.txt")
        
        assert str(full_path).endswith("subdir/file.txt")


class TestStorageBackendAbstract:
    """存储后端抽象类测试"""

    def test_storage_backend_is_abstract(self):
        """测试存储后端是抽象类"""
        with pytest.raises(TypeError):
            StorageBackend()  # 不能实例化抽象类
