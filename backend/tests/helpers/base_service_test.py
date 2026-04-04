"""
服务测试基类

提供通用的服务层测试基类，减少重复代码
"""
import pytest
from typing import Optional, Any, Dict, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session


class BaseServiceTest:
    """服务测试基类 - 提供通用的测试方法和 Mock 工具"""

    @pytest.fixture
    def db_session(self):
        """Mock 数据库会话"""
        session = Mock(spec=Session)
        session.query.return_value = session
        session.filter.return_value = session
        session.first.return_value = None
        session.all.return_value = []
        session.add.return_value = None
        session.commit.return_value = None
        session.rollback.return_value = None
        session.close.return_value = None
        return session

    @pytest.fixture
    def mock_instance(self):
        """Mock 数据库实例"""
        instance = Mock()
        instance.id = 1
        instance.name = "测试实例"
        instance.host = "localhost"
        instance.port = 3306
        instance.username = "test_user"
        instance.password_encrypted = "encrypted_password"
        instance.db_type = "mysql"
        return instance

    @pytest.fixture
    def mock_cursor(self):
        """Mock 数据库游标"""
        cursor = Mock()
        cursor.rowcount = 0
        cursor.description = None
        cursor.fetchall.return_value = []
        cursor.execute.return_value = None
        cursor.close.return_value = None
        return cursor

    @pytest.fixture
    def mock_connection(self, mock_cursor):
        """Mock 数据库连接"""
        connection = Mock()
        connection.cursor.return_value = mock_cursor
        connection.commit.return_value = None
        connection.rollback.return_value = None
        connection.__enter__ = Mock(return_value=connection)
        connection.__exit__ = Mock(return_value=None)
        return connection

    def assert_enum_value(self, enum_value: Any, expected: str):
        """断言枚举值"""
        assert enum_value.value == expected, f"Expected {expected}, got {enum_value.value}"

    def assert_risk_level(self, result: tuple, expected_level: str, expected_risks_count: int = 0):
        """断言风险等级"""
        risk_level, risks = result
        assert risk_level.value == expected_level, f"Expected risk level {expected_level}, got {risk_level.value}"
        assert len(risks) == expected_risks_count, f"Expected {expected_risks_count} risks, got {len(risks)}"

    def assert_validation_result(self, result: tuple, expected_valid: bool, expected_error: str = ""):
        """断言验证结果"""
        is_valid, error = result
        assert is_valid == expected_valid, f"Expected valid={expected_valid}, got {is_valid}"
        if expected_error:
            assert expected_error in error, f"Expected error '{expected_error}' in '{error}'"
        else:
            assert error == "", f"Expected no error, got '{error}'"

    def create_mock_query_result(self, columns: List[str], rows: List[List[Any]]) -> Dict[str, Any]:
        """创建 mock 查询结果"""
        return {
            'success': True,
            'columns': columns,
            'data': [dict(zip(columns, row, strict=False)) for row in rows],
            'affected_rows': len(rows)
        }


class AsyncServiceTest(BaseServiceTest):
    """异步服务测试基类"""

    @pytest.fixture
    def async_db_session(self):
        """Mock 异步数据库会话"""
        session = AsyncMock(spec=Session)
        session.execute.return_value = None
        session.commit.return_value = None
        session.rollback.return_value = None
        session.close.return_value = None
        return session

    @pytest.fixture
    def async_mock_cursor(self):
        """Mock 异步数据库游标"""
        cursor = AsyncMock()
        cursor.rowcount = 0
        cursor.description = None
        cursor.fetchall = AsyncMock(return_value=[])
        cursor.execute = AsyncMock(return_value=None)
        cursor.close = AsyncMock(return_value=None)
        return cursor

    @pytest.fixture
    def async_mock_connection(self, async_mock_cursor):
        """Mock 异步数据库连接"""
        connection = AsyncMock()
        connection.cursor = AsyncMock(return_value=async_mock_cursor)
        connection.commit = AsyncMock(return_value=None)
        connection.rollback = AsyncMock(return_value=None)
        connection.__aenter__ = AsyncMock(return_value=connection)
        connection.__aexit__ = AsyncMock(return_value=None)
        return connection
