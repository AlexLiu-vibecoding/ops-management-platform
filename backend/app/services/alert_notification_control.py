"""
告警通知管控服务

功能：
1. 告警静默 - 在特定时间段内静默告警通知
2. 频率限制 - 限制告警通知的发送频率，防止通知风暴
3. 告警聚合 - 将相似告警按规则聚合
4. 告警升级 - 超时未处理的告警自动升级

作者：OpsCenter Team
"""
import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from collections import defaultdict

from app.models import (
    AlertRecord, AlertAggregationRule, AlertAggregation,
    AlertSilenceRule, AlertRateLimitRule, AlertEscalationRule,
    NotificationLog
)

logger = logging.getLogger(__name__)


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
        
        # 查询启用的静默规则，按优先级降序
        rules = db.query(AlertSilenceRule).filter(
            AlertSilenceRule.is_enabled == True
        ).order_by(desc(AlertSilenceRule.created_at)).all()
        
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
        try:
            # 静默类型判断
            if rule.silence_type == "once":
                # 一次性静默：检查日期范围
                if rule.start_date and now < rule.start_date:
                    return False
                if rule.end_date and now > rule.end_date:
                    return False
                # 如果在日期范围内，则静默
                return True
                
            elif rule.silence_type == "daily":
                # 每日重复：检查时间部分
                if not rule.time_start or not rule.time_end:
                    return False
                    
                current_time = now.time()
                start_time = datetime.strptime(rule.time_start, "%H:%M").time()
                end_time = datetime.strptime(rule.time_end, "%H:%M").time()
                
                # 处理跨天情况
                if start_time <= end_time:
                    return start_time <= current_time <= end_time
                else:
                    # 跨天，例如 22:00 - 06:00
                    return current_time >= start_time or current_time <= end_time
                    
            elif rule.silence_type == "weekly":
                # 每周重复：检查星期和时间
                current_weekday = now.weekday()  # 0=周一, 6=周日
                
                # 检查星期是否在允许列表中
                if rule.weekdays and isinstance(rule.weekdays, list):
                    if current_weekday not in rule.weekdays:
                        return False
                
                # 检查时间部分
                if rule.time_start and rule.time_end:
                    current_time = now.time()
                    start_time = datetime.strptime(rule.time_start, "%H:%M").time()
                    end_time = datetime.strptime(rule.time_end, "%H:%M").time()
                    
                    # 处理跨天情况
                    if start_time <= end_time:
                        return start_time <= current_time <= end_time
                    else:
                        return current_time >= start_time or current_time <= end_time
                
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"检查静默时间窗口失败: {e}")
            return False


