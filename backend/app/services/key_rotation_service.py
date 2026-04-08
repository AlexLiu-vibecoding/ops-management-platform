"""
密钥轮换服务 - 支持动态多版本
"""

import secrets
import re
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.key_rotation import KeyRotationLog, KeyRotationConfig, KeyRotationKey
from app.utils.auth import AESCipher
from app.config import settings

logger = logging.getLogger(__name__)


class KeyRotationService:
    """密钥轮换服务 - 支持动态多版本"""

    def __init__(self, db: Session, operator_id: Optional[int] = None):
        self.db = db
        self.operator_id = operator_id

    def get_or_create_initial_key(self) -> KeyRotationKey:
        """获取或创建初始密钥（V1）"""
        # 检查是否已有密钥
        existing = self.db.query(KeyRotationKey).first()
        if existing:
            return existing
        
        # 获取初始密钥（优先环境变量，否则生成）
        initial_key = settings.security.AES_KEY
        if not initial_key:
            initial_key = "dev-aes-key-32-characters-please!"
        
        # 创建 V1 密钥
        key = KeyRotationKey(
            key_id="v1",
            key_value=initial_key,
            is_active=True
        )
        self.db.add(key)
        self.db.commit()
        self.db.refresh(key)
        return key

    def get_next_key_version(self) -> str:
        """获取下一个密钥版本号"""
        # 获取所有密钥版本号
        keys = self.db.query(KeyRotationKey).all()
        if not keys:
            return "v1"
        
        # 解析版本号
        versions = []
        for k in keys:
            match = re.match(r'v(\d+)', k.key_id)
            if match:
                versions.append(int(match.group(1)))
        
        if not versions:
            return "v1"
        
        return f"v{max(versions) + 1}"

    def get_active_key(self) -> Optional[KeyRotationKey]:
        """获取当前激活的密钥"""
        return self.db.query(KeyRotationKey).filter(
            KeyRotationKey.is_active == True
        ).first()

    def get_key_by_id(self, key_id: str) -> Optional[KeyRotationKey]:
        """根据版本号获取密钥"""
        return self.db.query(KeyRotationKey).filter(
            KeyRotationKey.key_id == key_id
        ).first()

    def generate_new_key(self) -> KeyRotationKey:
        """生成新的密钥版本"""
        new_version = self.get_next_key_version()
        new_key_value = secrets.token_hex(16)  # 32字符
        
        new_key = KeyRotationKey(
            key_id=new_version,
            key_value=new_key_value,
            is_active=False
        )
        self.db.add(new_key)
        self.db.commit()
        self.db.refresh(new_key)
        
        logger.info(f"生成新密钥: {new_version}")
        return new_key

    def get_all_keys(self) -> List[KeyRotationKey]:
        """获取所有密钥"""
        return self.db.query(KeyRotationKey).order_by(
            KeyRotationKey.created_at.asc()
        ).all()

    # ==================== 配置管理 ====================

    def get_config(self) -> KeyRotationConfig:
        """获取轮换配置"""
        config = self.db.query(KeyRotationConfig).first()
        if not config:
            # 确保有初始密钥
            self.get_or_create_initial_key()
            
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

    def get_overview(self) -> Dict[str, Any]:
        """获取密钥轮换概览（用于仪表盘显示）"""
        config = self.get_config()
        keys = self.get_all_keys()
        stats = self.get_statistics()
        
        # 获取最新创建的密钥
        latest_key = keys[0] if keys else None
        
        return {
            "current_version": config.current_key_id,
            "total_keys": len(keys),
            "total_records": stats["total"],
            "latest_key_created_at": latest_key.created_at.isoformat() if latest_key else None
        }

    def get_status(self) -> Dict[str, Any]:
        """获取密钥轮换状态"""
        config = self.get_config()
        keys = self.get_all_keys()
        stats = self.get_statistics()
        
        # 获取当前密钥
        current_key = self.get_key_by_id(config.current_key_id)
        
        # 检查是否有待迁移的数据
        needs_migration = stats["needs_migration"] > 0
        
        return {
            "current_version": config.current_key_id,
            "can_rotate": len(keys) > 0,
            "reason": None if len(keys) > 0 else "没有可用密钥",
            "migration_needed": needs_migration,
            "unrotated_count": stats["needs_migration"],
            "total_versions": len(keys),
            "current_key_preview": current_key.key_value[:4] + "***" if current_key else "",
            "has_pending_key": any(not k.is_active for k in keys)
        }

    # ==================== 历史记录 ====================

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

    # ==================== 统计 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """获取加密数据统计"""
        config = self.get_config()
        keys = self.get_all_keys()
        
        # 获取所有密钥版本号，用于匹配加密数据前缀
        key_versions = [k.key_id for k in keys]  # 如 ["v1", "v2", "v3"]
        
        tables_fields = [
            ("rdb_instances", "password_encrypted"),
            ("redis_instances", "password_encrypted"),
            ("ai_models", "api_key_encrypted"),
            ("aws_credentials", "aws_secret_access_key"),
        ]
        
        total = 0
        by_version = {}
        legacy_count = 0
        
        for version in key_versions:
            by_version[version] = 0
        
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
                for version in key_versions:
                    version_query = f"""
                        SELECT COUNT(*) FROM {table} 
                        WHERE {field} LIKE '{version}$%'
                    """
                    version_count = self.db.execute(text(version_query)).scalar() or 0
                    by_version[version] += version_count
                
            except Exception as e:
                logger.warning(f"统计表 {table} 失败: {e}")
        
        # 计算待迁移数（legacy + 旧版本）
        current_version = config.current_key_id
        current_idx = key_versions.index(current_version) if current_version in key_versions else 0
        
        needs_migration = 0
        for i, version in enumerate(key_versions):
            if i < current_idx:
                needs_migration += by_version.get(version, 0)
        
        # legacy = 总数 - 所有已知版本
        known_version_count = sum(by_version.values())
        legacy_count = max(0, total - known_version_count)
        needs_migration += legacy_count
        
        return {
            "total": total,
            "by_version": by_version,
            "legacy_count": legacy_count,
            "needs_migration": needs_migration,
            "versions": key_versions
        }

    # ==================== 迁移 ====================

    def get_next_key_for_migration(self) -> Optional[KeyRotationKey]:
        """获取下一个待迁移的密钥（当前未激活且版本最高的）"""
        keys = self.db.query(KeyRotationKey).filter(
            KeyRotationKey.is_active == False
        ).all()
        
        if not keys:
            return None
        
        # 返回版本最高的未激活密钥
        versions = []
        for k in keys:
            match = re.match(r'v(\d+)', k.key_id)
            if match:
                versions.append((int(match.group(1)), k))
        
        if not versions:
            return None
        
        versions.sort(key=lambda x: x[0])
        return versions[-1][1]  # 返回版本号最大的

    def preview_migration(self) -> List[Dict[str, Any]]:
        """预览迁移"""
        config = self.get_config()
        keys = self.get_all_keys()
        next_key = self.get_next_key_for_migration()
        
        if not next_key:
            # 如果没有待迁移的密钥，返回当前版本统计
            return [{
                "description": "所有数据已迁移到最新版本",
                "total": 0,
                "migrated": 0,
                "pending": 0,
                "target_version": config.current_key_id
            }]
        
        tables_fields = [
            ("rdb_instances", "password_encrypted", "RDB 实例密码"),
            ("redis_instances", "password_encrypted", "Redis 实例密码"),
            ("ai_models", "api_key_encrypted", "AI 模型 API 密钥"),
            ("aws_credentials", "aws_secret_access_key", "AWS 访问密钥"),
        ]
        
        results = []
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
                
                # 统计目标版本数量
                target_query = f"""
                    SELECT COUNT(*) FROM {table} 
                    WHERE {field} LIKE '{next_key.key_id}$%'
                """
                migrated = self.db.execute(text(target_query)).scalar() or 0
                
                results.append({
                    "description": description,
                    "table": table,
                    "field": field,
                    "total": total,
                    "migrated": migrated,
                    "pending": total - migrated,
                    "target_version": next_key.key_id
                })
                
            except Exception as e:
                logger.warning(f"预览表 {table} 失败: {e}")
        
        return results

    def execute_migration(self, batch_size: int = 100) -> Dict[str, Any]:
        """执行数据迁移"""
        next_key = self.get_next_key_for_migration()
        
        if not next_key:
            return {
                "success": False,
                "message": "没有待迁移的密钥",
                "results": [],
                "total_migrated": 0,
                "total_failed": 0,
                "target_version": None
            }
        
        tables_fields = [
            ("rdb_instances", "password_encrypted"),
            ("redis_instances", "password_encrypted"),
            ("ai_models", "api_key_encrypted"),
            ("aws_credentials", "aws_secret_access_key"),
        ]
        
        results = []
        total_migrated = 0
        total_failed = 0
        
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
                
                # 获取需要迁移的记录（不是目标版本）
                select_query = f"""
                    SELECT id, {field} FROM {table} 
                    WHERE {field} IS NOT NULL 
                    AND {field} != ''
                    AND NOT ({field} LIKE :target_prefix)
                    LIMIT :batch_size
                """
                rows = self.db.execute(text(select_query), {
                    "target_prefix": f"{next_key.key_id}$%",
                    "batch_size": batch_size
                }).fetchall()
                
                migrated = 0
                failed = 0
                errors = []
                
                for row in rows:
                    record_id = row[0]
                    old_value = row[1]
                    
                    try:
                        # 解密并重新加密
                        plaintext = AESCipher.decrypt(old_value)
                        new_value = AESCipher(next_key.key_value).encrypt(plaintext)
                        
                        # 更新数据库
                        update_query = f"""
                            UPDATE {table} 
                            SET {field} = :new_value 
                            WHERE id = :id
                        """
                        self.db.execute(text(update_query), {
                            "new_value": new_value,
                            "id": record_id
                        })
                        migrated += 1
                        
                    except Exception as e:
                        failed += 1
                        errors.append(f"ID={record_id}: {str(e)}")
                
                self.db.commit()
                
                results.append({
                    "table": table,
                    "field": field,
                    "total": len(rows),
                    "migrated": migrated,
                    "failed": failed,
                    "errors": errors[:5]
                })
                
                total_migrated += migrated
                total_failed += failed
                
            except Exception as e:
                logger.error(f"迁移表 {table} 失败: {e}")
                self.db.rollback()
                results.append({
                    "table": table,
                    "field": field,
                    "total": 0,
                    "migrated": 0,
                    "failed": 0,
                    "errors": [str(e)]
                })
        
        # 汇总所有错误
        all_errors = []
        for r in results:
            if r.get("errors"):
                all_errors.extend(r["errors"][:3])  # 每个表最多取3条
        error_message = "; ".join(all_errors[:10]) if all_errors else None
        
        # 记录日志
        self.add_log(
            action="migrate",
            status="success" if total_failed == 0 else "partial",
            from_version=self.get_active_key().key_id if self.get_active_key() else None,
            to_version=next_key.key_id,
            total_records=total_migrated + total_failed,
            migrated_records=total_migrated,
            failed_records=total_failed,
            error_message=error_message
        )
        
        return {
            "success": total_failed == 0,
            "message": f"迁移到 {next_key.key_id} 完成",
            "results": results,
            "total_migrated": total_migrated,
            "total_failed": total_failed,
            "target_version": next_key.key_id
        }

    def switch_version(self, target_version: str) -> bool:
        """切换密钥版本"""
        # 获取目标密钥
        target_key = self.get_key_by_id(target_version)
        if not target_key:
            logger.warning(f"密钥版本 {target_version} 不存在")
            return False
        
        # 获取当前密钥
        current_key = self.get_active_key()
        old_version = current_key.key_id if current_key else None
        
        # 如果切换到不同版本，先执行迁移
        total_migrated = 0
        total_failed = 0
        error_msg = None
        if old_version and old_version != target_version:
            logger.info(f"切换前先迁移数据: {old_version} -> {target_version}")
            migration_result = self.migrate_to_key(target_key.key_id)
            total_migrated = migration_result.get("total_migrated", 0)
            total_failed = migration_result.get("total_failed", 0)
            if total_failed > 0:
                error_msg = f"迁移失败 {total_failed} 条"
        
        # 标记所有密钥为非活跃
        self.db.query(KeyRotationKey).update({KeyRotationKey.is_active: False})
        
        # 激活目标密钥
        target_key.is_active = True
        
        # 更新配置中的当前版本
        config = self.get_config()
        config.current_key_id = target_version
        config.last_rotation_at = datetime.now()
        
        self.db.commit()
        
        # 记录日志
        self.add_log(
            action="switch",
            status="success" if total_failed == 0 else "partial",
            from_version=old_version,
            to_version=target_version,
            total_records=total_migrated + total_failed,
            migrated_records=total_migrated,
            failed_records=total_failed,
            error_message=error_msg
        )
        
        logger.info(f"切换密钥版本: {old_version} -> {target_version}")
        return True

    # ==================== 一键轮换 ====================

    def full_rotation(self) -> Dict[str, Any]:
        """一键完成轮换：生成密钥 -> 迁移数据 -> 切换版本"""
        # 1. 生成新密钥（如果不存在）
        keys = self.get_all_keys()
        if not keys:
            self.get_or_create_initial_key()
        
        new_key = self.generate_new_key()
        
        # 2. 执行迁移
        migration_result = self.execute_migration()
        
        # 3. 如果迁移成功且配置了自动切换，则切换版本
        config = self.get_config()
        if config.auto_switch and migration_result["success"]:
            self.switch_version(new_key.key_id)
        
        return {
            "new_key_version": new_key.key_id,
            "migration_result": migration_result,
            "auto_switched": config.auto_switch and migration_result["success"]
        }

    def calculate_next_rotation(self) -> datetime:
        """计算下次轮换时间"""
        config = self.get_config()
        now = datetime.now()
        
        if config.schedule_type == "weekly":
            days_ahead = config.schedule_day - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return now + __import__('datetime').timedelta(days=days_ahead)
            
        elif config.schedule_type == "monthly":
            if now.day < config.schedule_day:
                return now.replace(day=config.schedule_day, hour=2, minute=0, second=0)
            else:
                if now.month == 12:
                    return now.replace(year=now.year + 1, month=1, day=config.schedule_day, hour=2, minute=0, second=0)
                else:
                    return now.replace(month=now.month + 1, day=config.schedule_day, hour=2, minute=0, second=0)
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
            
            return datetime(
                year=next_year,
                month=next_quarter_month,
                day=config.schedule_day,
                hour=2, minute=0, second=0
            )
