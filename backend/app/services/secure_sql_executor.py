"""
安全 SQL 执行服务

提供安全的 SQL 执行能力：
- 参数化查询防止 SQL 注入
- SQL 语句验证
- 危险操作检测
- 执行结果标准化
"""
import re
import logging
from typing import Tuple, Optional, List, Dict, Any, Union
from enum import Enum, StrEnum

from app.models import RDBInstance
from app.services.db_connection import db_manager, DatabaseConnectionError, DatabaseExecutionError
from app.core.exceptions import (
    ValidationException,
    ForbiddenException,
    QueryExecutionException
)

logger = logging.getLogger(__name__)


class SQLStatementType(StrEnum):
    """SQL 语句类型"""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    DDL = "DDL"
    DCL = "DCL"
    OTHER = "OTHER"


class SQLRiskLevel(StrEnum):
    """SQL 风险等级"""
    SAFE = "safe"           # 只读查询
    LOW = "low"             # 单行修改
    MEDIUM = "medium"       # 多行修改
    HIGH = "high"           # 批量修改、DDL
    CRITICAL = "critical"   # DROP、TRUNCATE 等危险操作


class SecureSQLExecutor:
    """
    安全 SQL 执行器
    
    特性：
    - 参数化查询（防注入）
    - SQL 类型识别
    - 风险等级评估
    - 危险操作检测
    """
    
    # 查询语句关键字
    QUERY_KEYWORDS = ('SELECT', 'SHOW', 'DESC', 'DESCRIBE', 'EXPLAIN', 'WITH')
    
    # DDL 关键字
    DDL_KEYWORDS = ('CREATE', 'ALTER', 'DROP', 'TRUNCATE', 'RENAME')
    
    # DML 关键字
    DML_KEYWORDS = ('INSERT', 'UPDATE', 'DELETE')
    
    # DCL 关键字
    DCL_KEYWORDS = ('GRANT', 'REVOKE')
    
    # 危险操作模式（不包括UPDATE/DELETE无WHERE的情况，由WHERE检查单独处理）
    DANGEROUS_PATTERNS = [
        r'\bDROP\s+(DATABASE|SCHEMA|TABLE)\b',
        r'\bTRUNCATE\s+(TABLE)?\b',
        r'\bGRANT\s+ALL\b',
        r'\bDROP\s+USER\b',
    ]
    
    # SQL 注入检测模式
    INJECTION_PATTERNS = [
        r"--\s*$",  # SQL 注释
        r";\s*(DROP|DELETE|TRUNCATE)",  # 语句拼接
        r"UNION\s+(ALL\s+)?SELECT",  # UNION 注入
        r"'\s*OR\s+'",  # OR 注入
        r"'\s*AND\s+'",  # AND 注入
        r"EXEC(\s+|\()",  # 存储过程执行
        r"xp_cmdshell",
    ]
    
    def detect_statement_type(self, sql: str) -> SQLStatementType:
        """
        检测 SQL 语句类型
        
        Args:
            sql: SQL 语句
        
        Returns:
            SQLStatementType: 语句类型
        """
        sql_upper = sql.upper().strip()
        
        # 移除注释
        sql_upper = re.sub(r'--.*$', '', sql_upper, flags=re.MULTILINE)
        sql_upper = re.sub(r'/\*.*?\*/', '', sql_upper, flags=re.DOTALL)
        sql_upper = sql_upper.strip()
        
        if any(sql_upper.startswith(kw) for kw in self.QUERY_KEYWORDS):
            return SQLStatementType.SELECT
        
        for kw in self.DDL_KEYWORDS:
            if sql_upper.startswith(kw):
                return SQLStatementType.DDL
        
        for kw in self.DML_KEYWORDS:
            if sql_upper.startswith(kw):
                return SQLStatementType.INSERT if kw == 'INSERT' else \
                       SQLStatementType.UPDATE if kw == 'UPDATE' else SQLStatementType.DELETE
        
        for kw in self.DCL_KEYWORDS:
            if sql_upper.startswith(kw):
                return SQLStatementType.DCL
        
        return SQLStatementType.OTHER
    
    def assess_risk_level(self, sql: str) -> tuple[SQLRiskLevel, list[str]]:
        """
        评估 SQL 风险等级
        
        Args:
            sql: SQL 语句
        
        Returns:
            Tuple[SQLRiskLevel, List[str]]: (风险等级, 风险点列表)
        """
        sql_upper = sql.upper().strip()
        risks = []
        
        # 检查危险操作（排除UPDATE/DELETE无WHERE的情况，单独处理）
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                risks.append(f"检测到危险操作: {pattern}")

        # 检查 SQL 注入模式
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                risks.append(f"疑似 SQL 注入: {pattern}")

        # 根据语句类型和风险点确定风险等级
        statement_type = self.detect_statement_type(sql)

        if risks:
            if any('DROP' in r or 'TRUNCATE' in r for r in risks):
                return SQLRiskLevel.CRITICAL, risks
            return SQLRiskLevel.HIGH, risks

        if statement_type == SQLStatementType.SELECT:
            return SQLRiskLevel.SAFE, []

        if statement_type == SQLStatementType.DDL:
            return SQLRiskLevel.HIGH, ["DDL 操作"]

        if statement_type in (SQLStatementType.UPDATE, SQLStatementType.DELETE):
            if 'WHERE' not in sql_upper:
                return SQLRiskLevel.HIGH, ["无 WHERE 条件的修改操作"]
            return SQLRiskLevel.MEDIUM, []

        if statement_type == SQLStatementType.INSERT:
            return SQLRiskLevel.LOW, []

        return SQLRiskLevel.MEDIUM, []
    
    def validate_sql(self, sql: str, allow_dangerous: bool = False) -> tuple[bool, str]:
        """
        验证 SQL 语句
        
        Args:
            sql: SQL 语句
            allow_dangerous: 是否允许危险操作
        
        Returns:
            Tuple[bool, str]: (是否有效, 错误消息)
        """
        if not sql or not sql.strip():
            return False, "SQL 语句为空"
        
        # 检查 SQL 注入模式
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                return False, f"检测到疑似 SQL 注入模式: {pattern}"
        
        # 评估风险等级
        risk_level, risks = self.assess_risk_level(sql)
        
        if risk_level == SQLRiskLevel.CRITICAL and not allow_dangerous:
            return False, f"检测到危险操作，禁止执行: {'; '.join(risks)}"
        
        return True, ""
    
    async def execute_query(
        self,
        instance: RDBInstance,
        sql: str,
        params: Optional[tuple | dict] = None,
        database: Optional[str] = None,
        fetch: bool = True
    ) -> dict[str, Any]:
        """
        执行单条查询（参数化）
        
        Args:
            instance: 数据库实例
            sql: SQL 语句
            params: 查询参数（参数化查询）
            database: 数据库名
            fetch: 是否获取结果
        
        Returns:
            Dict: 执行结果
        """
        # 验证 SQL
        valid, error = self.validate_sql(sql)
        if not valid:
            raise ValidationException(error)
        
        try:
            with db_manager.connection(instance, database) as conn:
                cursor = conn.cursor()
                
                # 参数化执行（防注入）
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                
                result = {
                    'success': True,
                    'statement_type': self.detect_statement_type(sql).value,
                    'affected_rows': cursor.rowcount if cursor.rowcount >= 0 else 0,
                    'data': []
                }
                
                # 获取数据
                if fetch and cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    result['data'] = [dict(zip(columns, row, strict=False)) for row in rows]
                    result['columns'] = columns
                
                # 非查询语句需要提交
                if not fetch:
                    conn.commit()
                
                cursor.close()
                return result
                
        except DatabaseConnectionError as e:
            raise QueryExecutionException(f"数据库连接失败: {str(e)}")
        except Exception as e:
            logger.error(f"SQL 执行失败: {sql[:100]}, 错误: {e}")
            raise QueryExecutionException(f"SQL 执行失败: {str(e)}")
    
    async def execute_script(
        self,
        instance: RDBInstance,
        script: str,
        database: Optional[str] = None,
        stop_on_error: bool = True,
        allow_dangerous: bool = False
    ) -> dict[str, Any]:
        """
        执行 SQL 脚本（多条语句）
        
        Args:
            instance: 数据库实例
            script: SQL 脚本
            database: 数据库名
            stop_on_error: 遇到错误是否停止
            allow_dangerous: 是否允许危险操作
        
        Returns:
            Dict: 执行结果
        """
        # 分割语句
        statements = self._parse_script(script)
        results = []
        total_affected = 0
        has_error = False
        
        try:
            with db_manager.connection(instance, database) as conn:
                cursor = conn.cursor()
                
                for i, sql in enumerate(statements):
                    if not sql.strip():
                        continue
                    
                    # 验证语句
                    valid, error = self.validate_sql(sql, allow_dangerous)
                    if not valid:
                        results.append({
                            'statement': i + 1,
                            'sql': sql[:100],
                            'success': False,
                            'error': error
                        })
                        has_error = True
                        if stop_on_error:
                            break
                        continue
                    
                    try:
                        cursor.execute(sql)
                        affected = cursor.rowcount if cursor.rowcount >= 0 else 0
                        conn.commit()
                        total_affected += affected
                        
                        results.append({
                            'statement': i + 1,
                            'sql': sql[:100],
                            'success': True,
                            'affected_rows': affected,
                            'risk_level': self.assess_risk_level(sql)[0].value
                        })
                        
                    except Exception as e:
                        conn.rollback()
                        results.append({
                            'statement': i + 1,
                            'sql': sql[:100],
                            'success': False,
                            'error': str(e)
                        })
                        has_error = True
                        if stop_on_error:
                            break
                
                cursor.close()
            
            success_count = sum(1 for r in results if r['success'])
            
            return {
                'success': not has_error,
                'results': results,
                'total_affected': total_affected,
                'summary': f"执行 {len(statements)} 条，成功 {success_count} 条，失败 {len(results) - success_count} 条"
            }
            
        except DatabaseConnectionError as e:
            raise QueryExecutionException(f"数据库连接失败: {str(e)}")
    
    def _parse_script(self, script: str) -> list[str]:
        """
        解析 SQL 脚本，分割为独立语句
        
        处理：
        - 分号分割
        - 保留字符串内的分号
        - 移除注释
        """
        statements = []
        current = []
        in_string = False
        string_char = None
        
        lines = script.split('\n')
        
        for line in lines:
            # 移除单行注释
            if '--' in line and not in_string:
                line = line[:line.index('--')]
            
            for char in line:
                if char in ('"', "'") and not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char and in_string:
                    in_string = False
                    string_char = None
                
                if char == ';' and not in_string:
                    stmt = ''.join(current).strip()
                    if stmt:
                        statements.append(stmt)
                    current = []
                else:
                    current.append(char)
        
        # 处理最后一条语句
        if current:
            stmt = ''.join(current).strip()
            if stmt:
                statements.append(stmt)
        
        return statements


# 单例实例
secure_sql_executor = SecureSQLExecutor()


__all__ = [
    'SecureSQLExecutor',
    'secure_sql_executor',
    'SQLStatementType',
    'SQLRiskLevel'
]
