#!/usr/bin/env python3
"""
数据库迁移脚本
用于同步模型变更到数据库

使用方法:
  python migrations/migrate.py

迁移记录:
  - 001: 添加 instances 表的 redis_mode 和 redis_db 字段
  - 002: 添加 approval_records 表的文件存储字段
  - 003: 添加 global_configs 表（如果不存在）
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine
from datetime import datetime


def log(message):
    """打印带时间戳的日志"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")


def column_exists(table_name, column_name):
    """检查列是否存在"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table AND column_name = :column
        """), {"table": table_name, "column": column_name})
        return result.fetchone() is not None


def table_exists(table_name):
    """检查表是否存在"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = :table
        """), {"table": table_name})
        return result.fetchone() is not None


def migration_001():
    """
    迁移 001: 添加 instances 表的 Redis 相关字段
    """
    log("执行迁移 001: 添加 instances 表的 redis_mode 和 redis_db 字段")
    
    with engine.connect() as conn:
        # 添加 redis_mode 列
        if not column_exists('instances', 'redis_mode'):
            conn.execute(text("ALTER TABLE instances ADD COLUMN redis_mode VARCHAR(50)"))
            conn.commit()
            log("  ✓ 添加 redis_mode 列")
        else:
            log("  - redis_mode 列已存在，跳过")
        
        # 添加 redis_db 列
        if not column_exists('instances', 'redis_db'):
            conn.execute(text("ALTER TABLE instances ADD COLUMN redis_db INTEGER DEFAULT 0"))
            conn.commit()
            log("  ✓ 添加 redis_db 列")
        else:
            log("  - redis_db 列已存在，跳过")


def migration_002():
    """
    迁移 002: 添加 approval_records 表的文件存储字段
    """
    log("执行迁移 002: 添加 approval_records 表的文件存储字段")
    
    with engine.connect() as conn:
        # 添加 sql_file_path 列
        if not column_exists('approval_records', 'sql_file_path'):
            conn.execute(text("ALTER TABLE approval_records ADD COLUMN sql_file_path VARCHAR(500)"))
            conn.commit()
            log("  ✓ 添加 sql_file_path 列")
        else:
            log("  - sql_file_path 列已存在，跳过")
        
        # 添加 rollback_file_path 列
        if not column_exists('approval_records', 'rollback_file_path'):
            conn.execute(text("ALTER TABLE approval_records ADD COLUMN rollback_file_path VARCHAR(500)"))
            conn.commit()
            log("  ✓ 添加 rollback_file_path 列")
        else:
            log("  - rollback_file_path 列已存在，跳过")
        
        # 添加 file_storage_type 列
        if not column_exists('approval_records', 'file_storage_type'):
            conn.execute(text("ALTER TABLE approval_records ADD COLUMN file_storage_type VARCHAR(20) DEFAULT 'database'"))
            conn.commit()
            log("  ✓ 添加 file_storage_type 列")
        else:
            log("  - file_storage_type 列已存在，跳过")


def migration_003():
    """
    迁移 003: 确保 global_configs 表存在
    """
    log("执行迁移 003: 检查 global_configs 表")
    
    if not table_exists('global_configs'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE global_configs (
                    id SERIAL PRIMARY KEY,
                    config_key VARCHAR(100) UNIQUE NOT NULL,
                    config_value VARCHAR(500) NOT NULL,
                    description VARCHAR(200),
                    updated_by INTEGER REFERENCES users(id),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            log("  ✓ 创建 global_configs 表")
    else:
        log("  - global_configs 表已存在，跳过")


def run_migrations():
    """执行所有迁移"""
    log("=" * 50)
    log("开始数据库迁移")
    log("=" * 50)
    
    try:
        migration_001()
        migration_002()
        migration_003()
        
        log("=" * 50)
        log("所有迁移执行完成")
        log("=" * 50)
        return True
    except Exception as e:
        log(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
