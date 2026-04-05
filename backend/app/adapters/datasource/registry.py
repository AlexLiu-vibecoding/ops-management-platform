"""
注册内置数据源适配器

自动注册所有内置的数据源适配器类型。
"""
from app.adapters.datasource.factory import DataSourceAdapterFactory
from app.adapters.datasource.mysql_adapter import MySQLAdapter
from app.adapters.datasource.postgresql_adapter import PostgreSQLAdapter
from app.adapters.datasource.redis_adapter import RedisAdapter


def register_builtin_adapters():
    """注册所有内置数据源适配器"""
    DataSourceAdapterFactory.register("mysql", MySQLAdapter)
    DataSourceAdapterFactory.register("postgresql", PostgreSQLAdapter)
    DataSourceAdapterFactory.register("redis", RedisAdapter)


# 模块导入时自动注册
register_builtin_adapters()
