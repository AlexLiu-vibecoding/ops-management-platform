"""
数据迁移模块
"""
from app.migrations.migrate_aes_key import AESKeyMigration, run_migration

__all__ = ["AESKeyMigration", "run_migration"]
