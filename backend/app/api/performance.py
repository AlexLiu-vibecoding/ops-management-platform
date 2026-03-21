"""
性能监控API
"""
import random
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import (
    PerformanceMetric, Instance, MonitorSwitch, 
    MonitorType, User
)
from app.schemas import PerformanceMetricResponse, MessageResponse
from app.deps import get_current_user

router = APIRouter(prefix="/performance", tags=["性能监控"])


def generate_mock_metrics(instance_id: int, hours: int = 1):
    """生成模拟的性能数据用于演示"""
    import os
    
    # 仅在开发环境生成模拟数据
    if os.getenv("COZE_PROJECT_ENV", "DEV") != "DEV":
        return []
    
    now = datetime.now()
    metrics = []
    
    # 根据时间范围决定数据点间隔
    if hours <= 1:
        interval = 5  # 5分钟一个点
        points = hours * 12
    elif hours <= 6:
        interval = 10  # 10分钟一个点
        points = hours * 6
    else:
        interval = 30  # 30分钟一个点
        points = hours * 2
    
    # 生成基础值（模拟真实负载）
    base_cpu = random.uniform(20, 40)
    base_memory = random.uniform(40, 60)
    base_connections = random.randint(10, 30)
    base_qps = random.uniform(100, 300)
    
    for i in range(points):
        collect_time = now - timedelta(minutes=interval * (points - i - 1))
        
        # 添加随机波动
        cpu_usage = max(5, min(95, base_cpu + random.uniform(-15, 15) + random.uniform(-5, 5) * (i % 10 / 10)))
        memory_usage = max(20, min(90, base_memory + random.uniform(-10, 10)))
        connections = max(5, int(base_connections + random.randint(-10, 15)))
        qps = max(10, base_qps + random.uniform(-50, 80))
        
        metrics.append({
            "id": -i,  # 负数表示模拟数据
            "instance_id": instance_id,
            "collect_time": collect_time.isoformat(),
            "cpu_usage": round(cpu_usage, 2),
            "memory_usage": round(memory_usage, 2),
            "disk_io_read": round(random.uniform(0, 100), 2),
            "disk_io_write": round(random.uniform(0, 50), 2),
            "connections": connections,
            "qps": round(qps, 2),
            "tps": round(qps * random.uniform(0.1, 0.3), 2),
            "lock_wait_count": random.randint(0, 5)
        })
    
    return metrics


