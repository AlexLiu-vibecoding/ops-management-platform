"""
SQL 优化闭环服务

提供 SQL 性能优化的完整闭环能力：
- 慢 SQL 自动采集
- 周期性 LLM 分析
- 优化建议存储
- 一键提交变更
- 效果验证
"""
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

        # 执行 EXPLAIN 分析
        explain_result = self.analyzer.execute_explain(
            instance=instance,
            sql=sql_text,
            database_name=database_name
        )

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
