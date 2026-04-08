"""
任务调度器服务
使用 APScheduler 实现定时任务调度
"""
import asyncio
import os
import json
import tempfile
import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.base import JobLookupError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    ScheduledTask, Script, ScriptExecution, RDBInstance, PerformanceMetric,
    ExecutionStatus, TriggerType, MonitorSwitch, MonitorType
)
from app.services.notification import notification_service

logger = logging.getLogger(__name__)


class TaskScheduler:
    """定时任务调度器"""
    
    # 性能采集任务间隔（秒）
    PERFORMANCE_COLLECT_INTERVAL = 300  # 5分钟采集一次
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
    
    @property
    def running(self) -> bool:
        """检查调度器是否正在运行"""
        return self.scheduler is not None and self.scheduler.running
    
    def start(self):
        """启动调度器"""
        if self.scheduler is not None:
            logger.warning("任务调度器已在运行")
            return
        
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        logger.info("定时任务调度器已启动")
        
        # 加载所有启用的任务
        self._load_enabled_tasks()
        
        # 启动性能指标采集任务
        self._start_performance_collector()
        
        # 启动密钥轮换任务
        self._start_key_rotation_scheduler()
    
    def stop(self):
        """停止调度器"""
        if self.scheduler:
            # 停止性能采集任务
            self._stop_performance_collector()
            self.scheduler.shutdown()
            self.scheduler = None
            logger.info("定时任务调度器已停止")
    
    def _start_performance_collector(self):
        """启动性能指标采集任务"""
        try:
            # 每5分钟采集一次
            self.scheduler.add_job(
                self._collect_rds_metrics,
                trigger=IntervalTrigger(seconds=self.PERFORMANCE_COLLECT_INTERVAL),
                id="rds_performance_collector",
                replace_existing=True
            )
            logger.info("RDS 性能指标采集任务已启动")
        except Exception as e:
            logger.error(f"启动性能采集任务失败: {e}")
    
    def _stop_performance_collector(self):
        """停止性能指标采集任务"""
        try:
            self.scheduler.remove_job("rds_performance_collector")
            logger.info("RDS 性能指标采集任务已停止")
        except JobLookupError:
            pass
    
    def _start_key_rotation_scheduler(self):
        """启动密钥轮换定时任务"""
        try:
            from app.models import KeyRotationConfig
            
            db = SessionLocal()
            try:
                config = db.query(KeyRotationConfig).first()
                
                if config and config.enabled:
                    self._schedule_key_rotation(config)
                    logger.info(f"密钥轮换任务已启动 (周期: {config.schedule_type}, 时间: {config.schedule_time})")
                else:
                    logger.info("密钥轮换任务未启用")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"启动密钥轮换任务失败: {e}")
    
    def _schedule_key_rotation(self, config):
        """根据配置安排密钥轮换任务"""
        from app.models import KeyRotationConfig
        
        # 移除旧任务
        try:
            self.scheduler.remove_job("key_rotation")
        except JobLookupError:
            pass
        
        # 解析执行时间
        time_parts = config.schedule_time.split(':')
        hour = int(time_parts[0]) if len(time_parts) > 0 else 2
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        
        # 根据周期类型设置触发器
        if config.schedule_type == "weekly":
            # 每周执行
            trigger = CronTrigger(
                day_of_week=config.schedule_day,
                hour=hour,
                minute=minute
            )
        elif config.schedule_type == "monthly":
            # 每月执行
            trigger = CronTrigger(
                day=config.schedule_day,
                hour=hour,
                minute=minute
            )
        else:
            # 每季度执行 (每3个月)
            # 简化处理：使用每月执行，但在业务逻辑中判断
            trigger = CronTrigger(
                day=config.schedule_day,
                hour=hour,
                minute=minute
            )
        
        self.scheduler.add_job(
            self._execute_key_rotation,
            trigger=trigger,
            id="key_rotation",
            replace_existing=True
        )
    
    async def _execute_key_rotation(self):
        """执行密钥轮换任务"""
        from app.models import KeyRotationConfig
        from app.services.key_rotation_service import KeyRotationService
        
        logger.info("开始执行密钥轮换任务")
        
        db = SessionLocal()
        try:
            # 获取配置
            config = db.query(KeyRotationConfig).first()
            if not config or not config.enabled:
                logger.info("密钥轮换任务已禁用，跳过执行")
                return
            
            # 检查是否到达执行时间（季度检查）
            now = datetime.now()
            if config.schedule_type == "quarterly":
                # 只在 1, 4, 7, 10 月执行
                if now.month not in [1, 4, 7, 10]:
                    logger.info(f"当前月份 {now.month} 不在季度执行月份中，跳过")
                    return
            
            service = KeyRotationService(db)
            
            # 执行迁移
            result = service.execute_migration()
            
            # 如果配置了自动切换
            if config.auto_switch and result["success"]:
                current_version = config.current_key_id
                target_version = "v2" if current_version == "v1" else "v1"
                service.switch_version(target_version)
            
            # 更新配置
            config.last_rotation_at = datetime.now()
            config.next_rotation_at = service.calculate_next_rotation()
            db.commit()
            
            logger.info(f"密钥轮换任务执行完成: 迁移 {result['total_migrated']} 条, 失败 {result['total_failed']} 条")
            
        except Exception as e:
            logger.error(f"密钥轮换任务执行失败: {e}")
        finally:
            db.close()
    
    def reload_key_rotation_task(self):
        """重新加载密钥轮换任务（配置变更后调用）"""
        from app.models import KeyRotationConfig
        
        db = SessionLocal()
        try:
            config = db.query(KeyRotationConfig).first()
            
            if config and config.enabled:
                self._schedule_key_rotation(config)
                logger.info("密钥轮换任务已重新加载")
            else:
                # 禁用任务
                try:
                    self.scheduler.remove_job("key_rotation")
                    logger.info("密钥轮换任务已移除")
                except JobLookupError:
                    pass
        finally:
            db.close()
    
    async def _collect_rds_metrics(self):
        """采集所有 RDS 实例的性能指标"""
        from app.utils.aws_rds_collector import get_rds_collector_for_environment
        
        db = SessionLocal()
        try:
            # 查询所有启用了 RDS 监控的实例
            rds_instances = db.query(RDBInstance).filter(
                RDBInstance.is_rds,
                RDBInstance.rds_instance_id is not None,
                RDBInstance.status  # 只采集在线实例
            ).all()
            
            if not rds_instances:
                return
            
            for instance in rds_instances:
                try:
                    # 检查是否启用了性能监控
                    switch = db.query(MonitorSwitch).filter(
                        MonitorSwitch.instance_id == instance.id,
                        MonitorSwitch.monitor_type == MonitorType.PERFORMANCE
                    ).first()
                    
                    if not switch or not switch.enabled:
                        continue
                    
                    # 从环境获取 AWS 凭证
                    collector = get_rds_collector_for_environment(
                        environment_id=instance.environment_id,
                        aws_region=instance.aws_region
                    )
                    
                    if not collector:
                        logger.warning(f"实例 {instance.id} 所属环境未配置 AWS 凭证，跳过采集")
                        continue
                    
                    # 采集指标
                    metrics = collector.collect_metrics(instance.rds_instance_id)
                    
                    if metrics.error:
                        logger.warning(f"RDS {instance.rds_instance_id} 采集失败: {metrics.error}")
                        continue
                    
                    # 存储到数据库
                    metric_record = PerformanceMetric(
                        instance_id=instance.id,
                        collect_time=metrics.collect_time or datetime.now(),
                        cpu_usage=metrics.cpu_usage,
                        memory_usage=metrics.memory_usage,
                        disk_io_read=metrics.read_iops,
                        disk_io_write=metrics.write_iops,
                        connections=metrics.connections,
                        qps=metrics.qps
                    )
                    db.add(metric_record)
                    
                    logger.info(f"RDS {instance.rds_instance_id} 性能指标采集成功")
                    
                except Exception as e:
                    logger.error(f"RDS {instance.rds_instance_id} 采集异常: {e}")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"RDS 性能采集任务执行失败: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _load_enabled_tasks(self):
        """加载所有启用的定时任务"""
        db = SessionLocal()
        try:
            tasks = db.query(ScheduledTask).filter(
                ScheduledTask.status == "enabled"
            ).all()
            
            for task in tasks:
                try:
                    self.add_job(task)
                    logger.info(f"已加载定时任务: {task.id} - {task.name}")
                except Exception as e:
                    logger.error(f"加载定时任务失败: {task.id}, 错误: {e}")
        finally:
            db.close()
    
    def add_job(self, task: ScheduledTask):
        """添加定时任务到调度器"""
        if self.scheduler is None:
            logger.error("调度器未启动")
            return False
        
        job_id = f"scheduled_task_{task.id}"
        
        # 创建 Cron 触发器
        trigger = CronTrigger.from_crontab(
            task.cron_expression,
            timezone=task.timezone
        )
        
        # 添加任务
        self.scheduler.add_job(
            self._execute_scheduled_task,
            trigger=trigger,
            id=job_id,
            args=[task.id],
            replace_existing=True
        )
        
        # 更新下次执行时间
        db = SessionLocal()
        try:
            next_run = trigger.get_next_fire_time(None, datetime.now())
            db.query(ScheduledTask).filter(
                ScheduledTask.id == task.id
            ).update({"next_run_time": next_run})
            db.commit()
        finally:
            db.close()
        
        logger.info(f"已添加定时任务: {task.id} - {task.name}")
        return True
    
    def update_job(self, task: ScheduledTask):
        """更新定时任务"""
        self.remove_job(task.id)
        if task.status == "enabled":
            self.add_job(task)
    
    def remove_job(self, task_id: int):
        """移除定时任务"""
        if self.scheduler is None:
            return
        
        job_id = f"scheduled_task_{task_id}"
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"已移除定时任务: {task_id}")
        except JobLookupError:
            pass
    
    def pause_job(self, task_id: int):
        """暂停定时任务"""
        if self.scheduler is None:
            return
        
        job_id = f"scheduled_task_{task_id}"
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"已暂停定时任务: {task_id}")
        except JobLookupError:
            pass
    
    def resume_job(self, task: ScheduledTask):
        """恢复定时任务"""
        if self.scheduler is None:
            return
        
        job_id = f"scheduled_task_{task.id}"
        try:
            self.scheduler.resume_job(job_id)
        except JobLookupError:
            # 如果任务不存在，重新添加
            self.add_job(task)
        
        logger.info(f"已恢复定时任务: {task.id}")
    
    def trigger_now(self, task: ScheduledTask, triggered_by: int):
        """立即触发任务执行"""
        # 异步执行
        asyncio.create_task(self._execute_task_async(task.id, triggered_by))
    
    async def _execute_scheduled_task(self, task_id: int):
        """执行定时任务（由调度器调用）"""
        await self._execute_task_async(task_id, triggered_by=None)
    
    async def _execute_task_async(self, task_id: int, triggered_by: Optional[int] = None):
        """
        异步执行任务
        
        Args:
            task_id: 定时任务ID
            triggered_by: 触发人ID（手动触发时有值）
        """
        db = SessionLocal()
        try:
            task = db.query(ScheduledTask).filter(
                ScheduledTask.id == task_id
            ).first()
            
            if not task:
                logger.error(f"定时任务不存在: {task_id}")
                return
            
            script = db.query(Script).filter(
                Script.id == task.script_id
            ).first()
            
            if not script or not script.is_enabled:
                logger.error(f"脚本不存在或已禁用: {task.script_id}")
                return
            
            # 创建执行记录
            execution = ScriptExecution(
                script_id=script.id,
                script_version=script.version,
                trigger_type=TriggerType.SCHEDULED if triggered_by is None else TriggerType.MANUAL,
                scheduled_task_id=task.id,
                params=task.params or {},
                status=ExecutionStatus.PENDING,
                triggered_by=triggered_by
            )
            
            db.add(execution)
            db.commit()
            db.refresh(execution)
            
            # 更新状态为执行中
            execution.status = ExecutionStatus.RUNNING
            execution.start_time = datetime.now()
            db.commit()
            
            # 执行脚本
            success = await self._run_script(script, task.params or {}, execution, db)
            
            # 更新任务统计
            task.run_count += 1
            task.last_run_time = datetime.now()
            task.last_run_status = "success" if success else "failed"
            
            if success:
                task.success_count += 1
            else:
                task.fail_count += 1
            
            # 更新下次执行时间
            if task.status == "enabled":
                trigger = CronTrigger.from_crontab(task.cron_expression)
                task.next_run_time = trigger.get_next_fire_time(None, datetime.now())
            
            db.commit()
            
            # 发送通知
            try:
                await notification_service.send_scheduled_task_notification(
                    db, task, execution, success
                )
            except Exception as notify_error:
                logger.error(f"发送任务通知失败: {notify_error}")
            
            logger.info(f"定时任务执行完成: {task_id}, 状态: {execution.status}")
            
        except Exception as e:
            logger.error(f"定时任务执行失败: {task_id}, 错误: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _run_script(
        self,
        script: Script,
        params: dict,
        execution: ScriptExecution,
        db: Session
    ) -> bool:
        """
        执行脚本
        
        Returns:
            是否执行成功
        """
        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix=f'.{script.script_type.value}',
            delete=False
        ) as f:
            f.write(script.content)
            script_path = f.name
        
        # 构建执行命令
        env = os.environ.copy()
        env['SCRIPT_PARAMS'] = json.dumps(params)
        for key, value in params.items():
            env[f'PARAM_{key.upper()}'] = str(value)
        
        if script.script_type.value == "python":
            cmd = ['python3', script_path]
        elif script.script_type.value == "bash":
            cmd = ['bash', script_path]
        else:
            execution.status = ExecutionStatus.FAILED
            execution.error_output = f"不支持的脚本类型: {script.script_type}"
            execution.end_time = datetime.now()
            db.commit()
            return False
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=script.timeout
                )
                
                execution.status = ExecutionStatus.SUCCESS if process.returncode == 0 else ExecutionStatus.FAILED
                execution.output = stdout.decode('utf-8', errors='replace')
                execution.error_output = stderr.decode('utf-8', errors='replace')
                execution.exit_code = process.returncode
                
            except TimeoutError:
                process.kill()
                execution.status = ExecutionStatus.TIMEOUT
                execution.error_output = f"脚本执行超时（{script.timeout}秒）"
            
        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error_output = str(e)
        
        finally:
            # 清理临时文件
            try:
                os.unlink(script_path)
            except Exception:
                pass
        
        # 更新执行时间
        execution.end_time = datetime.now()
        if execution.start_time:
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
        
        db.commit()
        
        return execution.status == ExecutionStatus.SUCCESS


# 全局调度器实例
task_scheduler = TaskScheduler()
