"""
数据库连接管理服务

提供统一的数据库连接管理，支持：
- MySQL / PostgreSQL 连接
- Redis 连接
- 连接池管理
- 密码自动解密
- 连接测试
- 统一异常处理

使用示例:
    # 方式1：上下文管理器（推荐）
    with db_manager.connection(instance, 'mydb') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")

    # 方式2：Redis 连接
    with db_manager.redis_connection(redis_instance) as r:
        r.get('key')
"""
import logging
from typing import Optional, Dict, Any, Tuple, List
from contextlib import contextmanager
import pymysql
import psycopg2
from psycopg2 import pool as pg_pool
from dbutils.pooled_db import PooledDB

from app.models import RDBInstance
from app.utils.auth import decrypt_instance_password

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """数据库连接异常"""
    pass


class DatabaseExecutionError(Exception):
    """数据库执行异常"""
    pass


class DatabaseConnectionManager:
    """
    数据库连接管理器

    支持 MySQL 和 PostgreSQL 的连接池管理
    """

    # 连接池配置
    POOL_MIN_CACHED = 1      # 初始空闲连接数
    POOL_MAX_CACHED = 5      # 最大空闲连接数
    POOL_MAX_SHARED = 3      # 最大共享连接数
    POOL_MAX_CONNECTIONS = 10  # 最大连接数
    POOL_BLOCKING = True     # 连接池耗尽时阻塞

    # 连接超时配置
    CONNECT_TIMEOUT = 10

    # 实例连接池缓存
    _mysql_pools: dict[int, PooledDB] = {}
    _pg_pools: dict[int, pg_pool.ThreadedConnectionPool] = {}

    def __init__(self):
        self._instance_cache: dict[int, dict[str, Any]] = {}

    def _get_credentials(self, instance: RDBInstance) -> tuple[str, str, str, int]:
        """
        获取实例连接凭证

        Returns:
            Tuple[str, str, str, int]: (host, username, password, port)
        """
        try:
            password = decrypt_instance_password(instance.password_encrypted)
        except ValueError as e:
            raise DatabaseConnectionError(f"密码解密失败: {str(e)}") from None

        return instance.host, instance.username, password, instance.port

    def _get_pool_key(self, instance: RDBInstance, database: Optional[str] = None) -> tuple:
        """生成连接池键"""
        return (instance.id, database or 'default')

    # ==================== MySQL 连接管理 ====================

    def _create_mysql_pool(self, instance: RDBInstance, database: Optional[str] = None) -> PooledDB:
        """创建 MySQL 连接池"""
        host, username, password, port = self._get_credentials(instance)

        try:
            pool = PooledDB(
                creator=pymysql,
                mincached=self.POOL_MIN_CACHED,
                maxcached=self.POOL_MAX_CACHED,
                maxshared=self.POOL_MAX_SHARED,
                maxconnections=self.POOL_MAX_CONNECTIONS,
                blocking=self.POOL_BLOCKING,
                host=host,
                port=port,
                user=username,
                password=password,
                database=database,
                charset='utf8mb4',
                connect_timeout=self.CONNECT_TIMEOUT,
                autocommit=False
            )
            logger.info(f"创建MySQL连接池成功: 实例={instance.id}, 数据库={database}")
            return pool
        except Exception as e:
            logger.error(f"创建MySQL连接池失败: {str(e)}")
            raise DatabaseConnectionError(f"创建连接池失败: {str(e)}") from e

    def get_mysql_connection(
        self,
        instance: RDBInstance,
        database: Optional[str] = None,
        use_pool: bool = True
    ) -> pymysql.Connection:
        """
        获取 MySQL 连接

        Args:
            instance: 数据库实例
            database: 数据库名
            use_pool: 是否使用连接池

        Returns:
            pymysql.Connection
        """
        host, username, password, port = self._get_credentials(instance)

        if not use_pool:
            return pymysql.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database,
                charset='utf8mb4',
                connect_timeout=self.CONNECT_TIMEOUT
            )

        pool_key = self._get_pool_key(instance, database)

        if pool_key not in self._mysql_pools:
            self._mysql_pools[pool_key] = self._create_mysql_pool(instance, database)

        return self._mysql_pools[pool_key].connection()

    # ==================== PostgreSQL 连接管理 ====================

    def _create_pg_pool(self, instance: RDBInstance, database: Optional[str] = None) -> pg_pool.ThreadedConnectionPool:
        """创建 PostgreSQL 连接池"""
        host, username, password, port = self._get_credentials(instance)

        try:
            pool = pg_pool.ThreadedConnectionPool(
                minconn=self.POOL_MIN_CACHED,
                maxconn=self.POOL_MAX_CONNECTIONS,
                host=host,
                port=port,
                user=username,
                password=password,
                database=database or 'postgres',
                connect_timeout=self.CONNECT_TIMEOUT
            )
            logger.info(f"创建PostgreSQL连接池成功: 实例={instance.id}, 数据库={database}")
            return pool
        except Exception as e:
            logger.error(f"创建PostgreSQL连接池失败: {str(e)}")
            raise DatabaseConnectionError(f"创建连接池失败: {str(e)}") from e

    def get_postgresql_connection(
        self,
        instance: RDBInstance,
        database: Optional[str] = None,
        use_pool: bool = True
    ) -> psycopg2.extensions.connection:
        """
        获取 PostgreSQL 连接

        Args:
            instance: 数据库实例
            database: 数据库名
            use_pool: 是否使用连接池

        Returns:
            psycopg2 connection
        """
        host, username, password, port = self._get_credentials(instance)

        if not use_pool:
            return psycopg2.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                database=database or 'postgres',
                connect_timeout=self.CONNECT_TIMEOUT
            )

        pool_key = self._get_pool_key(instance, database)

        if pool_key not in self._pg_pools:
            self._pg_pools[pool_key] = self._create_pg_pool(instance, database)

        return self._pg_pools[pool_key].getconn()

    def release_postgresql_connection(
        self,
        instance: RDBInstance,
        conn: psycopg2.extensions.connection,
        database: Optional[str] = None
    ):
        """释放 PostgreSQL 连接回连接池"""
        pool_key = self._get_pool_key(instance, database)
        if pool_key in self._pg_pools:
            self._pg_pools[pool_key].putconn(conn)

    # ==================== 通用方法 ====================

    def get_connection(
        self,
        instance: RDBInstance,
        database: Optional[str] = None,
        use_pool: bool = True
    ):
        """
        获取数据库连接（自动判断类型）

        Args:
            instance: 数据库实例
            database: 数据库名
            use_pool: 是否使用连接池

        Returns:
            数据库连接对象
        """
        db_type = instance.db_type.lower() if instance.db_type else 'mysql'

        if db_type == 'postgresql':
            return self.get_postgresql_connection(instance, database, use_pool)
        else:
            return self.get_mysql_connection(instance, database, use_pool)

    @contextmanager
    def connection(
        self,
        instance: RDBInstance,
        database: Optional[str] = None,
        use_pool: bool = True
    ):
        """
        连接上下文管理器

        使用示例:
            with db_manager.connection(instance, 'mydb') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
        """
        db_type = instance.db_type.lower() if instance.db_type else 'mysql'
        conn = None

        try:
            conn = self.get_connection(instance, database, use_pool)
            yield conn
        finally:
            if conn:
                if db_type == 'postgresql' and use_pool:
                    self.release_postgresql_connection(instance, conn, database)
                else:
                    conn.close()

    # ==================== 连接测试 ====================

    async def test_connection(
        self,
        instance: RDBInstance,
        database: Optional[str] = None
    ) -> dict[str, Any]:
        """
        测试数据库连接

        Returns:
            Dict: {'success': bool, 'message': str, 'version': str}
        """
        db_type = instance.db_type.lower() if instance.db_type else 'mysql'

        try:
            with self.connection(instance, database, use_pool=False) as conn:
                cursor = conn.cursor()

                # 获取版本
                if db_type == 'postgresql':
                    cursor.execute("SELECT version()")
                    version = cursor.fetchone()[0]
                else:
                    cursor.execute("SELECT VERSION()")
                    version = cursor.fetchone()[0]

                cursor.close()

                return {
                    'success': True,
                    'message': '连接成功',
                    'version': version
                }

        except DatabaseConnectionError as e:
            return {'success': False, 'message': str(e)}
        except Exception as e:
            return {'success': False, 'message': f'连接失败: {str(e)}'}

    # ==================== 查询执行 ====================

    async def execute_query(
        self,
        instance: RDBInstance,
        sql: str,
        database: Optional[str] = None,
        params: Optional[tuple] = None,
        fetch: bool = True
    ) -> dict[str, Any]:
        """
        执行单条 SQL 查询

        Args:
            instance: 数据库实例
            sql: SQL语句
            database: 数据库名
            params: 参数化查询参数
            fetch: 是否获取结果

        Returns:
            Dict: {'success': bool, 'data': List, 'affected_rows': int, 'message': str}
        """
        try:
            with self.connection(instance, database) as conn:
                cursor = conn.cursor()

                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)

                result = {
                    'success': True,
                    'affected_rows': cursor.rowcount if cursor.rowcount >= 0 else 0,
                    'data': [],
                    'message': '执行成功'
                }

                if fetch and cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    result['data'] = [dict(zip(columns, row, strict=False)) for row in rows]
                    result['affected_rows'] = len(rows)

                # 非查询语句需要提交
                if not fetch:
                    conn.commit()

                cursor.close()
                return result

        except Exception as e:
            logger.error(f"SQL执行失败: {sql[:100]}, 错误: {e}")
            return {'success': False, 'data': [], 'affected_rows': 0, 'message': str(e)}

    async def execute_script(
        self,
        instance: RDBInstance,
        script: str,
        database: Optional[str] = None,
        stop_on_error: bool = False
    ) -> dict[str, Any]:
        """
        执行多条 SQL 脚本

        Args:
            instance: 数据库实例
            script: SQL脚本（多条语句用分号分隔）
            database: 数据库名
            stop_on_error: 遇到错误是否停止

        Returns:
            Dict: {'success': bool, 'results': List, 'total_affected': int}
        """
        statements = [s.strip() for s in script.split(';') if s.strip()]
        results = []
        total_affected = 0

        with self.connection(instance, database) as conn:
            cursor = conn.cursor()

            for i, sql in enumerate(statements):
                try:
                    cursor.execute(sql)
                    affected = cursor.rowcount if cursor.rowcount >= 0 else 0
                    conn.commit()
                    total_affected += affected
                    results.append({
                        'statement': i + 1,
                        'success': True,
                        'affected_rows': affected
                    })
                except Exception as e:
                    conn.rollback()
                    results.append({
                        'statement': i + 1,
                        'success': False,
                        'error': str(e)
                    })
                    if stop_on_error:
                        break

            cursor.close()

        success_count = sum(1 for r in results if r['success'])
        return {
            'success': success_count == len(results),
            'results': results,
            'total_affected': total_affected,
            'summary': f"成功{success_count}条, 失败{len(results) - success_count}条"
        }

    # ==================== 数据库/表信息获取 ====================

    async def get_databases(self, instance: RDBInstance) -> list[str]:
        """获取实例所有数据库列表"""
        db_type = instance.db_type.lower() if instance.db_type else 'mysql'

        with self.connection(instance) as conn:
            cursor = conn.cursor()

            if db_type == 'postgresql':
                cursor.execute(
                    "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname"
                )
            else:
                cursor.execute("SHOW DATABASES")

            databases = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return databases

    async def get_tables(
        self,
        instance: RDBInstance,
        database: str
    ) -> list[dict[str, Any]]:
        """获取数据库所有表"""
        db_type = instance.db_type.lower() if instance.db_type else 'mysql'

        with self.connection(instance, database) as conn:
            cursor = conn.cursor()

            if db_type == 'postgresql':
                cursor.execute("""
                    SELECT table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
            else:
                cursor.execute("""
                    SELECT table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    ORDER BY table_name
                """, (database,))

            tables = [
                {'name': row[0], 'type': row[1]}
                for row in cursor.fetchall()
            ]
            cursor.close()
            return tables

    async def get_table_structure(
        self,
        instance: RDBInstance,
        database: str,
        table: str
    ) -> dict[str, Any]:
        """获取表结构"""
        db_type = instance.db_type.lower() if instance.db_type else 'mysql'

        with self.connection(instance, database) as conn:
            cursor = conn.cursor()

            # 获取列信息
            if db_type == 'postgresql':
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                """, (table,))
            else:
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s
                    ORDER BY ordinal_position
                """, (database, table))

            columns = cursor.fetchall()

            # 获取索引信息
            if db_type == 'postgresql':
                cursor.execute("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public' AND tablename = %s
                """, (table,))
            else:
                cursor.execute(f"SHOW INDEX FROM {table}")

            indexes = cursor.fetchall()

            cursor.close()

            return {
                'table': table,
                'columns': columns,
                'indexes': indexes
            }

    # ==================== 连接池管理 ====================

    def close_pool(self, instance: RDBInstance, database: Optional[str] = None):
        """关闭指定连接池"""
        pool_key = self._get_pool_key(instance, database)

        if pool_key in self._mysql_pools:
            self._mysql_pools[pool_key].close()
            del self._mysql_pools[pool_key]
            logger.info(f"关闭MySQL连接池: {pool_key}")

        if pool_key in self._pg_pools:
            self._pg_pools[pool_key].closeall()
            del self._pg_pools[pool_key]
            logger.info(f"关闭PostgreSQL连接池: {pool_key}")

    def close_all_pools(self):
        """关闭所有连接池"""
        for pool in self._mysql_pools.values():
            pool.close()
        self._mysql_pools.clear()

        for pool in self._pg_pools.values():
            pool.closeall()
        self._pg_pools.clear()

        logger.info("关闭所有数据库连接池")


