"""
SQL优化器API
结合规则引擎和LLM提供智能SQL优化建议
"""
import time
import re
import json
import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.models import (
    RDBInstance, TableSchema, SQLAnalysisHistory, User
)
from app.schemas import (
    SQLAnalyzeRequest, SQLAnalysisResponse, TableSchemaSyncRequest,
    TableSchemaResponse, RuleIssue, ExplainRow
)
from app.deps import get_current_user
from app.utils.auth import decrypt_instance_password
import pymysql
import psycopg2
import psycopg2.extras

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sql-optimizer", tags=["SQL优化器"])

# 超时配置
DB_CONNECT_TIMEOUT = 5  # 数据库连接超时（秒）
DB_QUERY_TIMEOUT = 30   # 查询超时（秒）
LLM_TIMEOUT = 60        # LLM调用超时（秒）


# ============ 数据库连接工具 ============

def get_instance_type(instance: RDBInstance) -> str:
    """判断实例类型：mysql 或 postgresql"""
    # 通过 db_type 枚举判断
    db_type_str = instance.db_type.value if hasattr(instance.db_type, 'value') else str(instance.db_type)
    if db_type_str.upper() == 'POSTGRESQL':
        return "postgresql"
    return "mysql"


def get_db_connection(instance: RDBInstance, database: str = None):
    """获取数据库连接（支持 MySQL 和 PostgreSQL）"""
    db_type = get_instance_type(instance)
    password = decrypt_instance_password(instance.password_encrypted)
    
    if db_type == "postgresql":
        conn = psycopg2.connect(
            host=instance.host,
            port=instance.port,
            user=instance.username,
            password=password,
            database=database or 'postgres',
            connect_timeout=DB_CONNECT_TIMEOUT
        )
        return conn, "postgresql"
    else:
        conn = pymysql.connect(
            host=instance.host,
            port=instance.port,
            user=instance.username,
            password=password,
            database=database,
            connect_timeout=DB_CONNECT_TIMEOUT,
            read_timeout=DB_QUERY_TIMEOUT,
            write_timeout=DB_QUERY_TIMEOUT,
            charset='utf8mb4'
        )
        return conn, "mysql"


def test_connection(instance: RDBInstance) -> Dict[str, Any]:
    """测试数据库连接"""
    try:
        conn, db_type = get_db_connection(instance)
        cursor = conn.cursor()
        
        if db_type == "postgresql":
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
        else:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {"success": True, "db_type": db_type, "version": version}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ============ 表结构抓取功能 ============

