"""
慢查询分析服务

提供慢查询的分析能力：
- EXPLAIN 执行分析
- LLM 智能分析
- 优化建议生成
"""
import json
import logging
from typing import Dict, Any, List, Optional

import pymysql
from pymysql.cursors import DictCursor

from app.models import RDBInstance, SlowQuery
from app.utils.auth import aes_cipher
from app.services.db_connection import db_manager

logger = logging.getLogger(__name__)


class SlowQueryAnalyzer:
    """慢查询分析器"""
    
    async def execute_explain(
        self,
        instance: RDBInstance,
        sql: str,
        database_name: Optional[str] = None
    ) -> dict[str, Any]:
        """
        执行 EXPLAIN 分析
        
        Args:
            instance: 数据库实例
            sql: SQL语句
            database_name: 数据库名
            
        Returns:
            EXPLAIN 结果
        """
        if not sql:
            return {"error": "SQL语句为空"}
        
        # 清理 SQL
        sql = sql.strip()
        if sql.endswith(';'):
            sql = sql[:-1]
        
        result = {
            "explain": [],
            "explain_json": None,
            "warnings": [],
            "error": None
        }
        
        connection = None
        try:
            # 解密密码
            password = aes_cipher.decrypt(instance.password_encrypted)
            
            # 连接数据库
            connection = pymysql.connect(
                host=instance.host,
                port=instance.port,
                user=instance.username,
                password=password,
                database=database_name if database_name else None,
                connect_timeout=10,
                read_timeout=30,
                cursorclass=DictCursor
            )
            
            with connection.cursor() as cursor:
                # 执行 EXPLAIN
                explain_sql = f"EXPLAIN {sql}"
                cursor.execute(explain_sql)
                explain_rows = cursor.fetchall()
                
                # 转换为列表并处理特殊类型
                result["explain"] = []
                for row in explain_rows:
                    row_dict = {}
                    for key, value in row.items():
                        if isinstance(value, bytes):
                            row_dict[key] = value.decode('utf-8', errors='replace')
                        else:
                            row_dict[key] = value
                    result["explain"].append(row_dict)
                
                # 尝试获取 JSON 格式的 EXPLAIN（MySQL 5.6.5+）
                try:
                    cursor.execute(f"EXPLAIN FORMAT=JSON {sql}")
                    json_result = cursor.fetchone()
                    if json_result and 'EXPLAIN' in json_result:
                        result["explain_json"] = json.loads(json_result['EXPLAIN'])
                except Exception as e:
                    logger.debug(f"获取 JSON 格式 EXPLAIN 失败: {e}")
                
                # 检查警告
                cursor.execute("SHOW WARNINGS")
                warnings = cursor.fetchall()
                if warnings:
                    result["warnings"] = [
                        {"level": w.get('Level', ''), "code": w.get('Code', ''),
                         "message": w.get('Message', '')}
                        for w in warnings
                    ]
                    
        except pymysql.err.OperationalError as e:
            error_code, error_msg = e.args
            result["error"] = f"数据库连接错误: {error_msg}"
            logger.error(f"连接数据库失败: {e}")
        except pymysql.err.ProgrammingError as e:
            error_code, error_msg = e.args
            result["error"] = f"SQL语法错误: {error_msg}"
            logger.error(f"SQL 执行错误: {e}")
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"执行 EXPLAIN 失败: {e}")
        finally:
            if connection:
                try:
                    connection.close()
                except Exception:
                    pass
        
        return result
    
    def generate_suggestions(
        self,
        explain_result: dict[str, Any],
        slow_query: Optional[SlowQuery] = None
    ) -> list[dict[str, str]]:
        """
        根据EXPLAIN结果生成优化建议
        
        Args:
            explain_result: EXPLAIN 分析结果
            slow_query: 慢查询记录
            
        Returns:
            优化建议列表
        """
        suggestions = []
        
        if explain_result.get("error"):
            suggestions.append({
                "type": "error",
                "title": "分析失败",
                "description": explain_result["error"],
                "action": "请检查SQL语法是否正确，或数据库连接是否正常"
            })
            return suggestions
        
        explain_rows = explain_result.get("explain", [])
        
        for row in explain_rows:
            select_type = row.get("select_type", "")
            type_ = row.get("type", "")
            key = row.get("key", "")
            rows_examined = row.get("rows", 0)
            extra = row.get("Extra", "")
            
            # 全表扫描
            if type_ == "ALL":
                suggestions.append({
                    "type": "warning",
                    "title": f"表 {row.get('table', '未知')} 全表扫描",
                    "description": f"type={type_}，正在扫描全表，这是最慢的访问方式",
                    "action": f"建议为 WHERE/JOIN 条件中的列添加索引，当前表扫描约 {rows_examined:,} 行"
                })
            
            # 索引效率低
            elif type_ in ["index", "range"] and rows_examined and rows_examined > 10000:
                suggestions.append({
                    "type": "warning",
                    "title": f"表 {row.get('table', '未知')} 扫描行数过多",
                    "description": f"type={type_}，扫描约 {rows_examined:,} 行，可能索引选择不佳",
                    "action": "检查索引是否覆盖了查询条件，考虑创建更合适的复合索引"
                })
            
            # 使用了临时表
            if "Using temporary" in str(extra):
                suggestions.append({
                    "type": "info",
                    "title": "使用临时表",
                    "description": "查询需要创建临时表来处理结果",
                    "action": "检查 GROUP BY 或 ORDER BY 是否可以使用索引，避免临时表"
                })
            
            # 使用了文件排序
            if "Using filesort" in str(extra):
                suggestions.append({
                    "type": "info",
                    "title": "使用文件排序",
                    "description": "查询需要额外的排序操作",
                    "action": "为 ORDER BY 列添加索引，避免额外排序"
                })
            
            # 没有使用索引
            if not key or key == "NULL":
                if type_ != "ALL":
                    suggestions.append({
                        "type": "warning",
                        "title": f"表 {row.get('table', '未知')} 未使用索引",
                        "description": f"当前访问类型为 {type_}，未使用任何索引",
                        "action": "检查查询条件，为相关列创建合适的索引"
                    })
            
            # DERIVED 子查询
            if select_type == "DERIVED":
                suggestions.append({
                    "type": "info",
                    "title": "派生表（子查询）",
                    "description": "使用了派生表，可能导致性能问题",
                    "action": "考虑将子查询改写为 JOIN，或确保子查询使用了索引"
                })
        
        # 基于慢查询统计数据的建议
        if slow_query:
            if slow_query.rows_examined and slow_query.rows_sent:
                ratio = slow_query.rows_examined / slow_query.rows_sent if slow_query.rows_sent > 0 else 0
                if ratio > 100:
                    suggestions.append({
                        "type": "warning",
                        "title": "扫描行数与返回行数比例过高",
                        "description": f"扫描了 {slow_query.rows_examined:,} 行但只返回了 {slow_query.rows_sent:,} 行（比例: {ratio:.0f}:1）",
                        "action": "查询效率低，建议优化 WHERE 条件或添加更精确的索引"
                    })
            
            if slow_query.lock_time and slow_query.lock_time > 0.1:
                suggestions.append({
                    "type": "warning",
                    "title": "锁等待时间较长",
                    "description": f"锁等待时间: {slow_query.lock_time:.3f} 秒",
                    "action": "检查是否有长事务阻塞，考虑优化事务范围或使用乐观锁"
                })
        
        # 如果没有建议，给出正面反馈
        if not suggestions:
            suggestions.append({
                "type": "success",
                "title": "查询计划看起来不错",
                "description": "EXPLAIN 结果显示查询使用了索引，没有明显的性能问题",
                "action": "如果仍然较慢，可能是数据量过大或网络延迟导致，考虑分库分表"
            })
        
        return suggestions
    
    async def analyze_with_llm(
        self,
        sql: str,
        explain_result: dict,
        slow_query: Optional[SlowQuery] = None
    ) -> dict[str, Any]:
        """
        使用大模型分析 SQL 和 EXPLAIN 结果，生成优化建议
        
        Args:
            sql: SQL 语句
            explain_result: EXPLAIN 分析结果
            slow_query: 慢查询记录（可选）
            
        Returns:
            大模型分析结果
        """
        try:
            from coze_coding_dev_sdk import LLMClient
            from langchain_core.messages import SystemMessage, HumanMessage
            
            # 构建 EXPLAIN 结果的文本描述
            explain_text = self._format_explain_text(explain_result)
            
            # 构建慢查询统计信息
            stats_text = self._format_stats_text(slow_query) if slow_query else ""
            
            # 构建提示词
            system_prompt = self._get_llm_system_prompt()
            user_prompt = self._get_llm_user_prompt(sql, explain_text, stats_text)
            
            client = LLMClient()
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            # 调用大模型
            response = client.invoke(
                messages=messages,
                model="doubao-seed-2-0-lite-260215",
                temperature=0.3,
                max_completion_tokens=4096
            )
            
            # 处理响应内容
            content = response.content
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                content = " ".join(text_parts)
            
            # 尝试解析 JSON
            llm_analysis = self._parse_llm_response(content)
            
            return {
                "success": True,
                "analysis": llm_analysis
            }
            
        except Exception as e:
            logger.error(f"LLM 分析失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_explain_text(self, explain_result: dict) -> str:
        """格式化 EXPLAIN 结果为文本"""
        explain_text = ""
        if explain_result.get("explain"):
            explain_text = "执行计划:\n"
            for idx, row in enumerate(explain_result["explain"]):
                explain_text += f"表 {idx + 1}:\n"
                explain_text += f"  - 查询类型: {row.get('select_type', '-')}\n"
                explain_text += f"  - 表名: {row.get('table', '-')}\n"
                explain_text += f"  - 访问类型: {row.get('type', '-')}\n"
                explain_text += f"  - 可能使用的索引: {row.get('possible_keys', '-')}\n"
                explain_text += f"  - 实际使用的索引: {row.get('key', '-')}\n"
                explain_text += f"  - 索引长度: {row.get('key_len', '-')}\n"
                explain_text += f"  - 预估扫描行数: {row.get('rows', '-')}\n"
                explain_text += f"  - 额外信息: {row.get('Extra', '-')}\n\n"
        return explain_text
    
    def _format_stats_text(self, slow_query: SlowQuery) -> str:
        """格式化慢查询统计信息"""
        return f"""
查询统计信息:
- 执行耗时: {slow_query.query_time:.2f} 秒
- 锁等待时间: {slow_query.lock_time:.3f} 秒
- 扫描行数: {slow_query.rows_examined or 0}
- 返回行数: {slow_query.rows_sent or 0}
- 执行次数: {slow_query.execution_count or 1}
"""
    
    def _get_llm_system_prompt(self) -> str:
        """获取 LLM 系统提示词"""
        return """你是一位资深的数据库性能优化专家，擅长分析 MySQL 慢查询和 EXPLAIN 执行计划。

你的任务是：
1. 分析 SQL 语句的结构和逻辑
2. 解读 EXPLAIN 执行计划，识别性能瓶颈
3. 给出具体、可执行的优化建议

分析要点：
- 访问类型（type）：重点关注 ALL（全表扫描）、index（索引扫描）、range（范围扫描）
- 索引使用：检查是否使用了合适的索引
- 扫描行数：预估扫描行数与实际返回行数的比例
- Extra 信息：关注 Using temporary（临时表）、Using filesort（文件排序）
- SQL 写法：检查是否有不合理的写法

请以 JSON 格式输出分析结果，格式如下：
{
  "summary": "一句话总结查询性能问题",
  "issues": [
    {
      "severity": "high/medium/low",
      "type": "问题类型",
      "description": "问题描述",
      "location": "问题位置"
    }
  ],
  "suggestions": [
    {
      "priority": "high/medium/low",
      "type": "索引优化/SQL改写/配置调整",
      "description": "建议描述",
      "action": "具体操作步骤",
      "expected_improvement": "预期效果"
    }
  ],
  "optimized_sql": "优化后的SQL（如有）",
  "create_index_sql": "建议创建索引的SQL语句（如有）"
}"""
    
    def _get_llm_user_prompt(self, sql: str, explain_text: str, stats_text: str) -> str:
        """获取 LLM 用户提示词"""
        return f"""请分析以下慢查询：

SQL 语句:
```sql
{sql}
```

{explain_text}
{stats_text}

请给出详细的性能分析和优化建议。"""
    
    def _parse_llm_response(self, content: str) -> dict:
        """解析 LLM 响应"""
        try:
            json_str = content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            
            return json.loads(json_str.strip())
        except json.JSONDecodeError:
            return {
                "summary": "大模型分析结果",
                "raw_response": content
            }


# 单例实例
slow_query_analyzer = SlowQueryAnalyzer()
