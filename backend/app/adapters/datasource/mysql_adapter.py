"""
MySQL 数据源适配器

实现 MySQL 数据源的连接、查询和监控功能。
"""
import time
from typing import Any, Dict, List, Optional
import pymysql
from dbutils.pooled_db import PooledDB

from app.adapters.datasource.base import DataSourceAdapter


class MySQLAdapter(DataSourceAdapter):
    """MySQL 适配器"""
    
    # 连接池配置
    POOL_MIN_CACHED = 1
    POOL_MAX_CACHED = 5
    POOL_MAX_SHARED = 3
    POOL_MAX_CONNECTIONS = 10
    POOL_BLOCKING = True
    CONNECT_TIMEOUT = 10
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 MySQL 适配器
        
        Args:
            config: 配置字典，包含:
                - host: 主机地址
                - port: 端口
                - username: 用户名
                - password: 密码
                - database: 数据库名
                - charset: 字符集（默认 utf8mb4）
        """
        self.config = config
        self.connection_pool = None
        self._metrics = {
            "total_queries": 0,
            "total_errors": 0,
            "total_query_time": 0.0,
        }
    
    def connect(self) -> bool:
        """建立连接"""
        try:
            self.connection_pool = PooledDB(
                creator=pymysql,
                mincached=self.POOL_MIN_CACHED,
                maxcached=self.POOL_MAX_CACHED,
                maxshared=self.POOL_MAX_SHARED,
                maxconnections=self.POOL_MAX_CONNECTIONS,
                blocking=self.POOL_BLOCKING,
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 3306),
                user=self.config.get("username"),
                password=self.config.get("password"),
                database=self.config.get("database"),
                charset=self.config.get("charset", "utf8mb4"),
                connect_timeout=self.CONNECT_TIMEOUT,
                cursorclass=pymysql.cursors.DictCursor,
            )
            return True
        except Exception as e:
            self._metrics["total_errors"] += 1
            raise ConnectionError(f"MySQL 连接失败: {str(e)}")
    
    def disconnect(self) -> bool:
        """断开连接"""
        if self.connection_pool:
            self.connection_pool.close()
            self.connection_pool = None
        return True
    
    def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        start_time = time.time()
        try:
            conn = self.connection_pool.connection()
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            cursor.close()
            conn.close()
            
            latency = (time.time() - start_time) * 1000
            return {
                "success": True,
                "message": "连接成功",
                "latency": round(latency, 2),
                "version": version.get("VERSION()") if version else "unknown"
            }
        except Exception as e:
            self._metrics["total_errors"] += 1
            latency = (time.time() - start_time) * 1000
            return {
                "success": False,
                "message": f"连接失败: {str(e)}",
                "latency": round(latency, 2),
                "version": None
            }
    
    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """执行查询"""
        if not self.connection_pool:
            raise RuntimeError("未建立连接，请先调用 connect()")
        
        start_time = time.time()
        try:
            conn = self.connection_pool.connection()
            cursor = conn.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # 判断是否为查询语句
            if query.strip().upper().startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN")):
                result = cursor.fetchall()
            else:
                result = [{"affected_rows": cursor.rowcount}]
            
            cursor.close()
            conn.close()
            
            query_time = time.time() - start_time
            self._metrics["total_queries"] += 1
            self._metrics["total_query_time"] += query_time
            
            return result
        except Exception as e:
            self._metrics["total_errors"] += 1
            raise RuntimeError(f"查询执行失败: {str(e)}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取监控指标"""
        if not self.connection_pool:
            return {
                "connection_pool_size": 0,
                "active_connections": 0,
                "idle_connections": 0,
                "total_queries": self._metrics["total_queries"],
                "total_errors": self._metrics["total_errors"],
                "avg_query_time": 0.0,
            }
        
        total_queries = self._metrics["total_queries"]
        avg_query_time = (
            self._metrics["total_query_time"] / total_queries
            if total_queries > 0 else 0.0
        )
        
        return {
            "connection_pool_size": self.POOL_MAX_CONNECTIONS,
            "active_connections": len(self.connection_pool._connections),
            "idle_connections": self.connection_pool._idle_cache,
            "total_queries": total_queries,
            "total_errors": self._metrics["total_errors"],
            "avg_query_time": round(avg_query_time * 1000, 2),  # 转换为毫秒
        }
    
    def get_adapter_type(self) -> str:
        """获取适配器类型"""
        return "mysql"
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connection_pool is not None
