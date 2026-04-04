"""
告警 AI 分析服务

在发送告警通知时，自动调用 AI 分析告警原因并提供解决建议。
分析结果直接附在告警通知内容中。
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import (
    AlertRecord, RDBInstance, RedisInstance, SlowQuery,
    PerformanceMetric, LockWait, ReplicationStatus
)

logger = logging.getLogger(__name__)


class AlertAIAnalyzer:
    """告警 AI 分析器"""
    
    # 分析超时时间（秒）
    ANALYSIS_TIMEOUT = 10
    
    # 是否启用 AI 分析（可从全局配置读取）
    _enabled = True
    
    @classmethod
    def is_enabled(cls) -> bool:
        """检查 AI 分析是否启用"""
        return cls._enabled
    
    @classmethod
    def set_enabled(cls, enabled: bool):
        """设置是否启用"""
        cls._enabled = enabled
    
    @classmethod
    async def analyze_alert(
        cls,
        db: Session,
        alert: AlertRecord,
        timeout: int = None
    ) -> Optional[str]:
        """
        分析告警并返回分析结果
        
        Args:
            db: 数据库会话
            alert: 告警记录
            timeout: 超时时间（秒）
            
        Returns:
            AI 分析结果（Markdown 格式），失败返回 None
        """
        if not cls._enabled:
            return None
        
        timeout = timeout or cls.ANALYSIS_TIMEOUT
        
        try:
            # 1. 收集告警相关数据
            context = cls._collect_alert_context(db, alert)
            
            # 2. 构建 AI 分析提示词
            prompt = cls._build_analysis_prompt(alert, context)
            
            # 3. 通过场景配置调用 AI
            from app.services.ai_model_service import call_with_scene
            
            analysis, model_used = call_with_scene(
                db=db,
                scene="alert_analysis",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # 低温度保证稳定性
                max_tokens=1024
            )
            
            if analysis:
                logger.info(f"AI 分析完成，使用模型: {model_used.name if model_used else '未知'}")
                # 格式化分析结果
                return cls._format_analysis(analysis)
            
            return None
            
        except RuntimeError as e:
            # 配置错误，记录日志但不影响告警发送
            logger.warning(f"AI 分析配置问题: {e}")
            return None
        except Exception as e:
            logger.error(f"AI 分析告警失败: {e}")
            return None
    
    @classmethod
    def _collect_alert_context(cls, db: Session, alert: AlertRecord) -> dict[str, Any]:
        """
        收集告警相关的上下文数据
        
        包括：
        - 实例信息
        - 最近的慢查询
        - 最近的性能数据
        - 历史告警
        """
        context = {
            "instance": None,
            "recent_slow_queries": [],
            "recent_performance": [],
            "recent_alerts": [],
            "lock_info": None,
            "replication_info": None
        }
        
        try:
            # 获取实例信息
            instance = None
            instance_type = None
            
            if alert.rdb_instance_id:
                instance = db.query(RDBInstance).filter(
                    RDBInstance.id == alert.rdb_instance_id
                ).first()
                instance_type = "rdb"
            elif alert.redis_instance_id:
                instance = db.query(RedisInstance).filter(
                    RedisInstance.id == alert.redis_instance_id
                ).first()
                instance_type = "redis"
            
            if instance:
                context["instance"] = {
                    "name": instance.name,
                    "type": instance_type,
                    "db_type": getattr(instance, 'db_type', 'redis'),
                    "host": instance.host,
                    "port": instance.port,
                    "environment": instance.environment.name if instance.environment else "未知"
                }
            
            # 根据告警类型收集相关数据
            if alert.metric_type == "slow_query" and alert.rdb_instance_id:
                # 慢查询告警：获取最近的慢查询
                slow_queries = db.query(SlowQuery).filter(
                    SlowQuery.instance_id == alert.rdb_instance_id
                ).order_by(desc(SlowQuery.last_seen)).limit(5).all()
                
                context["recent_slow_queries"] = [
                    {
                        "sql": sq.sql_sample[:500] if sq.sql_sample else "",  # 限制长度
                        "execution_time": sq.query_time,
                        "rows_examined": sq.rows_examined,
                        "rows_sent": sq.rows_sent
                    }
                    for sq in slow_queries
                ]
            
            elif alert.metric_type == "lock" and alert.rdb_instance_id:
                # 锁等待告警：获取最近的锁信息
                lock = db.query(LockWait).filter(
                    LockWait.instance_id == alert.rdb_instance_id
                ).order_by(desc(LockWait.created_at)).first()
                
                if lock:
                    context["lock_info"] = {
                        "waiting_query": lock.waiting_sql[:300] if lock.waiting_sql else "",
                        "blocking_query": lock.blocking_sql[:300] if lock.blocking_sql else "",
                        "wait_time": lock.waiting_time
                    }
            
            elif alert.metric_type == "repl" and alert.rdb_instance_id:
                # 复制告警：获取复制状态
                repl = db.query(ReplicationStatus).filter(
                    ReplicationStatus.instance_id == alert.rdb_instance_id
                ).order_by(desc(ReplicationStatus.check_time)).first()
                
                if repl:
                    context["replication_info"] = {
                        "seconds_behind": repl.seconds_behind_master,
                        "io_running": repl.slave_io_running,
                        "sql_running": repl.slave_sql_running
                    }
            
            # 获取最近 24 小时的同类型告警
            recent_alerts = db.query(AlertRecord).filter(
                AlertRecord.metric_type == alert.metric_type,
                AlertRecord.rdb_instance_id == alert.rdb_instance_id,
                AlertRecord.redis_instance_id == alert.redis_instance_id,
                AlertRecord.created_at >= datetime.now() - timedelta(hours=24)
            ).order_by(desc(AlertRecord.created_at)).limit(10).all()
            
            context["recent_alerts"] = [
                {
                    "title": a.alert_title,
                    "level": a.alert_level,
                    "time": a.created_at.strftime("%H:%M") if a.created_at else ""
                }
                for a in recent_alerts if a.id != alert.id
            ]
            
        except Exception as e:
            logger.error(f"收集告警上下文失败: {e}")
        
        return context
    
    @classmethod
    def _build_analysis_prompt(cls, alert: AlertRecord, context: dict[str, Any]) -> str:
        """构建 AI 分析提示词"""
        
        # 告警基础信息
        alert_info = f"""
