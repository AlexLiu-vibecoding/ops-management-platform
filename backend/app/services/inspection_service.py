"""
巡检服务 - 执行巡检任务并生成报告
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from croniter import croniter

from app.models import (
    ScheduledInspection, InspectionExecution, RDBInstance,
    InspectMetric, InspectResult, SlowQuery, IndexAnalysis,
    ReplicationStatus, LongTransaction, LockWait, AlertRecord
)
from app.services.db_connection import db_manager


class InspectionService:
    """巡检服务"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def run_inspection(self, task: ScheduledInspection, execution: InspectionExecution):
        """执行巡检任务"""
        try:
            start_time = datetime.now()
            
            # 获取要检查的实例列表
            instances = self._get_instances(task)
            execution.total_instances = len(instances)
            
            # 获取启用的巡检指标
            metrics = self._get_metrics(task.modules)
            
            all_results = []
            summary = {
                "total_checks": 0,
                "normal": 0,
                "warning": 0,
                "critical": 0,
                "error": 0,
                "instances": []
            }
            
            # 对每个实例执行检查
            for instance in instances:
                instance_result = {
                    "instance_id": instance.id,
                    "instance_name": instance.name,
                    "checks": []
                }
                
                for metric in metrics:
                    try:
                        result = self._run_single_check(instance, metric)
                        instance_result["checks"].append(result)
                        
                        summary["total_checks"] += 1
                        if result["status"] == "normal":
                            summary["normal"] += 1
                        elif result["status"] == "warning":
                            summary["warning"] += 1
                        elif result["status"] == "critical":
                            summary["critical"] += 1
                        else:
                            summary["error"] += 1
                    except Exception as e:
                        instance_result["checks"].append({
                            "metric_id": metric.id,
                            "metric_name": metric.metric_name,
                            "module": metric.module,
                            "status": "error",
                            "error": str(e)
                        })
                        summary["total_checks"] += 1
                        summary["error"] += 1
                
                all_results.append(instance_result)
                summary["instances"].append({
                    "id": instance.id,
                    "name": instance.name,
                    "warning_count": sum(1 for c in instance_result["checks"] if c.get("status") == "warning"),
                    "critical_count": sum(1 for c in instance_result["checks"] if c.get("status") == "critical")
                })
            
            # 更新执行记录
            end_time = datetime.now()
            execution.end_time = end_time
            execution.duration = int((end_time - start_time).total_seconds())
            execution.status = "completed"
            execution.normal_count = summary["normal"]
            execution.warning_count = summary["warning"]
            execution.critical_count = summary["critical"]
            execution.error_count = summary["error"]
            execution.summary = summary
            execution.details = all_results
            
            # 更新任务统计
            task.last_run_time = start_time
            task.last_run_status = "completed"
            task.run_count += 1
            task.success_count += 1
            
            # 计算下次执行时间
            cron = croniter(task.cron_expression, datetime.now())
            task.next_run_time = cron.get_next(datetime)
            
            self.db.commit()
            
            # 发送通知
            self._send_notification(task, execution, summary)
            
            return execution
            
        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.end_time = datetime.now()
            
            task.last_run_time = datetime.now()
            task.last_run_status = "failed"
            task.run_count += 1
            task.fail_count += 1
            
            # 计算下次执行时间
            cron = croniter(task.cron_expression, datetime.now())
            task.next_run_time = cron.get_next(datetime)
            
            self.db.commit()
            raise
    
    def _get_instances(self, task: ScheduledInspection) -> List[RDBInstance]:
        """获取要检查的实例列表"""
        query = self.db.query(RDBInstance).filter(RDBInstance.status == True)
        
        if task.instance_scope == "selected" and task.instance_ids:
            query = query.filter(RDBInstance.id.in_(task.instance_ids))
        
        return query.all()
    
    def _get_metrics(self, modules: Optional[List[str]] = None) -> List[InspectMetric]:
        """获取启用的巡检指标"""
        query = self.db.query(InspectMetric).filter(InspectMetric.is_enabled == True)
        
        if modules:
            query = query.filter(InspectMetric.module.in_(modules))
        
        return query.all()
    
    def _run_single_check(self, instance: RDBInstance, metric: InspectMetric) -> Dict[str, Any]:
        """执行单个检查"""
        status = "normal"
        actual_value = None
        result_detail = {}
        suggestion = None
        
        check_time = datetime.now()
        
        if metric.module == "slow_query":
            # 检查慢查询
            slow_query_count = self.db.query(SlowQuery).filter(
                SlowQuery.instance_id == instance.id,
                SlowQuery.last_seen >= check_time - timedelta(hours=24)
            ).count()
            
            actual_value = str(slow_query_count)
            
            warn_threshold = int(metric.warn_threshold) if metric.warn_threshold else 10
            critical_threshold = int(metric.critical_threshold) if metric.critical_threshold else 50
            
            if slow_query_count >= critical_threshold:
                status = "critical"
                suggestion = f"24小时内慢查询数量({slow_query_count})超过严重阈值({critical_threshold})"
            elif slow_query_count >= warn_threshold:
                status = "warning"
                suggestion = f"24小时内慢查询数量({slow_query_count})超过警告阈值({warn_threshold})"
            
            result_detail = {"slow_query_count": slow_query_count}
        
        elif metric.module == "index":
            # 检查索引问题
            index_issues = self.db.query(IndexAnalysis).filter(
                IndexAnalysis.instance_id == instance.id
            ).count()
            
            actual_value = str(index_issues)
            
            warn_threshold = int(metric.warn_threshold) if metric.warn_threshold else 5
            critical_threshold = int(metric.critical_threshold) if metric.critical_threshold else 20
            
            if index_issues >= critical_threshold:
                status = "critical"
                suggestion = f"发现{index_issues}个索引问题，建议清理冗余和未使用索引"
            elif index_issues >= warn_threshold:
                status = "warning"
                suggestion = f"发现{index_issues}个索引问题，建议关注并优化"
            
            result_detail = {"total_issues": index_issues}
        
        elif metric.module == "lock":
            # 检查锁等待
            lock_count = self.db.query(LockWait).filter(
                LockWait.instance_id == instance.id,
                LockWait.status == "active",
                LockWait.created_at >= check_time - timedelta(hours=1)
            ).count()
            
            actual_value = str(lock_count)
            
            warn_threshold = int(metric.warn_threshold) if metric.warn_threshold else 3
            critical_threshold = int(metric.critical_threshold) if metric.critical_threshold else 10
            
            if lock_count >= critical_threshold:
                status = "critical"
                suggestion = f"发现{lock_count}个活跃锁等待，建议排查阻塞事务"
            elif lock_count >= warn_threshold:
                status = "warning"
                suggestion = f"发现{lock_count}个锁等待，建议关注"
            
            result_detail = {"lock_wait_count": lock_count}
        
        elif metric.module == "transaction":
            # 检查长事务
            long_trx_count = self.db.query(LongTransaction).filter(
                LongTransaction.instance_id == instance.id,
                LongTransaction.status == "active"
            ).count()
            
            actual_value = str(long_trx_count)
            
            warn_threshold = int(metric.warn_threshold) if metric.warn_threshold else 1
            critical_threshold = int(metric.critical_threshold) if metric.critical_threshold else 5
            
            if long_trx_count >= critical_threshold:
                status = "critical"
                suggestion = f"发现{long_trx_count}个活跃长事务，建议Kill或优化"
            elif long_trx_count >= warn_threshold:
                status = "warning"
                suggestion = f"发现{long_trx_count}个长事务，建议关注"
            
            result_detail = {"long_transaction_count": long_trx_count}
        
        elif metric.module == "repl":
            # 检查主从复制
            repl_status = self.db.query(ReplicationStatus).filter(
                ReplicationStatus.instance_id == instance.id
            ).order_by(ReplicationStatus.check_time.desc()).first()
            
            if repl_status:
                delay = repl_status.seconds_behind_master or 0
                io_running = repl_status.slave_io_running == "Yes"
                sql_running = repl_status.slave_sql_running == "Yes"
                
                actual_value = f"IO:{io_running}, SQL:{sql_running}, Delay:{delay}s"
                
                if not io_running or not sql_running:
                    status = "critical"
                    suggestion = "主从复制线程异常，请立即检查"
                elif delay > (int(metric.critical_threshold) if metric.critical_threshold else 60):
                    status = "critical"
                    suggestion = f"主从延迟{delay}秒，超过严重阈值"
                elif delay > (int(metric.warn_threshold) if metric.warn_threshold else 10):
                    status = "warning"
                    suggestion = f"主从延迟{delay}秒，建议关注"
                
                result_detail = {
                    "io_running": io_running,
                    "sql_running": sql_running,
                    "seconds_behind": delay
                }
            else:
                status = "normal"
                actual_value = "无复制状态数据"
                result_detail = {"note": "未配置主从复制或无数据"}
        
        elif metric.module == "capacity":
            # 检查容量
            try:
                conn = db_manager.get_connection(instance)
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT SUM(data_length + index_length) / 1024 / 1024 / 1024 AS size_gb FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', 'mysql', 'performance_schema')")
                    result = cursor.fetchone()
                    size_gb = float(result[0]) if result and result[0] else 0
                    
                    actual_value = f"{size_gb:.2f} GB"
                    
                    warn_threshold = float(metric.warn_threshold) if metric.warn_threshold else 100
                    critical_threshold = float(metric.critical_threshold) if metric.critical_threshold else 500
                    
                    if size_gb >= critical_threshold:
                        status = "critical"
                        suggestion = f"数据库总大小({size_gb:.2f}GB)超过严重阈值({critical_threshold}GB)"
                    elif size_gb >= warn_threshold:
                        status = "warning"
                        suggestion = f"数据库总大小({size_gb:.2f}GB)超过警告阈值({warn_threshold}GB)"
                    
                    result_detail = {"size_gb": round(size_gb, 2)}
            except Exception as e:
                status = "error"
                actual_value = str(e)
                result_detail = {"error": str(e)}
        
        # 保存检查结果
        inspect_result = InspectResult(
            instance_id=instance.id,
            metric_id=metric.id,
            check_time=check_time,
            status=status,
            actual_value=actual_value,
            result_detail=result_detail,
            suggestion=suggestion
        )
        self.db.add(inspect_result)
        self.db.commit()
        
        # 如果发现严重或警告问题，创建告警记录
        if status in ["warning", "critical"]:
            self._create_alert(instance, metric, status, suggestion, check_time)
        
        return {
            "metric_id": metric.id,
            "metric_name": metric.metric_name,
            "module": metric.module,
            "status": status,
            "actual_value": actual_value,
            "result_detail": result_detail,
            "suggestion": suggestion,
            "check_time": check_time.isoformat()
        }
    
    def _create_alert(self, instance: RDBInstance, metric: InspectMetric, 
                      status: str, suggestion: str, check_time: datetime):
        """创建告警记录"""
        alert = AlertRecord(
            rdb_instance_id=instance.id,
            metric_type=metric.module,
            alert_level=status,
            alert_title=f"巡检发现{status}问题: {metric.metric_name}",
            alert_content=suggestion,
            alert_source="inspection",
            status="pending",
            created_at=check_time
        )
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        # 调用告警聚合服务处理新告警
        try:
            from app.services.alert_notification_control import AlertAggregationService
            AlertAggregationService.process_new_alert(self.db, alert)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"告警聚合处理失败: {e}")
    
    def _send_notification(self, task: ScheduledInspection, execution: InspectionExecution, 
                          summary: Dict[str, Any]):
        """发送巡检通知"""
        # 判断是否需要发送通知
        should_notify = False
        if task.notify_on_complete and execution.status == "completed":
            should_notify = True
        if task.notify_on_warning and summary["warning"] > 0:
            should_notify = True
        if task.notify_on_critical and summary["critical"] > 0:
            should_notify = True
        
        if not should_notify or not task.notify_channels:
            return
        
        # TODO: 实现通知发送逻辑
        # 这里需要根据 notify_channels 发送通知
        pass
