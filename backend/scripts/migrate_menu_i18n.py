#!/usr/bin/env python3
"""
Menu Internationalization Migration Script
Migrate menu names from English to Chinese

Usage:
    cd backend && python scripts/migrate_menu_i18n.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import SessionLocal, engine

# Menu name mappings: English -> Chinese
MENU_MIGRATIONS = [
    # Parent menus
    ("Dashboard", "仪表盘", "/dashboard"),
    ("Instances", "实例管理", "/instances"),
    ("Environments", "环境管理", "/environments"),
    ("SQL Editor", "SQL编辑器", "/sql-editor"),
    ("Approvals", "变更审批", "/approvals"),
    ("Monitor", "监控中心", "/monitor"),
    ("Scripts", "脚本管理", "/scripts"),
    ("Scheduled Tasks", "定时任务", "/scheduled-tasks"),
    ("Users", "用户管理", "/users"),
    ("Registrations", "注册审批", "/registrations"),
    ("Config", "配置管理", "/config"),
    ("Audit Logs", "审计日志", "/audit"),
    ("Menu Config", "菜单配置", "/menu-config"),
    
    # Child menus (Monitor sub-menus)
    ("Performance", "性能监控", "/monitor/performance"),
    ("Slow Query", "慢查询监控", "/monitor/slow-query"),
    ("Monitor Settings", "监控配置", "/monitor/settings"),
]


def run_migration():
    """Run the migration"""
    db = SessionLocal()
    try:
        print("=" * 50)
        print("Menu i18n Migration Script (English -> Chinese)")
        print("=" * 50)
        
        # Check if menu_configs table exists
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'menu_configs'
            );
        """))
        
        if not result.scalar():
            print("❌ Table 'menu_configs' does not exist.")
            print("   Please run the application first to create tables.")
            return False
        
        # Count existing menus
        result = db.execute(text("SELECT COUNT(*) FROM menu_configs"))
        total_count = result.scalar()
        print(f"\n📊 Found {total_count} menu records")
        
        # Migrate each menu
        migrated = 0
        for english_name, chinese_name, path in MENU_MIGRATIONS:
            result = db.execute(text("""
                UPDATE menu_configs 
                SET name = :chinese_name 
                WHERE path = :path AND name = :english_name
            """), {"chinese_name": chinese_name, "path": path, "english_name": english_name})
            
            if result.rowcount > 0:
                print(f"  ✓ '{english_name}' -> '{chinese_name}' ({path})")
                migrated += result.rowcount
        
        # Commit changes
        db.commit()
        
        print(f"\n✅ Migration complete! Updated {migrated} records.")
        
        # Show final state
        print("\n📋 Current menu configuration:")
        result = db.execute(text("""
            SELECT id, name, path, parent_id 
            FROM menu_configs 
            ORDER BY sort_order, id
        """))
        
        for row in result:
            indent = "  " if row.parent_id else ""
            print(f"  {indent}{row.id}: {row.name} ({row.path})")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Migration failed: {e}")
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