class AlertRateLimitService:
    """告警频率限制服务"""
    
    # 用于追踪通知频率的缓存（实例级）
    # 结构: {rule_id: {instance_key: {'count': int, 'first_time': datetime, 'cooldown_until': datetime}}}
    _rate_limit_cache = defaultdict(lambda: defaultdict(dict))
    
    @staticmethod
    def check_rate_limit(db: Session, alert: AlertRecord) -> tuple[bool, Optional[str]]:
        """
        检查告警是否应该被频率限制
        
        Args:
            db: 数据库会话
            alert: 告警记录
            
        Returns:
            (是否允许发送, 限制原因)
        """
        now = datetime.now()
        
        # 查询启用的频率限制规则，按优先级降序
        rules = db.query(AlertRateLimitRule).filter(
            AlertRateLimitRule.is_enabled == True
        ).order_by(desc(AlertRateLimitRule.priority)).all()
        
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
            
            # 构建实例标识
            instance_key = f"{alert.rdb_instance_id or ''}_{alert.redis_instance_id or ''}"
            
            # 检查频率限制
            should_block, reason = AlertRateLimitService._check_rule(
                rule, instance_key, now, db, alert
            )
            
            if should_block:
                return False, reason
        
        return True, None
    
    @staticmethod
    def _check_rule(
        rule: AlertRateLimitRule, 
        instance_key: str, 
        now: datetime,
        db: Session,
        alert: AlertRecord
    ) -> tuple[bool, Optional[str]]:
        """检查单个频率限制规则"""
        cache_key = str(rule.id)
        
        # 获取或初始化缓存
        rule_cache = AlertRateLimitService._rate_limit_cache[cache_key]
        instance_cache = rule_cache.get(instance_key, {
            'count': 0,
            'first_time': None,
            'cooldown_until': None
        })
        
        # 检查是否在冷却期
        if instance_cache['cooldown_until'] and now < instance_cache['cooldown_until']:
            remaining = (instance_cache['cooldown_until'] - now).total_seconds()
            return True, f"处于冷却期，剩余 {int(remaining)} 秒"
        
        # 检查时间窗口
        window_start = now - timedelta(seconds=rule.limit_window)
        
        # 如果是新的时间窗口，重置计数
        if not instance_cache['first_time'] or instance_cache['first_time'] < window_start:
            instance_cache['count'] = 1
            instance_cache['first_time'] = now
            instance_cache['cooldown_until'] = None
            rule_cache[instance_key] = instance_cache
            return False, None
        
        # 在同一个时间窗口内
        instance_cache['count'] += 1
        rule_cache[instance_key] = instance_cache
        
        # 检查是否超过限制
        if instance_cache['count'] > rule.max_notifications:
            # 设置冷却期
            instance_cache['cooldown_until'] = now + timedelta(seconds=rule.cooldown_period)
            rule_cache[instance_key] = instance_cache
            
            logger.warning(
                f"告警频率超限: rule={rule.name}, count={instance_cache['count']}, "
                f"limit={rule.max_notifications}, cooldown={rule.cooldown_period}s"
            )
            
            return True, (
                f"频率超限：{rule.limit_window}秒内已发送 {instance_cache['count']} 条通知，"
                f"超过限制 {rule.max_notifications}，进入 {rule.cooldown_period} 秒冷却期"
            )
        
        return False, None
    
    @staticmethod
    def record_notification_sent(db: Session, alert: AlertRecord):
        """
        记录通知已发送（用于频率限制计数）
        
        Args:
            db: 数据库会话
            alert: 告警记录
        """
        now = datetime.now()
        
        # 查询匹配的频率限制规则
        rules = db.query(AlertRateLimitRule).filter(
            AlertRateLimitRule.is_enabled == True
        ).order_by(desc(AlertRateLimitRule.priority)).all()
        
        for rule in rules:
            # 检查是否匹配规则
            if rule.metric_type and rule.metric_type != alert.metric_type:
                continue
            if rule.alert_level and rule.alert_level != alert.alert_level:
                continue
            if rule.rdb_instance_id and rule.rdb_instance_id != alert.rdb_instance_id:
                continue
            if rule.redis_instance_id and rule.redis_instance_id != alert.redis_instance_id:
                continue
            
            # 记录到缓存（已在 check_rate_limit 中处理）
            logger.info(f"告警 {alert.id} 通知已记录，匹配频率规则: {rule.name}")


