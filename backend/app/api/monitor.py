"""
监控开关配置API
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.models import (
    MonitorSwitch, MonitorType, GlobalConfig,
    RDBInstance, RedisInstance, User, SlowQuery, PerformanceMetric
)
from sqlalchemy import func
from app.schemas import (
    MonitorSwitchUpdate, MonitorSwitchResponse,
    GlobalMonitorSwitchUpdate, MessageResponse
)
from app.deps import get_super_admin, get_current_user

router = APIRouter(prefix="/monitor", tags=["监控配置"])


# ============ 配置模型 ============

class SlowQueryConfig(BaseModel):
    """慢查询监控配置"""
    enabled: bool = Field(True, description="是否启用")
    threshold: float = Field(1.0, ge=0.1, le=3600, description="慢查询阈值(秒)")
    collect_interval: int = Field(300, ge=60, le=3600, description="采集间隔(秒)")
    log_path: Optional[str] = Field(None, description="慢查询日志路径")
    analysis_tool: str = Field("built-in", description="分析工具: built-in/pt-query-digest")
    auto_analyze: bool = Field(True, description="自动分析开关")
    retention_days: int = Field(30, ge=1, le=365, description="数据保留天数")
    top_n: int = Field(10, ge=1, le=100, description="Top N 慢查询数量")


class HighCPUSQLConfig(BaseModel):
    """高CPU SQL监控配置"""
    enabled: bool = Field(True, description="是否启用")
    cpu_threshold: float = Field(80.0, ge=0, le=100, description="CPU使用率阈值(%)")
    memory_threshold: float = Field(80.0, ge=0, le=100, description="内存使用率阈值(%)")
    collect_interval: int = Field(10, ge=1, le=60, description="采集间隔(秒)")
    track_realtime: bool = Field(True, description="实时追踪开关")
    auto_kill: bool = Field(False, description="自动Kill开关(危险)")
    auto_kill_threshold: float = Field(95.0, ge=0, le=100, description="自动Kill阈值(%)")
    max_kill_time: int = Field(300, ge=10, le=3600, description="最长执行时间阈值(秒)")
    alert_cooldown: int = Field(300, ge=60, le=3600, description="告警冷却时间(秒)")


class AlertRuleConfig(BaseModel):
    """告警规则配置"""
    rule_id: str = Field(..., description="规则ID")
    name: str = Field(..., description="规则名称")
    metric_type: str = Field(..., description="指标类型: cpu/memory/disk/connections/qps/slow_query")
    operator: str = Field(">", description="比较操作符: >/</>=/<=/==")
    threshold: float = Field(..., description="阈值")
    severity: str = Field("warning", description="严重级别: info/warning/critical")
    enabled: bool = Field(True, description="是否启用")
    notify_channels: Optional[list[int]] = Field(None, description="通知通道ID列表")
    cooldown: int = Field(300, description="冷却时间(秒)")


class MonitorOverview(BaseModel):
    """监控总览"""
    slow_query: dict
    high_cpu_sql: dict
    performance: dict
    alert_stats: dict


# ============ 监控开关管理 ============

@router.get("/switches/global", response_model=dict)
async def get_global_monitor_switches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取全局监控开关状态"""
    # 从全局配置表获取
    configs = db.query(GlobalConfig).filter(
        GlobalConfig.config_key.like("monitor_%_enabled")
    ).all()
    
    result = {}
    for config in configs:
        # 提取监控类型 (从 monitor_X_enabled 中提取 X)
        # 支持 monitor_slow_query_enabled -> slow_query
        key = config.config_key
        if key.startswith("monitor_") and key.endswith("_enabled"):
            monitor_type = key[8:-8]  # 去掉前缀 "monitor_" 和后缀 "_enabled"
            result[monitor_type] = config.config_value == "true"
    
    # 确保所有类型都有默认值
    for mt in MonitorType:
        if mt.value not in result:
            result[mt.value] = True  # 默认启用
    
    return result


