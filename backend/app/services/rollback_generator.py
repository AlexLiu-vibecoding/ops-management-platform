"""
回滚SQL生成服务
在执行变更前分析SQL并生成回滚脚本
"""
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import sqlparse
from sqlparse.sql import Statement, IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML, DDL

logger = logging.getLogger(__name__)


class SQLType(Enum):
    """SQL操作类型"""
    # DDL
    CREATE_TABLE = "CREATE_TABLE"
    ALTER_TABLE = "ALTER_TABLE"
    DROP_TABLE = "DROP_TABLE"
    CREATE_INDEX = "CREATE_INDEX"
    DROP_INDEX = "DROP_INDEX"
    TRUNCATE_TABLE = "TRUNCATE_TABLE"
    
    # DML
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    
    # 其他
    UNKNOWN = "UNKNOWN"


@dataclass
class RollbackResult:
    """回滚SQL生成结果"""
    success: bool
    sql_type: SQLType
    rollback_sql: Optional[str] = None
    warning: Optional[str] = None
    affected_table: Optional[str] = None
    requires_data_backup: bool = False
    data_backup_sql: Optional[str] = None


class RollbackGenerator:
    """回滚SQL生成器"""
    
    def __init__(self):
        # SQL关键字模式
        self.patterns = {
            SQLType.CREATE_TABLE: re.compile(r'^\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?\s*\(', re.IGNORECASE | re.MULTILINE),
            SQLType.ALTER_TABLE: re.compile(r'^\s*ALTER\s+TABLE\s+[`"]?(\w+)[`"]?', re.IGNORECASE | re.MULTILINE),
            SQLType.DROP_TABLE: re.compile(r'^\s*DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?[`"]?(\w+)[`"]?', re.IGNORECASE | re.MULTILINE),
            SQLType.CREATE_INDEX: re.compile(r'^\s*CREATE\s+(?:UNIQUE\s+)?INDEX\s+[`"]?(\w+)[`"]?\s+ON\s+[`"]?(\w+)[`"]?', re.IGNORECASE | re.MULTILINE),
            SQLType.DROP_INDEX: re.compile(r'^\s*DROP\s+INDEX\s+[`"]?(\w+)[`"]?\s+ON\s+[`"]?(\w+)[`"]?', re.IGNORECASE | re.MULTILINE),
            SQLType.TRUNCATE_TABLE: re.compile(r'^\s*TRUNCATE\s+TABLE?\s+[`"]?(\w+)[`"]?', re.IGNORECASE | re.MULTILINE),
            SQLType.INSERT: re.compile(r'^\s*INSERT\s+INTO\s+[`"]?(\w+)[`"]?', re.IGNORECASE | re.MULTILINE),
            SQLType.UPDATE: re.compile(r'^\s*UPDATE\s+[`"]?(\w+)[`"]?\s+SET', re.IGNORECASE | re.MULTILINE),
            SQLType.DELETE: re.compile(r'^\s*DELETE\s+FROM\s+[`"]?(\w+)[`"]?', re.IGNORECASE | re.MULTILINE),
        }
    
    def analyze_sql(self, sql: str) -> list[tuple[SQLType, str, str]]:
        """
        分析SQL语句
        
        Returns:
            List of (SQL类型, 表名, 原始SQL)
        """
        results = []
        
        # 分割多条SQL
        statements = sqlparse.split(sql)
        
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
            
            # 识别SQL类型
            for sql_type, pattern in self.patterns.items():
                match = pattern.match(stmt)
                if match:
                    table = match.group(1) if match.groups() else None
                    results.append((sql_type, table, stmt))
                    break
            else:
                results.append((SQLType.UNKNOWN, None, stmt))
        
        return results
    
    def generate_rollback_sql(self, sql: str, db_connection=None) -> list[RollbackResult]:
        """
        生成回滚SQL
        
        Args:
            sql: 原始SQL语句
            db_connection: 数据库连接（用于查询当前数据状态）
        
        Returns:
            每条SQL对应的回滚结果列表
        """
        results = []
        analyzed = self.analyze_sql(sql)
        
        for sql_type, table, original_sql in analyzed:
            result = self._generate_single_rollback(sql_type, table, original_sql, db_connection)
            results.append(result)
        
        return results
    
    def _generate_single_rollback(
        self,
        sql_type: SQLType,
        table: Optional[str],
        original_sql: str,
        db_connection=None
    ) -> RollbackResult:
        """生成单条SQL的回滚语句"""
        
        if sql_type == SQLType.CREATE_TABLE:
            return RollbackResult(
                success=True,
                sql_type=sql_type,
                rollback_sql=f"DROP TABLE IF EXISTS `{table}`;",
                affected_table=table,
                warning="DROP TABLE会删除表及其所有数据"
            )
        
        elif sql_type == SQLType.DROP_TABLE:
            return RollbackResult(
                success=False,
                sql_type=sql_type,
                affected_table=table,
                warning="DROP TABLE无法自动生成回滚SQL，需要从备份恢复表结构",
                requires_data_backup=True
            )
        
        elif sql_type == SQLType.ALTER_TABLE:
            return self._generate_alter_rollback(table, original_sql)
        
        elif sql_type == SQLType.CREATE_INDEX:
            return RollbackResult(
                success=True,
                sql_type=sql_type,
                rollback_sql=f"DROP INDEX `{table}`;",  # table 实际是 index name
                affected_table=table,
                warning="删除索引可能影响查询性能"
            )
        
        elif sql_type == SQLType.DROP_INDEX:
            return RollbackResult(
                success=False,
                sql_type=sql_type,
                affected_table=table,
                warning="DROP INDEX无法自动生成回滚SQL，需要重新创建索引",
                requires_data_backup=True
            )
        
        elif sql_type == SQLType.TRUNCATE_TABLE:
            return RollbackResult(
                success=False,
                sql_type=sql_type,
                affected_table=table,
                warning="TRUNCATE无法自动生成回滚SQL，需要从备份恢复数据",
                requires_data_backup=True
            )
        
        elif sql_type == SQLType.INSERT:
            # INSERT的回滚是DELETE
            # 需要知道插入的记录的主键
            return RollbackResult(
                success=True,
                sql_type=sql_type,
                rollback_sql=f"-- INSERT回滚需要根据主键删除记录\n-- DELETE FROM `{table}` WHERE <主键条件>;",
                affected_table=table,
                warning="INSERT回滚需要知道插入记录的主键，请在执行后根据实际情况生成",
                requires_data_backup=False
            )
        
        elif sql_type == SQLType.UPDATE:
            # UPDATE的回滚需要先查询当前值
            return RollbackResult(
                success=True,
                sql_type=sql_type,
                rollback_sql=f"-- UPDATE回滚需要先备份原始数据\n-- SELECT * FROM `{table}` WHERE <条件> INTO OUTFILE 'backup.csv';\n-- 然后生成反向UPDATE语句",
                affected_table=table,
                warning="UPDATE回滚需要先备份受影响行的原始数据",
                requires_data_backup=True
            )
        
        elif sql_type == SQLType.DELETE:
            # DELETE的回滚需要先备份被删除的数据
            return RollbackResult(
                success=True,
                sql_type=sql_type,
                rollback_sql=f"-- DELETE回滚需要先备份被删除的数据\n-- SELECT * FROM `{table}` WHERE <条件> INTO OUTFILE 'backup.csv';\n-- 然后生成INSERT语句恢复",
                affected_table=table,
                warning="DELETE回滚需要先备份将被删除的数据",
                requires_data_backup=True
            )
        
        else:
            return RollbackResult(
                success=False,
                sql_type=sqlType.UNKNOWN,
                warning="无法识别的SQL类型，无法生成回滚SQL"
            )
    
    def _generate_alter_rollback(self, table: str, original_sql: str) -> RollbackResult:
        """生成ALTER TABLE的回滚SQL"""
        
        rollback_parts = []
        warnings = []
        
        # ADD COLUMN -> DROP COLUMN
        add_col_pattern = re.compile(r'ADD\s+(?:COLUMN\s+)?[`"]?(\w+)[`"]?\s+\w+', re.IGNORECASE)
        for match in add_col_pattern.finditer(original_sql):
            col_name = match.group(1)
            rollback_parts.append(f"ALTER TABLE `{table}` DROP COLUMN `{col_name}`;")
            warnings.append(f"删除列 {col_name} 会丢失该列数据")
        
        # DROP COLUMN -> ADD COLUMN (无法自动恢复类型)
        drop_col_pattern = re.compile(r'DROP\s+(?:COLUMN\s+)?[`"]?(\w+)[`"]?', re.IGNORECASE)
        for match in drop_col_pattern.finditer(original_sql):
            col_name = match.group(1)
            rollback_parts.append(f"-- ALTER TABLE `{table}` ADD COLUMN `{col_name}` <需要原始类型定义>;")
            warnings.append(f"无法自动恢复列 {col_name} 的类型定义")
        
        # MODIFY COLUMN -> 需要知道原始定义
        modify_col_pattern = re.compile(r'MODIFY\s+(?:COLUMN\s+)?[`"]?(\w+)[`"]?\s+(\w+(?:\([^)]+\))?)', re.IGNORECASE)
        for match in modify_col_pattern.finditer(original_sql):
            col_name = match.group(1)
            rollback_parts.append(f"-- ALTER TABLE `{table}` MODIFY COLUMN `{col_name}` <需要原始类型定义>;")
            warnings.append(f"无法自动恢复列 {col_name} 的原始类型")
        
        # ADD INDEX -> DROP INDEX
        add_idx_pattern = re.compile(r'ADD\s+(?:UNIQUE\s+)?(?:INDEX|KEY)\s+[`"]?(\w+)[`"]?', re.IGNORECASE)
        for match in add_idx_pattern.finditer(original_sql):
            idx_name = match.group(1)
            rollback_parts.append(f"ALTER TABLE `{table}` DROP INDEX `{idx_name}`;")
        
        # DROP INDEX -> ADD INDEX (需要知道索引列)
        drop_idx_pattern = re.compile(r'DROP\s+(?:INDEX|KEY)\s+[`"]?(\w+)[`"]?', re.IGNORECASE)
        for match in drop_idx_pattern.finditer(original_sql):
            idx_name = match.group(1)
            rollback_parts.append(f"-- ALTER TABLE `{table}` ADD INDEX `{idx_name}` (<需要索引列定义>);")
            warnings.append(f"无法自动恢复索引 {idx_name} 的列定义")
        
        # RENAME COLUMN
        rename_pattern = re.compile(r'RENAME\s+(?:COLUMN\s+)?[`"]?(\w+)[`"]?\s+TO\s+[`"]?(\w+)[`"]?', re.IGNORECASE)
        for match in rename_pattern.finditer(original_sql):
            old_name = match.group(2)  # 新名字
            new_name = match.group(1)  # 旧名字
            rollback_parts.append(f"ALTER TABLE `{table}` RENAME COLUMN `{old_name}` TO `{new_name}`;")
        
        # RENAME TABLE
        rename_table_pattern = re.compile(r'RENAME\s+(?:TO|AS)\s+[`"]?(\w+)[`"]?', re.IGNORECASE)
        match = rename_table_pattern.search(original_sql)
        if match:
            new_name = match.group(1)
            rollback_parts.append(f"ALTER TABLE `{new_name}` RENAME TO `{table}`;")
        
        if rollback_parts:
            return RollbackResult(
                success=True,
                sql_type=SQLType.ALTER_TABLE,
                rollback_sql="\n".join(rollback_parts),
                affected_table=table,
                warning="; ".join(warnings) if warnings else None
            )
        else:
            return RollbackResult(
                success=False,
                sql_type=SQLType.ALTER_TABLE,
                affected_table=table,
                warning="无法解析ALTER TABLE的具体操作，无法生成回滚SQL"
            )
    
    def generate_data_backup_sql(
        self,
        sql_type: SQLType,
        table: str,
        where_clause: Optional[str] = None
    ) -> str:
        """
        生成数据备份SQL
        
        用于UPDATE/DELETE操作前备份受影响的数据
        """
        if sql_type in [SQLType.UPDATE, SQLType.DELETE]:
            where = f" WHERE {where_clause}" if where_clause else ""
            return f"SELECT * FROM `{table}`{where};"
        return ""
    
    def generate_redis_rollback(self, command: str) -> RollbackResult:
        """
        生成Redis命令的回滚命令
        
        Args:
            command: Redis命令，如 SET key value
        """
        parts = command.strip().split()
        if not parts:
            return RollbackResult(
                success=False,
                sql_type=SQLType.UNKNOWN,
                warning="无效的Redis命令"
            )
        
        cmd = parts[0].upper()
        
        if cmd == "SET":
            # SET的回滚需要知道原值
            key = parts[1] if len(parts) > 1 else None
            return RollbackResult(
                success=True,
                sql_type=SQLType.UPDATE,
                rollback_sql=f"-- SET回滚需要先备份原值\n-- GET {key}\n-- DEL {key} (如果原来不存在)",
                affected_table=key,
                warning="SET操作回滚需要先备份原值",
                requires_data_backup=True
            )
        
        elif cmd == "DEL":
            # DEL的回滚需要知道原值
            keys = parts[1:]
            return RollbackResult(
                success=False,
                sql_type=SQLType.DELETE,
                affected_table=",".join(keys),
                warning="DEL操作无法自动回滚，需要先备份被删除的值",
                requires_data_backup=True
            )
        
        elif cmd == "HSET":
            key = parts[1] if len(parts) > 1 else None
            field = parts[2] if len(parts) > 2 else None
            return RollbackResult(
                success=True,
                sql_type=SQLType.UPDATE,
                rollback_sql=f"HDEL {key} {field}",
                affected_table=key,
                warning="HSET回滚使用HDEL删除字段"
            )
        
        elif cmd == "LPUSH" or cmd == "RPUSH":
            key = parts[1] if len(parts) > 1 else None
            return RollbackResult(
                success=True,
                sql_type=SQLType.UPDATE,
                rollback_sql=f"-- LPOP/RPOP {key} (移除添加的元素)",
                affected_table=key,
                warning="PUSH操作回滚需要移除添加的元素"
            )
        
        elif cmd == "EXPIRE" or cmd == "PEXPIRE":
            key = parts[1] if len(parts) > 1 else None
            return RollbackResult(
                success=True,
                sql_type=SQLType.UPDATE,
                rollback_sql=f"PERSIST {key}",
                affected_table=key,
                warning="EXPIRE回滚使用PERSIST移除过期时间"
            )
        
        elif cmd == "RENAME":
            old_key = parts[1] if len(parts) > 1 else None
            new_key = parts[2] if len(parts) > 2 else None
            return RollbackResult(
                success=True,
                sql_type=SQLType.UPDATE,
                rollback_sql=f"RENAME {new_key} {old_key}",
                affected_table=old_key
            )
        
        else:
            return RollbackResult(
                success=False,
                sql_type=SQLType.UNKNOWN,
                warning=f"不支持的Redis命令: {cmd}"
            )


# 全局实例
rollback_generator = RollbackGenerator()
