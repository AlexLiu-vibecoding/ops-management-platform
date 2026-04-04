"""
SQL执行服务

负责执行MySQL/PostgreSQL的SQL语句，支持多种数据库类型
"""
import re
import logging
from typing import Tuple, Optional
import pymysql
import psycopg2
import redis

from app.models import ApprovalRecord, RDBInstance, RedisInstance
from app.utils.auth import decrypt_instance_password
from app.services.storage import storage_manager

logger = logging.getLogger(__name__)


class SQLExecutor:
    """SQL执行器，支持MySQL/PostgreSQL"""
    
    # 查询语句前缀
    QUERY_PREFIXES = ('SELECT', 'SHOW', 'DESC', 'DESCRIBE', 'EXPLAIN', 'WITH')
    
    async def execute_for_approval(self, approval: ApprovalRecord, instance: RDBInstance) -> tuple[bool, str, int]:
        """
        执行审批工单中的SQL
        
        Args:
            approval: 审批记录
            instance: 数据库实例
            
        Returns:
            Tuple[bool, str, int]: (是否全部成功, 结果消息, 影响行数)
        """
        # 解密密码
        try:
            password = decrypt_instance_password(instance.password_encrypted)
        except ValueError as e:
            return False, f"密码解密失败: {str(e)}", 0
        
        # 确定数据库类型
        db_type = instance.db_type.lower() if instance.db_type else 'mysql'
        
        # 确定目标数据库
        database = self._get_target_database(approval)
        
        # 获取SQL内容
        sql_content = await self._get_sql_content(approval)
        if not sql_content:
            return True, "执行完成: 无有效SQL语句", 0
        
        # 根据数据库类型执行
        if db_type == 'postgresql':
            return await self._execute_postgresql(instance, password, database, sql_content)
        else:
            return await self._execute_mysql(instance, password, database, sql_content)
    
    def _get_target_database(self, approval: ApprovalRecord) -> Optional[str]:
        """确定目标数据库"""
        if approval.database_mode == 'single':
            return approval.database_name
        elif approval.database_mode == 'multiple' and approval.database_list:
            return approval.database_list[0]
        return None
    
    async def _get_sql_content(self, approval: ApprovalRecord) -> str:
        """获取SQL内容"""
        sql_content = approval.sql_content or ""
        
        # 处理大文件SQL
        if approval.sql_file_path:
            try:
                file_content = storage_manager.backend.read(approval.sql_file_path)
                if file_content:
                    sql_content = file_content if isinstance(file_content, str) else file_content.decode('utf-8')
            except Exception as e:
                logger.error(f"读取SQL文件失败: {e}")
                raise Exception(f"读取SQL文件失败: {str(e)}")
        
        return sql_content
    
    async def _execute_mysql(
        self,
        instance: RDBInstance,
        password: str,
        database: Optional[str],
        sql_content: str
    ) -> tuple[bool, str, int]:
        """执行MySQL SQL"""
        conn = None
        try:
            conn = pymysql.connect(
                host=instance.host,
                port=instance.port,
                user=instance.username,
                password=password,
                database=database,
                connect_timeout=10,
                charset='utf8mb4'
            )
            return await self._execute_sql_statements(conn, sql_content, 'mysql')
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            return False, f"数据库连接失败: {str(e)}", 0
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
    
    async def _execute_postgresql(
        self,
        instance: RDBInstance,
        password: str,
        database: Optional[str],
        sql_content: str
    ) -> tuple[bool, str, int]:
        """执行PostgreSQL SQL"""
        conn = None
        try:
            conn = psycopg2.connect(
                host=instance.host,
                port=instance.port,
                user=instance.username,
                password=password,
                database=database or 'postgres',
                connect_timeout=10
            )
            # PostgreSQL默认自动提交关闭，需要设置
            conn.autocommit = False
            return await self._execute_sql_statements(conn, sql_content, 'postgresql')
        except Exception as e:
            logger.error(f"PostgreSQL连接失败: {e}")
            return False, f"数据库连接失败: {str(e)}", 0
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
    
    async def _execute_sql_statements(
        self,
        conn,
        sql_content: str,
        db_type: str
    ) -> tuple[bool, str, int]:
        """
        执行SQL语句
        
        Args:
            conn: 数据库连接
            sql_content: SQL内容
            db_type: 数据库类型
            
        Returns:
            Tuple[bool, str, int]: (是否全部成功, 结果消息, 影响行数)
        """
        cursor = conn.cursor()
        total_affected = 0
        results = []
        
        # 分割SQL语句
        sql_statements = [s.strip() for s in sql_content.split(';') if s.strip()]
        
        for i, sql in enumerate(sql_statements):
            if not sql:
                continue
            
            try:
                cursor.execute(sql)
                
                # 判断是否为查询语句
                sql_upper = sql.upper().strip()
                if self._is_query_statement(sql_upper):
                    # 查询语句，获取行数
                    rows = cursor.fetchall()
                    affected = len(rows)
                else:
                    # 修改语句
                    affected = cursor.rowcount if cursor.rowcount >= 0 else 0
                    conn.commit()
                
                total_affected += affected
                results.append(f"语句{i+1}: 成功, 影响{affected}行")
                logger.info(f"SQL执行成功: 语句{i+1}, 影响{affected}行")
                
            except Exception as e:
                conn.rollback()
                results.append(f"语句{i+1}: 失败 - {str(e)}")
                logger.error(f"SQL执行失败: 语句{i+1}, 错误: {e}")
        
        cursor.close()
        
        # 构建结果消息
        return self._build_result_message(results, total_affected)
    
    def _is_query_statement(self, sql_upper: str) -> bool:
        """判断是否为查询语句"""
        return sql_upper.startswith(self.QUERY_PREFIXES)
    
    def _build_result_message(self, results: list, total_affected: int) -> tuple[bool, str, int]:
        """构建结果消息"""
        if not results:
            return True, "执行完成: 无有效SQL语句", 0
        
        success_count = sum(1 for r in results if '成功' in r)
        fail_count = len(results) - success_count
        result_msg = f"执行完成: 成功{success_count}条, 失败{fail_count}条, 共影响{total_affected}行"
        
        # 有失败则返回False
        return fail_count == 0, result_msg, total_affected
    
    def check_execution_success(self, execute_result: str) -> bool:
        """
        检查执行结果是否成功
        
        Args:
            execute_result: 执行结果消息
            
        Returns:
            bool: 是否成功（失败条数为0）
        """
        fail_match = re.search(r'失败(\d+)条', execute_result)
        fail_count = int(fail_match.group(1)) if fail_match else 0
        return fail_count == 0


