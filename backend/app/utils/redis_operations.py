"""
Redis 实例连接和操作工具类
用于管理 Redis 实例的连接和操作
"""
import redis
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime


class RedisInstanceClient:
    """Redis 实例客户端封装"""
    
    def __init__(
        self,
        host: str,
        port: int = 6379,
        password: Optional[str] = None,
        db: int = 0,
        redis_mode: str = "standalone",
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5,
        decode_responses: bool = True
    ):
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.redis_mode = redis_mode
        self._client = None
        self._config = {
            "socket_timeout": socket_timeout,
            "socket_connect_timeout": socket_connect_timeout,
            "decode_responses": decode_responses
        }
    
    @property
    def client(self) -> redis.Redis:
        """获取 Redis 客户端"""
        if self._client is None:
            if self.redis_mode == "cluster":
                # 集群模式
                self._client = redis.RedisCluster(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    **self._config
                )
            else:
                # 单机或哨兵模式
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    db=self.db,
                    **self._config
                )
        return self._client
    
    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            self._client = None
    
    def test_connection(self) -> tuple[bool, str, Optional[str]]:
        """
        测试连接
        返回: (成功标志, 消息, 版本号)
        """
        try:
            info = self.client.info("server")
            version = info.get("redis_version", "unknown")
            return True, "连接成功", version
        except redis.AuthenticationError:
            return False, "认证失败，请检查密码", None
        except redis.ConnectionError as e:
            return False, f"连接失败: {str(e)}", None
        except Exception as e:
            return False, f"连接异常: {str(e)}", None
    
    def get_info(self, section: str = "default") -> dict[str, Any]:
        """获取 Redis 信息"""
        try:
            return self.client.info(section)
        except Exception:
            return {}
    
    def get_server_info(self) -> dict[str, Any]:
        """获取服务器信息"""
        info = self.get_info("server")
        return {
            "version": info.get("redis_version"),
            "mode": info.get("redis_mode"),
            "os": info.get("os"),
            "arch_bits": info.get("arch_bits"),
            "process_id": info.get("process_id"),
            "uptime_in_seconds": info.get("uptime_in_seconds"),
            "uptime_in_days": info.get("uptime_in_days"),
            "executable": info.get("executable"),
            "config_file": info.get("config_file"),
            "tcp_port": info.get("tcp_port"),
        }
    
    def get_memory_info(self) -> dict[str, Any]:
        """获取内存信息"""
        info = self.get_info("memory")
        return {
            "used_memory": info.get("used_memory", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "used_memory_rss": info.get("used_memory_rss", 0),
            "used_memory_rss_human": info.get("used_memory_rss_human", "0B"),
            "used_memory_peak": info.get("used_memory_peak", 0),
            "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
            "total_system_memory": info.get("total_system_memory", 0),
            "total_system_memory_human": info.get("total_system_memory_human", "0B"),
            "used_memory_lua": info.get("used_memory_lua", 0),
            "maxmemory": info.get("maxmemory", 0),
            "maxmemory_human": info.get("maxmemory_human", "0B"),
            "maxmemory_policy": info.get("maxmemory_policy", "noeviction"),
            "mem_fragmentation_ratio": info.get("mem_fragmentation_ratio", 1.0),
            "mem_allocator": info.get("mem_allocator", ""),
        }
    
    def get_stats_info(self) -> dict[str, Any]:
        """获取统计信息"""
        info = self.get_info("stats")
        return {
            "total_connections_received": info.get("total_connections_received", 0),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
            "total_net_input_bytes": info.get("total_net_input_bytes", 0),
            "total_net_output_bytes": info.get("total_net_output_bytes", 0),
            "instantaneous_input_kbps": info.get("instantaneous_input_kbps", 0),
            "instantaneous_output_kbps": info.get("instantaneous_output_kbps", 0),
            "rejected_connections": info.get("rejected_connections", 0),
            "expired_keys": info.get("expired_keys", 0),
            "evicted_keys": info.get("evicted_keys", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
        }
    
    def get_clients_info(self) -> dict[str, Any]:
        """获取客户端信息"""
        info = self.get_info("clients")
        return {
            "connected_clients": info.get("connected_clients", 0),
            "client_longest_output_list": info.get("client_longest_output_list", 0),
            "client_biggest_input_buf": info.get("client_biggest_input_buf", 0),
            "blocked_clients": info.get("blocked_clients", 0),
        }
    
    def get_keyspace_info(self) -> dict[str, Any]:
        """获取键空间信息"""
        info = self.get_info("keyspace")
        return info or {}
    
    def get_db_size(self) -> int:
        """获取当前数据库的键数量"""
        try:
            return self.client.dbsize()
        except Exception:
            return 0
    
    def get_key_info(self, key: str) -> dict[str, Any]:
        """获取键信息"""
        try:
            key_type = self.client.type(key)
            if key_type == "none":
                return {"exists": False}
            
            ttl = self.client.ttl(key)
            info = {
                "exists": True,
                "type": key_type,
                "ttl": ttl,
                "ttl_human": self._format_ttl(ttl),
            }
            
            # 获取键值大小
            if key_type == "string":
                info["length"] = self.client.strlen(key)
            elif key_type == "list":
                info["length"] = self.client.llen(key)
            elif key_type == "set":
                info["length"] = self.client.scard(key)
            elif key_type == "zset":
                info["length"] = self.client.zcard(key)
            elif key_type == "hash":
                info["length"] = self.client.hlen(key)
            
            return info
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    def _format_ttl(self, ttl: int) -> str:
        """格式化 TTL"""
        if ttl == -1:
            return "永不过期"
        elif ttl == -2:
            return "键不存在"
        elif ttl < 60:
            return f"{ttl}秒"
        elif ttl < 3600:
            return f"{ttl // 60}分钟"
        elif ttl < 86400:
            return f"{ttl // 3600}小时"
        else:
            return f"{ttl // 86400}天"
    
    def get_key_value(self, key: str, start: int = 0, end: int = -1) -> Any:
        """获取键值"""
        try:
            key_type = self.client.type(key)
            
            if key_type == "string":
                return self.client.get(key)
            elif key_type == "list":
                return self.client.lrange(key, start, end)
            elif key_type == "set":
                return list(self.client.smembers(key))
            elif key_type == "zset":
                return self.client.zrange(key, start, end, withscores=True)
            elif key_type == "hash":
                return self.client.hgetall(key)
            else:
                return None
        except Exception:
            return None
    
    def scan_keys(
        self,
        pattern: str = "*",
        count: int = 100,
        cursor: int = 0
    ) -> tuple[int, list[str]]:
        """
        扫描键
        返回: (新游标, 键列表)
        """
        try:
            cursor, keys = self.client.scan(cursor=cursor, match=pattern, count=count)
            return cursor, keys
        except Exception:
            return 0, []
    
    def find_keys(self, pattern: str = "*", limit: int = 1000) -> list[str]:
        """查找键（简化版，限制数量）"""
        keys = []
        cursor = 0
        while True:
            cursor, batch = self.client.scan(cursor=cursor, match=pattern, count=100)
            keys.extend(batch)
            if cursor == 0 or len(keys) >= limit:
                break
        return keys[:limit]
    
    def set_key_value(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置键值"""
        try:
            if ttl:
                return self.client.setex(key, ttl, value)
            return self.client.set(key, value)
        except Exception:
            return False
    
    def delete_key(self, key: str) -> bool:
        """删除键"""
        try:
            return self.client.delete(key) > 0
        except Exception:
            return False
    
    def rename_key(self, old_key: str, new_key: str) -> bool:
        """重命名键"""
        try:
            self.client.rename(old_key, new_key)
            return True
        except Exception:
            return False
    
    def set_ttl(self, key: str, ttl: int) -> bool:
        """设置过期时间"""
        try:
            return self.client.expire(key, ttl)
        except Exception:
            return False
    
    def get_config(self, pattern: str = "*") -> dict[str, str]:
        """获取配置"""
        try:
            config_list = self.client.config_get(pattern)
            return {config_list[i]: config_list[i + 1] for i in range(0, len(config_list), 2)}
        except Exception:
            return {}
    
    def get_slowlog(self, limit: int = 10) -> list[dict[str, Any]]:
        """获取慢查询日志"""
        try:
            slowlog = self.client.slowlog_get(limit)
            result = []
            for item in slowlog:
                result.append({
                    "id": item.get("id"),
                    "start_time": datetime.fromtimestamp(item.get("start_time", 0)).strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_us": item.get("duration"),
                    "command": " ".join(item.get("command", [])),
                })
            return result
        except Exception:
            return []
    
    def get_client_list(self) -> list[dict[str, Any]]:
        """获取客户端列表"""
        try:
            clients = self.client.client_list()
            return clients if isinstance(clients, list) else []
        except Exception:
            return []
    
    def flush_db(self) -> bool:
        """清空当前数据库"""
        try:
            self.client.flushdb()
            return True
        except Exception:
            return False
    
    def ping(self) -> bool:
        """Ping 测试"""
        try:
            return self.client.ping()
        except Exception:
            return False
