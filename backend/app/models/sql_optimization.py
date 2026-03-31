"""
SQL 优化闭环模型

包含：
- OptimizationSuggestion: 优化建议表
- SlowQueryCollectionTask: 慢SQL采集任务表
- SlowLogFile: 慢日志文件表（用户上传）
- SQLAnalysisHistory: SQL分析历史表（扩展）

数据保留策略：
- 上传文件：30天自动清理
- 分析历史：1年自动清理
"""
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, Float, JSON, DECIMAL, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class SlowLogFile(Base):
    """慢日志文件表 - 用户上传的慢日志文件"""
    __tablename__ = "slow_log_files"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, comment="RDB实例ID")
    
    # 文件信息
    file_name = Column(String(255), nullable=False, comment="原始文件名")
    file_path = Column(String(500), nullable=False, comment="存储路径")
    file_size = Column(Integer, comment="文件大小(字节)")
    file_hash = Column(String(64), comment="文件MD5哈希")
    
    # 解析状态
    parse_status = Column(String(20), default='pending', comment="解析状态: pending/parsing/parsed/failed")
    parse_error = Column(Text, comment="解析错误信息")
    parsed_count = Column(Integer, default=0, comment="解析出的慢查询数量")
    parsed_queries = Column(JSON, comment="解析出的查询列表")
    
    # 分析状态
    analyze_status = Column(String(20), default='pending', comment="分析状态: pending/analyzing/completed/failed")
    analyzed_count = Column(Integer, default=0, comment="已分析的慢查询数量")
    suggestion_count = Column(Integer, default=0, comment="生成的优化建议数量")
    
    # 上传信息
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), comment="上传人")
    
    # 保留策略：30天后自动删除
    expire_at = Column(DateTime, nullable=False, comment="过期时间（上传后30天）")
    
    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    rdb_instance = relationship("RDBInstance", back_populates="slow_log_files")
    uploader = relationship("User", foreign_keys=[uploaded_by])
    analysis_records = relationship("SQLAnalysisHistory", back_populates="source_file", foreign_keys="SQLAnalysisHistory.source_file_id")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expire_at:
            self.expire_at = datetime.now() + timedelta(days=30)


class OptimizationSuggestion(Base):
    """优化建议表"""
    __tablename__ = "sql_optimization_suggestions"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, comment="RDB实例ID")
    database_name = Column(String(100), comment="数据库名")
    
    # 慢SQL信息
    slow_query_id = Column(Integer, ForeignKey("slow_queries.id", ondelete="SET NULL"), comment="慢查询记录ID")
    sql_fingerprint = Column(Text, nullable=False, comment="SQL指纹")
    sql_sample = Column(Text, comment="SQL样例")
    
    # 分析结果
    issues = Column(JSON, comment="问题列表")
    suggestions = Column(JSON, nullable=False, comment="优化建议")
    suggested_sql = Column(Text, comment="建议的SQL（改写后）")
    index_ddl = Column(Text, comment="建议的索引DDL")
    rollback_sql = Column(Text, comment="回滚SQL（如DROP INDEX）")
    
    # 风险评估
    risk_level = Column(String(20), default='low', comment="风险等级: low/medium/high")
    confidence = Column(DECIMAL(3, 2), comment="LLM置信度 0-1")
    expected_improvement = Column(String(100), comment="预期提升")
    
    # 状态管理
    status = Column(String(20), default='pending', index=True, comment="状态: pending/adopted/rejected/expired")
    approval_id = Column(Integer, ForeignKey("approval_records.id", ondelete="SET NULL"), comment="关联的变更申请ID")
    adopted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), comment="采用人")
    adopted_at = Column(DateTime, comment="采用时间")
    
    # 效果验证
    before_avg_time = Column(DECIMAL(10, 3), comment="优化前平均执行时间")
    after_avg_time = Column(DECIMAL(10, 3), comment="优化后平均执行时间")
    actual_improvement = Column(DECIMAL(5, 2), comment="实际提升百分比")
    
    # 分析元数据
    analysis_time = Column(DECIMAL(5, 2), comment="分析耗时（秒）")
    llm_model = Column(String(50), comment="使用的模型")
    table_schemas_used = Column(JSON, comment="分析时使用的表结构")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    rdb_instance = relationship("RDBInstance", back_populates="optimization_suggestions")
    slow_query = relationship("SlowQuery", back_populates="optimization_suggestions")
    approval = relationship("ApprovalRecord", back_populates="optimization_suggestions")
    adopter = relationship("User", foreign_keys=[adopted_by])
    
    __table_args__ = (
        UniqueConstraint('instance_id', 'sql_fingerprint', 'created_at', name='uq_suggestion_instance_fingerprint'),
    )


class SlowQueryCollectionTask(Base):
    """慢SQL采集任务表"""
    __tablename__ = "slow_query_collection_tasks"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("rdb_instances.id", ondelete="CASCADE"), nullable=False, unique=True, comment="RDB实例ID")
    
    # 任务配置
    enabled = Column(Boolean, default=True, index=True, comment="是否启用")
    cron_expression = Column(String(50), default='0 */5 * * *', comment="Cron表达式")
    min_exec_time = Column(DECIMAL(5, 2), default=1.0, comment="最小执行时间阈值（秒）")
    top_n = Column(Integer, default=100, comment="每次采集Top N")
    
    # 自动分析配置
    auto_analyze = Column(Boolean, default=True, comment="是否自动分析")
    analyze_threshold = Column(Integer, default=3, comment="执行次数超过阈值才分析")
    llm_analysis = Column(Boolean, default=True, comment="是否启用LLM分析")
    
    # 统计信息
    last_run_at = Column(DateTime, comment="上次运行时间")
    last_run_status = Column(String(20), comment="上次运行状态")
    last_collected_count = Column(Integer, default=0, comment="上次采集数量")
    total_collected_count = Column(Integer, default=0, comment="总采集数量")
    
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    rdb_instance = relationship("RDBInstance", back_populates="collection_tasks")
