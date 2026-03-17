"""
监控开关配置API
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    MonitorSwitch, MonitorType, GlobalConfig, 
    Instance, User
)
from app.schemas import (
    MonitorSwitchUpdate, MonitorSwitchResponse, 
    GlobalMonitorSwitchUpdate, MessageResponse
)
from app.deps import get_super_admin, get_current_user

router = APIRouter(prefix="/monitor", tags=["监控配置"])


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
        # 提取监控类型
        key_parts = config.config_key.split("_")
        if len(key_parts) >= 2:
            monitor_type = key_parts[1]
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


@router.get("/switches/instance/{instance_id}", response_model=List[MonitorSwitchResponse])
async def get_instance_monitor_switches(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例级监控开关"""
    # 检查实例是否存在
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
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
    
    return [MonitorSwitchResponse.from_orm(s) for s in switches]


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

@router.get("/alert-rules", response_model=List[dict])
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
    rules: List[dict],
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
