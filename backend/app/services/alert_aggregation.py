"""
告警聚合与升级服务

功能：
1. 告警聚合 - 将相似告警按规则聚合，减少通知风暴
2. 告警静默 - 在特定时间段内静默告警
3. 告警升级 - 超时未处理的告警自动升级

作者：OpsCenter Team
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models import (
    AlertRecord, AlertAggregationRule, AlertAggregation,
    AlertSilenceRule, AlertEscalationRule
)

logger = logging.getLogger(__name__)


class AlertAggregationService:
    """告警聚合服务"""
    
    @staticmethod
    def should_aggregate_alert(db: Session, alert: AlertRecord) -> Optional[AlertAggregationRule]:
        """
        检查告警是否应该被聚合
        
        Args:
            db: 数据库会话
            alert: 告警记录
            
        Returns:
            匹配的聚合规则，如果不匹配则返回 None
        """
        # 查询启用的聚合规则，按优先级降序
        rules = db.query(AlertAggregationRule).filter(
            AlertAggregationRule.is_enabled == True
        ).order_by(AlertAggregationRule.priority.desc()).all()
        
        for rule in rules:
            # 检查指标类型匹配
            if rule.metric_type and rule.metric_type != alert.metric_type:
                continue
            
            # 检查告警级别匹配
            if rule.alert_level and rule.alert_level != alert.alert_level:
                continue
            
            # 检查实例匹配
            if rule.rdb_instance_id and rule.rdb_instance_id != alert.rdb_instance_id:
                continue
            if rule.redis_instance_id and rule.redis_instance_id != alert.redis_instance_id:
                continue
            
            return rule
        
        return None
    
    @staticmethod
    def aggregate_alert(db: Session, alert: AlertRecord, rule: AlertAggregationRule):
        """
        聚合告警
        
        Args:
            db: 数据库会话
            alert: 新告警
            rule: 聚合规则
        """
        # 计算聚合窗口的开始时间
        window_start = alert.created_at - timedelta(seconds=rule.aggregation_window)
        
        # 查找是否已有活跃的聚合记录
        existing_agg = db.query(AlertAggregation).filter(
            and_(
                AlertAggregation.rule_id == rule.id,
                AlertAggregation.metric_type == alert.metric_type,
                AlertAggregation.alert_level == alert.alert_level,
                AlertAggregation.rdb_instance_id == alert.rdb_instance_id,
                AlertAggregation.redis_instance_id == alert.redis_instance_id,
                AlertAggregation.started_at >= window_start,
                AlertAggregation.ended_at == None  # 未结束的聚合
            )
        ).first()
        
        if existing_agg:
            # 更新现有聚合
            existing_agg.alert_count += 1
            if existing_agg.alert_ids is None:
                existing_agg.alert_ids = []
            existing_agg.alert_ids.append(alert.id)
            existing_agg.aggregated_content = AlertAggregationService._build_aggregated_content(
                db, existing_agg, rule
            )
            
            # 检查是否达到发送条件
            if existing_agg.alert_count >= rule.min_alert_count and not existing_agg.notification_sent:
                AlertAggregationService._send_aggregated_notification(db, existing_agg, rule)
                existing_agg.notification_sent = True
        else:
            # 创建新聚合
            new_agg = AlertAggregation(
                rule_id=rule.id,
                metric_type=alert.metric_type,
                alert_level=alert.alert_level,
                rdb_instance_id=alert.rdb_instance_id,
                redis_instance_id=alert.redis_instance_id,
                alert_count=1,
                alert_ids=[alert.id],
                started_at=alert.created_at,
                notification_sent=False
            )
            db.add(new_agg)
        
        db.commit()
    
    @staticmethod
    def _build_aggregated_content(db: Session, agg: AlertAggregation, rule: AlertAggregationRule) -> str:
        """构建聚合后的内容"""
        if rule.aggregation_method == "summary":
            # 摘要模式：汇总告警
            return f"共 {agg.alert_count} 条 {agg.alert_level} 级别 {agg.metric_type} 告警"
        else:
            # 计数模式：简单计数
            return f"{agg.alert_count} 条告警已聚合"
    
    @staticmethod
    def _send_aggregated_notification(db: Session, agg: AlertAggregation, rule: AlertAggregationRule):
        """发送聚合后的告警通知"""
        try:
            from app.services.notification import notification_service
            
            # 创建一个临时告警记录用于通知
            temp_alert = AlertRecord(
                id=0,  # 临时ID
                rdb_instance_id=agg.rdb_instance_id,
                redis_instance_id=agg.redis_instance_id,
                metric_type=agg.metric_type,
                alert_level=agg.alert_level,
                alert_title=f"[聚合告警] {agg.alert_count} 条 {agg.metric_type} 告警",
                alert_content=agg.aggregated_content,
                status="pending",
                notification_sent=False,
                created_at=agg.started_at
            )
            
            # 发送通知（不实际保存这个临时告警）
            asyncio.create_task(notification_service.send_alert_notification(db, temp_alert, is_aggregated=True))
            
            logger.info(f"聚合告警通知已发送: rule_id={rule.id}, count={agg.alert_count}")
        except Exception as e:
            logger.error(f"发送聚合告警通知失败: {e}")
    
    @staticmethod
    def process_new_alert(db: Session, alert: AlertRecord):
        """
        处理新告警的主入口
        
        Args:
            db: 数据库会话
            alert: 新告警
        """
        # 1. 检查是否应该聚合
        rule = AlertAggregationService.should_aggregate_alert(db, alert)
        if rule:
            AlertAggregationService.aggregate_alert(db, alert, rule)
            return True
        
        return False


class AlertSilenceService:
    """告警静默服务"""
    
    @staticmethod
    def check_silence(db: Session, alert: AlertRecord) -> bool:
        """
        检查告警是否应该被静默
        
        Args:
            db: 数据库会话
            alert: 告警记录
            
        Returns:
            True 表示应该静默，False 表示不应该
        """
        now = datetime.now()
        
        # 查询启用的静默规则
        rules = db.query(AlertSilenceRule).filter(
            AlertSilenceRule.is_enabled == True
        ).all()
        
        for rule in rules:
            # 检查指标类型匹配
            if rule.metric_type and rule.metric_type != alert.metric_type:
                continue
            
            # 检查告警级别匹配
            if rule.alert_level and rule.alert_level != alert.alert_level:
                continue
            
            # 检查实例匹配
            if rule.rdb_instance_id and rule.rdb_instance_id != alert.rdb_instance_id:
                continue
            if rule.redis_instance_id and rule.redis_instance_id != alert.redis_instance_id:
                continue
            
            # 检查时间窗口
            if AlertSilenceService._is_in_time_window(now, rule):
                logger.info(f"告警 {alert.id} 命中静默规则: {rule.name}")
                return True
        
        return False
    
    @staticmethod
    def _is_in_time_window(now: datetime, rule: AlertSilenceRule) -> bool:
        """检查当前时间是否在规则的时间窗口内"""
        # 检查日期范围
        if rule.start_time and now < rule.start_time:
            return False
        if rule.end_time and now > rule.end_time:
            return False
        
        # 检查重复类型
        if rule.recurrence_type == "once":
            # 一次性：检查开始和结束时间
            if rule.start_time and rule.end_time:
                return rule.start_time <= now <= rule.end_time
            return True
        elif rule.recurrence_type == "daily":
            # 每日重复：检查时间部分
            if rule.start_time and rule.end_time:
                time_part = now.time()
                start_time = rule.start_time.time()
                end_time = rule.end_time.time()
                return start_time <= time_part <= end_time
            return True
        elif rule.recurrence_type == "weekly":
            # 每周重复：检查星期和时间
            weekday = now.weekday()  # 0=周一
            if hasattr(rule, 'weekdays') and rule.weekdays:
                if weekday not in rule.weekdays:
                    return False
            
            if rule.start_time and rule.end_time:
                time_part = now.time()
                start_time = rule.start_time.time()
                end_time = rule.end_time.time()
                return start_time <= time_part <= end_time
            return True
        
        return False


class AlertEscalationService:
    """告警升级服务"""
    
    @staticmethod
    def check_escalation(db: Session, alert: AlertRecord):
        """
        检查告警是否应该升级
        
        Args:
            db: 数据库会话
            alert: 告警记录
        """
        if alert.status != "pending":
            return  # 只有待处理的告警才会升级
        
        now = datetime.now()
        elapsed = (now - alert.created_at).total_seconds() / 60  # 分钟
        
        # 查询匹配的升级规则
        rules = db.query(AlertEscalationRule).filter(
            and_(
                AlertEscalationRule.is_enabled == True,
                or_(
                    AlertEscalationRule.alert_level == alert.alert_level,
                    AlertEscalationRule.alert_level == None
                )
            )
        ).order_by(AlertEscalationRule.priority.desc()).all()
        
        for rule in rules:
            if elapsed >= rule.trigger_minutes:
                AlertEscalationService._escalate_alert(db, alert, rule)
                break
    
    @staticmethod
    def _escalate_alert(db: Session, alert: AlertRecord, rule: AlertEscalationRule):
        """执行告警升级"""
        logger.info(f"告警 {alert.id} 升级: {rule.name}")
        
        # 更新告警级别
        if rule.escalation_level:
            alert.alert_level = rule.escalation_level
        
        # 更新告警标题，标记为已升级
        if not alert.alert_title.startswith("[已升级]"):
            alert.alert_title = f"[已升级] {alert.alert_title}"
        
        # 发送升级通知
        if rule.escalation_notification:
            AlertEscalationService._send_escalation_notification(db, alert, rule)
        
        db.commit()
    
    @staticmethod
    def _send_escalation_notification(db: Session, alert: AlertRecord, rule: AlertEscalationRule):
        """发送升级通知"""
        try:
            from app.services.notification import notification_service
            
            # 使用额外的通知通道
            if rule.additional_channel_id:
                # TODO: 实现特定通道的通知发送
                pass
            
            # 发送标准告警通知（可能会去重）
            asyncio.create_task(notification_service.send_alert_notification(db, alert))
            
            logger.info(f"升级通知已发送: alert_id={alert.id}, rule={rule.name}")
        except Exception as e:
            logger.error(f"发送升级通知失败: {e}")
    
    @staticmethod
    def scan_and_escalate(db: Session):
        """
        扫描所有待处理告警并执行升级检查
        
        应该由定时任务定期调用
        """
        pending_alerts = db.query(AlertRecord).filter(
            AlertRecord.status == "pending"
        ).all()
        
        count = 0
        for alert in pending_alerts:
            try:
                AlertEscalationService.check_escalation(db, alert)
                count += 1
            except Exception as e:
                logger.error(f"检查告警升级失败: alert_id={alert.id}, error={e}")
        
        logger.info(f"告警升级扫描完成: 检查了 {count} 条告警")