## 告警信息
- 标题: {alert.alert_title}
- 级别: {alert.alert_level}
- 类型: {alert.metric_type}
- 内容: {alert.alert_content or '无'}
- 时间: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S') if alert.created_at else '未知'}
"""
        
        # 实例信息
        instance_info = ""
        if context.get("instance"):
            inst = context["instance"]
            instance_info = f"""
## 实例信息
- 名称: {inst['name']}
- 类型: {inst['type']} / {inst.get('db_type', '未知')}
- 环境: {inst['environment']}
"""
        
        # 相关数据
        related_data = ""
        
        # 慢查询数据
        if context.get("recent_slow_queries"):
            related_data += "\n## 最近慢查询\n"
            for i, sq in enumerate(context["recent_slow_queries"][:3], 1):
                related_data += f"{i}. 执行时间: {sq['execution_time']}ms, 扫描行数: {sq['rows_examined']}\n"
                related_data += f"   SQL: {sq['sql'][:200]}...\n\n"
        
        # 锁信息
        if context.get("lock_info"):
            lock = context["lock_info"]
            related_data += "\n## 锁等待信息\n"
            related_data += f"- 等待时间: {lock['wait_time']}秒\n"
            related_data += f"- 等待查询: {lock['waiting_query'][:200]}\n"
            related_data += f"- 阻塞查询: {lock['blocking_query'][:200]}\n"
        
        # 复制信息
        if context.get("replication_info"):
            repl = context["replication_info"]
            related_data += "\n## 复制状态\n"
            related_data += f"- 延迟: {repl['seconds_behind']}秒\n"
            related_data += f"- IO线程: {'正常' if repl['io_running'] else '异常'}\n"
            related_data += f"- SQL线程: {'正常' if repl['sql_running'] else '异常'}\n"
        
        # 历史告警
        if context.get("recent_alerts"):
            related_data += f"\n## 24小时内同类告警 ({len(context['recent_alerts'])}条)\n"
            for a in context["recent_alerts"][:5]:
                related_data += f"- [{a['level']}] {a['time']} {a['title']}\n"
        
        # 构建完整提示词
        prompt = f"""你是一个专业的数据库运维专家。请分析以下告警，给出简洁的分析和解决建议。

{alert_info}
{instance_info}
{related_data}

请按以下格式回复（保持简洁，适合在钉钉/企微中展示）：

**根因分析**
(一句话说明最可能的原因)

**处理建议**
1. (立即可以做的操作)
2. (后续优化建议)

**风险提示**
(如果有潜在风险，简要说明)

注意：
- 分析要基于提供的具体数据
- 建议要具体可执行，避免空泛
- 如果数据不足，给出排查方向
- 总字数控制在 200 字以内"""
        
        return prompt
    
    @classmethod
    def _format_analysis(cls, analysis: str) -> str:
        """格式化分析结果"""
        # 清理多余的空白行
        lines = [line.strip() for line in analysis.strip().split('\n')]
        return '\n'.join(line for line in lines if line)
    
    @classmethod
    def build_notification_content_with_analysis(
        cls,
        original_content: str,
        analysis: str
    ) -> str:
        """
        将 AI 分析结果附加到通知内容中
        
        Args:
            original_content: 原始通知内容
            analysis: AI 分析结果
            
        Returns:
            包含分析的完整通知内容
        """
        if not analysis:
            return original_content
        
        return f"""{original_content}

---

🤖 **AI 分析**

{analysis}"""


# 便捷函数
async def analyze_alert(db: Session, alert: AlertRecord) -> Optional[str]:
    """
    分析告警的便捷函数
    
    Args:
        db: 数据库会话
        alert: 告警记录
        
    Returns:
        AI 分析结果
    """
    return await AlertAIAnalyzer.analyze_alert(db, alert)


def build_content_with_analysis(original: str, analysis: str) -> str:
    """
    构建包含分析的通知内容
    
    Args:
        original: 原始内容
        analysis: 分析结果
        
    Returns:
        完整内容
    """
    return AlertAIAnalyzer.build_notification_content_with_analysis(original, analysis)
