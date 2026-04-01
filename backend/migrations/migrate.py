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
  - 004: 创建 aws_regions 表并初始化区域数据
  - 005: 创建监控扩展相关表（告警记录、锁等待、主从复制状态、巡检指标、巡检结果、长事务）
  - 006: 实例表拆分（rdb_instances, redis_instances）及 Redis 监控表
  - 007: 通知系统重构（notification_channels, channel_silence_rules, channel_rate_limits）
"""

import sys
import os
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('migration')


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
    logger.info("执行迁移 001: 添加 instances 表的 redis_mode 和 redis_db 字段")
    
    with engine.connect() as conn:
        # 添加 redis_mode 列
        if not column_exists('instances', 'redis_mode'):
            conn.execute(text("ALTER TABLE instances ADD COLUMN redis_mode VARCHAR(50)"))
            conn.commit()
            logger.info("  ✓ 添加 redis_mode 列")
        else:
            logger.info("  - redis_mode 列已存在，跳过")
        
        # 添加 redis_db 列
        if not column_exists('instances', 'redis_db'):
            conn.execute(text("ALTER TABLE instances ADD COLUMN redis_db INTEGER DEFAULT 0"))
            conn.commit()
            logger.info("  ✓ 添加 redis_db 列")
        else:
            logger.info("  - redis_db 列已存在，跳过")


def migration_002():
    """
    迁移 002: 添加 approval_records 表的文件存储字段
    """
    logger.info("执行迁移 002: 添加 approval_records 表的文件存储字段")
    
    with engine.connect() as conn:
        # 添加 sql_file_path 列
        if not column_exists('approval_records', 'sql_file_path'):
            conn.execute(text("ALTER TABLE approval_records ADD COLUMN sql_file_path VARCHAR(500)"))
            conn.commit()
            logger.info("  ✓ 添加 sql_file_path 列")
        else:
            logger.info("  - sql_file_path 列已存在，跳过")
        
        # 添加 rollback_file_path 列
        if not column_exists('approval_records', 'rollback_file_path'):
            conn.execute(text("ALTER TABLE approval_records ADD COLUMN rollback_file_path VARCHAR(500)"))
            conn.commit()
            logger.info("  ✓ 添加 rollback_file_path 列")
        else:
            logger.info("  - rollback_file_path 列已存在，跳过")
        
        # 添加 file_storage_type 列
        if not column_exists('approval_records', 'file_storage_type'):
            conn.execute(text("ALTER TABLE approval_records ADD COLUMN file_storage_type VARCHAR(20) DEFAULT 'database'"))
            conn.commit()
            logger.info("  ✓ 添加 file_storage_type 列")
        else:
            logger.info("  - file_storage_type 列已存在，跳过")


def migration_003():
    """
    迁移 003: 确保 global_configs 表存在
    """
    logger.info("执行迁移 003: 检查 global_configs 表")
    
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
            logger.info("  ✓ 创建 global_configs 表")
    else:
        logger.info("  - global_configs 表已存在，跳过")


def migration_004():
    """
    迁移 004: 创建 aws_regions 表并初始化 AWS 区域数据
    """
    logger.info("执行迁移 004: 创建 aws_regions 表")
    
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
            logger.info("  ✓ 创建 aws_regions 表")
        
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
            logger.info(f"  ✓ 初始化 {len(aws_regions_data)} 个 AWS 区域")
    else:
        logger.info("  - aws_regions 表已存在，跳过")


def migration_005():
    """
    迁移 005: 创建监控扩展相关表
    """
    logger.info("执行迁移 005: 创建监控扩展相关表")
    
    # 1. 告警记录表
    if not table_exists('alert_records'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE alert_records (
                    id SERIAL PRIMARY KEY,
                    instance_id INTEGER REFERENCES instances(id) ON DELETE CASCADE,
                    metric_type VARCHAR(32) NOT NULL,
                    alert_level VARCHAR(16) NOT NULL,
                    alert_title VARCHAR(200) NOT NULL,
                    alert_content TEXT,
                    alert_source VARCHAR(100),
                    status VARCHAR(16) DEFAULT 'pending',
                    acknowledged_by INTEGER REFERENCES users(id),
                    acknowledged_at TIMESTAMP,
                    resolved_by INTEGER REFERENCES users(id),
                    resolved_at TIMESTAMP,
                    resolve_note TEXT,
                    notification_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_alert_records_instance ON alert_records(instance_id)"))
            conn.execute(text("CREATE INDEX idx_alert_records_status ON alert_records(status)"))
            conn.execute(text("CREATE INDEX idx_alert_records_created ON alert_records(created_at)"))
            conn.commit()
            logger.info("  ✓ 创建 alert_records 表")
    else:
        logger.info("  - alert_records 表已存在，跳过")
    
    # 2. 锁等待记录表
    if not table_exists('lock_waits'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE lock_waits (
                    id SERIAL PRIMARY KEY,
                    instance_id INTEGER REFERENCES instances(id) ON DELETE CASCADE NOT NULL,
                    database_name VARCHAR(100),
                    wait_type VARCHAR(32),
                    waiting_thread_id INTEGER,
                    waiting_sql TEXT,
                    waiting_time INTEGER,
                    blocking_thread_id INTEGER,
                    blocking_sql TEXT,
                    blocking_time INTEGER,
                    status VARCHAR(16) DEFAULT 'active',
                    resolved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_lock_waits_instance ON lock_waits(instance_id)"))
            conn.execute(text("CREATE INDEX idx_lock_waits_status ON lock_waits(status)"))
            conn.execute(text("CREATE INDEX idx_lock_waits_created ON lock_waits(created_at)"))
            conn.commit()
            logger.info("  ✓ 创建 lock_waits 表")
    else:
        logger.info("  - lock_waits 表已存在，跳过")
    
    # 3. 主从复制状态表
    if not table_exists('replication_status'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE replication_status (
                    id SERIAL PRIMARY KEY,
                    instance_id INTEGER REFERENCES instances(id) ON DELETE CASCADE NOT NULL,
                    slave_host VARCHAR(100),
                    slave_port INTEGER,
                    slave_io_running VARCHAR(16),
                    slave_sql_running VARCHAR(16),
                    seconds_behind_master INTEGER,
                    master_log_file VARCHAR(100),
                    read_master_log_pos INTEGER,
                    relay_master_log_file VARCHAR(100),
                    exec_master_log_pos INTEGER,
                    last_io_error TEXT,
                    last_sql_error TEXT,
                    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_replication_status_instance ON replication_status(instance_id)"))
            conn.execute(text("CREATE INDEX idx_replication_status_check_time ON replication_status(check_time)"))
            conn.commit()
            logger.info("  ✓ 创建 replication_status 表")
    else:
        logger.info("  - replication_status 表已存在，跳过")
    
    # 4. 巡检指标配置表
    if not table_exists('inspect_metrics'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE inspect_metrics (
                    id SERIAL PRIMARY KEY,
                    module VARCHAR(32) NOT NULL,
                    metric_name VARCHAR(128) NOT NULL,
                    metric_code VARCHAR(64) UNIQUE NOT NULL,
                    check_freq VARCHAR(16) DEFAULT 'daily',
                    warn_threshold VARCHAR(64),
                    critical_threshold VARCHAR(64),
                    collect_sql TEXT,
                    auto_fix_sql TEXT,
                    is_enabled BOOLEAN DEFAULT TRUE,
                    description VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("  ✓ 创建 inspect_metrics 表")
    else:
        logger.info("  - inspect_metrics 表已存在，跳过")
    
    # 5. 巡检结果表
    if not table_exists('inspect_results'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE inspect_results (
                    id SERIAL PRIMARY KEY,
                    instance_id INTEGER REFERENCES instances(id) ON DELETE CASCADE NOT NULL,
                    metric_id INTEGER REFERENCES inspect_metrics(id) NOT NULL,
                    check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(16) NOT NULL,
                    actual_value VARCHAR(255),
                    result_detail JSON,
                    suggestion TEXT,
                    is_fixed BOOLEAN DEFAULT FALSE,
                    fixed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_inspect_results_instance ON inspect_results(instance_id)"))
            conn.execute(text("CREATE INDEX idx_inspect_results_check_time ON inspect_results(check_time)"))
            conn.commit()
            logger.info("  ✓ 创建 inspect_results 表")
    else:
        logger.info("  - inspect_results 表已存在，跳过")
    
    # 6. 长事务记录表
    if not table_exists('long_transactions'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE long_transactions (
                    id SERIAL PRIMARY KEY,
                    instance_id INTEGER REFERENCES instances(id) ON DELETE CASCADE NOT NULL,
                    trx_id VARCHAR(64),
                    trx_thread_id INTEGER,
                    database_name VARCHAR(100),
                    trx_started TIMESTAMP,
                    trx_duration INTEGER,
                    trx_state VARCHAR(32),
                    trx_query TEXT,
                    trx_rows_locked INTEGER,
                    trx_tables_locked INTEGER,
                    "user" VARCHAR(64),
                    host VARCHAR(100),
                    status VARCHAR(16) DEFAULT 'active',
                    killed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_long_transactions_instance ON long_transactions(instance_id)"))
            conn.execute(text("CREATE INDEX idx_long_transactions_status ON long_transactions(status)"))
            conn.execute(text("CREATE INDEX idx_long_transactions_created ON long_transactions(created_at)"))
            conn.commit()
            logger.info("  ✓ 创建 long_transactions 表")
    else:
        logger.info("  - long_transactions 表已存在，跳过")


def migration_006():
    """
    迁移 006: 实例表拆分
    
    将 instances 表拆分为：
    - rdb_instances: MySQL/PostgreSQL 实例
    - redis_instances: Redis 实例
    
    同时创建 Redis 专用监控表：
    - redis_slow_logs
    - redis_memory_stats
    - redis_key_analyses
    """
    logger.info("执行迁移 006: 实例表拆分")
    
    # 1. 创建 rdb_instances 表
    if not table_exists('rdb_instances'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE rdb_instances (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    db_type VARCHAR(20) NOT NULL DEFAULT 'mysql',
                    host VARCHAR(100) NOT NULL,
                    port INTEGER DEFAULT 3306,
                    username VARCHAR(50),
                    password_encrypted VARCHAR(255),
                    environment_id INTEGER REFERENCES environments(id),
                    group_id INTEGER REFERENCES instance_groups(id),
                    description VARCHAR(200),
                    status BOOLEAN DEFAULT TRUE,
                    is_rds BOOLEAN DEFAULT FALSE,
                    rds_instance_id VARCHAR(100),
                    aws_region VARCHAR(50),
                    slow_query_threshold INTEGER DEFAULT 3,
                    enable_monitoring BOOLEAN DEFAULT TRUE,
                    last_check_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_rdb_instances_name ON rdb_instances(name)"))
            conn.execute(text("CREATE INDEX idx_rdb_instances_environment ON rdb_instances(environment_id)"))
            conn.execute(text("CREATE INDEX idx_rdb_instances_group ON rdb_instances(group_id)"))
            conn.commit()
            logger.info("  ✓ 创建 rdb_instances 表")
    else:
        logger.info("  - rdb_instances 表已存在，跳过")
    
    # 2. 创建 redis_instances 表
    if not table_exists('redis_instances'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE redis_instances (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    host VARCHAR(100) NOT NULL,
                    port INTEGER DEFAULT 6379,
                    password_encrypted VARCHAR(255),
                    redis_mode VARCHAR(20) DEFAULT 'standalone',
                    redis_db INTEGER DEFAULT 0,
                    cluster_nodes TEXT,
                    sentinel_master_name VARCHAR(100),
                    sentinel_hosts TEXT,
                    environment_id INTEGER REFERENCES environments(id),
                    group_id INTEGER REFERENCES instance_groups(id),
                    description VARCHAR(200),
                    status BOOLEAN DEFAULT TRUE,
                    slowlog_threshold INTEGER DEFAULT 10000,
                    enable_monitoring BOOLEAN DEFAULT TRUE,
                    last_check_time TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_redis_instances_name ON redis_instances(name)"))
            conn.execute(text("CREATE INDEX idx_redis_instances_environment ON redis_instances(environment_id)"))
            conn.execute(text("CREATE INDEX idx_redis_instances_group ON redis_instances(group_id)"))
            conn.commit()
            logger.info("  ✓ 创建 redis_instances 表")
    else:
        logger.info("  - redis_instances 表已存在，跳过")
    
    # 3. 从 instances 表迁移数据
    if table_exists('instances'):
        with engine.connect() as conn:
            # 检查是否已有数据
            rdb_count = conn.execute(text("SELECT COUNT(*) FROM rdb_instances")).scalar()
            redis_count = conn.execute(text("SELECT COUNT(*) FROM redis_instances")).scalar()
            
            if rdb_count == 0 and redis_count == 0:
                # 迁移 MySQL 和 PostgreSQL 实例
                conn.execute(text("""
                    INSERT INTO rdb_instances (
                        id, name, db_type, host, port, username, password_encrypted,
                        environment_id, group_id, description, status,
                        is_rds, rds_instance_id, aws_region,
                        last_check_time, created_at, updated_at
                    )
                    SELECT 
                        id, name, db_type, host, port, username, password_encrypted,
                        environment_id, group_id, description, status,
                        COALESCE(is_rds, FALSE), rds_instance_id, aws_region,
                        last_check_time, created_at, updated_at
                    FROM instances
                    WHERE db_type IN ('mysql', 'postgresql') OR db_type IS NULL
                """))
                rdb_migrated = conn.execute(text("SELECT COUNT(*) FROM rdb_instances")).scalar()
                conn.commit()
                logger.info(f"  ✓ 迁移 {rdb_migrated} 个 RDB 实例到 rdb_instances 表")
                
                # 迁移 Redis 实例
                conn.execute(text("""
                    INSERT INTO redis_instances (
                        id, name, host, port, password_encrypted,
                        redis_mode, redis_db,
                        environment_id, group_id, description, status,
                        last_check_time, created_at, updated_at
                    )
                    SELECT 
                        id, name, host, port, password_encrypted,
                        COALESCE(redis_mode, 'standalone'), COALESCE(redis_db, 0),
                        environment_id, group_id, description, status,
                        last_check_time, created_at, updated_at
                    FROM instances
                    WHERE db_type = 'redis'
                """))
                redis_migrated = conn.execute(text("SELECT COUNT(*) FROM redis_instances")).scalar()
                conn.commit()
                logger.info(f"  ✓ 迁移 {redis_migrated} 个 Redis 实例到 redis_instances 表")
            else:
                logger.info("  - 数据已迁移，跳过数据迁移")
    else:
        logger.info("  - instances 表不存在，跳过数据迁移")
    
    # 4. 更新 monitor_switches 表的外键
    if table_exists('monitor_switches') and not column_exists('monitor_switches', 'rdb_instance_id'):
        with engine.connect() as conn:
            # 添加新外键列
            conn.execute(text("ALTER TABLE monitor_switches ADD COLUMN rdb_instance_id INTEGER REFERENCES rdb_instances(id) ON DELETE CASCADE"))
            # 迁移数据
            conn.execute(text("""
                UPDATE monitor_switches ms
                SET rdb_instance_id = ms.instance_id
                WHERE EXISTS (SELECT 1 FROM rdb_instances ri WHERE ri.id = ms.instance_id)
            """))
            conn.commit()
            logger.info("  ✓ 更新 monitor_switches 表外键")
    
    # 5. 更新 performance_metrics 表的外键
    if table_exists('performance_metrics') and not column_exists('performance_metrics', 'rdb_instance_id'):
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE performance_metrics ADD COLUMN rdb_instance_id INTEGER REFERENCES rdb_instances(id) ON DELETE CASCADE"))
            conn.execute(text("""
                UPDATE performance_metrics pm
                SET rdb_instance_id = pm.instance_id
                WHERE EXISTS (SELECT 1 FROM rdb_instances ri WHERE ri.id = pm.instance_id)
            """))
            conn.commit()
            logger.info("  ✓ 更新 performance_metrics 表外键")
    
    # 6. 更新 slow_queries 表的外键
    if table_exists('slow_queries') and not column_exists('slow_queries', 'rdb_instance_id'):
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE slow_queries ADD COLUMN rdb_instance_id INTEGER REFERENCES rdb_instances(id) ON DELETE CASCADE"))
            conn.execute(text("""
                UPDATE slow_queries sq
                SET rdb_instance_id = sq.instance_id
                WHERE EXISTS (SELECT 1 FROM rdb_instances ri WHERE ri.id = sq.instance_id)
            """))
            conn.commit()
            logger.info("  ✓ 更新 slow_queries 表外键")
    
    # 7. 更新 approval_records 表的外键
    if table_exists('approval_records'):
        with engine.connect() as conn:
            if not column_exists('approval_records', 'rdb_instance_id'):
                conn.execute(text("ALTER TABLE approval_records ADD COLUMN rdb_instance_id INTEGER REFERENCES rdb_instances(id)"))
            if not column_exists('approval_records', 'redis_instance_id'):
                conn.execute(text("ALTER TABLE approval_records ADD COLUMN redis_instance_id INTEGER REFERENCES redis_instances(id)"))
            # 迁移数据
            conn.execute(text("""
                UPDATE approval_records ar
                SET rdb_instance_id = ar.instance_id
                WHERE EXISTS (SELECT 1 FROM rdb_instances ri WHERE ri.id = ar.instance_id)
            """))
            conn.execute(text("""
                UPDATE approval_records ar
                SET redis_instance_id = ar.instance_id
                WHERE EXISTS (SELECT 1 FROM redis_instances ri WHERE ri.id = ar.instance_id)
            """))
            conn.commit()
            logger.info("  ✓ 更新 approval_records 表外键")
    
    # 8. 更新 alert_records 表的外键
    if table_exists('alert_records'):
        with engine.connect() as conn:
            if not column_exists('alert_records', 'rdb_instance_id'):
                conn.execute(text("ALTER TABLE alert_records ADD COLUMN rdb_instance_id INTEGER REFERENCES rdb_instances(id) ON DELETE CASCADE"))
            if not column_exists('alert_records', 'redis_instance_id'):
                conn.execute(text("ALTER TABLE alert_records ADD COLUMN redis_instance_id INTEGER REFERENCES redis_instances(id) ON DELETE CASCADE"))
            # 迁移数据
            conn.execute(text("""
                UPDATE alert_records ar
                SET rdb_instance_id = ar.instance_id
                WHERE EXISTS (SELECT 1 FROM rdb_instances ri WHERE ri.id = ar.instance_id)
            """))
            conn.execute(text("""
                UPDATE alert_records ar
                SET redis_instance_id = ar.instance_id
                WHERE EXISTS (SELECT 1 FROM redis_instances ri WHERE ri.id = ar.instance_id)
            """))
            conn.commit()
            logger.info("  ✓ 更新 alert_records 表外键")
    
    # 9. 更新其他 RDB 相关表的外键
    rdb_tables = [
        ('lock_waits', 'lock_waits'),
        ('replication_status', 'replication_status'),
        ('long_transactions', 'long_transactions'),
        ('inspect_results', 'inspect_results'),
        ('inspection_reports', 'inspection_reports'),
        ('index_analyses', 'index_analyses'),
        ('high_cpu_sqls', 'high_cpu_sqls'),
        ('operation_snapshots', 'operation_snapshots'),
        ('table_schemas', 'table_schemas'),
        ('sql_analysis_history', 'sql_analysis_history'),
    ]
    
    for table_name, log_name in rdb_tables:
        if table_exists(table_name) and not column_exists(table_name, 'rdb_instance_id'):
            with engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN rdb_instance_id INTEGER REFERENCES rdb_instances(id) ON DELETE CASCADE"))
                conn.execute(text(f"""
                    UPDATE {table_name} t
                    SET rdb_instance_id = t.instance_id
                    WHERE EXISTS (SELECT 1 FROM rdb_instances ri WHERE ri.id = t.instance_id)
                """))
                conn.commit()
                logger.info(f"  ✓ 更新 {table_name} 表外键")
    
    # 10. 创建 Redis 慢日志表
    if not table_exists('redis_slow_logs'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE redis_slow_logs (
                    id SERIAL PRIMARY KEY,
                    instance_id INTEGER REFERENCES redis_instances(id) ON DELETE CASCADE NOT NULL,
                    slowlog_id INTEGER,
                    timestamp TIMESTAMP,
                    duration INTEGER,
                    command VARCHAR(500),
                    key VARCHAR(500),
                    args TEXT,
                    client_addr VARCHAR(100),
                    client_name VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_redis_slow_logs_instance ON redis_slow_logs(instance_id)"))
            conn.execute(text("CREATE INDEX idx_redis_slow_logs_timestamp ON redis_slow_logs(timestamp)"))
            conn.commit()
            logger.info("  ✓ 创建 redis_slow_logs 表")
    else:
        logger.info("  - redis_slow_logs 表已存在，跳过")
    
    # 11. 创建 Redis 内存统计表
    if not table_exists('redis_memory_stats'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE redis_memory_stats (
                    id SERIAL PRIMARY KEY,
                    instance_id INTEGER REFERENCES redis_instances(id) ON DELETE CASCADE NOT NULL,
                    collect_time TIMESTAMP NOT NULL,
                    used_memory INTEGER,
                    used_memory_peak INTEGER,
                    used_memory_rss INTEGER,
                    memory_fragmentation_ratio VARCHAR(20),
                    total_keys INTEGER,
                    expires_keys INTEGER,
                    avg_ttl INTEGER,
                    db_sizes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_redis_memory_stats_instance ON redis_memory_stats(instance_id)"))
            conn.execute(text("CREATE INDEX idx_redis_memory_stats_collect_time ON redis_memory_stats(collect_time)"))
            conn.commit()
            logger.info("  ✓ 创建 redis_memory_stats 表")
    else:
        logger.info("  - redis_memory_stats 表已存在，跳过")
    
    # 12. 创建 Redis Key 分析表
    if not table_exists('redis_key_analyses'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE redis_key_analyses (
                    id SERIAL PRIMARY KEY,
                    instance_id INTEGER REFERENCES redis_instances(id) ON DELETE CASCADE NOT NULL,
                    analysis_type VARCHAR(20),
                    key_pattern VARCHAR(200),
                    key_name VARCHAR(500),
                    key_type VARCHAR(20),
                    size INTEGER,
                    ttl INTEGER,
                    element_count INTEGER,
                    access_count INTEGER,
                    risk_level VARCHAR(10),
                    suggestion TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_redis_key_analyses_instance ON redis_key_analyses(instance_id)"))
            conn.execute(text("CREATE INDEX idx_redis_key_analyses_type ON redis_key_analyses(analysis_type)"))
            conn.commit()
            logger.info("  ✓ 创建 redis_key_analyses 表")
    else:
        logger.info("  - redis_key_analyses 表已存在，跳过")
    
    # 13. 创建统一实例视图（向后兼容）
    with engine.connect() as conn:
        conn.execute(text("DROP VIEW IF EXISTS v_all_instances"))
        conn.execute(text("""
            CREATE VIEW v_all_instances AS
            SELECT 
                id, name, db_type, host, port, username, password_encrypted,
                environment_id, group_id, description, status,
                last_check_time, created_at, updated_at,
                NULL AS redis_mode, NULL AS redis_db,
                is_rds, rds_instance_id, aws_region,
                NULL AS slowlog_threshold, slow_query_threshold
            FROM rdb_instances
            UNION ALL
            SELECT 
                id, name, 'redis' AS db_type, host, port, 
                NULL AS username, password_encrypted,
                environment_id, group_id, description, status,
                last_check_time, created_at, updated_at,
                redis_mode, redis_db,
                NULL AS is_rds, NULL AS rds_instance_id, NULL AS aws_region,
                slowlog_threshold, NULL AS slow_query_threshold
            FROM redis_instances
        """))
        conn.commit()
        logger.info("  ✓ 创建 v_all_instances 视图（向后兼容）")


def migration_007():
    """
    迁移 007: 通知系统重构 - 创建新的通道、静默规则、频率限制表
    
    创建表:
    - notification_channels: 统一的通道管理
    - channel_silence_rules: 通道静默规则
    - channel_rate_limits: 通道频率限制
    
    数据迁移:
    - 从 dingtalk_configs 迁移现有钉钉通道数据
    """
    logger.info("执行迁移 007: 通知系统重构")
    
    # 1. 创建 notification_channels 表
    if not table_exists('notification_channels'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE notification_channels (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    channel_type VARCHAR(20) NOT NULL,
                    config JSON NOT NULL,
                    is_enabled BOOLEAN DEFAULT TRUE,
                    description VARCHAR(200),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("CREATE INDEX idx_notification_channels_type ON notification_channels(channel_type)"))
            conn.execute(text("CREATE INDEX idx_notification_channels_enabled ON notification_channels(is_enabled)"))
            conn.commit()
            logger.info("  ✓ 创建 notification_channels 表")
    else:
        logger.info("  - notification_channels 表已存在，跳过")
    
    # 2. 创建 channel_silence_rules 表
    if not table_exists('channel_silence_rules'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE channel_silence_rules (
                    id SERIAL PRIMARY KEY,
                    channel_id INTEGER NOT NULL REFERENCES notification_channels(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    description VARCHAR(200),
                    alert_level VARCHAR(20),
                    instance_type VARCHAR(20),
                    instance_id INTEGER,
                    metric_type VARCHAR(50),
                    silence_type VARCHAR(20) DEFAULT 'once',
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    time_start VARCHAR(10),
                    time_end VARCHAR(10),
                    weekdays JSON,
                    is_enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(channel_id, name)
                )
            """))
            conn.execute(text("CREATE INDEX idx_channel_silence_rules_channel ON channel_silence_rules(channel_id)"))
            conn.execute(text("CREATE INDEX idx_channel_silence_rules_enabled ON channel_silence_rules(is_enabled)"))
            conn.commit()
            logger.info("  ✓ 创建 channel_silence_rules 表")
    else:
        logger.info("  - channel_silence_rules 表已存在，跳过")
    
    # 3. 创建 channel_rate_limits 表
    if not table_exists('channel_rate_limits'):
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE channel_rate_limits (
                    id SERIAL PRIMARY KEY,
                    channel_id INTEGER NOT NULL REFERENCES notification_channels(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    description VARCHAR(200),
                    alert_level VARCHAR(20),
                    instance_type VARCHAR(20),
                    instance_id INTEGER,
                    metric_type VARCHAR(50),
                    limit_window INTEGER DEFAULT 300,
                    max_notifications INTEGER DEFAULT 5,
                    cooldown_period INTEGER DEFAULT 600,
                    is_enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(channel_id, name)
                )
            """))
            conn.execute(text("CREATE INDEX idx_channel_rate_limits_channel ON channel_rate_limits(channel_id)"))
            conn.execute(text("CREATE INDEX idx_channel_rate_limits_enabled ON channel_rate_limits(is_enabled)"))
            conn.commit()
            logger.info("  ✓ 创建 channel_rate_limits 表")
    else:
        logger.info("  - channel_rate_limits 表已存在，跳过")
    
    # 4. 迁移现有钉钉配置数据
    if table_exists('dingtalk_configs') and table_exists('notification_channels'):
        with engine.connect() as conn:
            # 检查是否已有数据
            existing_count = conn.execute(text(
                "SELECT COUNT(*) FROM notification_channels WHERE channel_type = 'dingtalk'"
            )).scalar()
            
            if existing_count == 0:
                # 迁移钉钉配置
                result = conn.execute(text("""
                    SELECT 
                        name,
                        webhook_url,
                        secret,
                        keywords,
                        is_enabled,
                        description,
                        created_at
                    FROM dingtalk_configs
                    WHERE webhook_url IS NOT NULL AND webhook_url != ''
                """))
                
                rows = result.fetchall()
                for row in rows:
                    name, webhook_url, secret, keywords, is_enabled, description, created_at = row
                    
                    # 构建 config JSON
                    config = {"webhook": webhook_url}
                    if secret:
                        config["secret"] = secret
                        config["auth_type"] = "signature"
                    elif keywords:
                        config["keywords"] = keywords.split(",") if isinstance(keywords, str) else keywords
                        config["auth_type"] = "keyword"
                    else:
                        config["auth_type"] = "none"
                    
                    # 插入到新表
                    conn.execute(text("""
                        INSERT INTO notification_channels (name, channel_type, config, is_enabled, description, created_at)
                        VALUES (:name, 'dingtalk', :config::json, :is_enabled, :description, :created_at)
                    """), {
                        "name": name,
                        "config": str(config).replace("'", '"'),
                        "is_enabled": is_enabled if is_enabled is not None else True,
                        "description": description,
                        "created_at": created_at
                    })
                
                conn.commit()
                logger.info(f"  ✓ 迁移 {len(rows)} 条钉钉配置到 notification_channels 表")
            else:
                logger.info("  - 已有钉钉通道数据，跳过迁移")
    else:
        logger.info("  - dingtalk_configs 表不存在或已有通道数据，跳过数据迁移")


def run_migrations():
    """执行所有迁移"""
    logger.info("=" * 50)
    logger.info("开始数据库迁移")
    logger.info("=" * 50)
    
    try:
        migration_001()
        migration_002()
        migration_003()
        migration_004()
        migration_005()
        migration_006()
        migration_007()
        
        logger.info("=" * 50)
        logger.info("所有迁移执行完成")
        logger.info("=" * 50)
        return True
    except Exception as e:
        logger.info(f"迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