# 单例实例
db_manager = DatabaseConnectionManager()



# ==================== Redis 连接管理 ====================

class RedisConnectionManager:
    """
    Redis 连接管理器
    
    提供 Redis 连接的统一管理，支持：
    - 自动密码解密
    - 连接超时控制
    - 上下文管理器
    """
    
    # 连接超时配置
    CONNECT_TIMEOUT = 10
    SOCKET_TIMEOUT = 10
    
    def __init__(self):
        self._connection_cache: dict[int, Any] = {}
    
    def _get_credentials(self, instance: 'RedisInstance') -> Tuple[str, int, Optional[str], int]:
        """
        获取 Redis 实例连接凭证
        
        Args:
            instance: Redis 实例
        
        Returns:
            Tuple[str, int, Optional[str], int]: (host, port, password, db)
        """
        password = None
        if instance.password_encrypted:
            try:
                password = decrypt_instance_password(instance.password_encrypted)
            except ValueError as e:
                raise DatabaseConnectionError(f"Redis密码解密失败: {str(e)}") from None
        
        return (
            instance.host,
            instance.port,
            password,
            0  # 默认使用 db 0
        )
    
    def get_connection(self, instance: 'RedisInstance') -> 'redis.Redis':
        """
        获取 Redis 连接
        
        Args:
            instance: Redis 实例
        
        Returns:
            redis.Redis: Redis 连接对象
        
        Raises:
            DatabaseConnectionError: 连接失败
        """
        import redis
        
        host, port, password, db = self._get_credentials(instance)
        
        try:
            return redis.Redis(
                host=host,
                port=port,
                password=password,
                db=db,
                decode_responses=True,
                socket_connect_timeout=self.CONNECT_TIMEOUT,
                socket_timeout=self.SOCKET_TIMEOUT
            )
        except Exception as e:
            logger.error(f"Redis连接失败: {instance.host}:{instance.port}, 错误: {e}")
            raise DatabaseConnectionError(f"Redis连接失败: {str(e)}") from e
    
    @contextmanager
    def connection(self, instance: 'RedisInstance'):
        """
        Redis 连接上下文管理器
        
        使用示例:
            with redis_manager.connection(redis_instance) as r:
                r.get('key')
                r.set('key', 'value')
        """
        conn = None
        try:
            conn = self.get_connection(instance)
            yield conn
        finally:
            if conn:
                conn.close()
    
    async def test_connection(self, instance: 'RedisInstance') -> Dict[str, Any]:
        """
        测试 Redis 连接
        
        Returns:
            Dict: {'success': bool, 'message': str, 'version': str}
        """
        try:
            with self.connection(instance) as r:
                info = r.info('server')
                return {
                    'success': True,
                    'message': '连接成功',
                    'version': info.get('redis_version', 'unknown')
                }
        except DatabaseConnectionError as e:
            return {'success': False, 'message': str(e)}
        except Exception as e:
            return {'success': False, 'message': f'连接失败: {str(e)}'}
    
    async def get_info(self, instance: 'RedisInstance') -> Dict[str, Any]:
        """
        获取 Redis 信息
        
        Returns:
            Dict: Redis 服务器信息
        """
        with self.connection(instance) as r:
            return r.info()
    
    async def get_memory_stats(self, instance: 'RedisInstance') -> Dict[str, Any]:
        """
        获取 Redis 内存统计
        """
        with self.connection(instance) as r:
            info = r.info('memory')
            return {
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'used_memory_peak': info.get('used_memory_peak', 0),
                'used_memory_peak_human': info.get('used_memory_peak_human', '0B'),
                'mem_fragmentation_ratio': info.get('mem_fragmentation_ratio', 1.0)
            }


