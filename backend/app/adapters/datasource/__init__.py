"""
数据源适配器包

提供统一的数据源连接和操作接口，支持 MySQL/PostgreSQL/Redis 等多种数据源。

使用示例:
    from app.adapters.datasource.factory import DataSourceAdapterFactory
    
    # 创建适配器
    adapter = DataSourceAdapterFactory.create("mysql", config={"host": "localhost", ...})
    
    # 使用适配器
    adapter.connect()
    result = adapter.execute_query("SELECT * FROM users")
    metrics = adapter.get_metrics()
    adapter.disconnect()
"""

from app.adapters.datasource.base import DataSourceAdapter
from app.adapters.datasource.factory import DataSourceAdapterFactory

__all__ = ["DataSourceAdapter", "DataSourceAdapterFactory"]
