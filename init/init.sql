-- 初始化数据库脚本
-- 创建数据库
CREATE DATABASE IF NOT EXISTS mysql_platform 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE mysql_platform;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    real_name VARCHAR(50),
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(20),
    role ENUM('super_admin', 'approval_admin', 'operator', 'readonly') DEFAULT 'readonly',
    status BOOLEAN DEFAULT TRUE,
    failed_login_count INT DEFAULT 0,
    locked_until DATETIME,
    last_login_time DATETIME,
    last_login_ip VARCHAR(50),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';

-- 环境表
CREATE TABLE IF NOT EXISTS environments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    code VARCHAR(20) NOT NULL UNIQUE,
    color VARCHAR(10) DEFAULT '#52C41A',
    description VARCHAR(200),
    require_approval BOOLEAN DEFAULT TRUE,
    status BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='环境表';

-- 用户-环境关联表
CREATE TABLE IF NOT EXISTS user_environments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    environment_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (environment_id) REFERENCES environments(id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_env (user_id, environment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户-环境关联表';

-- 实例分组表
CREATE TABLE IF NOT EXISTS instance_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(200),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='实例分组表';

-- 实例表
CREATE TABLE IF NOT EXISTS instances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    host VARCHAR(100) NOT NULL,
    port INT DEFAULT 3306,
    username VARCHAR(50) NOT NULL,
    password_encrypted VARCHAR(255) NOT NULL,
    environment_id INT,
    group_id INT,
    description VARCHAR(200),
    status BOOLEAN DEFAULT TRUE,
    last_check_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (environment_id) REFERENCES environments(id) ON DELETE SET NULL,
    FOREIGN KEY (group_id) REFERENCES instance_groups(id) ON DELETE SET NULL,
    INDEX idx_name (name),
    INDEX idx_environment (environment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='MySQL实例表';

-- 监控类型枚举值注释
-- slow_query: 慢查询监控
-- cpu_sql: 高CPU SQL监控
-- performance: 性能监控
-- inspection: 实例巡检

-- 监控开关表
CREATE TABLE IF NOT EXISTS monitor_switches (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instance_id INT NOT NULL,
    monitor_type ENUM('slow_query', 'cpu_sql', 'performance', 'inspection') NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    config JSON,
    configured_by INT,
    configured_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE,
    FOREIGN KEY (configured_by) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE KEY uk_instance_monitor (instance_id, monitor_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='监控开关表';

-- 全局配置表
CREATE TABLE IF NOT EXISTS global_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value VARCHAR(500) NOT NULL,
    description VARCHAR(200),
    updated_by INT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='全局配置表';

-- 钉钉通道表
CREATE TABLE IF NOT EXISTS dingtalk_channels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    webhook_encrypted VARCHAR(500) NOT NULL,
    description VARCHAR(200),
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='钉钉通道表';

-- 通知绑定表
CREATE TABLE IF NOT EXISTS notification_bindings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    channel_id INT NOT NULL,
    notification_type VARCHAR(50) NOT NULL COMMENT 'approval/alert/operation',
    environment_id INT,
    instance_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES dingtalk_channels(id) ON DELETE CASCADE,
    FOREIGN KEY (environment_id) REFERENCES environments(id) ON DELETE CASCADE,
    FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='通知绑定表';

-- 审批记录表
CREATE TABLE IF NOT EXISTS approval_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    change_type VARCHAR(50) NOT NULL COMMENT 'DDL/DML/OPERATION/CUSTOM',
    instance_id INT,
    database_name VARCHAR(100),
    sql_content TEXT NOT NULL,
    sql_risk_level VARCHAR(20) COMMENT 'low/medium/high/critical',
    environment_id INT,
    requester_id INT NOT NULL,
    status ENUM('pending', 'approved', 'rejected', 'executed', 'failed') DEFAULT 'pending',
    approver_id INT,
    approve_time DATETIME,
    approve_comment VARCHAR(500),
    execute_time DATETIME,
    execute_result TEXT,
    scheduled_time DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE SET NULL,
    FOREIGN KEY (environment_id) REFERENCES environments(id) ON DELETE SET NULL,
    FOREIGN KEY (requester_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (approver_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_status (status),
    INDEX idx_requester (requester_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审批记录表';

-- 性能监控数据表
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instance_id INT NOT NULL,
    collect_time DATETIME NOT NULL,
    cpu_usage FLOAT,
    memory_usage FLOAT,
    disk_io_read FLOAT,
    disk_io_write FLOAT,
    connections INT,
    qps FLOAT,
    tps FLOAT,
    lock_wait_count INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE,
    INDEX idx_instance_time (instance_id, collect_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='性能监控数据表';

-- 慢查询记录表
CREATE TABLE IF NOT EXISTS slow_queries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instance_id INT NOT NULL,
    database_name VARCHAR(100),
    sql_fingerprint VARCHAR(500) NOT NULL,
    sql_sample TEXT,
    query_time FLOAT,
    lock_time FLOAT,
    rows_sent INT,
    rows_examined INT,
    execution_count INT DEFAULT 1,
    first_seen DATETIME,
    last_seen DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE,
    INDEX idx_instance (instance_id),
    INDEX idx_fingerprint (sql_fingerprint(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='慢查询记录表';

-- 高CPU SQL记录表
CREATE TABLE IF NOT EXISTS high_cpu_sqls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instance_id INT NOT NULL,
    process_id INT,
    sql_content TEXT,
    cpu_usage FLOAT,
    execution_time FLOAT,
    status VARCHAR(20) COMMENT 'running/killed',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='高CPU SQL记录表';

-- 操作快照表
CREATE TABLE IF NOT EXISTS operation_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instance_id INT NOT NULL,
    database_name VARCHAR(100),
    table_name VARCHAR(100),
    operation_type VARCHAR(20) COMMENT 'UPDATE/DELETE',
    original_sql TEXT,
    snapshot_data TEXT COMMENT '加密存储',
    row_count INT,
    approval_id INT,
    status VARCHAR(20) DEFAULT 'active' COMMENT 'active/used/expired',
    expire_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE,
    FOREIGN KEY (approval_id) REFERENCES approval_records(id) ON DELETE SET NULL,
    INDEX idx_instance (instance_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='操作快照表';

-- 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    username VARCHAR(50),
    instance_id INT,
    instance_name VARCHAR(100),
    environment_id INT,
    environment_name VARCHAR(50),
    operation_type VARCHAR(50) NOT NULL,
    operation_detail TEXT,
    request_ip VARCHAR(50),
    request_method VARCHAR(10),
    request_path VARCHAR(200),
    request_params TEXT,
    response_code INT,
    response_message VARCHAR(500),
    execution_time FLOAT COMMENT '毫秒',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user (user_id),
    INDEX idx_instance (instance_id),
    INDEX idx_time (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审计日志表';

-- 登录日志表
CREATE TABLE IF NOT EXISTS login_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    username VARCHAR(50),
    login_ip VARCHAR(50),
    login_device VARCHAR(200),
    login_status VARCHAR(20) COMMENT 'success/failed',
    failure_reason VARCHAR(200),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user (user_id),
    INDEX idx_time (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='登录日志表';

-- 巡检报告表
CREATE TABLE IF NOT EXISTS inspection_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instance_id INT NOT NULL,
    report_type VARCHAR(20) DEFAULT 'daily' COMMENT 'daily/weekly/monthly',
    status VARCHAR(20) DEFAULT 'pending' COMMENT 'pending/completed/failed',
    summary JSON,
    details JSON,
    risk_count_high INT DEFAULT 0,
    risk_count_medium INT DEFAULT 0,
    risk_count_low INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='巡检报告表';

-- 索引分析表
CREATE TABLE IF NOT EXISTS index_analyses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    instance_id INT NOT NULL,
    database_name VARCHAR(100),
    table_name VARCHAR(100),
    index_name VARCHAR(100),
    index_type VARCHAR(50),
    columns VARCHAR(500),
    issue_type VARCHAR(50) COMMENT 'redundant/unused/missing',
    risk_level VARCHAR(20) COMMENT 'high/medium/low',
    suggestion TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (instance_id) REFERENCES instances(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='索引分析表';

-- 插入默认环境数据
INSERT INTO environments (name, code, color, description, require_approval) VALUES
('开发环境', 'development', '#52C41A', '开发测试使用', FALSE),
('测试环境', 'testing', '#1890FF', '集成测试环境', FALSE),
('预发环境', 'staging', '#FA8C16', '预发布环境', TRUE),
('生产环境', 'production', '#FF4D4F', '生产环境', TRUE);

-- 插入默认全局配置
INSERT INTO global_configs (config_key, config_value, description) VALUES
('monitor_slow_query_enabled', 'true', '慢查询监控全局开关'),
('monitor_cpu_sql_enabled', 'true', '高CPU SQL监控全局开关'),
('monitor_performance_enabled', 'true', '性能监控全局开关'),
('monitor_inspection_enabled', 'true', '实例巡检全局开关'),
('monitor_collect_interval', '10', '性能监控采集间隔(秒)'),
('slow_query_threshold', '1.0', '慢查询阈值(秒)'),
('cpu_threshold', '80.0', 'CPU使用率告警阈值(%)'),
('memory_threshold', '80.0', '内存使用率告警阈值(%)'),
('performance_data_retention_days', '30', '性能数据保留天数'),
('snapshot_retention_days', '7', '快照保留天数');
