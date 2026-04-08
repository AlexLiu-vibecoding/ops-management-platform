"""
密钥轮换服务
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from app.models.key_rotation import KeyRotationLog, KeyRotationConfig
from app.utils.auth import AESCipher

logger = logging.getLogger(__name__)


class KeyRotationService:
    """密钥轮换服务"""

    def __init__(self, db: Session, operator_id: Optional[int] = None):
        """
        初始化服务
        
        Args:
            db: 数据库会话
            operator_id: 操作人 ID
        """
        self.db = db
        self.operator_id = operator_id

    def get_config(self) -> KeyRotationConfig:
        """获取轮换配置"""
        config = self.db.query(KeyRotationConfig).first()
        if not config:
            # 创建默认配置
            config = KeyRotationConfig(
                enabled=False,
                schedule_type="monthly",
                schedule_day=1,
                schedule_time="02:00",
                current_key_id="v1",
                auto_switch=False
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
        return config

    def update_config(
        self,
        enabled: Optional[bool] = None,
        schedule_type: Optional[str] = None,
        schedule_day: Optional[int] = None,
        schedule_time: Optional[str] = None,
        auto_switch: Optional[bool] = None
    ) -> KeyRotationConfig:
        """更新轮换配置"""
        config = self.get_config()
        
        if enabled is not None:
            config.enabled = enabled
        if schedule_type is not None:
            config.schedule_type = schedule_type
        if schedule_day is not None:
            config.schedule_day = schedule_day
        if schedule_time is not None:
            config.schedule_time = schedule_time
        if auto_switch is not None:
            config.auto_switch = auto_switch
        
        self.db.commit()
        self.db.refresh(config)
        return config

    def get_history(self, limit: int = 20, offset: int = 0) -> List[KeyRotationLog]:
        """获取轮换历史"""
        return (
            self.db.query(KeyRotationLog)
            .order_by(KeyRotationLog.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_history(self) -> int:
        """统计历史记录数"""
        return self.db.query(KeyRotationLog).count()

    def add_log(
        self,
        action: str,
        status: str,
        from_version: Optional[str] = None,
        to_version: Optional[str] = None,
        total_records: int = 0,
        migrated_records: int = 0,
        failed_records: int = 0,
        error_message: Optional[str] = None
    ) -> KeyRotationLog:
        """添加轮换日志"""
        log = KeyRotationLog(
            action=action,
            from_version=from_version,
            to_version=to_version,
            status=status,
            total_records=total_records,
            migrated_records=migrated_records,
            failed_records=failed_records,
            error_message=error_message,
            operator_id=self.operator_id
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def get_statistics(self) -> Dict[str, Any]:
        """获取加密数据统计"""
        from sqlalchemy import text, func
        
        tables_fields = [
            ("rdb_instances", "password_encrypted"),
            ("redis_instances", "password_encrypted"),
            ("ai_models", "api_key_encrypted"),
            ("aws_credentials", "aws_secret_access_key"),
        ]
        
        total = 0
        by_version = {"v1": 0, "v2": 0, "legacy": 0, "empty": 0}
        
        for table, field in tables_fields:
            try:
                # 检查表是否存在
                check_query = f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    )
                """
                exists = self.db.execute(text(check_query)).scalar()
                if not exists:
                    continue
                
                # 统计总数
                count_query = f"""
                    SELECT COUNT(*) FROM {table} 
                    WHERE {field} IS NOT NULL AND {field} != ''
                """
                count = self.db.execute(text(count_query)).scalar() or 0
                total += count
                
                # 按版本统计
                for version in ["v1", "v2"]:
                    version_query = f"""
                        SELECT COUNT(*) FROM {table} 
                        WHERE {field} LIKE '{version}$%'
                    """
                    version_count = self.db.execute(text(version_query)).scalar() or 0
                    by_version[version] += version_count
                
                # legacy = 总数 - v1 - v2
                by_version["legacy"] += count - by_version.get("v1", 0) - by_version.get("v2", 0)
                
            except Exception as e:
                logger.warning(f"统计表 {table} 失败: {e}")
        
        # 修正 legacy 计算
        by_version["legacy"] = max(0, total - by_version["v1"] - by_version["v2"])
        
        return {
            "total": total,
            "v1_count": by_version["v1"],
            "v2_count": by_version["v2"],
            "legacy_count": by_version["legacy"],
            "needs_migration": by_version["v1"] + by_version["legacy"]
        }

    def execute_migration(self, batch_size: int = 100) -> Dict[str, Any]:
        """执行数据迁移"""
        from sqlalchemy import text
        from app.config import settings
        
        results = []
        total_migrated = 0
        total_failed = 0
        
        # 获取 v2_key（优先使用数据库中的，如果没有则使用环境变量）
        config = self.get_config()
        v2_key = config.v2_key or settings.security.AES_KEY_V2
        
        if not v2_key:
            return {
                "success": False,
                "results": [{"error": "V2 密钥未配置"}],
                "total_migrated": 0,
                "total_failed": 0
            }
        
        tables_fields = [
            ("rdb_instances", "password_encrypted"),
            ("redis_instances", "password_encrypted"),
            ("ai_models", "api_key_encrypted"),
            ("aws_credentials", "aws_secret_access_key"),
        ]
        
        for table, field in tables_fields:
            try:
                # 检查表是否存在
                check_query = f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    )
                """
                exists = self.db.execute(text(check_query)).scalar()
                if not exists:
                    continue
                
                # 获取需要迁移的记录（v1 或 legacy 格式）
                select_query = f"""
                    SELECT id, {field} FROM {table} 
                    WHERE {field} IS NOT NULL 
                    AND {field} != ''
                    AND NOT ({field} LIKE 'v2$%')
                    LIMIT :batch_size
                """
                rows = self.db.execute(text(select_query), {"batch_size": batch_size}).fetchall()
                
                migrated = 0
                failed = 0
                errors = []
                
                for row in rows:
                    record_id = row[0]
                    old_value = row[1]
                    
                    try:
                        # 解密并重新加密（使用 v2_key）
                        plaintext = AESCipher.decrypt(old_value)
                        new_value = AESCipher(v2_key).encrypt(plaintext)
                        
                        # 更新数据库
                        update_query = f"""
                            UPDATE {table} 
                            SET {field} = :new_value 
                            WHERE id = :id
                        """
                        self.db.execute(text(update_query), {"new_value": new_value, "id": record_id})
                        migrated += 1
                        
                    except Exception as e:
                        failed += 1
                        error_msg = f"ID={record_id}: {str(e)}"
                        errors.append(error_msg)
                        logger.warning(f"迁移 {table}.{field} {error_msg}")
                
                self.db.commit()
                
                results.append({
                    "table_name": table,
                    "field_name": field,
                    "total": len(rows),
                    "migrated": migrated,
                    "failed": failed,
                    "errors": errors[:10]
                })
                
                total_migrated += migrated
                total_failed += failed
                
            except Exception as e:
                logger.error(f"迁移表 {table}.{field} 失败: {e}")
                self.db.rollback()
                results.append({
                    "table_name": table,
                    "field_name": field,
                    "total": 0,
                    "migrated": 0,
                    "failed": 0,
                    "errors": [str(e)]
                })
        
        # 记录日志
        self.add_log(
            action="migrate",
            status="success" if total_failed == 0 else "partial",
            from_version="v1/legacy",
            to_version="v2",
            total_records=total_migrated + total_failed,
            migrated_records=total_migrated,
            failed_records=total_failed,
            error_message=f"迁移完成，成功 {total_migrated}，失败 {total_failed}" if total_failed > 0 else None
        )
        
        return {
            "success": total_failed == 0,
            "results": results,
            "total_migrated": total_migrated,
            "total_failed": total_failed
        }

    def preview_migration(self) -> List[Dict[str, Any]]:
        """预览迁移"""
        from sqlalchemy import text
        
        results = []
        
        tables_fields = [
            ("rdb_instances", "password_encrypted", "RDB 实例密码"),
            ("redis_instances", "password_encrypted", "Redis 实例密码"),
            ("ai_models", "api_key_encrypted", "AI 模型 API 密钥"),
            ("aws_credentials", "aws_secret_access_key", "AWS 访问密钥"),
        ]
        
        for table, field, description in tables_fields:
            try:
                # 检查表是否存在
                check_query = f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    )
                """
                exists = self.db.execute(text(check_query)).scalar()
                if not exists:
                    continue
                
                # 统计总数
                count_query = f"""
                    SELECT COUNT(*) FROM {table} 
                    WHERE {field} IS NOT NULL AND {field} != ''
                """
                total = self.db.execute(text(count_query)).scalar() or 0
                
                # 统计 v2 数量
                v2_query = f"""
                    SELECT COUNT(*) FROM {table} 
                    WHERE {field} LIKE 'v2$%'
                """
                v2_count = self.db.execute(text(v2_query)).scalar() or 0
                
                results.append({
                    "table_name": table,
                    "field_name": field,
                    "description": description,
                    "total": total,
                    "v1_or_legacy": total - v2_count,
                    "v2": v2_count
                })
                
            except Exception as e:
                logger.warning(f"预览表 {table} 失败: {e}")
                results.append({
                    "table_name": table,
                    "field_name": field,
                    "description": description,
                    "total": 0,
                    "v1_or_legacy": 0,
                    "v2": 0
                })
        
        # 记录预览日志
        total_needs = sum(r["v1_or_legacy"] for r in results)
        self.add_log(
            action="preview",
            status="success",
            from_version="v1/legacy",
            to_version="v2",
            total_records=total_needs,
            migrated_records=0,
            failed_records=0,
            error_message=None
        )
        
        return results

    def switch_version(self, target_version: str) -> bool:
        """切换密钥版本"""
        from app.config import settings
        
        if target_version not in ["v1", "v2"]:
            return False
        
        if target_version == "v2" and not settings.security.has_aes_key_v2():
            return False
        
        config = self.get_config()
        old_version = config.current_key_id
        config.current_key_id = target_version
        
        self.db.commit()
        
        # 记录日志
        self.add_log(
            action="switch",
            status="success",
            from_version=old_version,
            to_version=target_version,
            total_records=0,
            migrated_records=0,
            failed_records=0,
            error_message=None
        )
        
        return True

    def calculate_next_rotation(self) -> datetime:
        """计算下次轮换时间"""
        import calendar
        from datetime import timedelta
        
        config = self.get_config()
        now = datetime.now()
        
        if config.schedule_type == "weekly":
            # 每周执行
            days_ahead = config.schedule_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_rotation = now + timedelta(days=days_ahead)
            
        elif config.schedule_type == "monthly":
            # 每月执行
            if now.day < config.schedule_day:
                next_rotation = now.replace(day=config.schedule_day, hour=2, minute=0, second=0)
            else:
                # 下个月
                if now.month == 12:
                    next_rotation = now.replace(year=now.year + 1, month=1, day=config.schedule_day, hour=2, minute=0, second=0)
                else:
                    next_rotation = now.replace(month=now.month + 1, day=config.schedule_day, hour=2, minute=0, second=0)
        else:
            # 每季度
            quarter_months = [1, 4, 7, 10]
            current_quarter_start = ((now.month - 1) // 3) * 3 + 1
            next_quarter_month = current_quarter_start + 3
            if next_quarter_month > 12:
                next_quarter_month -= 12
                next_year = now.year + 1
            else:
                next_year = now.year
            
            next_rotation = datetime(
                year=next_year,
                month=next_quarter_month,
                day=config.schedule_day,
                hour=2, minute=0, second=0
            )
        
        return next_rotation
