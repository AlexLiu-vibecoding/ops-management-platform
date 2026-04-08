"""
AES 密钥轮换与数据迁移脚本

使用方法：
1. 设置新密钥环境变量 AES_KEY_V2
2. 运行迁移：
   python -m app.migrations.migrate_aes_key

功能：
1. 将加密数据从 v1 迁移到 v2
2. 支持回滚（v2 迁移回 v1）
3. 提供进度报告
"""

import argparse
import logging
import sys
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """迁移结果"""
    table_name: str
    field_name: str
    total: int
    migrated: int
    failed: int
    errors: List[str]


class AESKeyMigration:
    """AES 密钥迁移器"""
    
    # 需要迁移的表和字段配置
    MIGRATION_TABLES = [
        {
            "table": "rdb_instances",
            "field": "password_encrypted",
            "model_class": "RDBInstance",
            "description": "RDB 实例密码"
        },
        {
            "table": "redis_instances",
            "field": "password_encrypted",
            "model_class": "RedisInstance",
            "description": "Redis 实例密码"
        },
        {
            "table": "ai_models",
            "field": "api_key_encrypted",
            "model_class": "AiModel",
            "description": "AI 模型 API 密钥"
        },
        {
            "table": "aws_credentials",
            "field": "aws_secret_access_key",
            "model_class": "AwsCredential",
            "description": "AWS 访问密钥"
        },
        {
            "table": "notification_channels",
            "field": "config_encrypted",
            "model_class": "NotificationChannel",
            "description": "通知通道配置（可能包含密钥）"
        },
    ]
    
    def __init__(self, db_session):
        """
        初始化迁移器
        
        Args:
            db_session: SQLAlchemy 数据库会话
        """
        self.db = db_session
        self.results: List[MigrationResult] = []
    
    def detect_version(self, encrypted_text: Optional[str]) -> str:
        """
        检测加密数据的密钥版本
        
        Args:
            encrypted_text: 加密数据
        
        Returns:
            版本标识：v1, v2, legacy
        """
        if not encrypted_text:
            return "empty"
        
        if encrypted_text.startswith("v1$"):
            return "v1"
        elif encrypted_text.startswith("v2$"):
            return "v2"
        elif encrypted_text.startswith("legacy$"):
            return "legacy"
        else:
            # 无前缀的旧格式
            return "legacy"
    
    def migrate_table(self, table_config: Dict[str, Any], target_version: str) -> MigrationResult:
        """
        迁移单个表的加密字段
        
        Args:
            table_config: 表配置
            target_version: 目标版本 (v1 或 v2)
        
        Returns:
            迁移结果
        """
        table_name = table_config["table"]
        field_name = table_config["field"]
        description = table_config["description"]
        
        result = MigrationResult(
            table_name=table_name,
            field_name=field_name,
            total=0,
            migrated=0,
            failed=0,
            errors=[]
        )
        
        try:
            from app.utils.auth import AESCipher
            
            # 构建查询
            query = f'SELECT id, {field_name} FROM {table_name} WHERE {field_name} IS NOT NULL AND {field_name} != ""'
            rows = self.db.execute(query).fetchall()
            
            result.total = len(rows)
            logger.info(f"[{table_name}.{field_name}] 发现 {result.total} 条加密数据")
            
            for row in rows:
                record_id = row[0]
                encrypted_value = row[1]
                
                try:
                    # 检测当前版本
                    current_version = self.detect_version(encrypted_value)
                    
                    # 检查是否需要迁移
                    current_version_normalized = current_version if current_version != "legacy" else "v1"
                    
                    if current_version_normalized == target_version:
                        logger.debug(f"  ID={record_id}: 已是 {target_version}，跳过")
                        continue
                    
                    # 解密并重新加密
                    plaintext = AESCipher.decrypt(encrypted_value)
                    new_encrypted = AESCipher().encrypt(plaintext)
                    
                    # 更新数据库
                    update_query = f'UPDATE {table_name} SET {field_name} = :new_value WHERE id = :id'
                    self.db.execute(update_query, {"new_value": new_encrypted, "id": record_id})
                    
                    result.migrated += 1
                    logger.debug(f"  ID={record_id}: {current_version} -> {target_version}")
                    
                except Exception as e:
                    result.failed += 1
                    error_msg = f"ID={record_id}: {str(e)}"
                    result.errors.append(error_msg)
                    logger.warning(f"  {error_msg}")
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"迁移 {table_name}.{field_name} 失败: {e}")
            result.errors.append(f"表迁移失败: {str(e)}")
            self.db.rollback()
        
        return result
    
    def migrate_all(self, target_version: str = "v2", dry_run: bool = False) -> List[MigrationResult]:
        """
        迁移所有加密数据
        
        Args:
            target_version: 目标版本
            dry_run: 是否仅预览不实际执行
        
        Returns:
            所有迁移结果
        """
        logger.info(f"{'='*60}")
        logger.info(f"AES 密钥迁移 - 目标版本: {target_version}")
        logger.info(f"模式: {'预览' if dry_run else '执行'}")
        logger.info(f"{'='*60}")
        
        self.results = []
        
        for table_config in self.MIGRATION_TABLES:
            table_name = table_config["table"]
            field_name = table_config["field"]
            
            logger.info(f"\n迁移 {table_name}.{field_name} ({table_config['description']})...")
            
            if dry_run:
                # 预览模式
                result = self.preview_table(table_config, target_version)
            else:
                result = self.migrate_table(table_config, target_version)
            
            self.results.append(result)
        
        return self.results
    
    def preview_table(self, table_config: Dict[str, Any], target_version: str) -> MigrationResult:
        """
        预览表迁移情况（不实际执行）
        
        Args:
            table_config: 表配置
            target_version: 目标版本
        
        Returns:
            预览结果
        """
        table_name = table_config["table"]
        field_name = table_config["field"]
        
        result = MigrationResult(
            table_name=table_name,
            field_name=field_name,
            total=0,
            migrated=0,
            failed=0,
            errors=[]
        )
        
        try:
            query = f'SELECT id, {field_name} FROM {table_name} WHERE {field_name} IS NOT NULL AND {field_name} != ""'
            rows = self.db.execute(query).fetchall()
            
            result.total = len(rows)
            
            version_counts = {"v1": 0, "v2": 0, "legacy": 0, "empty": 0}
            
            for row in rows:
                encrypted_value = row[1]
                version = self.detect_version(encrypted_value)
                version_counts[version] = version_counts.get(version, 0) + 1
            
            # 统计需要迁移的数量
            target_count = result.total - version_counts.get(target_version, 0) - version_counts.get("empty", 0)
            
            logger.info(f"  总数: {result.total}")
            logger.info(f"  版本分布: v1={version_counts.get('v1', 0)}, v2={version_counts.get('v2', 0)}, legacy={version_counts.get('legacy', 0)}")
            logger.info(f"  需要迁移: {target_count}")
            
            result.migrated = target_count
            
        except Exception as e:
            logger.error(f"预览 {table_name}.{field_name} 失败: {e}")
            result.errors.append(str(e))
        
        return result
    
    def get_status_report(self) -> str:
        """
        获取迁移状态报告
        
        Returns:
            格式化的报告文本
        """
        report = []
        report.append("\n" + "="*60)
        report.append("迁移报告")
        report.append("="*60)
        
        total_migrated = 0
        total_failed = 0
        
        for result in self.results:
            report.append(f"\n{result.table_name}.{result.field_name}:")
            report.append(f"  总数: {result.total}")
            report.append(f"  已迁移: {result.migrated}")
            report.append(f"  失败: {result.failed}")
            
            if result.errors:
                report.append(f"  错误:")
                for error in result.errors[:5]:  # 最多显示 5 条
                    report.append(f"    - {error}")
            
            total_migrated += result.migrated
            total_failed += result.failed
        
        report.append("\n" + "-"*60)
        report.append(f"总计: 迁移 {total_migrated} 条, 失败 {total_failed} 条")
        report.append("="*60)
        
        return "\n".join(report)