@router.put("/switches/global", response_model=MessageResponse)
async def update_global_monitor_switch(
    switch_data: GlobalMonitorSwitchUpdate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """更新全局监控开关（仅超级管理员）"""
    config_key = f"monitor_{switch_data.monitor_type.value}_enabled"
    config_value = "true" if switch_data.enabled else "false"
    
    # 更新或创建配置
    config = db.query(GlobalConfig).filter(
        GlobalConfig.config_key == config_key
    ).first()
    
    if config:
        config.config_value = config_value
    else:
        config = GlobalConfig(
            config_key=config_key,
            config_value=config_value,
            description=f"{switch_data.monitor_type.value}监控全局开关"
        )
        db.add(config)
    
    db.commit()
    
    return MessageResponse(
        message=f"全局{switch_data.monitor_type.value}监控已{'启用' if switch_data.enabled else '禁用'}"
    )


@router.get("/switches/instance/{instance_id}", response_model=list[MonitorSwitchResponse])
async def get_instance_monitor_switches(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例级监控开关"""
    # 检查实例是否存在（支持 RDB 和 Redis）
    instance = db.query(RDBInstance).filter(RDBInstance.id == instance_id).first()
    if not instance:
        instance = db.query(RedisInstance).filter(RedisInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    # 获取所有开关配置
    switches = db.query(MonitorSwitch).filter(
        MonitorSwitch.instance_id == instance_id
    ).all()
    
    # 如果没有配置，创建默认配置
    if not switches:
        for mt in MonitorType:
            switch = MonitorSwitch(
                instance_id=instance_id,
                monitor_type=mt,
                enabled=True
            )
            db.add(switch)
        db.commit()
        switches = db.query(MonitorSwitch).filter(
            MonitorSwitch.instance_id == instance_id
        ).all()
    
    return [MonitorSwitchResponse.model_validate(s) for s in switches]


@router.put("/switches/instance/{instance_id}/{monitor_type}", response_model=MessageResponse)
async def update_instance_monitor_switch(
    instance_id: int,
    monitor_type: MonitorType,
    switch_data: MonitorSwitchUpdate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """更新实例级监控开关（仅超级管理员）"""
    # 查找开关配置
    switch = db.query(MonitorSwitch).filter(
        MonitorSwitch.instance_id == instance_id,
        MonitorSwitch.monitor_type == monitor_type
    ).first()
    
    if not switch:
        # 创建新配置
        switch = MonitorSwitch(
            instance_id=instance_id,
            monitor_type=monitor_type,
            enabled=switch_data.enabled,
            config=switch_data.config,
            configured_by=current_user.id
        )
        db.add(switch)
    else:
        # 更新配置
        switch.enabled = switch_data.enabled
        if switch_data.config:
            switch.config = switch_data.config
        switch.configured_by = current_user.id
    
    db.commit()
    
    return MessageResponse(
        message=f"实例{monitor_type.value}监控已{'启用' if switch_data.enabled else '禁用'}"
    )


# ============ 监控配置 ============

@router.get("/config", response_model=dict)
async def get_monitor_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取监控配置"""
    configs = db.query(GlobalConfig).filter(
        GlobalConfig.config_key.in_([
            "monitor_collect_interval",
            "slow_query_threshold",
            "slow_query_collect_interval",
            "cpu_threshold",
            "performance_data_retention_days",
            "snapshot_retention_days"
        ])
    ).all()
    
    result = {
        "monitor_collect_interval": 10,
        "slow_query_threshold": 1.0,
        "slow_query_collect_interval": 300,
        "cpu_threshold": 80.0,
        "performance_data_retention_days": 30,
        "snapshot_retention_days": 7
    }
    
    for config in configs:
        try:
            # 尝试转换为数字
            if config.config_key in ["monitor_collect_interval", "slow_query_collect_interval",
                                      "performance_data_retention_days", "snapshot_retention_days"]:
                result[config.config_key] = int(config.config_value)
            else:
                result[config.config_key] = float(config.config_value)
        except:
            result[config.config_key] = config.config_value
    
    return result


@router.put("/config", response_model=MessageResponse)
async def update_monitor_config(
    config_data: dict,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """更新监控配置（仅超级管理员）"""
    for key, value in config_data.items():
        config = db.query(GlobalConfig).filter(
            GlobalConfig.config_key == key
        ).first()
        
        if config:
            config.config_value = str(value)
        else:
            config = GlobalConfig(
                config_key=key,
                config_value=str(value)
            )
            db.add(config)
    
    db.commit()
    
    return MessageResponse(message="监控配置更新成功")


# ============ 告警规则 ============

@router.get("/alert-rules", response_model=list[dict])
async def get_alert_rules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取告警规则"""
    configs = db.query(GlobalConfig).filter(
        GlobalConfig.config_key.like("alert_%")
    ).all()
    
    rules = []
    for config in configs:
        rules.append({
            "key": config.config_key,
            "value": config.config_value,
            "description": config.description
        })
    
    return rules


@router.put("/alert-rules", response_model=MessageResponse)
async def update_alert_rules(
    rules: list[dict],
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """更新告警规则（仅超级管理员）"""
    for rule in rules:
        config = db.query(GlobalConfig).filter(
            GlobalConfig.config_key == rule["key"]
        ).first()
        
        if config:
            config.config_value = str(rule["value"])
            if "description" in rule:
                config.description = rule["description"]
        else:
            config = GlobalConfig(
                config_key=rule["key"],
                config_value=str(rule["value"]),
                description=rule.get("description", "")
            )
            db.add(config)
    
    db.commit()
    
    return MessageResponse(message="告警规则更新成功")


# ============ 慢查询监控配置 ============

@router.get("/slow-query/config", response_model=SlowQueryConfig)
async def get_slow_query_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取慢查询监控配置"""
    configs = db.query(GlobalConfig).filter(
        GlobalConfig.config_key.in_([
            "monitor_slow_query_enabled",
            "slow_query_threshold",
            "slow_query_collect_interval",
            "slow_query_log_path",
            "slow_query_analysis_tool",
            "slow_query_auto_analyze",
            "slow_query_retention_days",
            "slow_query_top_n"
        ])
    ).all()
    
    config_dict = {c.config_key: c.config_value for c in configs}
    
    return SlowQueryConfig(
        enabled=config_dict.get("monitor_slow_query_enabled", "true") == "true",
        threshold=float(config_dict.get("slow_query_threshold", "1.0")),
        collect_interval=int(config_dict.get("slow_query_collect_interval", "300")),
        log_path=config_dict.get("slow_query_log_path"),
        analysis_tool=config_dict.get("slow_query_analysis_tool", "built-in"),
        auto_analyze=config_dict.get("slow_query_auto_analyze", "true") == "true",
        retention_days=int(config_dict.get("slow_query_retention_days", "30")),
        top_n=int(config_dict.get("slow_query_top_n", "10"))
    )


@router.put("/slow-query/config", response_model=MessageResponse)
async def update_slow_query_config(
    config: SlowQueryConfig,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """更新慢查询监控配置（仅超级管理员）"""
    config_items = [
        ("monitor_slow_query_enabled", "true" if config.enabled else "false", "慢查询监控开关"),
        ("slow_query_threshold", str(config.threshold), "慢查询阈值(秒)"),
        ("slow_query_collect_interval", str(config.collect_interval), "慢查询采集间隔(秒)"),
        ("slow_query_log_path", config.log_path or "", "慢查询日志路径"),
        ("slow_query_analysis_tool", config.analysis_tool, "慢查询分析工具"),
        ("slow_query_auto_analyze", "true" if config.auto_analyze else "false", "慢查询自动分析"),
        ("slow_query_retention_days", str(config.retention_days), "慢查询数据保留天数"),
        ("slow_query_top_n", str(config.top_n), "Top N 慢查询数量"),
    ]
    
    for key, value, desc in config_items:
        existing = db.query(GlobalConfig).filter(GlobalConfig.config_key == key).first()
        if existing:
            existing.config_value = value
        else:
            db.add(GlobalConfig(config_key=key, config_value=value, description=desc))
    
    db.commit()
    return MessageResponse(message="慢查询监控配置更新成功")


@router.get("/slow-query/statistics")
async def get_slow_query_statistics(
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取慢查询监控统计数据"""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # 总体统计
    stats = db.query(
        func.count(SlowQuery.id).label('total_count'),
        func.sum(SlowQuery.execution_count).label('total_executions'),
        func.max(SlowQuery.query_time).label('max_time'),
        func.avg(SlowQuery.query_time).label('avg_time')
    ).filter(SlowQuery.last_seen >= start_time).first()
    
    # 按实例统计 (只关联 RDB 实例，因为慢查询只存在于 RDB)
    instance_stats = db.query(
        SlowQuery.instance_id.label('instance_id'),
        RDBInstance.name.label('instance_name'),
        func.count(SlowQuery.id).label('count')
    ).join(RDBInstance, SlowQuery.instance_id == RDBInstance.id).filter(
        SlowQuery.last_seen >= start_time
    ).group_by(SlowQuery.instance_id, RDBInstance.name).all()
    
    return {
        "total_count": stats.total_count or 0,
        "total_executions": stats.total_executions or 0,
        "max_time": float(stats.max_time) if stats.max_time else 0,
        "avg_time": float(stats.avg_time) if stats.avg_time else 0,
        "by_instance": [
            {"instance_id": s.instance_id, "instance_name": s.instance_name, "count": s.count}
            for s in instance_stats
        ]
    }


# ============ 高CPU SQL监控配置 ============

@router.get("/high-cpu/config", response_model=HighCPUSQLConfig)
async def get_high_cpu_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取高CPU SQL监控配置"""
    configs = db.query(GlobalConfig).filter(
        GlobalConfig.config_key.in_([
            "monitor_cpu_sql_enabled",
            "cpu_threshold",
            "memory_threshold",
            "cpu_sql_collect_interval",
            "cpu_sql_track_realtime",
            "cpu_sql_auto_kill",
            "cpu_sql_auto_kill_threshold",
            "cpu_sql_max_kill_time",
            "cpu_sql_alert_cooldown"
        ])
    ).all()
    
    config_dict = {c.config_key: c.config_value for c in configs}
    
    return HighCPUSQLConfig(
        enabled=config_dict.get("monitor_cpu_sql_enabled", "true") == "true",
        cpu_threshold=float(config_dict.get("cpu_threshold", "80.0")),
        memory_threshold=float(config_dict.get("memory_threshold", "80.0")),
        collect_interval=int(config_dict.get("cpu_sql_collect_interval", "10")),
        track_realtime=config_dict.get("cpu_sql_track_realtime", "true") == "true",
        auto_kill=config_dict.get("cpu_sql_auto_kill", "false") == "true",
        auto_kill_threshold=float(config_dict.get("cpu_sql_auto_kill_threshold", "95.0")),
        max_kill_time=int(config_dict.get("cpu_sql_max_kill_time", "300")),
        alert_cooldown=int(config_dict.get("cpu_sql_alert_cooldown", "300"))
    )


@router.put("/high-cpu/config", response_model=MessageResponse)
async def update_high_cpu_config(
    config: HighCPUSQLConfig,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """更新高CPU SQL监控配置（仅超级管理员）"""
    config_items = [
        ("monitor_cpu_sql_enabled", "true" if config.enabled else "false", "高CPU SQL监控开关"),
        ("cpu_threshold", str(config.cpu_threshold), "CPU告警阈值(%)"),
        ("memory_threshold", str(config.memory_threshold), "内存告警阈值(%)"),
        ("cpu_sql_collect_interval", str(config.collect_interval), "高CPU SQL采集间隔(秒)"),
        ("cpu_sql_track_realtime", "true" if config.track_realtime else "false", "实时追踪开关"),
        ("cpu_sql_auto_kill", "true" if config.auto_kill else "false", "自动Kill开关"),
        ("cpu_sql_auto_kill_threshold", str(config.auto_kill_threshold), "自动Kill阈值(%)"),
        ("cpu_sql_max_kill_time", str(config.max_kill_time), "最长执行时间阈值(秒)"),
        ("cpu_sql_alert_cooldown", str(config.alert_cooldown), "告警冷却时间(秒)"),
    ]
    
    for key, value, desc in config_items:
        existing = db.query(GlobalConfig).filter(GlobalConfig.config_key == key).first()
        if existing:
            existing.config_value = value
        else:
            db.add(GlobalConfig(config_key=key, config_value=value, description=desc))
    
    db.commit()
    return MessageResponse(message="高CPU SQL监控配置更新成功")


@router.get("/high-cpu/statistics")
async def get_high_cpu_statistics(
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取高CPU SQL监控统计数据"""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # CPU使用率统计
    cpu_stats = db.query(
        func.max(PerformanceMetric.cpu_usage).label('max_cpu'),
        func.avg(PerformanceMetric.cpu_usage).label('avg_cpu'),
        func.max(PerformanceMetric.memory_usage).label('max_memory'),
        func.avg(PerformanceMetric.memory_usage).label('avg_memory'),
    ).filter(
        PerformanceMetric.collect_time >= start_time
    ).first()
    
    # 按实例统计 (只关联 RDB 实例)
    instance_stats = db.query(
        PerformanceMetric.instance_id.label('instance_id'),
        RDBInstance.name.label('instance_name'),
        func.max(PerformanceMetric.cpu_usage).label('max_cpu'),
        func.avg(PerformanceMetric.cpu_usage).label('avg_cpu'),
        func.max(PerformanceMetric.memory_usage).label('max_memory'),
    ).join(RDBInstance, PerformanceMetric.instance_id == RDBInstance.id).filter(
        PerformanceMetric.collect_time >= start_time
    ).group_by(
        PerformanceMetric.instance_id,
        RDBInstance.name
    ).all()
    
    return {
        "max_cpu": float(cpu_stats.max_cpu) if cpu_stats.max_cpu else 0,
        "avg_cpu": float(cpu_stats.avg_cpu) if cpu_stats.avg_cpu else 0,
        "max_memory": float(cpu_stats.max_memory) if cpu_stats.max_memory else 0,
        "avg_memory": float(cpu_stats.avg_memory) if cpu_stats.avg_memory else 0,
        "by_instance": [
            {
                "instance_id": s.instance_id,
                "instance_name": s.instance_name,
                "max_cpu": float(s.max_cpu) if s.max_cpu else 0,
                "avg_cpu": float(s.avg_cpu) if s.avg_cpu else 0,
                "max_memory": float(s.max_memory) if s.max_memory else 0,
            }
            for s in instance_stats
        ]
    }


# ============ 告警规则高级配置 ============

@router.get("/alert-rules/detail", response_model=list[dict])
async def get_alert_rules_detail(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取告警规则详细配置"""
    # 默认告警规则
    default_rules = [
        {
            "rule_id": "cpu_high",
            "name": "CPU使用率过高",
            "metric_type": "cpu",
            "operator": ">",
            "threshold": 80.0,
            "severity": "warning",
            "enabled": True,
            "notify_channels": [],
            "cooldown": 300
        },
        {
            "rule_id": "cpu_critical",
            "name": "CPU使用率严重过高",
            "metric_type": "cpu",
            "operator": ">",
            "threshold": 95.0,
            "severity": "critical",
            "enabled": True,
            "notify_channels": [],
            "cooldown": 60
        },
        {
            "rule_id": "memory_high",
            "name": "内存使用率过高",
            "metric_type": "memory",
            "operator": ">",
            "threshold": 80.0,
            "severity": "warning",
            "enabled": True,
            "notify_channels": [],
            "cooldown": 300
        },
        {
            "rule_id": "memory_critical",
            "name": "内存使用率严重过高",
            "metric_type": "memory",
            "operator": ">",
            "threshold": 95.0,
            "severity": "critical",
            "enabled": True,
            "notify_channels": [],
            "cooldown": 60
        },
        {
            "rule_id": "slow_query_count",
            "name": "慢查询数量过多",
            "metric_type": "slow_query",
            "operator": ">",
            "threshold": 100.0,
            "severity": "warning",
            "enabled": True,
            "notify_channels": [],
            "cooldown": 600
        },
        {
            "rule_id": "connections_high",
            "name": "连接数过高",
            "metric_type": "connections",
            "operator": ">",
            "threshold": 500.0,
            "severity": "warning",
            "enabled": True,
            "notify_channels": [],
            "cooldown": 300
        },
        {
            "rule_id": "qps_drop",
            "name": "QPS急剧下降",
            "metric_type": "qps",
            "operator": "<",
            "threshold": 10.0,
            "severity": "warning",
            "enabled": True,
            "notify_channels": [],
            "cooldown": 60
        }
    ]
    
    # 从数据库加载已保存的配置
    saved_configs = db.query(GlobalConfig).filter(
        GlobalConfig.config_key.like("alert_rule_%")
    ).all()
    
    saved_dict = {}
    for config in saved_configs:
        import json
        try:
            saved_dict[config.config_key] = json.loads(config.config_value)
        except:
            pass
    
    # 合并配置
    for rule in default_rules:
        key = f"alert_rule_{rule['rule_id']}"
        if key in saved_dict:
            rule.update(saved_dict[key])
    
    return default_rules


@router.put("/alert-rules/detail", response_model=MessageResponse)
async def update_alert_rules_detail(
    rules: list[AlertRuleConfig],
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """更新告警规则详细配置（仅超级管理员）"""
    import json
    
    for rule in rules:
        key = f"alert_rule_{rule.rule_id}"
        value = json.dumps({
            "name": rule.name,
            "metric_type": rule.metric_type,
            "operator": rule.operator,
            "threshold": rule.threshold,
            "severity": rule.severity,
            "enabled": rule.enabled,
            "notify_channels": rule.notify_channels or [],
            "cooldown": rule.cooldown
        })
        
        existing = db.query(GlobalConfig).filter(GlobalConfig.config_key == key).first()
        if existing:
            existing.config_value = value
        else:
            db.add(GlobalConfig(
                config_key=key,
                config_value=value,
                description=f"告警规则: {rule.name}"
            ))
    
    db.commit()
    return MessageResponse(message="告警规则配置更新成功")


# ============ 监控总览 ============

@router.get("/overview", response_model=dict)
async def get_monitor_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取监控总览"""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    
    # 慢查询统计
    slow_query_stats = db.query(
        func.count(SlowQuery.id).label('count'),
        func.max(SlowQuery.query_time).label('max_time')
    ).filter(SlowQuery.last_seen >= start_time).first()
    
    # 性能统计
    perf_stats = db.query(
        func.max(PerformanceMetric.cpu_usage).label('max_cpu'),
        func.max(PerformanceMetric.memory_usage).label('max_memory'),
        func.avg(PerformanceMetric.qps).label('avg_qps')
    ).filter(PerformanceMetric.collect_time >= start_time).first()
    
    # 实例统计 (RDB + Redis)
    total_rdb = db.query(func.count(RDBInstance.id)).scalar() or 0
    total_redis = db.query(func.count(RedisInstance.id)).scalar() or 0
    online_rdb = db.query(func.count(RDBInstance.id)).filter(RDBInstance.status).scalar() or 0
    online_redis = db.query(func.count(RedisInstance.id)).filter(RedisInstance.status).scalar() or 0
    total_instances = total_rdb + total_redis
    online_instances = online_rdb + online_redis
    
    return {
        "slow_query": {
            "total_count": slow_query_stats.count or 0,
            "max_time": float(slow_query_stats.max_time) if slow_query_stats.max_time else 0
        },
        "high_cpu_sql": {
            "max_cpu": float(perf_stats.max_cpu) if perf_stats.max_cpu else 0,
            "max_memory": float(perf_stats.max_memory) if perf_stats.max_memory else 0,
            "avg_qps": float(perf_stats.avg_qps) if perf_stats.avg_qps else 0
        },
        "performance": {
            "max_cpu": float(perf_stats.max_cpu) if perf_stats.max_cpu else 0,
            "max_memory": float(perf_stats.max_memory) if perf_stats.max_memory else 0,
            "avg_qps": float(perf_stats.avg_qps) if perf_stats.avg_qps else 0
        },
        "instances": {
            "total": total_instances or 0,
            "online": online_instances or 0
        }
    }
