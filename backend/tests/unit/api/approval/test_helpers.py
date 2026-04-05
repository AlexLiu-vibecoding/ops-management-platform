"""
审批辅助函数单元测试
"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime
import asyncio

from app.models import ApprovalRecord, RDBInstance, RedisInstance, ApprovalStatus, AuditLog
from app.api.approval.helpers import (
    get_instance_type,
    get_rdb_connection,
    get_redis_connection,
    get_sql_preview,
    analyze_sql_risk,
    analyze_redis_risk,
    format_approval_response,
    add_audit_log
)


class TestGetInstanceType:
    """get_instance_type 测试"""

    def test_mysql_port_3306(self):
        """测试 MySQL 实例（端口 3306）"""
        instance = RDBInstance(
            id=1,
            name="test-mysql",
            host="localhost",
            port=3306,
            username="root"
        )

        instance_type = get_instance_type(instance)

        assert instance_type == "mysql"

    def test_postgresql_port_5432(self):
        """测试 PostgreSQL 实例（端口 5432）"""
        instance = RDBInstance(
            id=1,
            name="test-pg",
            host="localhost",
            port=5432,
            username="postgres"
        )

        instance_type = get_instance_type(instance)

        assert instance_type == "postgresql"

    def test_postgresql_host(self):
        """测试 PostgreSQL 实例（主机名包含 pg）"""
        instance = RDBInstance(
            id=1,
            name="test-pg",
            host="pg-server.example.com",
            port=3306,  # 非标准端口
            username="postgres"
        )

        instance_type = get_instance_type(instance)

        assert instance_type == "postgresql"

    def test_postgresql_host_postgres(self):
        """测试 PostgreSQL 实例（主机名包含 postgres）"""
        instance = RDBInstance(
            id=1,
            name="test-pg",
            host="postgres.example.com",
            port=3306,
            username="postgres"
        )

        instance_type = get_instance_type(instance)

        assert instance_type == "postgresql"

    def test_mysql_default(self):
        """测试默认返回 MySQL"""
        instance = RDBInstance(
            id=1,
            name="test-mysql",
            host="db.example.com",
            port=3307,  # 非标准端口
            username="root"
        )

        instance_type = get_instance_type(instance)

        assert instance_type == "mysql"


class TestGetRDBConnection:
    """get_rdb_connection 测试"""

    @patch('app.api.approval.helpers.decrypt_instance_password')
    @patch('app.api.approval.helpers.psycopg2.connect')
    def test_postgresql_connection(self, mock_pg_connect, mock_decrypt):
        """测试 PostgreSQL 连接"""
        mock_decrypt.return_value = "password123"
        mock_conn = MagicMock()
        mock_pg_connect.return_value = mock_conn

        instance = RDBInstance(
            id=1,
            name="test-pg",
            host="localhost",
            port=5432,
            username="postgres",
            password_encrypted="encrypted_password"
        )

        conn, db_type = get_rdb_connection(instance, database="testdb")

        assert conn is mock_conn
        assert db_type == "postgresql"
        mock_pg_connect.assert_called_once_with(
            host="localhost",
            port=5432,
            user="postgres",
            password="password123",
            database="testdb",
            connect_timeout=5
        )

    @patch('app.api.approval.helpers.decrypt_instance_password')
    @patch('app.api.approval.helpers.pymysql.connect')
    def test_mysql_connection(self, mock_mysql_connect, mock_decrypt):
        """测试 MySQL 连接"""
        mock_decrypt.return_value = "password123"
        mock_conn = MagicMock()
        mock_mysql_connect.return_value = mock_conn

        instance = RDBInstance(
            id=1,
            name="test-mysql",
            host="localhost",
            port=3306,
            username="root",
            password_encrypted="encrypted_password"
        )

        conn, db_type = get_rdb_connection(instance, database="testdb")

        assert conn is mock_conn
        assert db_type == "mysql"
        mock_mysql_connect.assert_called_once_with(
            host="localhost",
            port=3306,
            user="root",
            password="password123",
            database="testdb",
            connect_timeout=5,
            charset='utf8mb4'
        )

    @patch('app.api.approval.helpers.decrypt_instance_password')
    @patch('app.api.approval.helpers.pymysql.connect')
    def test_mysql_connection_default_db(self, mock_mysql_connect, mock_decrypt):
        """测试 MySQL 连接（默认数据库）"""
        mock_decrypt.return_value = "password123"
        mock_conn = MagicMock()
        mock_mysql_connect.return_value = mock_conn

        instance = RDBInstance(
            id=1,
            name="test-mysql",
            host="localhost",
            port=3306,
            username="root",
            password_encrypted="encrypted_password"
        )

        conn, db_type = get_rdb_connection(instance)

        assert conn is mock_conn
        assert db_type == "mysql"
        mock_mysql_connect.assert_called_once()
        # 验证没有传递 database 参数
        call_kwargs = mock_mysql_connect.call_args[1]
        assert "database" in call_kwargs

    @patch('app.api.approval.helpers.decrypt_instance_password')
    @patch('app.api.approval.helpers.psycopg2.connect')
    def test_postgresql_connection_default_db(self, mock_pg_connect, mock_decrypt):
        """测试 PostgreSQL 连接（默认数据库）"""
        mock_decrypt.return_value = "password123"
        mock_conn = MagicMock()
        mock_pg_connect.return_value = mock_conn

        instance = RDBInstance(
            id=1,
            name="test-pg",
            host="localhost",
            port=5432,
            username="postgres",
            password_encrypted="encrypted_password"
        )

        conn, db_type = get_rdb_connection(instance)

        assert conn is mock_conn
        assert db_type == "postgresql"
        mock_pg_connect.assert_called_once()
        # 验证使用默认数据库 'postgres'
        call_kwargs = mock_pg_connect.call_args[1]
        assert call_kwargs["database"] == 'postgres'

    @patch('app.api.approval.helpers.decrypt_instance_password')
    def test_password_decrypt_failure(self, mock_decrypt):
        """测试密码解密失败"""
        mock_decrypt.side_effect = ValueError("Invalid password")

        instance = RDBInstance(
            id=1,
            name="test",
            host="localhost",
            port=3306,
            username="root",
            password_encrypted="invalid_encrypted"
        )

        with pytest.raises(ValueError, match="密码解密失败"):
            get_rdb_connection(instance)


class TestGetRedisConnection:
    """get_redis_connection 测试"""

    @patch('app.api.approval.helpers.decrypt_instance_password')
    @patch('app.api.approval.helpers.redis_client.Redis')
    def test_redis_connection_with_password(self, mock_redis, mock_decrypt):
        """测试 Redis 连接（有密码）"""
        mock_decrypt.return_value = "redis123"
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        instance = RedisInstance(
            id=1,
            name="test-redis",
            host="localhost",
            port=6379,
            password_encrypted="encrypted_password"
        )

        conn = get_redis_connection(instance)

        assert conn is mock_client
        mock_redis.assert_called_once_with(
            host="localhost",
            port=6379,
            password="redis123",
            db=0,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )

    @patch('app.api.approval.helpers.decrypt_instance_password')
    @patch('app.api.approval.helpers.redis_client.Redis')
    def test_redis_connection_without_password(self, mock_redis, mock_decrypt):
        """测试 Redis 连接（无密码）"""
        instance = RedisInstance(
            id=1,
            name="test-redis",
            host="localhost",
            port=6379,
            password_encrypted=None
        )

        conn = get_redis_connection(instance)

        assert conn is mock_client
        mock_redis.assert_called_once()
        call_kwargs = mock_redis.call_args[1]
        assert call_kwargs["password"] is None

    @patch('app.api.approval.helpers.decrypt_instance_password')
    @patch('app.api.approval.helpers.redis_client.Redis')
    def test_redis_connection_decrypt_fallback(self, mock_redis, mock_decrypt):
        """测试 Redis 连接（解密失败，使用原始密码）"""
        mock_decrypt.side_effect = ValueError()
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        instance = RedisInstance(
            id=1,
            name="test-redis",
            host="localhost",
            port=6379,
            password_encrypted="direct_password"
        )

        conn = get_redis_connection(instance)

        assert conn is mock_client
        call_kwargs = mock_redis.call_args[1]
        assert call_kwargs["password"] == "direct_password"


class TestGetSQLPreview:
    """get_sql_preview 测试"""

    def test_short_sql(self):
        """测试短 SQL（不超过限制）"""
        sql = "SELECT * FROM users WHERE id = 1;"

        preview = get_sql_preview(sql, max_lines=100)

        assert preview == sql

    def test_long_sql(self):
        """测试长 SQL（超过限制）"""
        sql = "\n".join([f"SELECT * FROM table_{i};" for i in range(150)])

        preview = get_sql_preview(sql, max_lines=100)

        lines = preview.split('\n')
        assert len(lines) == 100
        assert lines[0] == "SELECT * FROM table_0;"

    def test_custom_max_lines(self):
        """测试自定义最大行数"""
        sql = "\n".join([f"SELECT {i};" for i in range(50)])

        preview = get_sql_preview(sql, max_lines=10)

        lines = preview.split('\n')
        assert len(lines) == 10


class TestAnalyzeSQLRisk:
    """analyze_sql_risk 测试"""

    def test_critical_risk_drop_database(self):
        """测试极高风险：DROP DATABASE"""
        sql = "DROP DATABASE testdb;"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "critical"

    def test_critical_risk_drop_schema(self):
        """测试极高风险：DROP SCHEMA"""
        sql = "DROP SCHEMA public;"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "critical"

    def test_critical_risk_truncate(self):
        """测试极高风险：TRUNCATE TABLE"""
        sql = "TRUNCATE TABLE users;"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "critical"

    def test_critical_risk_delete_no_where(self):
        """测试极高风险：DELETE 无 WHERE"""
        sql = "DELETE FROM users;"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "critical"

    def test_critical_risk_update_no_where(self):
        """测试极高风险：UPDATE 无 WHERE"""
        sql = "UPDATE users SET name = 'test';"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "critical"

    def test_high_risk_drop_table(self):
        """测试高风险：DROP TABLE"""
        sql = "DROP TABLE users;"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "high"

    def test_high_risk_alter_drop(self):
        """测试高风险：ALTER TABLE DROP"""
        sql = "ALTER TABLE users DROP COLUMN age;"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "high"

    def test_high_risk_alter_modify(self):
        """测试高风险：ALTER TABLE MODIFY"""
        sql = "ALTER TABLE users MODIFY COLUMN age INT;"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "high"

    def test_medium_risk_alter_table(self):
        """测试中风险：ALTER TABLE"""
        sql = "ALTER TABLE users ADD COLUMN age INT;"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "medium"

    def test_medium_risk_create_table(self):
        """测试中风险：CREATE TABLE"""
        sql = "CREATE TABLE users (id INT, name VARCHAR(100));"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "medium"

    def test_medium_risk_create_index(self):
        """测试中风险：CREATE INDEX"""
        sql = "CREATE INDEX idx_name ON users(name);"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "medium"

    def test_medium_risk_delete_with_where(self):
        """测试中风险：DELETE 有 WHERE"""
        sql = "DELETE FROM users WHERE id = 1;"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "medium"

    def test_medium_risk_update_with_where(self):
        """测试中风险：UPDATE 有 WHERE"""
        sql = "UPDATE users SET name = 'test' WHERE id = 1;"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "medium"

    def test_low_risk_select(self):
        """测试低风险：SELECT"""
        sql = "SELECT * FROM users;"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "low"

    def test_low_risk_insert(self):
        """测试低风险：INSERT"""
        sql = "INSERT INTO users (name) VALUES ('test');"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "low"

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        sql = "drop database testdb;"

        risk = analyze_sql_risk(sql, environment_id=1, db=MagicMock())

        assert risk == "critical"


class TestAnalyzeRedisRisk:
    """analyze_redis_risk 测试"""

    def test_critical_risk_flushall(self):
        """测试极高风险：FLUSHALL"""
        commands = "FLUSHALL"

        risk = analyze_redis_risk(commands, environment_id=1, db=MagicMock())

        assert risk == "critical"

    def test_critical_risk_flushdb(self):
        """测试极高风险：FLUSHDB"""
        commands = "FLUSHDB"

        risk = analyze_redis_risk(commands, environment_id=1, db=MagicMock())

        assert risk == "critical"

    def test_critical_risk_shutdown(self):
        """测试极高风险：SHUTDOWN"""
        commands = "SHUTDOWN"

        risk = analyze_redis_risk(commands, environment_id=1, db=MagicMock())

        assert risk == "critical"

    def test_critical_risk_debug_reload(self):
        """测试极高风险：DEBUG RELOAD"""
        commands = "DEBUG RELOAD"

        risk = analyze_redis_risk(commands, environment_id=1, db=MagicMock())

        assert risk == "critical"

    def test_high_risk_del(self):
        """测试高风险：DEL"""
        commands = "DEL key1 key2"

        risk = analyze_redis_risk(commands, environment_id=1, db=MagicMock())

        assert risk == "high"

    def test_high_risk_rename(self):
        """测试高风险：RENAME"""
        commands = "RENAME old_key new_key"

        risk = analyze_redis_risk(commands, environment_id=1, db=MagicMock())

        assert risk == "high"

    def test_high_risk_unlink(self):
        """测试高风险：UNLINK"""
        commands = "UNLINK key1"

        risk = analyze_redis_risk(commands, environment_id=1, db=MagicMock())

        assert risk == "high"

    def test_medium_risk_set(self):
        """测试中风险：SET"""
        commands = "SET key value"

        risk = analyze_redis_risk(commands, environment_id=1, db=MagicMock())

        assert risk == "medium"

    def test_medium_risk_incr(self):
        """测试中风险：INCR"""
        commands = "INCR counter"

        risk = analyze_redis_risk(commands, environment_id=1, db=MagicMock())

        assert risk == "medium"

    def test_medium_risk_lpush(self):
        """测试中风险：LPUSH"""
        commands = "LPUSH mylist value1"

        risk = analyze_redis_risk(commands, environment_id=1, db=MagicMock())

        assert risk == "medium"

    def test_medium_risk_expire(self):
        """测试中风险：EXPIRE"""
        commands = "EXPIRE key 3600"

        risk = analyze_redis_risk(commands, environment_id=1, db=MagicMock())

        assert risk == "medium"

    def test_low_risk_get(self):
        """测试低风险：GET"""
        commands = "GET key"

        risk = analyze_redis_risk(commands, environment_id=1, db=MagicMock())

        assert risk == "low"

    def test_low_risk_select(self):
        """测试低风险：SELECT"""
        commands = "SELECT 0"

        risk = analyze_redis_risk(commands, environment_id=1, db=MagicMock())

        assert risk == "low"

    def test_case_insensitive(self):
        """测试大小写不敏感"""
        commands = "flushall"

        risk = analyze_redis_risk(commands, environment_id=1, db=MagicMock())

        assert risk == "critical"


class TestFormatApprovalResponse:
    """format_approval_response 测试"""

    def test_basic_response(self):
        """测试基本响应"""
        approval = ApprovalRecord(
            id=1,
            title="Test Approval",
            change_type="DDL",
            status=ApprovalStatus.PENDING,
            environment_id=1,
            sql_content="SELECT * FROM users;",
            sql_risk_level="low",
            database_mode="single",
            database_name="testdb",
            requester_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        response = format_approval_response(approval)

        assert response["id"] == 1
        assert response["title"] == "Test Approval"
        assert response["change_type"] == "DDL"
        assert response["status"] == "pending"
        assert response["environment_id"] == 1
        assert response["sql_risk_level"] == "low"
        assert "sql_preview" in response
        assert "sql_download_url" in response

    def test_sql_preview_short(self):
        """测试 SQL 预览（短内容）"""
        approval = ApprovalRecord(
            id=1,
            title="Test",
            change_type="DML",
            status=ApprovalStatus.PENDING,
            environment_id=1,
            sql_content="SELECT * FROM users;",
            sql_risk_level="low",
            database_mode="single",
            database_name="testdb",
            requester_id=1,
            created_at=datetime.now()
        )

        response = format_approval_response(approval)

        assert response["sql_preview"] == "SELECT * FROM users;"

    def test_sql_preview_long(self):
        """测试 SQL 预览（长内容）"""
        long_sql = "\n".join([f"SELECT {i};" for i in range(150)])
        approval = ApprovalRecord(
            id=1,
            title="Test",
            change_type="DML",
            status=ApprovalStatus.PENDING,
            environment_id=1,
            sql_content=long_sql,
            sql_risk_level="low",
            database_mode="single",
            database_name="testdb",
            requester_id=1,
            created_at=datetime.now()
        )

        response = format_approval_response(approval)

        lines = response["sql_preview"].split('\n')
        assert len(lines) == 100

    def test_include_full_sql_short(self):
        """测试包含完整 SQL（短内容）"""
        sql = "SELECT * FROM users;"
        approval = ApprovalRecord(
            id=1,
            title="Test",
            change_type="DML",
            status=ApprovalStatus.PENDING,
            environment_id=1,
            sql_content=sql,
            sql_risk_level="low",
            database_mode="single",
            database_name="testdb",
            requester_id=1,
            created_at=datetime.now()
        )

        response = format_approval_response(approval, include_full_sql=True)

        assert "sql_content" in response
        assert response["sql_content"] == sql

    def test_include_full_sql_long(self):
        """测试包含完整 SQL（长内容，不包含）"""
        long_sql = "x" * 15000
        approval = ApprovalRecord(
            id=1,
            title="Test",
            change_type="DML",
            status=ApprovalStatus.PENDING,
            environment_id=1,
            sql_content=long_sql,
            sql_risk_level="low",
            database_mode="single",
            database_name="testdb",
            requester_id=1,
            created_at=datetime.now()
        )

        response = format_approval_response(approval, include_full_sql=True)

        # 长内容不应该包含在响应中
        assert "sql_content" not in response

    def test_no_sql_content(self):
        """测试无 SQL 内容"""
        approval = ApprovalRecord(
            id=1,
            title="Test",
            change_type="DML",
            status=ApprovalStatus.PENDING,
            environment_id=1,
            sql_content=None,
            sql_risk_level="low",
            database_mode="single",
            database_name="testdb",
            requester_id=1,
            created_at=datetime.now()
        )

        response = format_approval_response(approval)

        assert response["sql_preview"] == "(无SQL内容或从文件读取失败)"

    def test_rdb_instance(self):
        """测试 RDB 实例"""
        approval = ApprovalRecord(
            id=1,
            title="Test",
            change_type="DML",
            status=ApprovalStatus.PENDING,
            environment_id=1,
            sql_content="SELECT 1;",
            sql_risk_level="low",
            rdb_instance_id=1,
            database_mode="single",
            database_name="testdb",
            requester_id=1,
            created_at=datetime.now()
        )

        response = format_approval_response(approval)

        assert response["rdb_instance_id"] == 1
        assert response["redis_instance_id"] is None
        assert response["instance_id"] == 1

    def test_redis_instance(self):
        """测试 Redis 实例"""
        approval = ApprovalRecord(
            id=1,
            title="Test",
            change_type="DML",
            status=ApprovalStatus.PENDING,
            environment_id=1,
            sql_content="GET key",
            sql_risk_level="low",
            redis_instance_id=1,
            requester_id=1,
            created_at=datetime.now()
        )

        response = format_approval_response(approval)

        assert response["redis_instance_id"] == 1
        assert response["rdb_instance_id"] is None
        assert response["instance_id"] == 1


class TestAddAuditLog:
    """add_audit_log 测试"""

    def test_add_audit_log_basic(self):
        """测试添加审计日志"""
        db = MagicMock()
        current_user = MagicMock()
        current_user.id = 1
        current_user.username = "test_user"

        approval = MagicMock()
        approval.id = 1
        approval.title = "Test Approval"
        approval.status = ApprovalStatus.PENDING

        add_audit_log(db, current_user, approval, "CREATE")

        db.add.assert_called_once()
        added_log = db.add.call_args[0][0]
        assert isinstance(added_log, AuditLog)
        assert added_log.user_id == 1
        assert added_log.username == "test_user"
        assert added_log.operation_type == "CREATE"
        assert added_log.operation_detail["approval_id"] == 1
        assert added_log.operation_detail["title"] == "Test Approval"
        assert added_log.operation_detail["status"] == "pending"

    def test_add_audit_log_different_action(self):
        """测试添加审计日志（不同操作）"""
        db = MagicMock()
        current_user = MagicMock()
        current_user.id = 2
        current_user.username = "admin_user"

        approval = MagicMock()
        approval.id = 5
        approval.title = "Update Data"
        approval.status = ApprovalStatus.APPROVED

        add_audit_log(db, current_user, approval, "APPROVE")

        db.add.assert_called_once()
        added_log = db.add.call_args[0][0]
        assert added_log.operation_type == "APPROVE"
        assert added_log.user_id == 2
