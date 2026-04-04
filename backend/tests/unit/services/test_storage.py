"""
存储服务测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from datetime import datetime

from app.services.storage import (
    FileInfo, LocalStorage, StorageManager
)


class TestFileInfo:
    """文件信息测试类"""

    def test_file_info_creation(self):
        """测试文件信息创建"""
        info = FileInfo(
            path="/tmp/test.txt",
            size=1024,
            created_at=datetime.now(),
            content_type="text/plain",
            metadata={"key": "value"}
        )

        assert info.path == "/tmp/test.txt"
        assert info.size == 1024
        assert info.content_type == "text/plain"

    def test_file_info_default_values(self):
        """测试文件信息默认值"""
        info = FileInfo(
            path="/tmp/test.txt",
            size=100,
            created_at=datetime.now()
        )

        assert info.content_type == "text/plain"
        assert info.metadata is None


class TestLocalStorage:
    """本地存储测试类"""

    @pytest.fixture
    def storage(self, tmp_path):
        """创建本地存储实例"""
        return LocalStorage(str(tmp_path))

    def test_ensure_base_path(self, storage, tmp_path):
        """测试确保基础路径存在"""
        # 基础路径已在初始化时创建
        assert Path(tmp_path).exists()

    def test_get_full_path(self, storage, tmp_path):
        """测试获取完整路径"""
        full_path = storage._get_full_path("test/file.txt")

        assert str(tmp_path) in str(full_path)
        assert "test/file.txt" in str(full_path)

    @pytest.mark.asyncio
    async def test_save_and_read_text(self, storage):
        """测试保存和读取文本"""
        content = "Hello, World!"
        path = "test/hello.txt"

        # 保存
        result = await storage.save(path, content)
        assert result is True

        # 读取
        read_content = await storage.read(path)
        assert read_content == content

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, storage):
        """测试读取不存在的文件"""
        result = await storage.read("nonexistent.txt")
        assert result is None

    @pytest.mark.asyncio
    async def test_exists(self, storage):
        """测试文件存在检查"""
        path = "test/exists.txt"
        await storage.save(path, "content")

        assert await storage.exists(path) is True
        assert await storage.exists("nonexistent.txt") is False

    @pytest.mark.asyncio
    async def test_delete(self, storage):
        """测试删除文件"""
        path = "test/delete.txt"
        await storage.save(path, "content")

        assert await storage.exists(path) is True

        result = await storage.delete(path)
        assert result is True
        assert await storage.exists(path) is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, storage):
        """测试删除不存在的文件"""
        result = await storage.delete("nonexistent.txt")
        assert result is True  # 删除不存在的文件也返回True

    @pytest.mark.asyncio
    async def test_get_info(self, storage):
        """测试获取文件信息"""
        path = "test/info.txt"
        content = "Hello, World!"
        await storage.save(path, content)

        info = await storage.get_info(path)

        assert info is not None
        assert info.size == len(content)

    @pytest.mark.asyncio
    async def test_list_files(self, storage):
        """测试列出文件"""
        await storage.save("dir/file1.txt", "content1")
        await storage.save("dir/file2.txt", "content2")

        files = await storage.list_files("dir")

        assert len(files) >= 2


class TestStorageManager:
    """存储管理器测试类"""

    def test_should_store_as_file_small_content(self):
        """测试小内容不存为文件"""
        manager = StorageManager()

        # 小内容（少于1000字符）不应该存为文件
        small_content = "x" * 100
        result = manager.should_store_as_file(small_content)

        assert result is False

    def test_should_store_as_file_large_content(self):
        """测试大内容存为文件"""
        manager = StorageManager()

        # 大内容应该存为文件，阈值默认为10MB
        # 使用一个足够大的内容（15MB）确保超过阈值
        large_content = "x" * 15000000
        result = manager.should_store_as_file(large_content)

        assert result is True

    def test_should_store_as_file_empty_content(self):
        """测试空内容"""
        manager = StorageManager()

        result = manager.should_store_as_file("")

        assert result is False