class AlertAggregationService:
    """告警聚合服务"""
    
    @staticmethod
    def should_aggregate_alert(db: Session, alert: AlertRecord) -> Optional[AlertAggregationRule]:
        """检查告警是否应该被聚合"""
        rules = db.query(AlertAggregationRule).filter(
            AlertAggregationRule.is_enabled == True
        ).order_by(desc(AlertAggregationRule.priority)).all()
        
        for rule in rules:
            if rule.metric_type and rule.metric_type != alert.metric_type:
                continue
            if rule.alert_level and rule.alert_level != alert.alert_level:
                continue
            if rule.rdb_instance_id and rule.rdb_instance_id != alert.rdb_instance_id:
                continue
            if rule.redis_instance_id and rule.redis_instance_id != alert.redis_instance_id:
                continue
            
            return rule
        
        return None
    
    @staticmethod
    def aggregate_alert(db: Session, alert: AlertRecord, rule: AlertAggregationRule):
        """聚合告警"""
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
                AlertAggregation.ended_at == None
            )
        ).first()
        
        if existing_agg:
            existing_agg.alert_count += 1
            if existing_agg.alert_ids is None:
                existing_agg.alert_ids = []
            existing_agg.alert_ids.append(alert.id)
            existing_agg.aggregated_content = AlertAggregationService._build_aggregated_content(
                db, existing_agg, rule
            )
            
            if existing_agg.alert_count >= rule.min_alert_count and not existing_agg.notification_sent:
                AlertAggregationService._send_aggregated_notification(db, existing_agg, rule)
                existing_agg.notification_sent = True
        else:
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
            return f"共 {agg.alert_count} 条 {agg.alert_level} 级别 {agg.metric_type} 告警"
        else:
            return f"{agg.alert_count} 条告警已聚合"
    
    @staticmethod
    def _send_aggregated_notification(db: Session, agg: AlertAggregation, rule: AlertAggregationRule):
        """发送聚合后的告警通知"""
        try:
            from app.services.notification import notification_service
            
            temp_alert = AlertRecord(
                id=0,
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
            
            asyncio.create_task(notification_service.send_alert_notification(db, temp_alert, is_aggregated=True))
            
            logger.info(f"聚合告警通知已发送: rule_id={rule.id}, count={agg.alert_count}")
        except Exception as e:
            logger.error(f"发送聚合告警通知失败: {e}")
    
    @staticmethod
    def process_new_alert(db: Session, alert: AlertRecord):
        """处理新告警的主入口"""
        rule = AlertAggregationService.should_aggregate_alert(db, alert)
        if rule:
            AlertAggregationService.aggregate_alert(db, alert, rule)
            return True
        return False


class AlertEscalationService:
    """告警升级服务"""
    
    @staticmethod
    def check_escalation(db: Session, alert: AlertRecord):
        """检查告警是否应该升级"""
        if alert.status != "pending":
            return
        
        now = datetime.now()
        elapsed = (now - alert.created_at).total_seconds() / 60
        
        rules = db.query(AlertEscalationRule).filter(
            and_(
                AlertEscalationRule.is_enabled == True,
                or_(
                    AlertEscalationRule.alert_level == alert.alert_level,
                    AlertEscalationRule.alert_level == None
                )
            )
        ).order_by(desc(AlertEscalationRule.priority)).all()
        
        for rule in rules:
            if elapsed >= rule.trigger_minutes:
                AlertEscalationService._escalate_alert(db, alert, rule)
                break
    
    @staticmethod
    def _escalate_alert(db: Session, alert: AlertRecord, rule: AlertEscalationRule):
        """执行告警升级"""
        logger.info(f"告警 {alert.id} 升级: {rule.name}")
        
        if rule.escalation_level:
            alert.alert_level = rule.escalation_level
        
        if not alert.alert_title.startswith("[已升级]"):
            alert.alert_title = f"[已升级] {alert.alert_title}"
        
        if rule.escalation_notification:
            AlertEscalationService._send_escalation_notification(db, alert, rule)
        
        db.commit()
    
    @staticmethod
    def _send_escalation_notification(db: Session, alert: AlertRecord, rule: AlertEscalationRule):
        """发送升级通知"""
        try:
            from app.services.notification import notification_service
            asyncio.create_task(notification_service.send_alert_notification(db, alert))
            logger.info(f"升级通知已发送: alert_id={alert.id}, rule={rule.name}")
        except Exception as e:
            logger.error(f"发送升级通知失败: {e}")
    
    @staticmethod
    def scan_and_escalate(db: Session):
        """扫描所有待处理告警并执行升级检查"""
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
