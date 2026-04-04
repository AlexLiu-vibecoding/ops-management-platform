"""
增强版回滚SQL生成服务
在执行变更前连接数据库查询数据，生成真正的回滚脚本
"""
import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import sqlparse
from sqlparse.sql import Statement, IdentifierList, Identifier, Where, Comparison
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
    affected_rows: int = 0
    requires_data_backup: bool = False
    data_backup_sql: Optional[str] = None
    backup_data: Optional[list[dict]] = None  # 备份的原始数据
    error: Optional[str] = None


@dataclass
class RedisRollbackResult:
    """Redis回滚命令生成结果"""
    success: bool
    rollback_commands: list[str] = field(default_factory=list)
    warning: Optional[str] = None
    affected_keys: list[str] = field(default_factory=list)
    backup_data: Optional[dict[str, Any]] = None  # 键值备份
    error: Optional[str] = None


class EnhancedRollbackGenerator:
    """增强版回滚SQL生成器 - 连接数据库查询真实数据"""
    
    # SQL关键字模式
    PATTERNS = {
        SQLType.CREATE_TABLE: re.compile(r'^\s*CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\[]?(\w+)[`"\]]?\s*\(', re.IGNORECASE | re.MULTILINE),
        SQLType.ALTER_TABLE: re.compile(r'^\s*ALTER\s+TABLE\s+[`"\[]?(\w+)[`"\]]?', re.IGNORECASE | re.MULTILINE),
        SQLType.DROP_TABLE: re.compile(r'^\s*DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?[`"\[]?(\w+)[`"\]]?', re.IGNORECASE | re.MULTILINE),
        SQLType.CREATE_INDEX: re.compile(r'^\s*CREATE\s+(?:UNIQUE\s+)?INDEX\s+[`"\[]?(\w+)[`"\]]?\s+ON\s+[`"\[]?(\w+)[`"\]]?', re.IGNORECASE | re.MULTILINE),
        SQLType.DROP_INDEX: re.compile(r'^\s*DROP\s+INDEX\s+[`"\[]?(\w+)[`"\]]?', re.IGNORECASE | re.MULTILINE),
        SQLType.TRUNCATE_TABLE: re.compile(r'^\s*TRUNCATE\s+TABLE?\s+[`"\[]?(\w+)[`"\]]?', re.IGNORECASE | re.MULTILINE),
        SQLType.INSERT: re.compile(r'^\s*INSERT\s+INTO\s+[`"\[]?(\w+)[`"\]]?', re.IGNORECASE | re.MULTILINE),
        SQLType.UPDATE: re.compile(r'^\s*UPDATE\s+[`"\[]?(\w+)[`"\]]?\s+SET', re.IGNORECASE | re.MULTILINE),
        SQLType.DELETE: re.compile(r'^\s*DELETE\s+FROM\s+[`"\[]?(\w+)[`"\]]?', re.IGNORECASE | re.MULTILINE),
    }
    
    # 最大备份行数限制
    MAX_BACKUP_ROWS = 10000
    
    def __init__(self, db_connection=None, db_type: str = "mysql"):
        """
        初始化生成器
        
        Args:
            db_connection: 数据库连接对象 (pymysql 或 psycopg2 连接)
            db_type: 数据库类型 "mysql" 或 "postgresql"
        """
        self.db_connection = db_connection
        self.db_type = db_type
    
    def analyze_sql(self, sql: str) -> list[tuple[SQLType, str, str]]:
        """
        分析SQL语句
        
        Returns:
            List of (SQL类型, 表名, 原始SQL)
        """
        results = []
        statements = sqlparse.split(sql)
        
        for stmt in statements:
            stmt = stmt.strip()
            if not stmt:
                continue
            
            for sql_type, pattern in self.PATTERNS.items():
                match = pattern.match(stmt)
                if match:
                    table = match.group(1) if match.groups() else None
                    results.append((sql_type, table, stmt))
                    break
            else:
                results.append((SQLType.UNKNOWN, None, stmt))
        
        return results
    
    def extract_where_clause(self, sql: str) -> Optional[str]:
        """从SQL中提取WHERE条件"""
        # 使用正则提取 WHERE 子句
        match = re.search(r'\bWHERE\b\s+(.+?)(?:\s*(?:ORDER|GROUP|LIMIT|;|$))', sql, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None
    
    def extract_set_clause(self, sql: str) -> dict[str, str]:
        """从UPDATE语句中提取SET子句的列和值"""
        set_match = re.search(r'\bSET\s+(.+?)\s*(?:WHERE|$)', sql, re.IGNORECASE | re.DOTALL)
        if not set_match:
            return {}
        
        set_clause = set_match.group(1)
        result = {}
        
        # 解析 col = value 格式
        for item in set_clause.split(','):
            item = item.strip()
            if '=' in item:
                parts = item.split('=', 1)
                col = parts[0].strip().strip('`"[]')
                val = parts[1].strip()
                result[col] = val
        
        return result
    
    def extract_insert_values(self, sql: str) -> tuple[list[str], list[list[str]]]:
        """从INSERT语句中提取列和值"""
        # 匹配 INSERT INTO table (cols) VALUES (vals)
        match = re.search(
            r'INSERT\s+INTO\s+[`"\[]?(\w+)[`"\]]?\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)',
            sql, re.IGNORECASE
        )
        if match:
            cols = [c.strip().strip('`"[]') for c in match.group(2).split(',')]
            vals = [v.strip() for v in match.group(3).split(',')]
            return cols, [vals]
        
        # 匹配 INSERT INTO table VALUES (vals)
        match = re.search(r'INSERT\s+INTO\s+[`"\[]?(\w+)[`"\]]?\s*VALUES\s*\(([^)]+)\)', sql, re.IGNORECASE)
        if match:
            vals = [v.strip() for v in match.group(2).split(',')]
            return [], [vals]
        
        return [], []
    
    def get_primary_key(self, table: str) -> list[str]:
        """获取表的主键列"""
        if not self.db_connection:
            return ['id']  # 默认假设主键是 id
        
        try:
            cursor = self.db_connection.cursor()
            if self.db_type == "postgresql":
                cursor.execute("""
                    SELECT a.attname
                    FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                    WHERE i.indrelid = %s::regclass AND i.indisprimary
                """, (table,))
            else:  # MySQL
                cursor.execute("""
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = %s
                    AND CONSTRAINT_NAME = 'PRIMARY'
                    ORDER BY ORDINAL_POSITION
                """, (table,))
            
            result = cursor.fetchall()
            cursor.close()
            return [row[0] for row in result] if result else ['id']
        except Exception as e:
            logger.warning(f"获取主键失败: {e}")
            return ['id']
    
    def get_table_columns(self, table: str) -> list[str]:
        """获取表的所有列名"""
        if not self.db_connection:
            return []
        
        try:
            cursor = self.db_connection.cursor()
            if self.db_type == "postgresql":
                cursor.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                """, (table,))
            else:  # MySQL
                cursor.execute("""
                    SELECT COLUMN_NAME
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (table,))
            
            result = cursor.fetchall()
            cursor.close()
            return [row[0] for row in result]
        except Exception as e:
            logger.warning(f"获取列名失败: {e}")
            return []
    
    def query_affected_data(self, table: str, where_clause: Optional[str], columns: list[str] = None) -> tuple[list[dict], int]:
        """
        查询受影响的数据
        
        Returns:
            (数据列表, 总行数)
        """
        if not self.db_connection:
            return [], 0
        
        try:
            cursor = self.db_connection.cursor()
            
            # 构建查询SQL
            col_list = ', '.join([f'`{c}`' if self.db_type == "mysql" else f'"{c}"' for c in columns]) if columns else '*'
            select_sql = f"SELECT {col_list} FROM {self._quote_identifier(table)}"
            
            if where_clause:
                select_sql += f" WHERE {where_clause}"
            
            # 添加行数限制
            select_sql += f" LIMIT {self.MAX_BACKUP_ROWS + 1}"
            
            cursor.execute(select_sql)
            rows = cursor.fetchall()
            
            # 获取列名
            if cursor.description:
                col_names = [desc[0] for desc in cursor.description]
            else:
                col_names = columns or []
            
            # 转换为字典列表
            data = []
            for row in rows[:self.MAX_BACKUP_ROWS]:
                data.append(dict(zip(col_names, row, strict=False)))
            
            cursor.close()
            return data, len(rows)
            
        except Exception as e:
            logger.error(f"查询受影响数据失败: {e}")
            return [], 0
    
    def _quote_identifier(self, name: str) -> str:
        """根据数据库类型引用标识符"""
        if self.db_type == "postgresql":
            return f'"{name}"'
        return f'`{name}`'
    
    def _format_value(self, value: Any) -> str:
        """格式化SQL值"""
        if value is None:
            return "NULL"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, bytes):
            return f"0x{value.hex()}"
        # 字符串类型，转义单引号
        escaped = str(value).replace("'", "''")
        return f"'{escaped}'"
    
    def generate_rollback_sql(
        self,
        sql: str,
        db_connection=None,
        db_type: str = None,
        database: str = None
    ) -> list[RollbackResult]:
        """
        生成回滚SQL - 连接数据库查询真实数据
        
        Args:
            sql: 原始SQL语句
            db_connection: 数据库连接（可选，如果不传则使用初始化时的连接）
            db_type: 数据库类型
            database: 数据库名（用于日志）
        
        Returns:
            每条SQL对应的回滚结果列表
        """
        if db_connection:
            self.db_connection = db_connection
        if db_type:
            self.db_type = db_type
        
        results = []
        analyzed = self.analyze_sql(sql)
        
        for sql_type, table, original_sql in analyzed:
            result = self._generate_single_rollback_with_data(sql_type, table, original_sql)
            results.append(result)
        
        return results
    
    def _generate_single_rollback_with_data(
        self,
        sql_type: SQLType,
        table: Optional[str],
        original_sql: str
    ) -> RollbackResult:
        """生成单条SQL的回滚语句 - 包含数据查询"""
        
        if sql_type == SQLType.CREATE_TABLE:
            return RollbackResult(
                success=True,
                sql_type=sql_type,
                rollback_sql=f"DROP TABLE IF EXISTS {self._quote_identifier(table)};",
                affected_table=table,
                warning="DROP TABLE会删除表及其所有数据"
            )
        
        elif sql_type == SQLType.DROP_TABLE:
            # DROP TABLE 需要先备份表结构
            if self.db_connection:
                try:
                    cursor = self.db_connection.cursor()
                    if self.db_type == "mysql":
                        cursor.execute(f"SHOW CREATE TABLE {self._quote_identifier(table)}")
                        result = cursor.fetchone()
                        create_sql = result[1] if result else None
                        cursor.close()
                        
                        if create_sql:
                            return RollbackResult(
                                success=True,
                                sql_type=sql_type,
                                rollback_sql=f"-- 原表结构:\n{create_sql};",
                                affected_table=table,
                                warning="已备份原表结构，但数据需要单独恢复",
                                requires_data_backup=True
                            )
                except Exception as e:
                    logger.warning(f"获取表结构失败: {e}")
            
            return RollbackResult(
                success=False,
                sql_type=sql_type,
                affected_table=table,
                warning="DROP TABLE无法自动生成回滚SQL，需要从备份恢复表结构和数据",
                requires_data_backup=True
            )
        
        elif sql_type == SQLType.ALTER_TABLE:
            return self._generate_alter_rollback(table, original_sql)
        
        elif sql_type == SQLType.CREATE_INDEX:
            return RollbackResult(
                success=True,
                sql_type=sql_type,
                rollback_sql=f"DROP INDEX {self._quote_identifier(table)};",  # table 实际是 index name
                affected_table=table,
                warning="删除索引可能影响查询性能"
            )
        
        elif sql_type == SQLType.DROP_INDEX:
            # 尝试获取索引定义
            if self.db_connection:
                try:
                    cursor = self.db_connection.cursor()
                    if self.db_type == "mysql":
                        cursor.execute(f"SHOW INDEX FROM {self._quote_identifier(table)}")
                        # 返回的是索引信息，需要整合
                        cursor.fetchall()
                        cursor.close()
                        # 简化处理：返回提示
                        return RollbackResult(
                            success=False,
                            sql_type=sql_type,
                            affected_table=table,
                            warning="DROP INDEX无法自动恢复，需要重新创建索引",
                            requires_data_backup=True
                        )
                except Exception as e:
                    logger.warning(f"获取索引信息失败: {e}")
            
            return RollbackResult(
                success=False,
                sql_type=sql_type,
                affected_table=table,
                warning="DROP INDEX无法自动生成回滚SQL",
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
            # INSERT的回滚是DELETE，需要知道主键
            # 这里无法提前知道会插入什么数据，只能在执行后生成
            return RollbackResult(
                success=True,
                sql_type=sql_type,
                rollback_sql=f"-- INSERT回滚需要在执行后根据插入的主键生成DELETE语句\n-- DELETE FROM {self._quote_identifier(table)} WHERE <主键条件>;",
                affected_table=table,
                warning="INSERT回滚需要在执行后根据实际插入的数据生成",
                requires_data_backup=False
            )
        
        elif sql_type == SQLType.UPDATE:
            return self._generate_update_rollback(table, original_sql)
        
        elif sql_type == SQLType.DELETE:
            return self._generate_delete_rollback(table, original_sql)
        
        else:
            return RollbackResult(
                success=False,
                sql_type=SQLType.UNKNOWN,
                warning="无法识别的SQL类型，无法生成回滚SQL"
            )
    
    def _generate_update_rollback(self, table: str, original_sql: str) -> RollbackResult:
        """生成UPDATE的回滚SQL - 查询并备份原始数据"""
        
        # 提取WHERE条件
        where_clause = self.extract_where_clause(original_sql)
        set_values = self.extract_set_clause(original_sql)
        
        if not set_values:
            return RollbackResult(
                success=False,
                sql_type=SQLType.UPDATE,
                affected_table=table,
                error="无法解析UPDATE的SET子句"
            )
        
        # 获取表的主键
        pk_columns = self.get_primary_key(table)
        all_columns = self.get_table_columns(table)
        
        # 查询受影响的数据
        data, total_rows = self.query_affected_data(table, where_clause, all_columns)
        
        if not data:
            # 没有数据受影响
            return RollbackResult(
                success=True,
                sql_type=SQLType.UPDATE,
                rollback_sql="-- 没有数据会被修改，无需回滚",
                affected_table=table,
                affected_rows=0,
                warning="没有数据会被此UPDATE语句修改"
            )
        
        # 检查是否超过限制
        if total_rows > self.MAX_BACKUP_ROWS:
            return RollbackResult(
                success=True,
                sql_type=SQLType.UPDATE,
                rollback_sql=f"-- 受影响行数({total_rows})超过限制({self.MAX_BACKUP_ROWS})，无法生成完整回滚SQL\n-- 建议使用数据导出工具备份",
                affected_table=table,
                affected_rows=total_rows,
                warning=f"受影响行数过多({total_rows})，已截断",
                backup_data=data
            )
        
        # 生成回滚UPDATE语句
        rollback_statements = []
        rollback_statements.append(f"-- UPDATE回滚SQL (共 {len(data)} 行受影响)")
        rollback_statements.append(f"-- 原始UPDATE: {original_sql[:200]}...")
        rollback_statements.append("")
        
        for row in data:
            # 构建WHERE条件（使用主键）
            where_parts = []
            for pk in pk_columns:
                if pk in row:
                    val = self._format_value(row[pk])
                    where_parts.append(f"{self._quote_identifier(pk)} = {val}")
            
            if not where_parts:
                # 如果没有主键，使用所有列作为条件
                for col, val in row.items():
                    where_parts.append(f"{self._quote_identifier(col)} = {self._format_value(val)}")
            
            where_str = " AND ".join(where_parts)
            
            # 构建SET子句（恢复原始值）
            set_parts = []
            for col in set_values.keys():
                if col in row:
                    original_val = self._format_value(row[col])
                    set_parts.append(f"{self._quote_identifier(col)} = {original_val}")
            
            if set_parts:
                set_str = ", ".join(set_parts)
                rollback_statements.append(f"UPDATE {self._quote_identifier(table)} SET {set_str} WHERE {where_str};")
        
        return RollbackResult(
            success=True,
            sql_type=SQLType.UPDATE,
            rollback_sql="\n".join(rollback_statements),
            affected_table=table,
            affected_rows=len(data),
            backup_data=data
        )
    
    def _generate_delete_rollback(self, table: str, original_sql: str) -> RollbackResult:
        """生成DELETE的回滚SQL - 查询并备份将被删除的数据"""
        
        # 提取WHERE条件
        where_clause = self.extract_where_clause(original_sql)
        
        # 获取表的所有列
        all_columns = self.get_table_columns(table)
        
        # 查询将被删除的数据
        data, total_rows = self.query_affected_data(table, where_clause, all_columns)
        
        if not data:
            # 没有数据会被删除
            return RollbackResult(
                success=True,
                sql_type=SQLType.DELETE,
                rollback_sql="-- 没有数据会被删除，无需回滚",
                affected_table=table,
                affected_rows=0,
                warning="没有数据会被此DELETE语句删除"
            )
        
        # 检查是否超过限制
        if total_rows > self.MAX_BACKUP_ROWS:
            return RollbackResult(
                success=True,
                sql_type=SQLType.DELETE,
                rollback_sql=f"-- 受影响行数({total_rows})超过限制({self.MAX_BACKUP_ROWS})，无法生成完整回滚SQL\n-- 建议使用数据导出工具备份",
                affected_table=table,
                affected_rows=total_rows,
                warning=f"受影响行数过多({total_rows})，已截断",
                backup_data=data
            )
        
        # 生成INSERT语句作为回滚
        rollback_statements = []
        rollback_statements.append(f"-- DELETE回滚SQL (共 {len(data)} 行将被删除)")
        rollback_statements.append(f"-- 原始DELETE: {original_sql[:200]}...")
        rollback_statements.append("")
        
        for row in data:
            columns = list(row.keys())
            values = [self._format_value(row[col]) for col in columns]
            
            col_str = ", ".join([self._quote_identifier(c) for c in columns])
            val_str = ", ".join(values)
            
            rollback_statements.append(f"INSERT INTO {self._quote_identifier(table)} ({col_str}) VALUES ({val_str});")
        
        return RollbackResult(
            success=True,
            sql_type=SQLType.DELETE,
            rollback_sql="\n".join(rollback_statements),
            affected_table=table,
            affected_rows=len(data),
            backup_data=data
        )
    
    def _generate_alter_rollback(self, table: str, original_sql: str) -> RollbackResult:
        """生成ALTER TABLE的回滚SQL"""
        
        rollback_parts = []
        warnings = []
        
        # ADD COLUMN -> DROP COLUMN
        add_col_pattern = re.compile(r'ADD\s+(?:COLUMN\s+)?[`"\[]?(\w+)[`"\]]?\s+(\w+)', re.IGNORECASE)
        for match in add_col_pattern.finditer(original_sql):
            col_name = match.group(1)
            rollback_parts.append(f"ALTER TABLE {self._quote_identifier(table)} DROP COLUMN {self._quote_identifier(col_name)};")
            warnings.append(f"删除列 {col_name} 会丢失该列数据")
        
        # DROP COLUMN -> 需要查询原始定义
        drop_col_pattern = re.compile(r'DROP\s+(?:COLUMN\s+)?[`"\[]?(\w+)[`"\]]?', re.IGNORECASE)
        for match in drop_col_pattern.finditer(original_sql):
            col_name = match.group(1)
            # 尝试获取列定义
            col_def = None
            if self.db_connection:
                try:
                    cursor = self.db_connection.cursor()
                    if self.db_type == "mysql":
                        cursor.execute("""
                            SELECT COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, EXTRA
                            FROM INFORMATION_SCHEMA.COLUMNS
                            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
                        """, (table, col_name))
                        result = cursor.fetchone()
                        if result:
                            col_def = result[0]
                            if result[1] == 'NO':
                                col_def += ' NOT NULL'
                            if result[2]:
                                col_def += f" DEFAULT '{result[2]}'"
                        cursor.close()
                except Exception as e:
                    logger.warning(f"获取列定义失败: {e}")
            
            if col_def:
                rollback_parts.append(f"ALTER TABLE {self._quote_identifier(table)} ADD COLUMN {self._quote_identifier(col_name)} {col_def};")
            else:
                rollback_parts.append(f"-- ALTER TABLE {self._quote_identifier(table)} ADD COLUMN {self._quote_identifier(col_name)} <需要原始类型定义>;")
                warnings.append(f"无法自动恢复列 {col_name} 的类型定义")
        
        # ADD INDEX -> DROP INDEX
        add_idx_pattern = re.compile(r'ADD\s+(?:UNIQUE\s+)?(?:INDEX|KEY)\s+[`"\[]?(\w+)[`"\]]?', re.IGNORECASE)
        for match in add_idx_pattern.finditer(original_sql):
            idx_name = match.group(1)
            rollback_parts.append(f"ALTER TABLE {self._quote_identifier(table)} DROP INDEX {self._quote_identifier(idx_name)};")
        
        # DROP INDEX -> 需要查询索引定义
        drop_idx_pattern = re.compile(r'DROP\s+(?:INDEX|KEY)\s+[`"\[]?(\w+)[`"\]]?', re.IGNORECASE)
        for match in drop_idx_pattern.finditer(original_sql):
            idx_name = match.group(1)
            # 尝试获取索引定义
            if self.db_connection:
                try:
                    cursor = self.db_connection.cursor()
                    if self.db_type == "mysql":
                        cursor.execute(f"SHOW INDEX FROM {self._quote_identifier(table)} WHERE Key_name = %s", (idx_name,))
                        idx_rows = cursor.fetchall()
                        cursor.close()
                        
                        if idx_rows:
                            cols = [row[4] for row in idx_rows]  # Column_name
                            rollback_parts.append(f"ALTER TABLE {self._quote_identifier(table)} ADD INDEX {self._quote_identifier(idx_name)} ({', '.join([self._quote_identifier(c) for c in cols])});")
                            continue
                except Exception as e:
                    logger.warning(f"获取索引定义失败: {e}")
            
            rollback_parts.append(f"-- ALTER TABLE {self._quote_identifier(table)} ADD INDEX {self._quote_identifier(idx_name)} (<需要索引列定义>);")
            warnings.append(f"无法自动恢复索引 {idx_name} 的列定义")
        
        # RENAME COLUMN
        rename_pattern = re.compile(r'RENAME\s+(?:COLUMN\s+)?[`"\[]?(\w+)[`"\]]?\s+TO\s+[`"\[]?(\w+)[`"\]]?', re.IGNORECASE)
        for match in rename_pattern.finditer(original_sql):
            old_name = match.group(2)  # 新名字
            new_name = match.group(1)  # 旧名字
            rollback_parts.append(f"ALTER TABLE {self._quote_identifier(table)} RENAME COLUMN {self._quote_identifier(old_name)} TO {self._quote_identifier(new_name)};")
        
        # RENAME TABLE
        rename_table_pattern = re.compile(r'RENAME\s+(?:TO|AS)\s+[`"\[]?(\w+)[`"\]]?', re.IGNORECASE)
        match = rename_table_pattern.search(original_sql)
        if match:
            new_name = match.group(1)
            rollback_parts.append(f"ALTER TABLE {self._quote_identifier(new_name)} RENAME TO {self._quote_identifier(table)};")
        
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
    
    def generate_redis_rollback(
        self,
        commands: str,
        redis_connection=None
    ) -> RedisRollbackResult:
        """
        生成Redis命令的回滚命令 - 查询原值
        
        Args:
            commands: Redis命令（可以是多行）
            redis_connection: Redis连接对象
        """
        rollback_commands = []
        affected_keys = []
        backup_data = {}
        warnings = []
        
        for line in commands.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if not parts:
                continue
            
            cmd = parts[0].upper()
            
            if cmd == "SET":
                key = parts[1] if len(parts) > 1 else None
                if not key:
                    continue
                
                affected_keys.append(key)
                
                # 查询原值
                if redis_connection:
                    try:
                        original_value = redis_connection.get(key)
                        original_ttl = redis_connection.ttl(key)
                        
                        backup_data[key] = {
                            'value': original_value,
                            'ttl': original_ttl
                        }
                        
                        if original_value is None:
                            # 原来不存在，回滚就是删除
                            rollback_commands.append(f"DEL {key}")
                        else:
                            # 原来存在，回滚就是恢复原值
                            if original_ttl > 0:
                                rollback_commands.append(f"SET {key} '{original_value}' EX {original_ttl}")
                            else:
                                rollback_commands.append(f"SET {key} '{original_value}'")
                    except Exception as e:
                        logger.warning(f"查询Redis键 {key} 失败: {e}")
                        rollback_commands.append(f"-- 需要手动备份 {key} 的原值")
                        warnings.append(f"无法获取 {key} 的原值")
                else:
                    rollback_commands.append(f"-- SET回滚需要先备份 {key} 的原值: GET {key}")
                    warnings.append("需要Redis连接来查询原值")
            
            elif cmd == "DEL":
                keys = parts[1:]
                if not keys:
                    continue
                
                affected_keys.extend(keys)
                
                if redis_connection:
                    for key in keys:
                        try:
                            # 检查键类型
                            key_type = redis_connection.type(key)
                            if key_type == 'none':
                                # 键不存在，无需回滚
                                continue
                            
                            # 根据类型获取值
                            if key_type == 'string':
                                value = redis_connection.get(key)
                                ttl = redis_connection.ttl(key)
                                backup_data[key] = {'type': 'string', 'value': value, 'ttl': ttl}
                                if ttl > 0:
                                    rollback_commands.append(f"SET {key} '{value}' EX {ttl}")
                                else:
                                    rollback_commands.append(f"SET {key} '{value}'")
                            elif key_type == 'hash':
                                value = redis_connection.hgetall(key)
                                ttl = redis_connection.ttl(key)
                                backup_data[key] = {'type': 'hash', 'value': value, 'ttl': ttl}
                                for field, val in value.items():
                                    rollback_commands.append(f"HSET {key} {field} '{val}'")
                            elif key_type == 'list':
                                value = redis_connection.lrange(key, 0, -1)
                                ttl = redis_connection.ttl(key)
                                backup_data[key] = {'type': 'list', 'value': value, 'ttl': ttl}
                                for val in value:
                                    rollback_commands.append(f"RPUSH {key} '{val}'")
                            elif key_type == 'set':
                                value = redis_connection.smembers(key)
                                ttl = redis_connection.ttl(key)
                                backup_data[key] = {'type': 'set', 'value': value, 'ttl': ttl}
                                for val in value:
                                    rollback_commands.append(f"SADD {key} '{val}'")
                            elif key_type == 'zset':
                                value = redis_connection.zrange(key, 0, -1, withscores=True)
                                ttl = redis_connection.ttl(key)
                                backup_data[key] = {'type': 'zset', 'value': value, 'ttl': ttl}
                                for val, score in value:
                                    rollback_commands.append(f"ZADD {key} {score} '{val}'")
                        except Exception as e:
                            logger.warning(f"备份Redis键 {key} 失败: {e}")
                            rollback_commands.append(f"-- 需要手动备份 {key}")
                            warnings.append(f"无法备份 {key}")
                else:
                    for key in keys:
                        rollback_commands.append(f"-- DEL回滚需要先备份 {key}: DUMP {key}")
                    warnings.append("需要Redis连接来查询原值")
            
            elif cmd == "HSET":
                key = parts[1] if len(parts) > 1 else None
                field = parts[2] if len(parts) > 2 else None
                if not key or not field:
                    continue
                
                affected_keys.append(key)
                
                if redis_connection:
                    try:
                        # 检查字段是否存在
                        original_value = redis_connection.hget(key, field)
                        backup_data[f"{key}.{field}"] = {'value': original_value}
                        
                        if original_value is None:
                            # 字段原来不存在，回滚就是删除字段
                            rollback_commands.append(f"HDEL {key} {field}")
                        else:
                            # 字段原来存在，恢复原值
                            rollback_commands.append(f"HSET {key} {field} '{original_value}'")
                    except Exception as e:
                        logger.warning(f"查询Redis哈希 {key}.{field} 失败: {e}")
                        rollback_commands.append(f"-- HSET回滚需要先备份 {key}.{field}")
                        warnings.append(f"无法获取 {key}.{field} 的原值")
                else:
                    rollback_commands.append(f"-- HSET回滚需要先备份 {key}.{field}: HGET {key} {field}")
                    warnings.append("需要Redis连接来查询原值")
            
            elif cmd == "EXPIRE" or cmd == "PEXPIRE":
                key = parts[1] if len(parts) > 1 else None
                if not key:
                    continue
                
                affected_keys.append(key)
                
                if redis_connection:
                    try:
                        original_ttl = redis_connection.ttl(key)
                        backup_data[key] = {'original_ttl': original_ttl}
                        
                        if original_ttl == -1:
                            # 原来没有过期时间
                            rollback_commands.append(f"PERSIST {key}")
                        elif original_ttl > 0:
                            # 恢复原有过期时间
                            rollback_commands.append(f"EXPIRE {key} {original_ttl}")
                        else:
                            # 键不存在
                            rollback_commands.append(f"-- 键 {key} 不存在")
                    except Exception as e:
                        logger.warning(f"查询Redis TTL {key} 失败: {e}")
                        warnings.append(f"无法获取 {key} 的TTL")
                else:
                    rollback_commands.append(f"-- EXPIRE回滚需要先备份 {key} 的原TTL: TTL {key}")
            
            elif cmd == "RENAME":
                old_key = parts[1] if len(parts) > 1 else None
                new_key = parts[2] if len(parts) > 2 else None
                if not old_key or not new_key:
                    continue
                
                affected_keys.extend([old_key, new_key])
                rollback_commands.append(f"RENAME {new_key} {old_key}")
            
            elif cmd in ("FLUSHALL", "FLUSHDB"):
                return RedisRollbackResult(
                    success=False,
                    rollback_commands=[],
                    warning=f"{cmd} 无法自动回滚，需要从备份恢复",
                    affected_keys=[],
                    error="危险操作，无法自动回滚"
                )
            
            else:
                # 不支持的命令
                rollback_commands.append(f"-- 不支持的命令: {line}")
                warnings.append(f"不支持自动生成 {cmd} 的回滚命令")
        
        return RedisRollbackResult(
            success=True,
            rollback_commands=rollback_commands,
            warning="; ".join(warnings) if warnings else None,
            affected_keys=affected_keys,
            backup_data=backup_data
        )


# 创建全局实例（兼容旧代码）
enhanced_rollback_generator = EnhancedRollbackGenerator()
