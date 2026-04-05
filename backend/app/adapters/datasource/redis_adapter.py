"""
Redis 数据源适配器

实现 Redis 数据源的连接、查询和监控功能。
"""
import time
import json
from typing import Any, Dict, List, Optional
import redis

from app.adapters.datasource.base import DataSourceAdapter


class RedisAdapter(DataSourceAdapter):
    """Redis 适配器"""
    
    CONNECT_TIMEOUT = 10
    DECODE_RESPONSES = True
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Redis 适配器
        
        Args:
            config: 配置字典，包含:
                - host: 主机地址
                - port: 端口
                - password: 密码（可选）
                - db: 数据库索引（默认 0）
                - decode_responses: 是否解码响应（默认 True）
        """
        self.config = config
        self.connection = None
        self._metrics = {
            "total_queries": 0,
            "total_errors": 0,
            "total_query_time": 0.0,
        }
    
    def connect(self) -> bool:
        """建立连接"""
        try:
            self.connection = redis.Redis(
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 6379),
                password=self.config.get("password"),
                db=self.config.get("db", 0),
                decode_responses=self.config.get("decode_responses", self.DECODE_RESPONSES),
                socket_timeout=self.CONNECT_TIMEOUT,
                socket_connect_timeout=self.CONNECT_TIMEOUT,
            )
            # 测试连接
            self.connection.ping()
            return True
        except Exception as e:
            self._metrics["total_errors"] += 1
            raise ConnectionError(f"Redis 连接失败: {str(e)}")
    
    def disconnect(self) -> bool:
        """断开连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
        return True
    
    def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        start_time = time.time()
        try:
            info = self.connection.info("server")
            latency = (time.time() - start_time) * 1000
            return {
                "success": True,
                "message": "连接成功",
                "latency": round(latency, 2),
                "version": info.get("redis_version", "unknown")
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
        """执行查询
        
        Args:
            query: Redis 命令，如 "GET key" 或 "HGETALL hash"
            params: 命令参数（可选）
        
        Returns:
            查询结果列表
        """
        if not self.connection:
            raise RuntimeError("未建立连接，请先调用 connect()")
        
        start_time = time.time()
        try:
            # 解析命令
            parts = query.strip().split()
            command = parts[0].upper()
            args = parts[1:] if len(parts) > 1 else []
            
            # 执行命令
            result = getattr(self.connection, command.lower())(*args)
            
            # 转换结果格式
            if command in ("HGETALL", "HKEYS", "HVALS"):
                # Redis 返回列表，转换为字典或保持列表
                if command == "HGETALL" and result:
                    # 将列表转换为字典
                    result = [dict(zip(result[::2], result[1::2]))]
                else:
                    result = [{"value": v} for v in result] if isinstance(result, list) else [{"value": result}]
            else:
                result = [{"value": result}]
            
            query_time = time.time() - start_time
            self._metrics["total_queries"] += 1
            self._metrics["total_query_time"] += query_time
            
            return result
        except Exception as e:
            self._metrics["total_errors"] += 1
            raise RuntimeError(f"查询执行失败: {str(e)}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取监控指标"""
        if not self.connection:
            return {
                "connection_pool_size": 0,
                "active_connections": 0,
                "idle_connections": 0,
                "total_queries": self._metrics["total_queries"],
                "total_errors": self._metrics["total_errors"],
                "avg_query_time": 0.0,
            }
        
        try:
            info = self.connection.info("stats")
            total_queries = self._metrics["total_queries"]
            avg_query_time = (
                self._metrics["total_query_time"] / total_queries
                if total_queries > 0 else 0.0
            )
            
            return {
                "connection_pool_size": 1,  # Redis 单连接
                "active_connections": info.get("connected_clients", 0),
                "idle_connections": 0,
                "total_queries": total_queries,
                "total_errors": self._metrics["total_errors"],
                "avg_query_time": round(avg_query_time * 1000, 2),  # 转换为毫秒
            }
        except Exception:
            return {
                "connection_pool_size": 1,
                "active_connections": 0,
                "idle_connections": 0,
                "total_queries": self._metrics["total_queries"],
                "total_errors": self._metrics["total_errors"],
                "avg_query_time": 0.0,
            }
    
    def get_adapter_type(self) -> str:
        """获取适配器类型"""
        return "redis"
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        if not self.connection:
            return False
        try:
            return self.connection.ping()
        except Exception:
            return False