class RedisExecutor:
    """Redis命令执行器"""
    
    async def execute_for_approval(self, approval: ApprovalRecord, instance: RDBInstance) -> str:
        """
        执行审批工单中的Redis命令
        
        Args:
            approval: 审批记录
            instance: Redis实例
            
        Returns:
            str: 执行结果消息
        """
        # 解密密码
        try:
            password = decrypt_instance_password(instance.password_encrypted)
        except ValueError as e:
            return f"密码解密失败: {str(e)}"
        
        # 获取Redis命令内容
        commands_content = approval.sql_content or ""
        
        # 建立Redis连接
        redis_client = None
        try:
            redis_client = redis.Redis(
                host=instance.host,
                port=instance.port,
                password=password if password else None,
                db=instance.redis_db or 0,
                decode_responses=True,
                socket_timeout=10,
                socket_connect_timeout=10
            )
            
            # 测试连接
            redis_client.ping()
            
            # 分割命令
            commands = [cmd.strip() for cmd in commands_content.split('\n') if cmd.strip()]
            
            results = []
            for i, cmd_line in enumerate(commands):
                if not cmd_line or cmd_line.startswith('#'):
                    continue
                
                try:
                    # 解析Redis命令
                    parts = cmd_line.split()
                    if not parts:
                        continue
                    
                    cmd = parts[0].upper()
                    args = parts[1:]
                    
                    # 执行命令
                    result = self._execute_redis_command(redis_client, cmd, args)
                    results.append(f"命令{i+1}: 成功 - {result}")
                    logger.info(f"Redis命令执行成功: {cmd}")
                    
                except Exception as e:
                    results.append(f"命令{i+1}: 失败 - {str(e)}")
                    logger.error(f"Redis命令执行失败: {cmd_line}, 错误: {e}")
            
            # 构建结果消息
            success_count = sum(1 for r in results if '成功' in r)
            fail_count = len(results) - success_count
            return f"执行完成: 成功{success_count}条, 失败{fail_count}条"
            
        except redis.ConnectionError as e:
            logger.error(f"Redis连接失败: {e}")
            return f"Redis连接失败: {str(e)}"
        except Exception as e:
            logger.error(f"Redis执行异常: {e}")
            return f"执行失败: {str(e)}"
        finally:
            if redis_client:
                try:
                    redis_client.close()
                except Exception:
                    pass
    
    def _execute_redis_command(self, redis_client: redis.Redis, cmd: str, args: list):
        """执行单个Redis命令"""
        # 常用命令映射
        if cmd == 'GET':
            return redis_client.get(args[0]) if args else None
        elif cmd == 'SET':
            return redis_client.set(args[0], args[1]) if len(args) >= 2 else None
        elif cmd == 'DEL':
            return redis_client.delete(*args)
        elif cmd == 'EXPIRE':
            return redis_client.expire(args[0], int(args[1])) if len(args) >= 2 else None
        elif cmd == 'TTL':
            return redis_client.ttl(args[0]) if args else None
        elif cmd == 'KEYS':
            return redis_client.keys(args[0]) if args else redis_client.keys('*')
        elif cmd == 'HGET':
            return redis_client.hget(args[0], args[1]) if len(args) >= 2 else None
        elif cmd == 'HSET':
            return redis_client.hset(args[0], args[1], args[2]) if len(args) >= 3 else None
        elif cmd == 'HGETALL':
            return redis_client.hgetall(args[0]) if args else None
        elif cmd == 'LPUSH':
            return redis_client.lpush(args[0], *args[1:]) if args else None
        elif cmd == 'RPOP':
            return redis_client.rpop(args[0]) if args else None
        elif cmd == 'LRANGE':
            return redis_client.lrange(args[0], int(args[1]), int(args[2])) if len(args) >= 3 else None
        elif cmd == 'SADD':
            return redis_client.sadd(args[0], *args[1:]) if args else None
        elif cmd == 'SMEMBERS':
            return redis_client.smembers(args[0]) if args else None
        elif cmd == 'ZADD':
            return redis_client.zadd(args[0], {args[1]: float(args[2])}) if len(args) >= 3 else None
        elif cmd == 'ZRANGE':
            return redis_client.zrange(args[0], int(args[1]), int(args[2])) if len(args) >= 3 else None
        elif cmd == 'PING':
            return redis_client.ping()
        elif cmd == 'INFO':
            return redis_client.info(args[0] if args else None)
        elif cmd == 'DBSIZE':
            return redis_client.dbsize()
        elif cmd == 'FLUSHDB':
            # 危险命令，需要确认
            return redis_client.flushdb()
        elif cmd == 'FLUSHALL':
            # 危险命令，需要确认
            return redis_client.flushall()
        else:
            # 尝试通用执行
            return redis_client.execute_command(cmd, *args)


# 单例实例
sql_executor = SQLExecutor()
redis_executor = RedisExecutor()
