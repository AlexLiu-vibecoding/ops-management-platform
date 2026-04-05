"""
数据源适配器基类

定义统一的数据源接口，所有数据源适配器必须实现此接口。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from contextlib import contextmanager


class DataSourceAdapter(ABC):
    """数据源适配器基类
    
    所有数据源适配器必须实现此接口，确保统一的操作方式。
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """建立连接
        
        Returns:
            是否连接成功
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """断开连接
        
        Returns:
            是否断开成功
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """测试连接
        
        Returns:
            连接测试结果，包含:
                - success: bool - 是否成功
                - message: str - 消息
                - latency: float - 延迟时间（毫秒）
                - version: str - 数据源版本（可选）
        """
        pass
    
    @abstractmethod
    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """执行查询
        
        Args:
            query: 查询语句
            params: 查询参数
        
        Returns:
            查询结果列表，每行是一个字典
        """
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """获取监控指标
        
        Returns:
            监控指标字典，包含:
                - connection_pool_size: int - 连接池大小
                - active_connections: int - 活跃连接数
                - idle_connections: int - 空闲连接数
                - total_queries: int - 总查询数
                - total_errors: int - 总错误数
                - avg_query_time: float - 平均查询时间
        """
        pass
    
    @abstractmethod
    def get_adapter_type(self) -> str:
        """获取适配器类型
        
        Returns:
            适配器类型标识，如 "mysql", "postgresql", "redis"
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查是否已连接
        
        Returns:
            是否已连接
        """
        pass
    
    @contextmanager
    def connection_context(self):
        """连接上下文管理器
        
        使用示例:
            with adapter.connection_context():
                result = adapter.execute_query("SELECT * FROM users")
        """
        if not self.is_connected():
            self.connect()
        try:
            yield self
        finally:
            pass  # 保持连接，由调用方决定是否断开
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典
        
        Returns:
            适配器信息字典
        """
        return {
            "type": self.get_adapter_type(),
            "connected": self.is_connected(),
            "metrics": self.get_metrics()
        }
