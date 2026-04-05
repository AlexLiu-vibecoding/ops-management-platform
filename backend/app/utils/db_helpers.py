"""
数据库连接辅助工具

提供统一的数据库连接和测试功能，消除重复代码：
- MySQL 连接测试
- PostgreSQL 连接测试
- 数据库连接创建（带密码解密）
- 统一异常处理
"""
import logging
from typing import Optional, Tuple
import pymysql
import psycopg2

from app.models import RDBInstance
from app.utils.auth import decrypt_instance_password

logger = logging.getLogger(__name__)


class DatabaseConnectionTestError(Exception):
    """数据库连接测试异常"""
    pass


def test_mysql_connection(
    host: str,
    port: int,
    username: str,
    password: str,
    database: Optional[str] = None
) -> dict:
    """
    测试 MySQL 连接

    Args:
        host: 主机地址
        port: 端口
        username: 用户名
        password: 密码
        database: 数据库名（可选）

    Returns:
        Dict: {
            "success": bool,
            "message": str,
            "version": str | None
        }
    """
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database,
            connect_timeout=5
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
        conn.close()
        return {
            "success": True,
            "message": "连接成功",
            "version": version
        }
    except Exception as e:
        logger.warning(f"MySQL 连接测试失败: {host}:{port}, 错误: {e}")
        return {
            "success": False,
            "message": f"连接失败: {str(e)}",
            "version": None
        }


def test_postgresql_connection(
    host: str,
    port: int,
    username: str,
    password: str,
    database: str = "postgres"
) -> dict:
    """
    测试 PostgreSQL 连接

    Args:
        host: 主机地址
        port: 端口
        username: 用户名
        password: 密码
        database: 数据库名

    Returns:
        Dict: {
            "success": bool,
            "message": str,
            "version": str | None
        }
    """
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database,
            connect_timeout=5
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
        conn.close()
        return {
            "success": True,
            "message": "连接成功",
            "version": version
        }
    except Exception as e:
        logger.warning(f"PostgreSQL 连接测试失败: {host}:{port}, 错误: {e}")
        return {
            "success": False,
            "message": f"连接失败: {str(e)}",
            "version": None
        }


def test_instance_connection(instance: RDBInstance, database: Optional[str] = None) -> dict:
    """
    测试数据库实例连接（自动解密密码）

    Args:
        instance: RDB 实例对象
        database: 数据库名（可选）

    Returns:
        Dict: 连接测试结果
    """
    try:
        # 获取解密后的密码
        password = decrypt_instance_password(instance.password_encrypted)

        # 根据实例类型调用对应的测试函数
        if instance.port == 5432 or ("pg" in instance.host.lower() or "postgres" in instance.host.lower()):
            return test_postgresql_connection(
                host=instance.host,
                port=instance.port,
                username=instance.username,
                password=password,
                database=database or "postgres"
            )
        else:
            return test_mysql_connection(
                host=instance.host,
                port=instance.port,
                username=instance.username,
                password=password,
                database=database
            )
    except Exception as e:
        logger.error(f"实例连接测试失败: {instance.name}, 错误: {e}")
        return {
            "success": False,
            "message": f"密码解密失败: {str(e)}",
            "version": None
        }


def create_mysql_connection(
    host: str,
    port: int,
    username: str,
    password: str,
    database: Optional[str] = None,
    charset: str = 'utf8mb4',
    connect_timeout: int = 10
) -> pymysql.connections.Connection:
    """
    创建 MySQL 连接

    Args:
        host: 主机地址
        port: 端口
        username: 用户名
        password: 密码
        database: 数据库名（可选）
        charset: 字符集
        connect_timeout: 连接超时（秒）

    Returns:
        MySQL 连接对象

    Raises:
        DatabaseConnectionTestError: 连接失败时
    """
    try:
        return pymysql.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database,
            charset=charset,
            connect_timeout=connect_timeout
        )
    except Exception as e:
        logger.error(f"MySQL 连接创建失败: {host}:{port}, 错误: {e}")
        raise DatabaseConnectionTestError(f"MySQL 连接失败: {str(e)}") from e


def create_postgresql_connection(
    host: str,
    port: int,
    username: str,
    password: str,
    database: str = "postgres",
    connect_timeout: int = 10
) -> psycopg2.extensions.connection:
    """
    创建 PostgreSQL 连接

    Args:
        host: 主机地址
        port: 端口
        username: 用户名
        password: 密码
        database: 数据库名
        connect_timeout: 连接超时（秒）

    Returns:
        PostgreSQL 连接对象

    Raises:
        DatabaseConnectionTestError: 连接失败时
    """
    try:
        return psycopg2.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database,
            connect_timeout=connect_timeout
        )
    except Exception as e:
        logger.error(f"PostgreSQL 连接创建失败: {host}:{port}, 错误: {e}")
        raise DatabaseConnectionTestError(f"PostgreSQL 连接失败: {str(e)}") from e


def create_instance_connection(
    instance: RDBInstance,
    database: Optional[str] = None,
    connect_timeout: int = 10
) -> Tuple:
    """
    创建数据库实例连接（自动解密密码）

    Args:
        instance: RDB 实例对象
        database: 数据库名（可选）
        connect_timeout: 连接超时（秒）

    Returns:
        Tuple: (connection, db_type)

    Raises:
        DatabaseConnectionTestError: 连接失败时
    """
    try:
        # 获取解密后的密码
        password = decrypt_instance_password(instance.password_encrypted)

        # 判断数据库类型
        if instance.port == 5432 or ("pg" in instance.host.lower() or "postgres" in instance.host.lower()):
            conn = create_postgresql_connection(
                host=instance.host,
                port=instance.port,
                username=instance.username,
                password=password,
                database=database or "postgres",
                connect_timeout=connect_timeout
            )
            return conn, "postgresql"
        else:
            conn = create_mysql_connection(
                host=instance.host,
                port=instance.port,
                username=instance.username,
                password=password,
                database=database,
                connect_timeout=connect_timeout
            )
            return conn, "mysql"
    except Exception as e:
        logger.error(f"实例连接创建失败: {instance.name}, 错误: {e}")
        raise DatabaseConnectionTestError(f"实例连接创建失败: {str(e)}") from e


__all__ = [
    'test_mysql_connection',
    'test_postgresql_connection',
    'test_instance_connection',
    'create_mysql_connection',
    'create_postgresql_connection',
    'create_instance_connection',
    'DatabaseConnectionTestError',
]
