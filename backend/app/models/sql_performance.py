"""
SQL 性能记录模型

存储 SQL 执行的性能指标，用于前后对比分析。
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class SQLPerformanceRecord(Base):
    """SQL 性能记录"""
    __tablename__ = "sql_performance_records"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 基本信息
    instance_id = Column(Integer, ForeignKey("instances.id"), nullable=False, index=True)
    sql_text = Column(Text, nullable=False, comment="SQL 语句")
    sql_hash = Column(String(64), nullable=False, index=True, comment="SQL Hash（用于去重）")
    
    # 版本标识
    version = Column(String(50), nullable=False, comment="版本：original 或 optimized")
    version_description = Column(String(255), comment="版本描述")
    
    # 执行指标
    execution_time_ms = Column(Float, comment="执行时间（毫秒）")
    rows_scanned = Column(Integer, comment="扫描行数")
    rows_returned = Column(Integer, comment="返回行数")
    buffer_pool_reads = Column(Integer, comment="缓冲池读取次数")
    disk_reads = Column(Integer, comment="磁盘读取次数")
    
    # CPU 和 IO 指标
    cpu_time_ms = Column(Float, comment="CPU 时间（毫秒）")
    io_time_ms = Column(Float, comment="IO 时间（毫秒）")
    memory_mb = Column(Float, comment="内存使用（MB）")
    
    # 执行计划
    execution_plan = Column(JSON, comment="EXPLAIN 执行计划")
    execution_plan_json = Column(Text, comment="EXPLAIN JSON 格式")
    
    # 元数据
    user_id = Column(Integer, ForeignKey("users.id"), comment="执行用户")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关联
    instance = relationship("Instance", back_populates="performance_records")
    user = relationship("User", backref="performance_records")
    comparison_source = relationship("SQLPerformanceComparison", foreign_keys="SQLPerformanceComparison.source_id", back_populates="source_record")
    comparison_target = relationship("SQLPerformanceComparison", foreign_keys="SQLPerformanceComparison.target_id", back_populates="target_record")


class SQLPerformanceComparison(Base):
    """SQL 性能对比记录"""
    __tablename__ = "sql_performance_comparisons"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # 对比的两个版本
    source_id = Column(Integer, ForeignKey("sql_performance_records.id"), nullable=False, comment="优化前记录 ID")
    target_id = Column(Integer, ForeignKey("sql_performance_records.id"), nullable=False, comment="优化后记录 ID")
    
    # 对比结果
    execution_time_improvement = Column(Float, comment="执行时间改善百分比")
    rows_scanned_improvement = Column(Float, comment="扫描行数改善百分比")
    cpu_time_improvement = Column(Float, comment="CPU 时间改善百分比")
    io_time_improvement = Column(Float, comment="IO 时间改善百分比")
    overall_improvement = Column(Float, comment="综合改善百分比")
    
    # 对比分析
    analysis = Column(Text, comment="分析文本")
    recommendations = Column(JSON, comment="优化建议")
    
    # 报告数据
    report_data = Column(JSON, comment="可视化报告数据")
    
    # 元数据
    user_id = Column(Integer, ForeignKey("users.id"), comment="创建用户")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关联
    source_record = relationship("SQLPerformanceRecord", foreign_keys=[source_id], back_populates="comparison_source")
    target_record = relationship("SQLPerformanceRecord", foreign_keys=[target_id], back_populates="comparison_target")
    user = relationship("User", backref="comparisons")
