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


def migration_004():
    """
    迁移 004: 创建 aws_regions 表并初始化 AWS 区域数据
    """
    log("执行迁移 004: 创建 aws_regions 表")
    
    if not table_exists('aws_regions'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE aws_regions (
                    id SERIAL PRIMARY KEY,
                    region_code VARCHAR(30) UNIQUE NOT NULL,
                    region_name VARCHAR(100) NOT NULL,
                    geo_group VARCHAR(50) NOT NULL,
                    display_order INTEGER DEFAULT 0,
                    is_enabled BOOLEAN DEFAULT TRUE,
                    description VARCHAR(200),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            log("  ✓ 创建 aws_regions 表")
        
        # 初始化 AWS 区域数据
        aws_regions_data = [
            # 美国
            ("us-east-1", "美国东部(弗吉尼亚北部)", "美国", 1),
            ("us-east-2", "美国东部(俄亥俄)", "美国", 2),
            ("us-west-1", "美国西部(加利福尼亚北部)", "美国", 3),
            ("us-west-2", "美国西部(俄勒冈)", "美国", 4),
            # 美洲其他
            ("ca-central-1", "加拿大(中部)", "美洲其他", 10),
            ("ca-west-1", "加拿大西部(卡尔加里)", "美洲其他", 11),
            ("sa-east-1", "南美洲(圣保罗)", "美洲其他", 12),
            ("mx-central-1", "墨西哥(中部)", "美洲其他", 13),
            # 欧洲
            ("eu-west-1", "欧洲(爱尔兰)", "欧洲", 20),
            ("eu-west-2", "欧洲(伦敦)", "欧洲", 21),
            ("eu-west-3", "欧洲(巴黎)", "欧洲", 22),
            ("eu-central-1", "欧洲(法兰克福)", "欧洲", 23),
            ("eu-central-2", "欧洲(苏黎世)", "欧洲", 24),
            ("eu-south-1", "欧洲(米兰)", "欧洲", 25),
            ("eu-south-2", "欧洲(西班牙)", "欧洲", 26),
            ("eu-north-1", "欧洲(斯德哥尔摩)", "欧洲", 27),
            # 亚太
            ("ap-east-1", "亚太地区(香港)", "亚太", 30),
            ("ap-northeast-1", "亚太地区(东京)", "亚太", 31),
            ("ap-northeast-2", "亚太地区(首尔)", "亚太", 32),
            ("ap-northeast-3", "亚太地区(大阪)", "亚太", 33),
            ("ap-southeast-1", "亚太地区(新加坡)", "亚太", 34),
            ("ap-southeast-2", "亚太地区(悉尼)", "亚太", 35),
            ("ap-southeast-3", "亚太地区(雅加达)", "亚太", 36),
            ("ap-southeast-4", "亚太地区(墨尔本)", "亚太", 37),
            ("ap-south-1", "亚太地区(孟买)", "亚太", 38),
            ("ap-south-2", "亚太地区(海德拉巴)", "亚太", 39),
            # 中东
            ("me-south-1", "中东(巴林)", "中东", 40),
            ("me-central-1", "中东(阿联酋)", "中东", 41),
            # 非洲
            ("af-south-1", "非洲(开普敦)", "非洲", 50),
            # 中国
            ("cn-north-1", "中国(北京)", "中国", 60),
            ("cn-northwest-1", "中国(宁夏)", "中国", 61),
        ]
        
        with engine.connect() as conn:
            for code, name, geo, order in aws_regions_data:
                conn.execute(text("""
                    INSERT INTO aws_regions (region_code, region_name, geo_group, display_order)
                    VALUES (:code, :name, :geo, :order)
                    ON CONFLICT (region_code) DO NOTHING
                """), {"code": code, "name": name, "geo": geo, "order": order})
            conn.commit()
            log(f"  ✓ 初始化 {len(aws_regions_data)} 个 AWS 区域")
    else:
        log("  - aws_regions 表已存在，跳过")


def run_migrations():
    """执行所有迁移"""
    log("=" * 50)
    log("开始数据库迁移")
    log("=" * 50)
    
    try:
        migration_001()
        migration_002()
        migration_003()
        migration_004()
        
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
