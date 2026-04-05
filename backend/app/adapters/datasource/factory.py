"""
数据源适配器工厂

负责创建和管理数据源适配器实例。
遵循开闭原则：新增数据源类型只需注册，无需修改工厂代码。
"""
from typing import Dict, Any, Type
from app.adapters.datasource.base import DataSourceAdapter


class DataSourceAdapterFactory:
    """数据源适配器工厂
    
    使用工厂模式创建适配器实例，支持动态注册新类型。
    """
    
    # 已注册的适配器类型
    _adapters: Dict[str, Type[DataSourceAdapter]] = {}
    
    @classmethod
    def register(cls, adapter_type: str, adapter_class: Type[DataSourceAdapter]):
        """注册新适配器类型
        
        Args:
            adapter_type: 适配器类型标识（如 "mysql", "postgresql"）
            adapter_class: 适配器类
        
        Example:
            DataSourceAdapterFactory.register("mongodb", MongoDBAdapter)
        """
        if not issubclass(adapter_class, DataSourceAdapter):
            raise TypeError(f"{adapter_class} 必须是 DataSourceAdapter 的子类")
        cls._adapters[adapter_type] = adapter_class
    
    @classmethod
    def create(cls, adapter_type: str, config: Dict[str, Any]) -> DataSourceAdapter:
        """创建适配器实例
        
        Args:
            adapter_type: 适配器类型标识
            config: 配置字典
        
        Returns:
            适配器实例
        
        Raises:
            ValueError: 不支持的适配器类型
        
        Example:
            adapter = DataSourceAdapterFactory.create("mysql", {
                "host": "localhost",
                "port": 3306,
                "username": "root",
                "password": "password",
                "database": "test"
            })
        """
        adapter_class = cls._adapters.get(adapter_type)
        if not adapter_class:
            raise ValueError(
                f"不支持的数据源类型: {adapter_type}. "
                f"支持的类型: {list(cls._adapters.keys())}"
            )
        return adapter_class(config)
    
    @classmethod
    def get_supported_types(cls) -> list[str]:
        """获取支持的数据源类型列表
        
        Returns:
            支持的类型列表
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def is_supported(cls, adapter_type: str) -> bool:
        """检查是否支持指定类型
        
        Args:
            adapter_type: 适配器类型标识
        
        Returns:
            是否支持
        """
        return adapter_type in cls._adapters
