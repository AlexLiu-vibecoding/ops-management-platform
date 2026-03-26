"""
实例模型 - 拆分架构

将原有的 Instance 表拆分为：
- RDBInstance: 关系型数据库实例（MySQL/PostgreSQL）
- RedisInstance: Redis 实例

优势：
1. 字段精确，无冗余
2. 业务隔离清晰
3. 监控指标表结构更贴合各自特性
4. 代码层面更直观，维护成本低
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class RDBType(str, enum.Enum):
    """关系型数据库类型枚举"""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"


class RedisMode(str, enum.Enum):
    """Redis 运行模式枚举"""
    STANDALONE = "standalone"
    CLUSTER = "cluster"
    SENTINEL = "sentinel"


class RDBInstance(Base):
    """
    关系型数据库实例表（MySQL/PostgreSQL）
    
    支持：
    - 慢查询监控
    - 性能指标采集
    - 主从复制监控
    - 锁等待监控
    - SQL 执行与审批
    - 索引分析
    """
    __tablename__ = "rdb_instances"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment="实例名称")
    db_type = Column(SQLEnum(RDBType), default=RDBType.MYSQL, nullable=False, comment="数据库类型: mysql/postgresql")
    host = Column(String(100), nullable=False, comment="主机地址")
    port = Column(Integer, default=3306, comment="端口")
    username = Column(String(50), comment="用户名")
    password_encrypted = Column(String(255), comment="加密后的密码")
    environment_id = Column(Integer, ForeignKey("environments.id"), comment="环境ID")
    group_id = Column(Integer, ForeignKey("instance_groups.id"), comment="分组ID")
    description = Column(String(200), comment="描述")
    status = Column(Boolean, default=True, comment="在线状态")
    
    # AWS RDS 相关字段
    is_rds = Column(Boolean, default=False, comment="是否为 AWS RDS 实例")
    rds_instance_id = Column(String(100), comment="AWS RDS 实例标识符")
    aws_region = Column(String(50), comment="AWS 区域")
    
    # 监控配置
    slow_query_threshold = Column(Integer, default=3, comment="慢查询阈值(秒)")
    enable_monitoring = Column(Boolean, default=True, comment="是否启用监控")
    
    last_check_time = Column(DateTime, comment="最后检测时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    environment = relationship("Environment", back_populates="rdb_instances")
    group = relationship("InstanceGroup", back_populates="rdb_instances")
    monitor_switches = relationship("MonitorSwitch", back_populates="rdb_instance")
    performance_metrics = relationship("PerformanceMetric", back_populates="rdb_instance")
    slow_queries = relationship("SlowQuery", back_populates="rdb_instance")
    snapshots = relationship("OperationSnapshot", back_populates="rdb_instance")
    approval_records = relationship("ApprovalRecord", back_populates="rdb_instance")
    table_schemas = relationship("TableSchema", back_populates="rdb_instance")
    sql_analysis_history = relationship("SQLAnalysisHistory", back_populates="rdb_instance")
    alert_records = relationship("AlertRecord", back_populates="rdb_instance")
    lock_waits = relationship("LockWait", back_populates="rdb_instance")
    replication_status = relationship("ReplicationStatus", back_populates="rdb_instance")
    long_transactions = relationship("LongTransaction", back_populates="rdb_instance")
    inspect_results = relationship("InspectResult", back_populates="rdb_instance")
    inspection_reports = relationship("InspectionReport", back_populates="rdb_instance")
    index_analyses = relationship("IndexAnalysis", back_populates="rdb_instance")
    high_cpu_sqls = relationship("HighCPUSQL", back_populates="rdb_instance")


class RedisInstance(Base):
    """
    Redis 实例表
    
    支持：
    - 慢日志监控（Slow Log）
    - 内存分析
    - 大 Key 扫描
    - 热点 Key 分析
    - 键过期监控
    """
    __tablename__ = "redis_instances"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment="实例名称")
    host = Column(String(100), nullable=False, comment="主机地址")
    port = Column(Integer, default=6379, comment="端口")
    password_encrypted = Column(String(255), comment="加密后的密码")
    
    # Redis 特有字段
    redis_mode = Column(SQLEnum(RedisMode), default=RedisMode.STANDALONE, comment="Redis模式: standalone/cluster/sentinel")
    redis_db = Column(Integer, default=0, comment="Redis数据库索引")
    
    # Cluster 模式配置
    cluster_nodes = Column(Text, comment="集群节点列表(JSON格式)")
    
    # Sentinel 模式配置
    sentinel_master_name = Column(String(100), comment="Sentinel 主节点名称")
    sentinel_hosts = Column(Text, comment="Sentinel 节点列表(JSON格式)")
    
    environment_id = Column(Integer, ForeignKey("environments.id"), comment="环境ID")
    group_id = Column(Integer, ForeignKey("instance_groups.id"), comment="分组ID")
    description = Column(String(200), comment="描述")
    status = Column(Boolean, default=True, comment="在线状态")
    
    # 监控配置
    slowlog_threshold = Column(Integer, default=10000, comment="慢日志阈值(微秒)")
    enable_monitoring = Column(Boolean, default=True, comment="是否启用监控")
    
    last_check_time = Column(DateTime, comment="最后检测时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    environment = relationship("Environment", back_populates="redis_instances")
    group = relationship("InstanceGroup", back_populates="redis_instances")
    approval_records = relationship("ApprovalRecord", back_populates="redis_instance")
    slow_logs = relationship("RedisSlowLog", back_populates="redis_instance")
    memory_stats = relationship("RedisMemoryStats", back_populates="redis_instance")
    key_analyses = relationship("RedisKeyAnalysis", back_populates="redis_instance")
    alert_records = relationship("AlertRecord", back_populates="redis_instance")


class RedisSlowLog(Base):
    """Redis 慢日志记录表"""
    __tablename__ = "redis_slow_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("redis_instances.id", ondelete="CASCADE"), nullable=False, comment="实例ID")
    slowlog_id = Column(Integer, comment="Redis慢日志ID")
    timestamp = Column(DateTime, comment="执行时间")
    duration = Column(Integer, comment="执行耗时(微秒)")
    command = Column(String(500), comment="命令")
    key = Column(String(500), comment="涉及的Key")
    args = Column(Text, comment="命令参数")
    client_addr = Column(String(100), comment="客户端地址")
    client_name = Column(String(100), comment="客户端名称")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关联
    redis_instance = relationship("RedisInstance", back_populates="slow_logs")


class RedisMemoryStats(Base):
    """Redis 内存统计表"""
    __tablename__ = "redis_memory_stats"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("redis_instances.id", ondelete="CASCADE"), nullable=False, comment="实例ID")
    collect_time = Column(DateTime, nullable=False, index=True, comment="采集时间")
    used_memory = Column(Integer, comment="已用内存(字节)")
    used_memory_peak = Column(Integer, comment="内存峰值(字节)")
    used_memory_rss = Column(Integer, comment="RSS内存(字节)")
    memory_fragmentation_ratio = Column(String(20), comment="内存碎片率")
    total_keys = Column(Integer, comment="总Key数")
    expires_keys = Column(Integer, comment="有过期时间的Key数")
    avg_ttl = Column(Integer, comment="平均TTL(毫秒)")
    db_sizes = Column(Text, comment="各数据库大小(JSON格式)")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关联
    redis_instance = relationship("RedisInstance", back_populates="memory_stats")


class RedisKeyAnalysis(Base):
    """Redis Key 分析结果表"""
    __tablename__ = "redis_key_analyses"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("redis_instances.id", ondelete="CASCADE"), nullable=False, comment="实例ID")
    analysis_type = Column(String(20), comment="分析类型: bigkey/hotkey/expire")
    key_pattern = Column(String(200), comment="Key模式")
    key_name = Column(String(500), comment="Key名称")
    key_type = Column(String(20), comment="Key类型: string/hash/list/set/zset/stream")
    size = Column(Integer, comment="大小(字节)")
    ttl = Column(Integer, comment="TTL(秒), -1表示永不过期, -2表示已过期")
    element_count = Column(Integer, comment="元素数量")
    access_count = Column(Integer, comment="访问次数(热点Key)")
    risk_level = Column(String(10), comment="风险等级: low/medium/high")
    suggestion = Column(Text, comment="优化建议")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    
    # 关联
    redis_instance = relationship("RedisInstance", back_populates="key_analyses")
