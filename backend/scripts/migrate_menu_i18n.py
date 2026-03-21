#!/usr/bin/env python3
"""
Menu Internationalization Migration Script
Migrate menu names from Chinese to English

Usage:
    cd backend && python scripts/migrate_menu_i18n.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import SessionLocal, engine

# Menu name mappings: Chinese -> English
MENU_MIGRATIONS = [
    # Parent menus
    ("仪表盘", "Dashboard", "/dashboard"),
    ("实例管理", "Instances", "/instances"),
    ("环境管理", "Environments", "/environments"),
    ("SQL编辑器", "SQL Editor", "/sql-editor"),
    ("变更审批", "Approvals", "/approvals"),
    ("监控中心", "Monitor", "/monitor"),
    ("脚本管理", "Scripts", "/scripts"),
    ("定时任务", "Scheduled Tasks", "/scheduled-tasks"),
    ("用户管理", "Users", "/users"),
    ("注册审批", "Registrations", "/registrations"),
    ("通知管理", "Notification", "/notification"),
    ("审计日志", "Audit Logs", "/audit"),
    ("菜单配置", "Menu Config", "/menu-config"),
    
    # Child menus (Monitor sub-menus)
    ("性能监控", "Performance", "/monitor/performance"),
    ("慢查询监控", "Slow Query", "/monitor/slow-query"),
    ("监控配置", "Monitor Settings", "/monitor/settings"),
]


def run_migration():
    """Run the migration"""
    db = SessionLocal()
    try:
        print("=" * 50)
        print("Menu i18n Migration Script")
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
        for chinese_name, english_name, path in MENU_MIGRATIONS:
            result = db.execute(text("""
                UPDATE menu_configs 
                SET name = :english_name 
                WHERE path = :path AND name = :chinese_name
            """), {"english_name": english_name, "path": path, "chinese_name": chinese_name})
            
            if result.rowcount > 0:
                print(f"  ✓ '{chinese_name}' -> '{english_name}' ({path})")
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