async def fetch_table_structure(instance: RDBInstance, database: str, table_name: str) -> Optional[Dict]:
    """抓取单个表的结构信息（支持 MySQL 和 PostgreSQL）"""
    conn = None
    try:
        conn, db_type = get_db_connection(instance, database)
        
        if db_type == "postgresql":
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # PostgreSQL: 获取表基本信息
            cursor.execute("""
                SELECT 
                    c.relname as table_name,
                    'BASE TABLE' as table_type,
                    '' as engine,
                    '' as row_format,
                    c.reltuples::bigint as table_rows,
                    pg_relation_size(c.oid) as data_length,
                    pg_indexes_size(c.oid) as index_length,
                    obj_description(c.oid) as table_comment,
                    '' as create_time,
                    '' as update_time
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relname = %s AND c.relkind = 'r'
            """, (table_name,))
            table_info = cursor.fetchone()
            
            if not table_info:
                return None
            
            # PostgreSQL: 获取列信息
            cursor.execute("""
                SELECT 
                    a.attname as name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type,
                    NOT a.attnotnull as nullable,
                    pg_catalog.pg_get_expr(d.adbin, d.adrelid) as default_value,
                    col_description(a.attrelid, a.attnum) as comment,
                    CASE WHEN pk.contype = 'p' THEN True ELSE False END as is_primary
                FROM pg_attribute a
                LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
                LEFT JOIN pg_constraint pk ON pk.conrelid = a.attrelid AND pk.contype = 'p' AND a.attnum = ANY(pk.conkey)
                JOIN pg_class c ON c.oid = a.attrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relname = %s AND a.attnum > 0 AND NOT a.attisdropped
                ORDER BY a.attnum
            """, (table_name,))
            columns = cursor.fetchall()
            
            # PostgreSQL: 获取索引信息
            cursor.execute("""
                SELECT 
                    i.relname as index_name,
                    array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)) as columns,
                    NOT ix.indisunique as non_unique,
                    'btree' as index_type,
                    ix.indisprimary as is_primary
                FROM pg_index ix
                JOIN pg_class t ON t.oid = ix.indrelid
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                WHERE n.nspname = 'public' AND t.relname = %s
                GROUP BY i.relname, ix.indisunique, ix.indisprimary
            """, (table_name,))
            indexes_raw = cursor.fetchall()
            
            # 处理列信息
            columns_json = []
            for col in columns:
                columns_json.append({
                    "name": col["name"],
                    "data_type": col["data_type"],
                    "nullable": col["nullable"],
                    "default": col["default_value"],
                    "comment": col["comment"],
                    "is_primary": col["is_primary"] or False,
                    "extra": ""
                })
            
            # 处理索引信息
            indexes_json = []
            for idx in indexes_raw:
                indexes_json.append({
                    "name": idx["index_name"],
                    "columns": list(idx["columns"]) if idx["columns"] else [],
                    "unique": not idx["non_unique"],
                    "primary": idx["is_primary"],
                    "type": idx["index_type"]
                })
            
            return {
                "table_name": table_info["table_name"],
                "table_type": table_info["table_type"],
                "engine": table_info["engine"] or "postgresql",
                "row_format": table_info["row_format"] or "heap",
                "row_count": int(table_info["table_rows"] or 0),
                "data_size": int(table_info["data_length"] or 0),
                "index_size": int(table_info["index_length"] or 0),
                "table_comment": table_info["table_comment"],
                "columns": columns_json,
                "indexes": indexes_json,
                "create_time": table_info["create_time"] if table_info["create_time"] else None,
                "update_time": table_info["update_time"] if table_info["update_time"] else None
            }
        else:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # MySQL: 获取表基本信息
            cursor.execute("""
                SELECT 
                    TABLE_NAME, TABLE_TYPE, ENGINE, ROW_FORMAT,
                    TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH, TABLE_COMMENT,
                    CREATE_TIME, UPDATE_TIME
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            """, (database, table_name))
            table_info = cursor.fetchone()
            
            if not table_info:
                return None
            
            # MySQL: 获取列信息
            cursor.execute("""
                SELECT 
                    COLUMN_NAME as name,
                    COLUMN_TYPE as data_type,
                    IS_NULLABLE as nullable,
                    COLUMN_DEFAULT as default_value,
                    COLUMN_COMMENT as comment,
                    COLUMN_KEY as key_type,
                    EXTRA as extra
                FROM information_schema.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (database, table_name))
            columns = cursor.fetchall()
            
            # MySQL: 获取索引信息
            cursor.execute("""
                SELECT 
                    INDEX_NAME as index_name,
                    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as columns,
                    NON_UNIQUE as non_unique,
                    INDEX_TYPE as index_type
                FROM information_schema.STATISTICS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                GROUP BY INDEX_NAME, NON_UNIQUE, INDEX_TYPE
            """, (database, table_name))
            indexes_raw = cursor.fetchall()
            
            # 处理列信息
            columns_json = []
            for col in columns:
                columns_json.append({
                    "name": col["name"],
                    "data_type": col["data_type"],
                    "nullable": col["nullable"] == "YES",
                    "default": col["default_value"],
                    "comment": col["comment"],
                    "is_primary": col["key_type"] == "PRI",
                    "extra": col["extra"]
                })
            
            # 处理索引信息
            indexes_json = []
            for idx in indexes_raw:
                index_name = idx["index_name"]
                indexes_json.append({
                    "name": index_name,
                    "columns": idx["columns"].split(",") if idx["columns"] else [],
                    "unique": idx["non_unique"] == 0,
                    "primary": index_name == "PRIMARY",
                    "type": idx["index_type"]
                })
            
            return {
                "table_name": table_info["TABLE_NAME"],
                "table_type": table_info["TABLE_TYPE"],
                "engine": table_info["ENGINE"],
                "row_format": table_info["ROW_FORMAT"],
                "row_count": table_info["TABLE_ROWS"] or 0,
                "data_size": table_info["DATA_LENGTH"] or 0,
                "index_size": table_info["INDEX_LENGTH"] or 0,
                "table_comment": table_info["TABLE_COMMENT"],
                "columns": columns_json,
                "indexes": indexes_json,
                "create_time": table_info["CREATE_TIME"],
                "update_time": table_info["UPDATE_TIME"]
            }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取表结构失败: {str(e)}"
        )
    finally:
        if conn:
            conn.close()


async def fetch_database_tables(instance: RDBInstance, database: str) -> List[str]:
    """获取数据库中所有表名（支持 MySQL 和 PostgreSQL）"""
    conn = None
    try:
        conn, db_type = get_db_connection(instance, database)
        cursor = conn.cursor()
        
        if db_type == "postgresql":
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
        else:
            cursor.execute("SHOW TABLES")
        
        return [row[0] for row in cursor.fetchall()]
    finally:
        if conn:
            conn.close()


@router.post("/sync-schema", response_model=Dict[str, Any])
async def sync_table_schema(
    request: TableSchemaSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """同步表结构到本地数据库"""
    instance = db.query(RDBInstance).filter(RDBInstance.id == request.instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 测试连接
    conn_test = test_connection(instance)
    if not conn_test["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"无法连接到数据库实例: {conn_test['error']}"
        )
    
    db_type = conn_test["db_type"]
    
    # 获取要同步的数据库列表
    databases = []
    if request.database_name:
        databases = [request.database_name]
    else:
        # 获取所有数据库
        conn = None
        try:
            conn, _ = get_db_connection(instance)
            cursor = conn.cursor()
            
            if db_type == "postgresql":
                cursor.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
                databases = [row[0] for row in cursor.fetchall() 
                            if row[0] not in ('template0', 'template1', 'postgres')]
            else:
                cursor.execute("SHOW DATABASES")
                databases = [row[0] for row in cursor.fetchall() 
                            if row[0] not in ('information_schema', 'mysql', 'performance_schema', 'sys')]
        finally:
            if conn:
                conn.close()
    
    synced_count = 0
    errors = []
    
    for database in databases:
        # 获取表列表
        if request.table_names:
            tables = request.table_names
        else:
            tables = await fetch_database_tables(instance, database)
        
        for table_name in tables:
            try:
                # 抓取表结构
                table_data = await fetch_table_structure(instance, database, table_name)
                
                if table_data:
                    # 检查是否已存在
                    existing = db.query(TableSchema).filter(
                        TableSchema.instance_id == instance.id,
                        TableSchema.database_name == database,
                        TableSchema.table_name == table_name
                    ).first()
                    
                    if existing:
                        # 更新
                        existing.table_type = table_data["table_type"]
                        existing.engine = table_data["engine"]
                        existing.row_format = table_data["row_format"]
                        existing.row_count = table_data["row_count"]
                        existing.data_size = table_data["data_size"]
                        existing.index_size = table_data["index_size"]
                        existing.table_comment = table_data["table_comment"]
                        existing.columns_json = table_data["columns"]
                        existing.indexes_json = table_data["indexes"]
                        existing.create_time = table_data["create_time"]
                        existing.update_time = table_data["update_time"]
                        existing.sync_time = datetime.now()
                    else:
                        # 新增
                        new_schema = TableSchema(
                            instance_id=instance.id,
                            database_name=database,
                            table_name=table_name,
                            table_type=table_data["table_type"],
                            engine=table_data["engine"],
                            row_format=table_data["row_format"],
                            row_count=table_data["row_count"],
                            data_size=table_data["data_size"],
                            index_size=table_data["index_size"],
                            table_comment=table_data["table_comment"],
                            columns_json=table_data["columns"],
                            indexes_json=table_data["indexes"],
                            create_time=table_data["create_time"],
                            update_time=table_data["update_time"],
                            sync_time=datetime.now()
                        )
                        db.add(new_schema)
                    
                    synced_count += 1
                    
            except Exception as e:
                print(f"同步表 {database}.{table_name} 失败: {e}")
                continue
    
    db.commit()
    
    return {
        "success": True,
        "message": f"成功同步 {synced_count} 张表的结构信息",
        "synced_count": synced_count
    }


@router.get("/schemas/{instance_id}", response_model=List[Dict])
async def get_table_schemas(
    instance_id: int,
    database: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取实例的表结构列表"""
    query = db.query(TableSchema).filter(TableSchema.instance_id == instance_id)
    
    if database:
        query = query.filter(TableSchema.database_name == database)
    
    schemas = query.all()
    
    return [{
        "id": s.id,
        "database_name": s.database_name,
        "table_name": s.table_name,
        "engine": s.engine,
        "row_count": s.row_count,
        "table_comment": s.table_comment,
        "sync_time": s.sync_time.isoformat() if s.sync_time else None
    } for s in schemas]


# ============ SQL规则引擎 ============

class SQLRuleEngine:
    """SQL规则引擎 - 基础检查"""
    
    @staticmethod
    def normalize_sql(sql: str) -> str:
        """标准化SQL（移除多余空格、注释等）"""
        # 移除注释
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        # 标准化空白
        sql = ' '.join(sql.split())
        return sql.strip()
    
    @staticmethod
    def extract_tables(sql: str) -> List[str]:
        """从SQL中提取表名"""
        sql_upper = sql.upper()
        tables = []
        
        # 匹配 FROM table_name
        from_matches = re.findall(r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE)
        tables.extend(from_matches)
        
        # 匹配 JOIN table_name
        join_matches = re.findall(r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE)
        tables.extend(join_matches)
        
        # 匹配 UPDATE table_name
        update_matches = re.findall(r'\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE)
        tables.extend(update_matches)
        
        # 匹配 INSERT INTO table_name
        insert_matches = re.findall(r'\bINSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)', sql, re.IGNORECASE)
        tables.extend(insert_matches)
        
        return list(set(tables))
    
    @staticmethod
    def check_full_table_scan(explain_rows: List[Dict]) -> List[RuleIssue]:
        """检查全表扫描"""
        issues = []
        for row in explain_rows:
            if row.get("type") == "ALL":
                issues.append(RuleIssue(
                    severity="warning",
                    category="index",
                    title="全表扫描",
                    description=f"表 `{row.get('table', 'unknown')}` 正在进行全表扫描(type=ALL)，这将扫描所有行数据",
                    suggestion="考虑添加适当的索引来避免全表扫描，或检查WHERE条件是否可以使用现有索引",
                    related_table=row.get("table")
                ))
        return issues
    
    @staticmethod
    def check_unused_index(explain_rows: List[Dict]) -> List[RuleIssue]:
        """检查未使用索引"""
        issues = []
        for row in explain_rows:
            possible_keys = row.get("possible_keys")
            key = row.get("key")
            
            if possible_keys and possible_keys != "NULL" and (not key or key == "NULL"):
                issues.append(RuleIssue(
                    severity="warning",
                    category="index",
                    title="索引未使用",
                    description=f"表 `{row.get('table', 'unknown')}` 有可用索引 [{possible_keys}] 但未使用",
                    suggestion="检查SQL条件是否可以使用索引，或考虑调整索引结构以匹配查询条件",
                    related_table=row.get("table"),
                    related_index=possible_keys
                ))
        return issues
    
    @staticmethod
    def check_temporary_table(explain_rows: List[Dict]) -> List[RuleIssue]:
        """检查临时表使用"""
        issues = []
        for row in explain_rows:
            extra = row.get("Extra") or ""
            if "Using temporary" in extra:
                issues.append(RuleIssue(
                    severity="warning",
                    category="performance",
                    title="使用临时表",
                    description=f"表 `{row.get('table', 'unknown')}` 查询使用了临时表，可能影响性能",
                    suggestion="检查GROUP BY、ORDER BY或DISTINCT是否可以使用索引优化，避免创建临时表",
                    related_table=row.get("table")
                ))
        return issues
    
    @staticmethod
    def check_filesort(explain_rows: List[Dict]) -> List[RuleIssue]:
        """检查文件排序"""
        issues = []
        for row in explain_rows:
            extra = row.get("Extra") or ""
            if "Using filesort" in extra:
                issues.append(RuleIssue(
                    severity="warning",
                    category="performance",
                    title="使用文件排序",
                    description=f"表 `{row.get('table', 'unknown')}` 查询使用了文件排序(filesort)",
                    suggestion="为ORDER BY涉及的字段添加索引，或调整查询避免不必要的排序",
                    related_table=row.get("table")
                ))
        return issues
    
    @staticmethod
    def check_large_scan(explain_rows: List[Dict]) -> List[RuleIssue]:
        """检查大范围扫描"""
        issues = []
        for row in explain_rows:
            rows = row.get("rows")
            if rows and rows > 10000:
                severity = "error" if rows > 100000 else "warning"
                issues.append(RuleIssue(
                    severity=severity,
                    category="performance",
                    title="扫描行数过多",
                    description=f"表 `{row.get('table', 'unknown')}` 预计扫描 {rows:,} 行数据",
                    suggestion="考虑添加更精确的WHERE条件，或添加合适的索引以减少扫描行数",
                    related_table=row.get("table")
                ))
        return issues
    
    @staticmethod
    def check_select_star(sql: str) -> List[RuleIssue]:
        """检查SELECT *"""
        issues = []
        sql_upper = sql.upper()
        # 简单检查 SELECT *
        if re.search(r'SELECT\s+\*\s+FROM', sql, re.IGNORECASE):
            issues.append(RuleIssue(
                severity="info",
                category="performance",
                title="使用SELECT *",
                description="查询使用了 SELECT *，会返回所有列",
                suggestion="明确指定需要的列名，避免返回不必要的数据，减少网络传输和内存消耗"
            ))
        return issues
    
    @staticmethod
    def check_like_pattern(sql: str) -> List[RuleIssue]:
        """检查LIKE模式"""
        issues = []
        # 检查 LIKE '%xxx' 模式
        if re.search(r"LIKE\s+['\"]%", sql, re.IGNORECASE):
            issues.append(RuleIssue(
                severity="warning",
                category="index",
                title="LIKE以通配符开头",
                description="LIKE条件以通配符开头(如 LIKE '%xxx')，无法使用索引",
                suggestion="如果必须使用前缀通配符，考虑使用全文索引或搜索引擎。如果可能，改为 LIKE 'xxx%' 以使用索引"
            ))
        return issues
    
    @staticmethod
    def check_or_condition(sql: str, explain_rows: List[Dict]) -> List[RuleIssue]:
        """检查OR条件"""
        issues = []
        sql_upper = sql.upper()
        
        if " OR " in sql_upper:
            for row in explain_rows:
                if row.get("type") == "ALL":
                    issues.append(RuleIssue(
                        severity="warning",
                        category="index",
                        title="OR条件导致全表扫描",
                        description="OR条件可能导致索引失效，触发全表扫描",
                        suggestion="考虑将OR改写为UNION ALL，或确保OR两边的字段都有索引",
                        related_table=row.get("table")
                    ))
                    break
        return issues
    
    @staticmethod
    def check_function_on_index(sql: str) -> List[RuleIssue]:
        """检查索引列上使用函数"""
        issues = []
        # 检查常见的函数使用模式
        function_patterns = [
            (r'WHERE\s+\w+\s*=\s*DATE\s*\(', "在DATE()函数中使用日期列"),
            (r'WHERE\s+\w+\s*=\s*YEAR\s*\(', "在YEAR()函数中使用日期列"),
            (r'WHERE\s+\w+\s*=\s*MONTH\s*\(', "在MONTH()函数中使用日期列"),
            (r'WHERE\s+LOWER\s*\(\s*\w+\s*\)', "在LOWER()函数中使用列"),
            (r'WHERE\s+UPPER\s*\(\s*\w+\s*\)', "在UPPER()函数中使用列"),
        ]
        
        for pattern, desc in function_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                issues.append(RuleIssue(
                    severity="warning",
                    category="index",
                    title="索引列上使用函数",
                    description=f"{desc}，会导致索引失效",
                    suggestion="将函数应用到值而不是列上，例如将 `WHERE DATE(create_time) = '2024-01-01'` 改为 `WHERE create_time >= '2024-01-01' AND create_time < '2024-01-02'`"
                ))
        return issues
    
    def analyze(self, sql: str, explain_rows: List[Dict]) -> List[RuleIssue]:
        """执行所有规则检查"""
        all_issues = []
        
        # 基于EXPLAIN的检查
        all_issues.extend(self.check_full_table_scan(explain_rows))
        all_issues.extend(self.check_unused_index(explain_rows))
        all_issues.extend(self.check_temporary_table(explain_rows))
        all_issues.extend(self.check_filesort(explain_rows))
        all_issues.extend(self.check_large_scan(explain_rows))
        
        # 基于SQL文本的检查
        all_issues.extend(self.check_select_star(sql))
        all_issues.extend(self.check_like_pattern(sql))
        all_issues.extend(self.check_or_condition(sql, explain_rows))
        all_issues.extend(self.check_function_on_index(sql))
        
        return all_issues


# ============ LLM分析模块 ============

async def get_llm_analysis(
    sql: str,
    explain_result: List[Dict],
    table_schemas: List[Dict],
    db_type: str = "mysql",
    db_version: str = "8.0"
) -> str:
    """使用LLM进行深度SQL分析（带超时控制）"""
    from app.utils.llm_client import get_llm_client
    
    # 构建上下文
    context = {
        "database_type": db_type,
        "database_version": db_version,
        "sql": sql,
        "explain_result": explain_result,
        "table_schemas": table_schemas
    }
    
    system_prompt = """你是一位资深的数据库性能优化专家，擅长MySQL和PostgreSQL的SQL优化。
你的任务是分析SQL语句的性能问题并提供优化建议。

请从以下几个方面进行分析：
1. **执行计划分析**：解读EXPLAIN结果，指出潜在的性能瓶颈
2. **索引建议**：根据表结构和查询条件，给出具体的索引创建建议
3. **SQL改写建议**：如果可以优化SQL写法，给出改写后的SQL
4. **风险提示**：指出可能存在的并发问题、锁风险等
5. **最佳实践**：结合数据库版本特性，给出最佳实践建议

请用中文回答，结构清晰，建议具体可操作。"""

    user_message = f"""请分析以下SQL语句：

**数据库类型**: {context['database_type']}
**数据库版本**: {context['database_version']}

**SQL语句**:
```sql
{context['sql']}
```

**EXPLAIN结果**:
```json
{json.dumps(context['explain_result'], ensure_ascii=False, indent=2)}
```

**相关表结构**:
```json
{json.dumps(context['table_schemas'], ensure_ascii=False, indent=2)}
```

请给出详细的优化建议。"""

    try:
        client = get_llm_client()
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # 使用 asyncio 等待，设置超时
        response = await asyncio.wait_for(
            client.ainvoke(
                messages=messages,
                temperature=0.3,
                max_tokens=4096
            ),
            timeout=LLM_TIMEOUT
        )
        
        return response
            
    except asyncio.TimeoutError:
        return "LLM分析超时，请稍后重试"
    except Exception as e:
        return f"LLM分析失败: {str(e)}"


# ============ 主要分析接口 ============

@router.post("/analyze", response_model=SQLAnalysisResponse)
async def analyze_sql(
    request: SQLAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """分析SQL并给出优化建议"""
    start_time = time.time()
    
    # 获取实例信息
    instance = db.query(RDBInstance).filter(RDBInstance.id == request.instance_id).first()
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="实例不存在"
        )
    
    # 测试连接
    conn_test = test_connection(instance)
    if not conn_test["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"无法连接到数据库实例: {conn_test['error']}"
        )
    
    db_type = conn_test["db_type"]
    
    conn = None
    try:
        # 连接数据库
        conn, actual_db_type = get_db_connection(instance, request.database_name)
        
        if actual_db_type == "postgresql":
            cursor = conn.cursor()
            
            # PostgreSQL: 获取数据库版本
            cursor.execute("SELECT version()")
            version = cursor.fetchone()
            db_version = version[0] if version else "15.0"
            
            # 执行 EXPLAIN (FORMAT JSON)
            sql_normalized = SQLRuleEngine.normalize_sql(request.sql_text)
            explain_sql = f"EXPLAIN (FORMAT JSON) {sql_normalized}"
            cursor.execute(explain_sql)
            explain_result = cursor.fetchone()
            
            # 解析 PostgreSQL EXPLAIN JSON 结果
            explain_rows = []
            if explain_result:
                try:
                    # PostgreSQL EXPLAIN JSON 返回的是数组
                    plan_str = explain_result[0] if isinstance(explain_result, (list, tuple)) else explain_result
                    plan_data = json.loads(plan_str) if isinstance(plan_str, str) else plan_str
                    
                    # plan_data 是数组，取第一个元素
                    if isinstance(plan_data, list) and len(plan_data) > 0:
                        plan_data = plan_data[0]
                    
                    def extract_plan_info(plan, depth=0):
                        rows = []
                        if not isinstance(plan, dict):
                            return rows
                        
                        node_type = plan.get("Node Type", "Unknown")
                        
                        rows.append({
                            "id": depth,
                            "select_type": plan.get("Parent Relationship", "Scan"),
                            "table": plan.get("Relation Name") or plan.get("Alias", ""),
                            "type": node_type.replace(" Scan", "").lower() if "Scan" in node_type else node_type.lower(),
                            "possible_keys": None,
                            "key": None,
                            "key_len": None,
                            "ref": None,
                            "rows": plan.get("Plan Rows", 0),
                            "filtered": None,
                            "Extra": plan.get("Filter", "")
                        })
                        
                        # 处理子计划
                        if "Plans" in plan:
                            for sub_plan in plan["Plans"]:
                                rows.extend(extract_plan_info(sub_plan, depth + 1))
                        
                        return rows
                    
                    if isinstance(plan_data, dict):
                        explain_rows = extract_plan_info(plan_data.get("Plan", plan_data))
                        
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    # 如果解析失败，返回基本信息
                    explain_rows = [{
                        "id": 1,
                        "select_type": "QUERY",
                        "table": "",
                        "type": "unknown",
                        "possible_keys": None,
                        "key": None,
                        "key_len": None,
                        "ref": None,
                        "rows": 0,
                        "filtered": None,
                        "Extra": f"Parse error: {str(e)}"
                    }]
        else:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # MySQL: 获取数据库版本
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            # 兼容 dict 和 tuple 两种返回类型
            if version:
                db_version = version["VERSION()"] if isinstance(version, dict) else version[0]
            else:
                db_version = "8.0"
            
            # 执行 EXPLAIN
            sql_normalized = SQLRuleEngine.normalize_sql(request.sql_text)
            explain_sql = f"EXPLAIN {sql_normalized}"
            cursor.execute(explain_sql)
            explain_result = cursor.fetchall()
            
            # 转换 EXPLAIN 结果
            explain_rows = []
            for row in explain_result:
                # 安全处理，确保 row 是字典
                if isinstance(row, dict):
                    explain_rows.append({
                        "id": row.get("id"),
                        "select_type": row.get("select_type"),
                        "table": row.get("table"),
                        "type": row.get("type"),
                        "possible_keys": row.get("possible_keys"),
                        "key": row.get("key"),
                        "key_len": row.get("key_len"),
                        "ref": row.get("ref"),
                        "rows": row.get("rows"),
                        "filtered": row.get("filtered"),
                        "Extra": row.get("Extra")
                    })
                elif isinstance(row, (list, tuple)) and len(row) >= 11:
                    # 如果返回的是 tuple，按顺序映射
                    explain_rows.append({
                        "id": row[0],
                        "select_type": row[1],
                        "table": row[2],
                        "type": row[3],
                        "possible_keys": row[4],
                        "key": row[5],
                        "key_len": row[6],
                        "ref": row[7],
                        "rows": row[8],
                        "filtered": row[9],
                        "Extra": row[10]
                    })
        
        # 规则引擎分析
        rule_engine = SQLRuleEngine()
        rule_issues = rule_engine.analyze(request.sql_text, explain_rows)
        
        # 提取表名
        tables = rule_engine.extract_tables(request.sql_text)
        
        # 获取已同步的表结构
        table_schemas = db.query(TableSchema).filter(
            TableSchema.instance_id == instance.id,
            TableSchema.database_name == request.database_name,
            TableSchema.table_name.in_(tables)
        ).all()
        
        # 自动同步未缓存的表结构
        synced_tables = [schema.table_name for schema in table_schemas]
        missing_tables = [t for t in tables if t not in synced_tables]
        
        # 检查已缓存表是否过期（超过 7 天）
        STALE_THRESHOLD_DAYS = 7
        stale_tables = []
        fresh_schemas = []
        
        for schema in table_schemas:
            if schema.sync_time:
                days_since_sync = (datetime.now() - schema.sync_time).days
                if days_since_sync > STALE_THRESHOLD_DAYS:
                    stale_tables.append(schema.table_name)
                    logger.info(f"表 {schema.table_name} 的结构已过期（{days_since_sync}天未更新），将重新获取")
                else:
                    fresh_schemas.append(schema)
            else:
                fresh_schemas.append(schema)
        
        auto_sync_info = {"synced": [], "failed": [], "refreshed": []}
        
        # 需要获取的表 = 未缓存的表 + 过期的表
        tables_to_fetch = list(set(missing_tables + stale_tables))
        
        if tables_to_fetch:
            logger.info(f"开始获取表结构: {tables_to_fetch}")
            
            # 获取连接
            try:
                conn, _ = get_db_connection(instance)
                cursor = conn.cursor()
                
                for table_name in tables_to_fetch:
                    try:
                        # 获取表结构
                        table_data = await fetch_table_structure(instance, request.database_name, table_name)
                        
                        if table_data:
                            # 检查是否已存在（可能是过期的表需要更新）
                            existing = db.query(TableSchema).filter(
                                TableSchema.instance_id == instance.id,
                                TableSchema.database_name == request.database_name,
                                TableSchema.table_name == table_name
                            ).first()
                            
                            if existing:
                                # 更新过期表
                                existing.table_type = table_data["table_type"]
                                existing.engine = table_data["engine"]
                                existing.row_format = table_data["row_format"]
                                existing.row_count = table_data["row_count"]
                                existing.data_size = table_data["data_size"]
                                existing.index_size = table_data["index_size"]
                                existing.table_comment = table_data["table_comment"]
                                existing.columns_json = table_data["columns"]
                                existing.indexes_json = table_data["indexes"]
                                existing.create_time = table_data["create_time"]
                                existing.update_time = table_data["update_time"]
                                existing.sync_time = datetime.now()
                                db.commit()
                                
                                fresh_schemas.append(existing)
                                auto_sync_info["refreshed"].append(table_name)
                                logger.info(f"刷新过期表结构成功: {table_name}")
                            else:
                                # 新增表
                                new_schema = TableSchema(
                                    instance_id=instance.id,
                                    database_name=request.database_name,
                                    table_name=table_name,
                                    table_type=table_data["table_type"],
                                    engine=table_data["engine"],
                                    row_format=table_data["row_format"],
                                    row_count=table_data["row_count"],
                                    data_size=table_data["data_size"],
                                    index_size=table_data["index_size"],
                                    table_comment=table_data["table_comment"],
                                    columns_json=table_data["columns"],
                                    indexes_json=table_data["indexes"],
                                    create_time=table_data["create_time"],
                                    update_time=table_data["update_time"],
                                    sync_time=datetime.now()
                                )
                                db.add(new_schema)
                                db.commit()
                                db.refresh(new_schema)
                                
                                fresh_schemas.append(new_schema)
                                auto_sync_info["synced"].append(table_name)
                                logger.info(f"自动同步表结构成功: {table_name}")
                        else:
                            auto_sync_info["failed"].append({"table": table_name, "error": "表不存在或无法获取结构"})
                    except Exception as e:
                        auto_sync_info["failed"].append({"table": table_name, "error": str(e)})
                        logger.error(f"获取表结构失败 {table_name}: {e}")
            except Exception as e:
                logger.error(f"连接数据库失败，无法自动同步: {e}")
            finally:
                if conn:
                    conn.close()
        
        # 使用最新的表结构列表
        table_schemas = fresh_schemas
        
        schemas_for_llm = []
        for schema in table_schemas:
            schemas_for_llm.append({
                "table_name": schema.table_name,
                "columns": schema.columns_json,
                "indexes": schema.indexes_json,
                "row_count": schema.row_count,
                "table_comment": schema.table_comment
            })
        
        # LLM分析
        llm_suggestions = None
        if request.enable_llm:
            llm_suggestions = await get_llm_analysis(
                sql_normalized,
                explain_rows,
                schemas_for_llm,
                db_type,  # 使用实际连接检测到的数据库类型
                db_version
            )
        
        # 计算风险等级
        risk_level = "low"
        if any(i.severity == "critical" for i in rule_issues):
            risk_level = "critical"
        elif any(i.severity == "error" for i in rule_issues):
            risk_level = "high"
        elif any(i.severity == "warning" for i in rule_issues):
            risk_level = "medium"
        
        # 计算分析耗时
        analysis_time = time.time() - start_time
        
        # 保存分析历史
        history = SQLAnalysisHistory(
            instance_id=instance.id,
            database_name=request.database_name,
            sql_text=request.sql_text,
            sql_normalized=sql_normalized,
            explain_json=explain_rows,
            rule_issues=[issue.model_dump() for issue in rule_issues],
            llm_suggestions=llm_suggestions,
            risk_level=risk_level,
            analysis_time=analysis_time,
            analyzed_by=current_user.id
        )
        db.add(history)
        db.commit()
        
        # 构建摘要
        summary = {
            "tables_involved": tables,
            "issues_count": len(rule_issues),
            "critical_count": sum(1 for i in rule_issues if i.severity == "critical"),
            "warning_count": sum(1 for i in rule_issues if i.severity == "warning"),
            "info_count": sum(1 for i in rule_issues if i.severity == "info"),
            "total_rows_scanned": sum(row.get("rows") or 0 for row in explain_rows)
        }
        
        # 判断是否需要返回自动同步信息
        auto_sync_result = None
        if auto_sync_info["synced"] or auto_sync_info["refreshed"] or auto_sync_info["failed"]:
            auto_sync_result = auto_sync_info
        
        return SQLAnalysisResponse(
            sql_text=request.sql_text,
            sql_normalized=sql_normalized,
            explain_result=[ExplainRow(**row) for row in explain_rows],
            rule_issues=rule_issues,
            llm_suggestions=llm_suggestions,
            risk_level=risk_level,
            analysis_time=analysis_time,
            summary=summary,
            auto_sync_info=auto_sync_result
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SQL分析失败: {str(e)}"
        )
    finally:
        if conn:
            conn.close()


@router.get("/history/{instance_id}", response_model=List[Dict])
async def get_analysis_history(
    instance_id: int,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取SQL分析历史"""
    history = db.query(SQLAnalysisHistory).filter(
        SQLAnalysisHistory.instance_id == instance_id
    ).order_by(SQLAnalysisHistory.created_at.desc()).limit(limit).all()
    
    return [{
        "id": h.id,
        "database_name": h.database_name,
        "sql_text": h.sql_text[:100] + "..." if len(h.sql_text) > 100 else h.sql_text,
        "risk_level": h.risk_level,
        "issues_count": len(h.rule_issues) if h.rule_issues else 0,
        "analysis_time": h.analysis_time,
        "created_at": h.created_at.isoformat()
    } for h in history]


@router.get("/history/detail/{history_id}", response_model=Dict)
async def get_analysis_detail(
    history_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取分析详情"""
    history = db.query(SQLAnalysisHistory).filter(
        SQLAnalysisHistory.id == history_id
    ).first()
    
    if not history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分析记录不存在"
        )
    
    # 从存储的数据中计算 summary
    rule_issues = history.rule_issues or []
    explain_rows = history.explain_json or []
    
    # 提取涉及的表
    tables = set()
    for row in explain_rows:
        if row.get("table"):
            tables.add(row.get("table"))
    
    summary = {
        "tables_involved": list(tables),
        "issues_count": len(rule_issues),
        "critical_count": sum(1 for i in rule_issues if i.get("severity") == "critical"),
        "warning_count": sum(1 for i in rule_issues if i.get("severity") == "warning"),
        "info_count": sum(1 for i in rule_issues if i.get("severity") == "info"),
        "total_rows_scanned": sum(row.get("rows") or 0 for row in explain_rows)
    }
    
    return {
        "id": history.id,
        "instance_id": history.instance_id,
        "database_name": history.database_name,
        "sql_text": history.sql_text,
        "sql_normalized": history.sql_normalized,
        "explain_result": history.explain_json,
        "rule_issues": history.rule_issues,
        "llm_suggestions": history.llm_suggestions,
        "risk_level": history.risk_level,
        "analysis_time": history.analysis_time,
        "summary": summary,
        "created_at": history.created_at.isoformat()
    }