@router.get("/{instance_id}/current", response_model=dict)
async def get_current_performance(
    instance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例当前性能指标"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    # 检查监控开关
    switch = db.query(MonitorSwitch).filter(
        MonitorSwitch.instance_id == instance_id,
        MonitorSwitch.monitor_type == MonitorType.PERFORMANCE
    ).first()
    
    if not switch or not switch.enabled:
        return {
            "enabled": False,
            "message": "该实例的性能监控已禁用"
        }
    
    # 获取最新性能数据
    latest = db.query(PerformanceMetric).filter(
        PerformanceMetric.instance_id == instance_id
    ).order_by(PerformanceMetric.collect_time.desc()).first()
    
    if not latest:
        return {
            "enabled": True,
            "data": None,
            "message": "暂无性能数据"
        }
    
    return {
        "enabled": True,
        "data": PerformanceMetricResponse.from_orm(latest),
        "collect_time": latest.collect_time
    }


@router.get("/{instance_id}/history")
async def get_performance_history(
    instance_id: int,
    hours: int = 1,
    metric_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例历史性能指标"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    # 计算时间范围
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # 查询历史数据
    query = db.query(PerformanceMetric).filter(
        PerformanceMetric.instance_id == instance_id,
        PerformanceMetric.collect_time >= start_time,
        PerformanceMetric.collect_time <= end_time
    ).order_by(PerformanceMetric.collect_time)
    
    metrics = query.all()
    
    # 如果没有数据，生成模拟数据用于演示
    if not metrics:
        metrics = generate_mock_metrics(instance_id, hours)
    
    return {
        "total": len(metrics),
        "items": [PerformanceMetricResponse.from_orm(m) if hasattr(m, 'id') else m for m in metrics]
    }


@router.get("/{instance_id}/statistics", response_model=dict)
async def get_performance_statistics(
    instance_id: int,
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取性能统计数据（最大值、最小值、平均值）"""
    instance = db.query(Instance).filter(Instance.id == instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instance not found"
        )
    
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=hours)
    
    # 统计查询
    stats = db.query(
        func.max(PerformanceMetric.cpu_usage).label('max_cpu'),
        func.min(PerformanceMetric.cpu_usage).label('min_cpu'),
        func.avg(PerformanceMetric.cpu_usage).label('avg_cpu'),
        func.max(PerformanceMetric.memory_usage).label('max_memory'),
        func.min(PerformanceMetric.memory_usage).label('min_memory'),
        func.avg(PerformanceMetric.memory_usage).label('avg_memory'),
        func.max(PerformanceMetric.connections).label('max_connections'),
        func.min(PerformanceMetric.connections).label('min_connections'),
        func.avg(PerformanceMetric.connections).label('avg_connections'),
        func.max(PerformanceMetric.qps).label('max_qps'),
        func.min(PerformanceMetric.qps).label('min_qps'),
        func.avg(PerformanceMetric.qps).label('avg_qps'),
    ).filter(
        PerformanceMetric.instance_id == instance_id,
        PerformanceMetric.collect_time >= start_time
    ).first()
    
    # 如果没有真实数据，从模拟数据计算统计
    if not stats or stats.max_cpu is None:
        mock_data = generate_mock_metrics(instance_id, hours)
        if mock_data:
            cpu_values = [m['cpu_usage'] for m in mock_data]
            memory_values = [m['memory_usage'] for m in mock_data]
            conn_values = [m['connections'] for m in mock_data]
            qps_values = [m['qps'] for m in mock_data]
            
            return {
                "cpu_usage": {
                    "max": max(cpu_values),
                    "min": min(cpu_values),
                    "avg": sum(cpu_values) / len(cpu_values)
                },
                "memory_usage": {
                    "max": max(memory_values),
                    "min": min(memory_values),
                    "avg": sum(memory_values) / len(memory_values)
                },
                "connections": {
                    "max": max(conn_values),
                    "min": min(conn_values),
                    "avg": sum(conn_values) / len(conn_values)
                },
                "qps": {
                    "max": max(qps_values),
                    "min": min(qps_values),
                    "avg": sum(qps_values) / len(qps_values)
                }
            }
    
    return {
        "cpu_usage": {
            "max": float(stats.max_cpu) if stats.max_cpu else 0,
            "min": float(stats.min_cpu) if stats.min_cpu else 0,
            "avg": float(stats.avg_cpu) if stats.avg_cpu else 0
        },
        "memory_usage": {
            "max": float(stats.max_memory) if stats.max_memory else 0,
            "min": float(stats.min_memory) if stats.min_memory else 0,
            "avg": float(stats.avg_memory) if stats.avg_memory else 0
        },
        "connections": {
            "max": int(stats.max_connections) if stats.max_connections else 0,
            "min": int(stats.min_connections) if stats.min_connections else 0,
            "avg": float(stats.avg_connections) if stats.avg_connections else 0
        },
        "qps": {
            "max": float(stats.max_qps) if stats.max_qps else 0,
            "min": float(stats.min_qps) if stats.min_qps else 0,
            "avg": float(stats.avg_qps) if stats.avg_qps else 0
        }
    }


@router.get("/overview", response_model=List[dict])
async def get_performance_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有实例的性能概览"""
    # 获取所有在线实例
    instances = db.query(Instance).filter(Instance.status == True).all()
    
    result = []
    for instance in instances:
        # 检查监控开关
        switch = db.query(MonitorSwitch).filter(
            MonitorSwitch.instance_id == instance.id,
            MonitorSwitch.monitor_type == MonitorType.PERFORMANCE
        ).first()
        
        enabled = switch and switch.enabled if switch else True
        
        # 获取最新性能数据
        latest = db.query(PerformanceMetric).filter(
            PerformanceMetric.instance_id == instance.id
        ).order_by(PerformanceMetric.collect_time.desc()).first()
        
        result.append({
            "instance_id": instance.id,
            "instance_name": instance.name,
            "environment": instance.environment.name if instance.environment else None,
            "environment_color": instance.environment.color if instance.environment else None,
            "monitor_enabled": enabled,
            "current_cpu": latest.cpu_usage if latest else None,
            "current_memory": latest.memory_usage if latest else None,
            "current_connections": latest.connections if latest else None,
            "current_qps": latest.qps if latest else None,
            "collect_time": latest.collect_time if latest else None
        })
    
    return result