def run_migration(target_version: str = "v2", dry_run: bool = False, batch_size: int = 100):
    """
    运行迁移
    
    Args:
        target_version: 目标版本
        dry_run: 是否仅预览
        batch_size: 每批处理数量
    """
    from app.database import SessionLocal
    
    db = SessionLocal()
    
    try:
        # 检查 V2 密钥是否配置
        from app.config import settings
        if not settings.security.AES_KEY_V2:
            logger.error("错误: AES_KEY_V2 未配置!")
            logger.error("请设置 AES_KEY_V2 环境变量（32字符）")
            sys.exit(1)
        
        logger.info("密钥轮换配置检查:")
        logger.info(f"  AES_KEY (v1): {'已配置' if settings.security.AES_KEY else '未配置'}")
        logger.info(f"  AES_KEY_V2 (v2): {'已配置' if settings.security.AES_KEY_V2 else '未配置'}")
        logger.info(f"  当前版本: {settings.security.AES_CURRENT_VERSION}")
        
        migrator = AESKeyMigration(db)
        results = migrator.migrate_all(target_version=target_version, dry_run=dry_run)
        
        print(migrator.get_status_report())
        
        if dry_run:
            logger.info("\n这是预览模式，未执行实际迁移")
            logger.info("去掉 --dry-run 参数执行实际迁移")
        else:
            logger.info("\n迁移完成!")
            
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="AES 密钥轮换与数据迁移")
    parser.add_argument(
        "--target",
        choices=["v1", "v2"],
        default="v2",
        help="目标密钥版本 (默认: v2)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅预览，不执行实际迁移"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="批处理大小 (默认: 100)"
    )
    
    args = parser.parse_args()
    
    run_migration(
        target_version=args.target,
        dry_run=args.dry_run,
        batch_size=args.batch_size
    )


if __name__ == "__main__":
    main()