# Redis 单例实例
redis_manager = RedisConnectionManager()


# ==================== 统一连接工厂 ====================

class ConnectionFactory:
    """
    统一连接工厂
    
    提供统一的连接获取入口，根据实例类型自动选择连接管理器
    """
    
    @staticmethod
    def get_manager(instance):
        """
        根据实例类型获取对应的连接管理器
        
        Args:
            instance: RDBInstance 或 RedisInstance
        
        Returns:
            DatabaseConnectionManager 或 RedisConnectionManager
        """
        from app.models import RedisInstance
        
        if isinstance(instance, RedisInstance):
            return redis_manager
        return db_manager
    
    @staticmethod
    @contextmanager
    def connection(instance, database: Optional[str] = None):
        """
        统一连接上下文管理器
        
        使用示例:
            with ConnectionFactory.connection(instance) as conn:
                if isinstance(instance, RDBInstance):
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
                else:
                    conn.get('key')
        """
        from app.models import RedisInstance
        
        if isinstance(instance, RedisInstance):
            with redis_manager.connection(instance) as conn:
                yield conn
        else:
            with db_manager.connection(instance, database) as conn:
                yield conn


# 导出
__all__ = [
    'DatabaseConnectionManager',
    'RedisConnectionManager', 
    'ConnectionFactory',
    'db_manager',
    'redis_manager',
    'DatabaseConnectionError',
    'DatabaseExecutionError'
]
