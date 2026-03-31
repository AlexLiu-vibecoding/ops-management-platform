"""
SQL 优化闭环服务

提供 SQL 性能优化的完整闭环能力：
- 慢 SQL 自动采集
- 周期性 LLM 分析
- 优化建议存储
- 一键提交变更
- 效果验证
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import select, and_, desc
from sqlalchemy.orm import Session

from app.models import (
    RDBInstance, SlowQuery, ApprovalRecord, ApprovalStatus,
    OptimizationSuggestion, SlowQueryCollectionTask, TableSchema,
    User, Environment
)
from app.schemas import (
    OptimizationSuggestionCreate, CollectionTaskCreate,
    CollectionTaskUpdate
)
from app.services.slow_query_collector import SlowQueryCollector
from app.services.slow_query_analyzer import SlowQueryAnalyzer
from app.utils.auth import aes_cipher

logger = logging.getLogger(__name__)


class SQLOptimizationService:
    """SQL 优化闭环服务"""

    def __init__(self, db: Session):
        self.db = db
        self.collector = SlowQueryCollector()
        self.analyzer = SlowQueryAnalyzer()

    # ==================== 采集任务管理 ====================

    def create_collection_task(
        self,
        task_data: CollectionTaskCreate,
        current_user: User
    ) -> SlowQueryCollectionTask:
        """创建采集任务"""
        # 检查实例是否存在
        instance = self._get_instance(task_data.instance_id)
        if not instance:
            raise ValueError(f"实例不存在: {task_data.instance_id}")

        # 检查是否已存在任务
        existing = self._get_task_by_instance(task_data.instance_id)
        if existing:
            raise ValueError(f"实例 {instance.name} 已存在采集任务")

        task = SlowQueryCollectionTask(
            instance_id=task_data.instance_id,
            enabled=task_data.enabled,
            cron_expression=task_data.cron_expression,
            min_exec_time=task_data.min_exec_time,
            top_n=task_data.top_n,
            auto_analyze=task_data.auto_analyze,
            analyze_threshold=task_data.analyze_threshold,
            llm_analysis=task_data.llm_analysis
        )

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)

        logger.info(f"创建采集任务: instance_id={task.instance_id}, task_id={task.id}")
        return task

    def update_collection_task(
        self,
        task_id: int,
        task_data: CollectionTaskUpdate
    ) -> Optional[SlowQueryCollectionTask]:
        """更新采集任务"""
        task = self._get_task(task_id)
        if not task:
            return None

        update_data = task_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(task, key, value)

        self.db.commit()
        self.db.refresh(task)

        logger.info(f"更新采集任务: task_id={task_id}")
        return task

    def delete_collection_task(self, task_id: int) -> bool:
        """删除采集任务"""
        task = self._get_task(task_id)
        if not task:
            return False

        self.db.delete(task)
        self.db.commit()

        logger.info(f"删除采集任务: task_id={task_id}")
        return True

    def list_collection_tasks(
        self,
        instance_id: Optional[int] = None,
        enabled: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[SlowQueryCollectionTask], int]:
        """获取采集任务列表"""
        query = select(SlowQueryCollectionTask)

        if instance_id:
            query = query.where(SlowQueryCollectionTask.instance_id == instance_id)
        if enabled is not None:
            query = query.where(SlowQueryCollectionTask.enabled == enabled)

        # 统计总数
        count_query = select(SlowQueryCollectionTask.id)
        if instance_id:
            count_query = count_query.where(SlowQueryCollectionTask.instance_id == instance_id)
        if enabled is not None:
            count_query = count_query.where(SlowQueryCollectionTask.enabled == enabled)

        from sqlalchemy import func
        total_query = select(func.count()).select_from(count_query.subquery())
        total_result = self.db.execute(total_query)
        total = total_result.scalar() or 0

        # 分页查询
        query = query.order_by(desc(SlowQueryCollectionTask.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = self.db.execute(query)
        tasks = result.scalars().all()

        return list(tasks), total

    # ==================== 慢 SQL 采集 ====================

    def run_collection(
        self,
        task_id: int
    ) -> Dict[str, Any]:
        """执行采集任务"""
        task = self._get_task(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")

        instance = self._get_instance(task.instance_id)
        if not instance:
            raise ValueError(f"实例不存在: {task.instance_id}")

        start_time = time.time()
        collected_count = 0
        analyzed_count = 0
        errors = []

        try:
            # 采集慢查询
            slow_queries = self.collector.fetch_from_performance_schema(
                instance=instance,
                limit=task.top_n,
                min_exec_time=float(task.min_exec_time)
            )

            # 存储慢查询记录
            for sq_data in slow_queries:
                try:
                    # 检查是否已存在
                    existing = self._find_existing_slow_query(
                        instance.id,
                        sq_data.get("digest_text", "")
                    )

                    if existing:
                        # 更新执行次数和时间
                        existing.execution_count += sq_data.get("exec_count", 1)
                        existing.last_seen = datetime.now()
                        existing.query_time = sq_data.get("avg_exec_time_sec", 0)
                    else:
                        # 创建新记录
                        slow_query = SlowQuery(
                            instance_id=instance.id,
                            database_name=sq_data.get("schema_name"),
                            sql_fingerprint=sq_data.get("digest_text", "")[:500],
                            sql_sample=sq_data.get("sample_query"),
                            digest=sq_data.get("digest"),
                            query_time=sq_data.get("avg_exec_time_sec", 0),
                            rows_sent=sq_data.get("rows_sent", 0),
                            rows_examined=sq_data.get("rows_examined", 0),
                            execution_count=sq_data.get("exec_count", 1),
                            first_seen=datetime.now(),
                            last_seen=datetime.now()
                        )
                        self.db.add(slow_query)

                    collected_count += 1

                except Exception as e:
                    logger.error(f"存储慢查询失败: {e}")
                    errors.append(str(e))

            self.db.commit()

            # 自动分析
            if task.auto_analyze:
                analyzed_count = self._auto_analyze_slow_queries(
                    instance=instance,
                    task=task
                )

            # 更新任务状态
            task.last_run_at = datetime.now()
            task.last_run_status = "success" if not errors else "partial"
            task.last_collected_count = collected_count
            task.total_collected_count += collected_count
            self.db.commit()

            duration = time.time() - start_time

            logger.info(
                f"采集任务完成: task_id={task_id}, "
                f"collected={collected_count}, analyzed={analyzed_count}, "
                f"duration={duration:.2f}s"
            )

            return {
                "task_id": task_id,
                "instance_id": instance.id,
                "instance_name": instance.name,
                "collected_count": collected_count,
                "analyzed_count": analyzed_count,
                "duration": duration,
                "errors": errors[:5] if errors else [],
                "message": "采集完成" if not errors else f"采集完成，{len(errors)} 条记录失败"
            }

        except Exception as e:
            # 更新任务失败状态
            task.last_run_at = datetime.now()
            task.last_run_status = "failed"
            self.db.commit()

            logger.error(f"采集任务失败: task_id={task_id}, error={str(e)}")
            raise

    def _auto_analyze_slow_queries(
        self,
        instance: RDBInstance,
        task: SlowQueryCollectionTask
    ) -> int:
        """自动分析慢查询"""
        # 查找执行次数超过阈值且未分析过的慢查询
        query = select(SlowQuery).where(
            and_(
                SlowQuery.instance_id == instance.id,
                SlowQuery.execution_count >= task.analyze_threshold
            )
        ).order_by(desc(SlowQuery.query_time)).limit(20)

        result = self.db.execute(query)
        slow_queries = result.scalars().all()

        analyzed_count = 0
        for sq in slow_queries:
            # 检查是否已有优化建议
            existing = self._has_suggestion(sq.id)
            if existing:
                continue

            try:
                # 执行 LLM 分析
                if task.llm_analysis and sq.sql_sample:
                    self._create_suggestion_from_slow_query(
                        instance=instance,
                        slow_query=sq,
                        enable_llm=True
                    )
                    analyzed_count += 1
            except Exception as e:
                logger.error(f"分析慢查询失败: slow_query_id={sq.id}, error={str(e)}")

        return analyzed_count

    # ==================== 优化建议管理 ====================

    def create_suggestion(
        self,
        suggestion_data: OptimizationSuggestionCreate
    ) -> OptimizationSuggestion:
        """创建优化建议"""
        suggestion = OptimizationSuggestion(
            instance_id=suggestion_data.instance_id,
            database_name=suggestion_data.database_name,
            slow_query_id=suggestion_data.slow_query_id,
            sql_fingerprint=suggestion_data.sql_fingerprint,
            sql_sample=suggestion_data.sql_sample,
            issues=suggestion_data.issues,
            suggestions=suggestion_data.suggestions,
            suggested_sql=suggestion_data.suggested_sql,
            index_ddl=suggestion_data.index_ddl,
            rollback_sql=suggestion_data.rollback_sql,
            risk_level=suggestion_data.risk_level,
            confidence=suggestion_data.confidence,
            expected_improvement=suggestion_data.expected_improvement,
            table_schemas_used=suggestion_data.table_schemas_used,
            analysis_time=suggestion_data.analysis_time,
            llm_model=suggestion_data.llm_model
        )

        self.db.add(suggestion)
        self.db.commit()
        self.db.refresh(suggestion)

        logger.info(f"创建优化建议: suggestion_id={suggestion.id}")
        return suggestion

    def list_suggestions(
        self,
        instance_id: Optional[int] = None,
        status: Optional[str] = None,
        risk_level: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[OptimizationSuggestion], int]:
        """获取优化建议列表"""
        query = select(OptimizationSuggestion)

        conditions = []
        if instance_id:
            conditions.append(OptimizationSuggestion.instance_id == instance_id)
        if status:
            conditions.append(OptimizationSuggestion.status == status)
        if risk_level:
            conditions.append(OptimizationSuggestion.risk_level == risk_level)

        if conditions:
            query = query.where(and_(*conditions))

        # 统计总数
        from sqlalchemy import func
        count_subquery = query.subquery()
        total_query = select(func.count()).select_from(count_subquery)
        total_result = self.db.execute(total_query)
        total = total_result.scalar() or 0

        # 分页查询
        query = query.order_by(desc(OptimizationSuggestion.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = self.db.execute(query)
        suggestions = result.scalars().all()

        return list(suggestions), total

    def get_suggestion(self, suggestion_id: int) -> Optional[OptimizationSuggestion]:
        """获取优化建议详情"""
        query = select(OptimizationSuggestion).where(
            OptimizationSuggestion.id == suggestion_id
        )
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def adopt_suggestion(
        self,
        suggestion_id: int,
        current_user: User
    ) -> Dict[str, Any]:
        """采用建议，创建变更申请"""
        suggestion = self.get_suggestion(suggestion_id)
        if not suggestion:
            raise ValueError(f"建议不存在: {suggestion_id}")

        if suggestion.status != "pending":
            raise ValueError(f"建议状态不是 pending，无法采用: {suggestion.status}")

        # 确定变更内容
        change_sql = suggestion.index_ddl or suggestion.suggested_sql
        if not change_sql:
            raise ValueError("该建议没有可执行的 SQL 语句")

        # 获取实例和环境信息
        instance = self._get_instance(suggestion.instance_id)
        if not instance:
            raise ValueError(f"实例不存在: {suggestion.instance_id}")

        # 创建变更申请
        approval = ApprovalRecord(
            title=f"SQL优化建议: {suggestion.sql_fingerprint[:50]}...",
            change_type="DDL" if suggestion.index_ddl else "DML",
            rdb_instance_id=suggestion.instance_id,
            database_name=suggestion.database_name,
            sql_content=change_sql,
            rollback_sql=suggestion.rollback_sql,
            sql_risk_level=suggestion.risk_level,
            environment_id=instance.environment_id,
            requester_id=current_user.id,
            status=ApprovalStatus.PENDING
        )

        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)

        # 更新建议状态
        suggestion.status = "adopted"
        suggestion.approval_id = approval.id
        suggestion.adopted_by = current_user.id
        suggestion.adopted_at = datetime.now()
        self.db.commit()

        logger.info(
            f"采用优化建议: suggestion_id={suggestion_id}, "
            f"approval_id={approval.id}, user={current_user.username}"
        )

        return {
            "id": suggestion.id,
            "status": suggestion.status,
            "approval_id": approval.id,
            "approval_url": f"/change/requests/{approval.id}",
            "message": "已创建变更申请，等待审批"
        }

    def reject_suggestion(
        self,
        suggestion_id: int,
        reason: Optional[str],
        current_user: User
    ) -> OptimizationSuggestion:
        """拒绝建议"""
        suggestion = self.get_suggestion(suggestion_id)
        if not suggestion:
            raise ValueError(f"建议不存在: {suggestion_id}")

        if suggestion.status != "pending":
            raise ValueError(f"建议状态不是 pending，无法拒绝: {suggestion.status}")

        suggestion.status = "rejected"
        self.db.commit()
        self.db.refresh(suggestion)

        logger.info(
            f"拒绝优化建议: suggestion_id={suggestion_id}, "
            f"reason={reason}, user={current_user.username}"
        )

        return suggestion

    def verify_suggestion(
        self,
        suggestion_id: int
    ) -> Dict[str, Any]:
        """验证优化效果"""
        suggestion = self.get_suggestion(suggestion_id)
        if not suggestion:
            raise ValueError(f"建议不存在: {suggestion_id}")

        if suggestion.status != "adopted" or not suggestion.approval_id:
            raise ValueError("建议未被采用或没有关联的变更申请")

        # 获取关联的审批记录
        approval_query = select(ApprovalRecord).where(
            ApprovalRecord.id == suggestion.approval_id
        )
        result = self.db.execute(approval_query)
        approval = result.scalar_one_or_none()

        if not approval or approval.status != ApprovalStatus.EXECUTED:
            raise ValueError("变更申请尚未执行")

        # 查询优化后的慢查询性能
        instance = self._get_instance(suggestion.instance_id)
        if not instance:
            raise ValueError("实例不存在")

        # 记录优化前的时间
        before_time = suggestion.adopted_at or suggestion.created_at

        # 查询优化后的平均执行时间
        # 这里简化实现，实际应该从慢查询表中统计
        after_avg_time = self._get_avg_query_time_after_optimization(
            instance=instance,
            sql_fingerprint=suggestion.sql_fingerprint,
            after_time=before_time
        )

        # 计算提升百分比
        before_avg_time = float(suggestion.before_avg_time) if suggestion.before_avg_time else None
        actual_improvement = None

        if before_avg_time and after_avg_time:
            actual_improvement = ((before_avg_time - after_avg_time) / before_avg_time) * 100

        # 更新建议
        suggestion.after_avg_time = after_avg_time
        suggestion.actual_improvement = actual_improvement
        self.db.commit()

        improvement_msg = ""
        if actual_improvement:
            improvement_msg = f"性能提升 {actual_improvement:.1f}%"
        else:
            improvement_msg = "无法计算性能提升"

        logger.info(
            f"验证优化效果: suggestion_id={suggestion_id}, "
            f"before={before_avg_time}, after={after_avg_time}, "
            f"improvement={actual_improvement}"
        )

        return {
            "id": suggestion.id,
            "before_avg_time": before_avg_time,
            "after_avg_time": after_avg_time,
            "actual_improvement": actual_improvement,
            "message": improvement_msg
        }

    def manual_analyze(
        self,
        instance_id: int,
        sql_text: str,
        database_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """手动分析 SQL"""
        instance = self._get_instance(instance_id)
        if not instance:
            raise ValueError(f"实例不存在: {instance_id}")

        start_time = time.time()

        # 执行 EXPLAIN 分析（异步调用需要用 asyncio.run）
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，创建一个新的线程来运行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self.analyzer.execute_explain(
                            instance=instance,
                            sql=sql_text,
                            database_name=database_name
                        )
                    )
                    explain_result = future.result()
            else:
                explain_result = asyncio.run(self.analyzer.execute_explain(
                    instance=instance,
                    sql=sql_text,
                    database_name=database_name
                ))
        except RuntimeError:
            # 如果没有事件循环，创建一个新的
            explain_result = asyncio.run(self.analyzer.execute_explain(
                instance=instance,
                sql=sql_text,
                database_name=database_name
            ))

        # 规则检测
        rule_issues = self._detect_rule_issues(explain_result)

        # 获取相关表结构
        table_schemas = self._get_relevant_table_schemas(
            instance_id=instance_id,
            database_name=database_name,
            sql_text=sql_text
        )

        # LLM 分析（使用 SDK）
        llm_suggestions = None
        suggested_sql = None
        index_ddl = None
        rollback_sql = None
        risk_level = "low"

        try:
            llm_result = self._llm_analyze_sql(
                sql_text=sql_text,
                explain_result=explain_result,
                table_schemas=table_schemas
            )
            llm_suggestions = llm_result.get("suggestions")
            suggested_sql = llm_result.get("optimized_sql")
            index_ddl = llm_result.get("index_ddl")
            rollback_sql = llm_result.get("rollback_sql")
            risk_level = llm_result.get("risk_level", "low")
        except Exception as e:
            logger.warning(f"LLM 分析失败: {e}")

        analysis_time = time.time() - start_time

        # 创建优化建议
        suggestion = self.create_suggestion(
            OptimizationSuggestionCreate(
                instance_id=instance_id,
                database_name=database_name,
                sql_fingerprint=sql_text[:500],
                sql_sample=sql_text,
                issues=[issue.model_dump() for issue in rule_issues],
                suggestions=[{"type": "llm", "description": llm_suggestions}] if llm_suggestions else [],
                suggested_sql=suggested_sql,
                index_ddl=index_ddl,
                rollback_sql=rollback_sql,
                risk_level=risk_level,
                analysis_time=analysis_time,
                llm_model="doubao"
            )
        )

        return {
            "suggestion_id": suggestion.id,
            "explain_result": explain_result,
            "rule_issues": [issue.model_dump() for issue in rule_issues],
            "llm_suggestions": llm_suggestions,
            "suggested_sql": suggested_sql,
            "index_ddl": index_ddl,
            "risk_level": risk_level,
            "analysis_time": analysis_time
        }

    # ==================== 辅助方法 ====================

    def _get_instance(self, instance_id: int) -> Optional[RDBInstance]:
        """获取实例"""
        query = select(RDBInstance).where(RDBInstance.id == instance_id)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def _get_task(self, task_id: int) -> Optional[SlowQueryCollectionTask]:
        """获取采集任务"""
        query = select(SlowQueryCollectionTask).where(
            SlowQueryCollectionTask.id == task_id
        )
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def _get_task_by_instance(self, instance_id: int) -> Optional[SlowQueryCollectionTask]:
        """根据实例ID获取采集任务"""
        query = select(SlowQueryCollectionTask).where(
            SlowQueryCollectionTask.instance_id == instance_id
        )
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def _find_existing_slow_query(
        self,
        instance_id: int,
        sql_fingerprint: str
    ) -> Optional[SlowQuery]:
        """查找已存在的慢查询记录"""
        query = select(SlowQuery).where(
            and_(
                SlowQuery.instance_id == instance_id,
                SlowQuery.sql_fingerprint == sql_fingerprint[:500]
            )
        ).order_by(desc(SlowQuery.created_at)).limit(1)
        result = self.db.execute(query)
        return result.scalar_one_or_none()

    def _has_suggestion(self, slow_query_id: int) -> bool:
        """检查慢查询是否已有优化建议"""
        query = select(OptimizationSuggestion.id).where(
            OptimizationSuggestion.slow_query_id == slow_query_id
        ).limit(1)
        result = self.db.execute(query)
        return result.scalar_one_or_none() is not None

    def _create_suggestion_from_slow_query(
        self,
        instance: RDBInstance,
        slow_query: SlowQuery,
        enable_llm: bool = True
    ) -> Optional[OptimizationSuggestion]:
        """从慢查询创建优化建议"""
        if not slow_query.sql_sample:
            return None

        # 获取表结构
        table_schemas = self._get_relevant_table_schemas(
            instance_id=instance.id,
            database_name=slow_query.database_name,
            sql_text=slow_query.sql_sample
        )

        # 执行 EXPLAIN
        explain_result = self.analyzer.execute_explain(
            instance=instance,
            sql=slow_query.sql_sample,
            database_name=slow_query.database_name
        )

        # 规则检测
        rule_issues = self._detect_rule_issues(explain_result)

        # LLM 分析
        llm_result = {}
        if enable_llm:
            try:
                llm_result = self._llm_analyze_sql(
                    sql_text=slow_query.sql_sample,
                    explain_result=explain_result,
                    table_schemas=table_schemas
                )
            except Exception as e:
                logger.warning(f"LLM 分析失败: {e}")

        # 记录优化前的平均执行时间
        before_avg_time = slow_query.query_time

        suggestion = OptimizationSuggestion(
            instance_id=instance.id,
            database_name=slow_query.database_name,
            slow_query_id=slow_query.id,
            sql_fingerprint=slow_query.sql_fingerprint[:500],
            sql_sample=slow_query.sql_sample,
            issues=[issue.model_dump() for issue in rule_issues],
            suggestions=[{"type": "llm", "description": llm_result.get("suggestions")}] if llm_result.get("suggestions") else [],
            suggested_sql=llm_result.get("optimized_sql"),
            index_ddl=llm_result.get("index_ddl"),
            rollback_sql=llm_result.get("rollback_sql"),
            risk_level=llm_result.get("risk_level", "low"),
            confidence=llm_result.get("confidence"),
            expected_improvement=llm_result.get("expected_improvement"),
            before_avg_time=before_avg_time,
            table_schemas_used=table_schemas,
            llm_model="doubao" if enable_llm else None
        )

        self.db.add(suggestion)
        self.db.commit()
        self.db.refresh(suggestion)

        return suggestion

    def _get_relevant_table_schemas(
        self,
        instance_id: int,
        database_name: Optional[str],
        sql_text: str
    ) -> List[Dict]:
        """获取 SQL 中涉及的表结构"""
        # 简化实现：从 table_schemas 表获取
        # 实际应该解析 SQL 提取表名
        query = select(TableSchema).where(
            TableSchema.instance_id == instance_id
        )

        if database_name:
            query = query.where(TableSchema.database_name == database_name)

        result = self.db.execute(query.limit(10))
        schemas = result.scalars().all()

        return [
            {
                "database_name": s.database_name,
                "table_name": s.table_name,
                "columns": s.columns_json,
                "indexes": s.indexes_json
            }
            for s in schemas
        ]

    def _llm_analyze_sql(
        self,
        sql_text: str,
        explain_result: Dict[str, Any],
        table_schemas: List[Dict]
    ) -> Dict[str, Any]:
        """使用 LLM 分析 SQL"""
        # 这里使用 coze-coding-dev-sdk 调用豆包大模型
        # 由于当前环境限制，这里返回模拟结果
        # 实际实现需要集成 LLM SDK

        # 简单规则分析
        suggestions = []
        index_ddl = None
        rollback_sql = None
        risk_level = "low"

        # 检查是否全表扫描
        if explain_result.get("explain"):
            for row in explain_result["explain"]:
                if row.get("type") == "ALL":
                    table = row.get("table", "unknown")
                    suggestions.append(
                        f"表 {table} 存在全表扫描，建议添加索引"
                    )

                    # 生成简单的索引建议
                    # 实际应该根据 WHERE 条件分析
                    if table_schemas:
                        index_ddl = f"-- 建议根据查询条件添加索引\n-- CREATE INDEX idx_{table}_xxx ON {table}(column_name);"
                        rollback_sql = f"-- DROP INDEX idx_{table}_xxx ON {table};"

        # 检查是否使用临时表
        for row in explain_result.get("explain", []):
            extra = row.get("Extra", "")
            if "Using temporary" in extra:
                suggestions.append("查询使用了临时表，可能影响性能")

        return {
            "suggestions": "\n".join(suggestions) if suggestions else "SQL 结构良好，无明显优化点",
            "index_ddl": index_ddl,
            "rollback_sql": rollback_sql,
            "optimized_sql": None,
            "risk_level": risk_level,
            "confidence": 0.85
        }

    def _get_avg_query_time_after_optimization(
        self,
        instance: RDBInstance,
        sql_fingerprint: str,
        after_time: datetime
    ) -> Optional[float]:
        """获取优化后的平均执行时间"""
        query = select(SlowQuery).where(
            and_(
                SlowQuery.instance_id == instance.id,
                SlowQuery.sql_fingerprint == sql_fingerprint[:500],
                SlowQuery.last_seen >= after_time
            )
        ).order_by(desc(SlowQuery.last_seen)).limit(10)

        result = self.db.execute(query)
        slow_queries = result.scalars().all()

        if not slow_queries:
            return None

        # 计算平均执行时间
        total_time = sum(sq.query_time or 0 for sq in slow_queries)
        return total_time / len(slow_queries) if slow_queries else None

    def _detect_rule_issues(self, explain_result: Dict[str, Any]) -> List[Any]:
        """规则检测"""
        from app.schemas import RuleIssue

        issues = []

        for row in explain_result.get("explain", []):
            # 全表扫描
            if row.get("type") == "ALL":
                issues.append(RuleIssue(
                    severity="warning",
                    category="index",
                    title="全表扫描",
                    description=f"表 {row.get('table', 'unknown')} 使用了全表扫描",
                    suggestion="考虑添加合适的索引",
                    related_table=row.get("table")
                ))

            # Using filesort
            extra = row.get("Extra", "")
            if "Using filesort" in extra:
                issues.append(RuleIssue(
                    severity="warning",
                    category="performance",
                    title="文件排序",
                    description="查询需要额外的排序操作",
                    suggestion="考虑添加 ORDER BY 相关的索引",
                    related_table=row.get("table")
                ))

            # Using temporary
            if "Using temporary" in extra:
                issues.append(RuleIssue(
                    severity="info",
                    category="performance",
                    title="使用临时表",
                    description="查询使用了临时表",
                    suggestion="检查 GROUP BY 或 DISTINCT 是否可以优化",
                    related_table=row.get("table")
                ))

        return issues

    # ==================== 分析历史管理 ====================
    
    def list_analysis_history(
        self,
        instance_id: Optional[int] = None,
        analysis_type: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list, int]:
        """获取分析历史列表"""
        # 由于没有专门的分析历史表，我们从慢查询和优化建议中构建
        # 这里简化处理，返回空的列表
        # 实际项目中应该有一个专门的分析历史表
        
        query = select(OptimizationSuggestion)
        conditions = []
        
        if instance_id:
            conditions.append(OptimizationSuggestion.instance_id == instance_id)
        
        # 这里可以添加更多的筛选条件
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # 统计总数
        from sqlalchemy import func
        count_subquery = query.subquery()
        total_query = select(func.count()).select_from(count_subquery)
        total_result = self.db.execute(total_query)
        total = total_result.scalar() or 0
        
        # 分页查询
        query = query.order_by(desc(OptimizationSuggestion.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = self.db.execute(query)
        suggestions = result.scalars().all()
        
        # 将建议转换为分析历史格式
        history = []
        for s in suggestions:
            history.append({
                "id": s.id,
                "instance_id": s.instance_id,
                "instance_name": self._get_instance_name(s.instance_id),
                "database_name": s.database_name,
                "sql_fingerprint": s.sql_fingerprint[:100] if s.sql_fingerprint else "",
                "sql_sample": s.sql_sample,
                "analysis_type": "rule",  # 简化处理
                "analysis_content": s.analysis_result,
                "issues": s.issues or [],
                "issues_count": len(s.issues) if s.issues else 0,
                "suggestions": s.suggestions or [],
                "suggestions_count": len(s.suggestions) if s.suggestions else 0,
                "analyzed_by": s.analyzed_by,
                "created_at": s.created_at
            })
        
        return history, total
    
    def _get_instance_name(self, instance_id: int) -> str:
        """获取实例名称"""
        query = select(RDBInstance.name).where(RDBInstance.id == instance_id)
        result = self.db.execute(query)
        name = result.scalar_one_or_none()
        return name or "未知实例"
    
    def get_analysis_detail(self, history_id: int) -> Optional[Dict[str, Any]]:
        """获取分析历史详情"""
        suggestion = self.get_suggestion(history_id)
        if not suggestion:
            return None
        
        return {
            "id": suggestion.id,
            "instance_id": suggestion.instance_id,
            "instance_name": self._get_instance_name(suggestion.instance_id),
            "database_name": suggestion.database_name,
            "sql_fingerprint": suggestion.sql_fingerprint,
            "sql_sample": suggestion.sql_sample,
            "analysis_type": "rule",
            "analysis_content": suggestion.analysis_result,
            "issues": suggestion.issues or [],
            "issues_count": len(suggestion.issues) if suggestion.issues else 0,
            "suggestions": suggestion.suggestions or [],
            "suggestions_count": len(suggestion.suggestions) if suggestion.suggestions else 0,
            "explain_result": suggestion.explain_result,
            "analyzed_by": suggestion.analyzed_by,
            "created_at": suggestion.created_at
        }
    
    # ==================== 慢日志文件上传 ====================
    
    async def upload_slow_log_file(
        self,
        instance_id: int,
        file,
        auto_analyze: bool,
        current_user: User
    ) -> Dict[str, Any]:
        """
        上传慢日志文件
        
        Args:
            instance_id: 实例ID
            file: 上传的文件对象
            auto_analyze: 是否自动分析
            current_user: 当前用户
        
        Returns:
            文件信息字典
        """
        from app.models import SlowLogFile
        from datetime import datetime, timedelta
        import os
        import hashlib
        import aiofiles
        
        # 检查实例是否存在
        instance = self._get_instance(instance_id)
        if not instance:
            raise ValueError(f"实例不存在: {instance_id}")
        
        # 验证文件类型
        filename = file.filename or ""
        if not (filename.endswith('.log') or filename.endswith('.txt')):
            raise ValueError("仅支持 .log 或 .txt 格式的慢日志文件")
        
        # 创建上传目录
        upload_dir = "/tmp/slow_log_files"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 计算文件哈希（用于去重）
        file_hash = hashlib.md5()
        content = await file.read()
        file_hash.update(content)
        hash_value = file_hash.hexdigest()
        
        # 重置文件指针
        await file.seek(0)
        
        # 检查是否已存在相同文件
        existing = self.db.query(SlowLogFile).filter(
            SlowLogFile.instance_id == instance_id,
            SlowLogFile.file_hash == hash_value
        ).first()
        
        if existing:
            # 文件已存在，返回已有记录
            logger.info(f"文件已存在: file_id={existing.id}, hash={hash_value}")
            return self._format_file_info(existing)
        
        # 保存文件
        file_path = os.path.join(upload_dir, f"{instance_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}")
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        file_size = len(content)
        
        # 创建数据库记录
        expire_at = datetime.now() + timedelta(days=30)
        
        slow_log_file = SlowLogFile(
            instance_id=instance_id,
            file_name=filename,
            file_path=file_path,
            file_size=file_size,
            file_hash=hash_value,
            parse_status="pending",
            analyze_status="pending",
            uploaded_by=current_user.username,
            expire_at=expire_at
        )
        
        self.db.add(slow_log_file)
        self.db.commit()
        self.db.refresh(slow_log_file)
        
        logger.info(f"上传慢日志文件: file_id={slow_log_file.id}, instance_id={instance_id}")
        
        # 自动解析和分析
        if auto_analyze:
            try:
                self.parse_slow_log_file(slow_log_file.id)
                self.analyze_slow_log_file(slow_log_file.id, current_user)
            except Exception as e:
                logger.error(f"自动解析分析失败: {e}")
        
        return self._format_file_info(slow_log_file)
    
    def parse_slow_log_file(self, file_id: int) -> Dict[str, Any]:
        """
        解析慢日志文件
        
        Args:
            file_id: 文件ID
        
        Returns:
            解析结果
        """
        from app.models import SlowLogFile
        import re
        
        slow_log_file = self.db.query(SlowLogFile).filter(SlowLogFile.id == file_id).first()
        if not slow_log_file:
            raise ValueError(f"文件不存在: {file_id}")
        
        try:
            # 更新解析状态
            slow_log_file.parse_status = "parsing"
            self.db.commit()
            
            # 读取文件内容
            with open(slow_log_file.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 解析慢日志（MySQL 格式）
            # 示例格式：
            # # Time: 2024-01-01T10:00:00.000000Z
            # # User@Host: root[root] @ localhost []
            # # Query_time: 5.000000  Lock_time: 0.000000 Rows_sent: 1  Rows_examined: 10000
            # SET timestamp=1704100800;
            # SELECT * FROM users WHERE name = 'test';
            
            parsed_queries = []
            
            # MySQL 慢查询日志解析
            pattern = r'# Time:.*?\n# User@Host:.*?\n# Query_time:\s*([\d.]+).*?Rows_sent:\s*(\d+).*?Rows_examined:\s*(\d+).*?\n.*?\n(.*?)(?=# Time:|$)'
            matches = re.findall(pattern, content, re.DOTALL)
            
            for match in matches:
                query_time = float(match[0])
                rows_sent = int(match[1])
                rows_examined = int(match[2])
                sql = match[3].strip()
                
                # 跳过空SQL或系统SQL
                if not sql or sql.startswith('#'):
                    continue
                
                parsed_queries.append({
                    "query_time": query_time,
                    "rows_sent": rows_sent,
                    "rows_examined": rows_examined,
                    "sql": sql
                })
            
            # 存储解析结果
            slow_log_file.parsed_queries = parsed_queries
            slow_log_file.parsed_count = len(parsed_queries)
            slow_log_file.parse_status = "completed"
            self.db.commit()
            
            logger.info(f"解析慢日志文件完成: file_id={file_id}, parsed_count={len(parsed_queries)}")
            
            return {
                "file_id": file_id,
                "parsed_count": len(parsed_queries),
                "status": "completed"
            }
            
        except Exception as e:
            slow_log_file.parse_status = "failed"
            slow_log_file.parse_error = str(e)
            self.db.commit()
            
            logger.error(f"解析慢日志文件失败: file_id={file_id}, error={str(e)}")
            raise
    
    def analyze_slow_log_file(
        self,
        file_id: int,
        current_user: User
    ) -> Dict[str, Any]:
        """
        分析慢日志文件
        
        Args:
            file_id: 文件ID
            current_user: 当前用户
        
        Returns:
            分析结果
        """
        from app.models import SlowLogFile, SQLAnalysisHistory
        from datetime import datetime, timedelta
        import json
        
        slow_log_file = self.db.query(SlowLogFile).filter(SlowLogFile.id == file_id).first()
        if not slow_log_file:
            raise ValueError(f"文件不存在: {file_id}")
        
        if slow_log_file.parse_status != "completed":
            raise ValueError(f"文件尚未解析完成: {slow_log_file.parse_status}")
        
        if slow_log_file.analyze_status == "analyzing":
            raise ValueError("文件正在分析中")
        
        try:
            # 更新分析状态
            slow_log_file.analyze_status = "analyzing"
            self.db.commit()
            
            parsed_queries = slow_log_file.parsed_queries or []
            analyzed_count = 0
            suggestion_count = 0
            
            # 对每个查询进行分析
            for query_data in parsed_queries:
                try:
                    # 创建分析历史记录
                    expire_at = datetime.now() + timedelta(days=365)
                    
                    # 对SQL进行去重（基于SQL指纹）
                    sql = query_data.get("sql", "")
                    sql_fingerprint = self._generate_sql_fingerprint(sql)
                    
                    # 检查是否已分析过
                    existing = self.db.query(SQLAnalysisHistory).filter(
                        SQLAnalysisHistory.source_file_id == file_id,
                        SQLAnalysisHistory.sql_fingerprint == sql_fingerprint
                    ).first()
                    
                    if existing:
                        continue
                    
                    # 执行规则分析
                    issues = self._analyze_sql_rules(sql, query_data)
                    
                    # 创建分析历史
                    analysis = SQLAnalysisHistory(
                        instance_id=slow_log_file.instance_id,
                        source_file_id=file_id,
                        analysis_type="file_upload",
                        sql_fingerprint=sql_fingerprint,
                        sql_sample=sql,
                        analysis_content={
                            "query_time": query_data.get("query_time"),
                            "rows_sent": query_data.get("rows_sent"),
                            "rows_examined": query_data.get("rows_examined"),
                            "issues": issues
                        },
                        issues=issues,
                        suggestions=self._generate_suggestions(issues),
                        analyzed_by=current_user.username,
                        expire_at=expire_at
                    )
                    
                    self.db.add(analysis)
                    analyzed_count += 1
                    
                    if issues:
                        suggestion_count += 1
                    
                except Exception as e:
                    logger.error(f"分析查询失败: {str(e)}")
            
            self.db.commit()
            
            # 更新文件分析状态
            slow_log_file.analyze_status = "completed"
            slow_log_file.analyzed_count = analyzed_count
            slow_log_file.suggestion_count = suggestion_count
            self.db.commit()
            
            logger.info(f"分析慢日志文件完成: file_id={file_id}, analyzed_count={analyzed_count}")
            
            return {
                "file_id": file_id,
                "analyzed_count": analyzed_count,
                "suggestion_count": suggestion_count,
                "status": "completed"
            }
            
        except Exception as e:
            slow_log_file.analyze_status = "failed"
            self.db.commit()
            
            logger.error(f"分析慢日志文件失败: file_id={file_id}, error={str(e)}")
            raise
    
    def _generate_sql_fingerprint(self, sql: str) -> str:
        """生成SQL指纹（用于去重）"""
        import hashlib
        # 简化处理：移除空白字符、参数值等
        normalized = ' '.join(sql.split()).lower()
        # 移除字符串字面值
        import re
        normalized = re.sub(r"'[^']*'", "?", normalized)
        normalized = re.sub(r'"[^"]*"', "?", normalized)
        # 移除数字
        normalized = re.sub(r'\b\d+\b', "?", normalized)
        # 生成哈希
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _analyze_sql_rules(self, sql: str, query_data: Dict) -> List[Dict]:
        """
        基于规则分析SQL
        
        Args:
            sql: SQL语句
            query_data: 查询数据
        
        Returns:
            问题列表
        """
        issues = []
        
        # 检查查询时间
        query_time = query_data.get("query_time", 0)
        if query_time > 10:
            issues.append({
                "severity": "error",
                "category": "performance",
                "title": "查询时间过长",
                "description": f"查询执行时间 {query_time}秒，超过阈值10秒",
                "suggestion": "建议添加索引或优化查询"
            })
        elif query_time > 5:
            issues.append({
                "severity": "warning",
                "category": "performance",
                "title": "查询时间较长",
                "description": f"查询执行时间 {query_time}秒",
                "suggestion": "建议检查是否可以优化"
            })
        
        # 检查扫描行数
        rows_examined = query_data.get("rows_examined", 0)
        rows_sent = query_data.get("rows_sent", 0)
        
        if rows_examined > 10000 and rows_sent > 0:
            scan_ratio = rows_examined / rows_sent
            if scan_ratio > 100:
                issues.append({
                    "severity": "warning",
                    "category": "index",
                    "title": "扫描行数过多",
                    "description": f"扫描了 {rows_examined} 行，只返回 {rows_sent} 行，扫描比 {scan_ratio:.1f}",
                    "suggestion": "建议添加索引减少扫描行数"
                })
        
        # 检查全表扫描
        sql_upper = sql.upper()
        if "SELECT * FROM" in sql_upper or "SELECT *" in sql_upper:
            issues.append({
                "severity": "warning",
                "category": "best_practice",
                "title": "使用 SELECT *",
                "description": "查询使用了 SELECT *，可能返回不必要的数据",
                "suggestion": "建议明确指定需要的列"
            })
        
        # 检查没有WHERE子句
        if "WHERE" not in sql_upper and "SELECT" in sql_upper:
            issues.append({
                "severity": "info",
                "category": "best_practice",
                "title": "缺少WHERE条件",
                "description": "查询没有WHERE条件，可能返回大量数据",
                "suggestion": "建议添加适当的过滤条件"
            })
        
        return issues
    
    def _generate_suggestions(self, issues: List[Dict]) -> List[Dict]:
        """根据问题生成建议"""
        suggestions = []
        
        for issue in issues:
            suggestions.append({
                "type": "rule",
                "priority": issue.get("severity"),
                "description": issue.get("suggestion"),
                "related_issue": issue.get("title")
            })
        
        return suggestions
    
    def list_slow_log_files(
        self,
        instance_id: Optional[int] = None,
        parse_status: Optional[str] = None,
        analyze_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[list, int]:
        """获取慢日志文件列表"""
        from app.models import SlowLogFile
        
        query = self.db.query(SlowLogFile)
        
        if instance_id:
            query = query.filter(SlowLogFile.instance_id == instance_id)
        if parse_status:
            query = query.filter(SlowLogFile.parse_status == parse_status)
        if analyze_status:
            query = query.filter(SlowLogFile.analyze_status == analyze_status)
        
        # 统计总数
        total = query.count()
        
        # 分页查询
        files = query.order_by(desc(SlowLogFile.created_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return [self._format_file_info(f) for f in files], total
    
    def get_slow_log_file(self, file_id: int) -> Optional[Dict[str, Any]]:
        """获取慢日志文件详情"""
        from app.models import SlowLogFile
        
        file = self.db.query(SlowLogFile).filter(SlowLogFile.id == file_id).first()
        if not file:
            return None
        
        return self._format_file_info(file)
    
    def delete_slow_log_file(self, file_id: int) -> bool:
        """删除慢日志文件"""
        from app.models import SlowLogFile
        import os
        
        file = self.db.query(SlowLogFile).filter(SlowLogFile.id == file_id).first()
        if not file:
            return False
        
        # 删除物理文件
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
        
        # 删除数据库记录（关联的分析历史会被级联删除）
        self.db.delete(file)
        self.db.commit()
        
        logger.info(f"删除慢日志文件: file_id={file_id}")
        return True
    
    def _format_file_info(self, file) -> Dict[str, Any]:
        """格式化文件信息"""
        return {
            "id": file.id,
            "instance_id": file.instance_id,
            "instance_name": self._get_instance_name(file.instance_id),
            "file_name": file.file_name,
            "file_size": file.file_size,
            "file_hash": file.file_hash,
            "parse_status": file.parse_status,
            "parse_error": file.parse_error,
            "parsed_count": file.parsed_count,
            "analyze_status": file.analyze_status,
            "analyzed_count": file.analyzed_count,
            "suggestion_count": file.suggestion_count,
            "uploaded_by": file.uploaded_by,
            "expire_at": file.expire_at,
            "created_at": file.created_at
        }
