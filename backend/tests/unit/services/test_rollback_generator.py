"""
回滚SQL生成器测试
"""
import pytest
from app.services.rollback_generator import (
    RollbackGenerator,
    RollbackResult,
    SQLType,
    rollback_generator
)


class TestSQLType:
    """测试SQL类型枚举"""
    
    def test_sql_type_values(self):
        """测试SQL类型枚举值"""
        assert SQLType.CREATE_TABLE.value == "CREATE_TABLE"
        assert SQLType.ALTER_TABLE.value == "ALTER_TABLE"
        assert SQLType.DROP_TABLE.value == "DROP_TABLE"
        assert SQLType.CREATE_INDEX.value == "CREATE_INDEX"
        assert SQLType.DROP_INDEX.value == "DROP_INDEX"
        assert SQLType.TRUNCATE_TABLE.value == "TRUNCATE_TABLE"
        assert SQLType.INSERT.value == "INSERT"
        assert SQLType.UPDATE.value == "UPDATE"
        assert SQLType.DELETE.value == "DELETE"
        assert SQLType.UNKNOWN.value == "UNKNOWN"


class TestRollbackResult:
    """测试回滚结果"""
    
    def test_success_result(self):
        """测试成功结果"""
        result = RollbackResult(
            success=True,
            sql_type=SQLType.CREATE_TABLE,
            rollback_sql="DROP TABLE test;",
            affected_table="test"
        )
        
        assert result.success is True
        assert result.sql_type == SQLType.CREATE_TABLE
        assert result.rollback_sql == "DROP TABLE test;"
        assert result.affected_table == "test"
    
    def test_failed_result(self):
        """测试失败结果"""
        result = RollbackResult(
            success=False,
            sql_type=SQLType.DROP_TABLE,
            warning="无法生成回滚SQL",
            requires_data_backup=True
        )
        
        assert result.success is False
        assert result.warning == "无法生成回滚SQL"
        assert result.requires_data_backup is True


class TestRollbackGeneratorPatterns:
    """测试SQL模式匹配"""
    
    def test_create_table_pattern(self):
        """测试CREATE TABLE模式"""
        gen = RollbackGenerator()
        results = gen.analyze_sql("CREATE TABLE test (id INT);")
        
        assert len(results) > 0
        sql_type, table, _ = results[0]
        assert sql_type == SQLType.CREATE_TABLE
        assert table == "test"
    
    def test_alter_table_pattern(self):
        """测试ALTER TABLE模式"""
        gen = RollbackGenerator()
        results = gen.analyze_sql("ALTER TABLE test ADD COLUMN name VARCHAR(100);")
        
        assert len(results) > 0
        sql_type, table, _ = results[0]
        assert sql_type == SQLType.ALTER_TABLE
        assert table == "test"
    
    def test_drop_table_pattern(self):
        """测试DROP TABLE模式"""
        gen = RollbackGenerator()
        results = gen.analyze_sql("DROP TABLE test;")
        
        assert len(results) > 0
        sql_type, table, _ = results[0]
        assert sql_type == SQLType.DROP_TABLE
        assert table == "test"
    
    def test_create_index_pattern(self):
        """测试CREATE INDEX模式"""
        gen = RollbackGenerator()
        results = gen.analyze_sql("CREATE INDEX idx_name ON test(col1);")
        
        assert len(results) > 0
        sql_type, table, _ = results[0]
        assert sql_type == SQLType.CREATE_INDEX
        # 注意：正则捕获的是索引名
        assert table == "idx_name"
    
    def test_drop_index_pattern(self):
        """测试DROP INDEX模式"""
        gen = RollbackGenerator()
        results = gen.analyze_sql("DROP INDEX idx_name ON test;")
        
        assert len(results) > 0
        sql_type, table, _ = results[0]
        assert sql_type == SQLType.DROP_INDEX
        # 注意：正则捕获的是索引名
        assert table == "idx_name"
    
    def test_truncate_pattern(self):
        """测试TRUNCATE模式"""
        gen = RollbackGenerator()
        results = gen.analyze_sql("TRUNCATE TABLE test;")
        
        assert len(results) > 0
        sql_type, table, _ = results[0]
        assert sql_type == SQLType.TRUNCATE_TABLE
        assert table == "test"
    
    def test_insert_pattern(self):
        """测试INSERT模式"""
        gen = RollbackGenerator()
        results = gen.analyze_sql("INSERT INTO test (id, name) VALUES (1, 'test');")
        
        assert len(results) > 0
        sql_type, table, _ = results[0]
        assert sql_type == SQLType.INSERT
        assert table == "test"
    
    def test_update_pattern(self):
        """测试UPDATE模式"""
        gen = RollbackGenerator()
        results = gen.analyze_sql("UPDATE test SET name = 'new' WHERE id = 1;")
        
        assert len(results) > 0
        sql_type, table, _ = results[0]
        assert sql_type == SQLType.UPDATE
        assert table == "test"
    
    def test_delete_pattern(self):
        """测试DELETE模式"""
        gen = RollbackGenerator()
        results = gen.analyze_sql("DELETE FROM test WHERE id = 1;")
        
        assert len(results) > 0
        sql_type, table, _ = results[0]
        assert sql_type == SQLType.DELETE
        assert table == "test"
    
    def test_backtick_table_name(self):
        """测试反引号表名"""
        gen = RollbackGenerator()
        results = gen.analyze_sql("CREATE TABLE `test` (id INT);")
        
        assert len(results) > 0
        sql_type, table, _ = results[0]
        assert sql_type == SQLType.CREATE_TABLE
        assert table == "test"
    
    def test_quoted_table_name(self):
        """测试双引号表名"""
        gen = RollbackGenerator()
        results = gen.analyze_sql('CREATE TABLE "test" (id INT);')
        
        assert len(results) > 0
        sql_type, table, _ = results[0]
        assert sql_type == SQLType.CREATE_TABLE
        assert table == "test"


class TestAnalyzeSQL:
    """测试SQL分析"""
    
    def test_empty_sql(self):
        """测试空SQL"""
        gen = RollbackGenerator()
        results = gen.analyze_sql("")
        
        assert len(results) == 0
    
    def test_whitespace_sql(self):
        """测试空白SQL"""
        gen = RollbackGenerator()
        results = gen.analyze_sql("   \n\t  ")
        
        assert len(results) == 0
    
    def test_unknown_sql(self):
        """测试未知SQL"""
        gen = RollbackGenerator()
        results = gen.analyze_sql("SHOW TABLES;")
        
        assert len(results) == 1
        sql_type, table, _ = results[0]
        assert sql_type == SQLType.UNKNOWN
    
    def test_multiple_statements(self):
        """测试多条SQL"""
        gen = RollbackGenerator()
        results = gen.analyze_sql("CREATE TABLE t1(id INT); CREATE TABLE t2(id INT);")
        
        assert len(results) == 2
        assert results[0][0] == SQLType.CREATE_TABLE
        assert results[1][0] == SQLType.CREATE_TABLE


class TestGenerateRollbackSQL:
    """测试生成回滚SQL"""
    
    def test_generate_create_table_rollback(self):
        """测试CREATE TABLE回滚"""
        gen = RollbackGenerator()
        results = gen.generate_rollback_sql("CREATE TABLE test (id INT);")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.sql_type == SQLType.CREATE_TABLE
        assert "DROP TABLE" in result.rollback_sql
        assert result.warning is not None
    
    def test_generate_drop_table_rollback(self):
        """测试DROP TABLE回滚"""
        gen = RollbackGenerator()
        results = gen.generate_rollback_sql("DROP TABLE test;")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.sql_type == SQLType.DROP_TABLE
        assert result.requires_data_backup is True
    
    def test_generate_insert_rollback(self):
        """测试INSERT回滚"""
        gen = RollbackGenerator()
        results = gen.generate_rollback_sql("INSERT INTO test (id) VALUES (1);")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.sql_type == SQLType.INSERT
        assert "DELETE FROM" in result.rollback_sql
    
    def test_generate_update_rollback(self):
        """测试UPDATE回滚"""
        gen = RollbackGenerator()
        results = gen.generate_rollback_sql("UPDATE test SET name = 'new' WHERE id = 1;")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.sql_type == SQLType.UPDATE
        assert result.requires_data_backup is True
    
    def test_generate_delete_rollback(self):
        """测试DELETE回滚"""
        gen = RollbackGenerator()
        results = gen.generate_rollback_sql("DELETE FROM test WHERE id = 1;")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.sql_type == SQLType.DELETE
        assert result.requires_data_backup is True
    
    def test_generate_create_index_rollback(self):
        """测试CREATE INDEX回滚"""
        gen = RollbackGenerator()
        results = gen.generate_rollback_sql("CREATE INDEX idx ON test(col);")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.sql_type == SQLType.CREATE_INDEX
        assert "DROP INDEX" in result.rollback_sql
    
    def test_generate_drop_index_rollback(self):
        """测试DROP INDEX回滚"""
        gen = RollbackGenerator()
        results = gen.generate_rollback_sql("DROP INDEX idx ON test;")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.sql_type == SQLType.DROP_INDEX
    
    def test_generate_truncate_rollback(self):
        """测试TRUNCATE回滚"""
        gen = RollbackGenerator()
        results = gen.generate_rollback_sql("TRUNCATE TABLE test;")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is False
        assert result.sql_type == SQLType.TRUNCATE_TABLE


class TestAlterTableRollback:
    """测试ALTER TABLE回滚"""
    
    def test_add_column_rollback(self):
        """测试ADD COLUMN回滚"""
        gen = RollbackGenerator()
        results = gen.generate_rollback_sql("ALTER TABLE test ADD COLUMN name VARCHAR(100);")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.sql_type == SQLType.ALTER_TABLE
        assert "DROP COLUMN" in result.rollback_sql
    
    def test_drop_column_rollback(self):
        """测试DROP COLUMN回滚"""
        gen = RollbackGenerator()
        results = gen.generate_rollback_sql("ALTER TABLE test DROP COLUMN name;")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert result.sql_type == SQLType.ALTER_TABLE
        assert "ADD COLUMN" in result.rollback_sql
    
    def test_add_index_rollback(self):
        """测试ADD INDEX回滚"""
        gen = RollbackGenerator()
        results = gen.generate_rollback_sql("ALTER TABLE test ADD INDEX idx(name);")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert "DROP INDEX" in result.rollback_sql
    
    def test_drop_index_rollback(self):
        """测试DROP INDEX回滚"""
        gen = RollbackGenerator()
        results = gen.generate_rollback_sql("ALTER TABLE test DROP INDEX idx;")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert "ADD INDEX" in result.rollback_sql
    
    def test_rename_column_rollback(self):
        """测试RENAME COLUMN回滚"""
        gen = RollbackGenerator()
        results = gen.generate_rollback_sql("ALTER TABLE test RENAME COLUMN old_name TO new_name;")
        
        assert len(results) == 1
        result = results[0]
        assert result.success is True
        assert "new_name" in result.rollback_sql
        assert "old_name" in result.rollback_sql


class TestDataBackup:
    """测试数据备份"""
    
    def test_backup_update(self):
        """测试UPDATE备份SQL"""
        gen = RollbackGenerator()
        sql = gen.generate_data_backup_sql(SQLType.UPDATE, "test", "id = 1")
        
        assert "SELECT" in sql
        assert "test" in sql
        assert "WHERE" in sql
    
    def test_backup_delete(self):
        """测试DELETE备份SQL"""
        gen = RollbackGenerator()
        sql = gen.generate_data_backup_sql(SQLType.DELETE, "test", "id = 1")
        
        assert "SELECT" in sql
        assert "test" in sql
    
    def test_backup_create_table(self):
        """测试CREATE TABLE不需要备份"""
        gen = RollbackGenerator()
        sql = gen.generate_data_backup_sql(SQLType.CREATE_TABLE, "test")
        
        assert sql == ""


class TestRedisRollback:
    """测试Redis回滚"""
    
    def test_redis_set_rollback(self):
        """测试SET回滚"""
        gen = RollbackGenerator()
        result = gen.generate_redis_rollback("SET key value")
        
        assert result.success is True
        assert result.sql_type == SQLType.UPDATE
        assert "GET" in result.rollback_sql
    
    def test_redis_del_rollback(self):
        """测试DEL回滚"""
        gen = RollbackGenerator()
        result = gen.generate_redis_rollback("DEL key1 key2")
        
        assert result.success is False
        assert result.requires_data_backup is True
    
    def test_redis_hset_rollback(self):
        """测试HSET回滚"""
        gen = RollbackGenerator()
        result = gen.generate_redis_rollback("HSET key field value")
        
        assert result.success is True
        assert "HDEL" in result.rollback_sql
    
    def test_redis_lpush_rollback(self):
        """测试LPUSH回滚"""
        gen = RollbackGenerator()
        result = gen.generate_redis_rollback("LPUSH key value")
        
        assert result.success is True
        assert "LPOP" in result.rollback_sql
    
    def test_redis_expire_rollback(self):
        """测试EXPIRE回滚"""
        gen = RollbackGenerator()
        result = gen.generate_redis_rollback("EXPIRE key 60")
        
        assert result.success is True
        assert "PERSIST" in result.rollback_sql
    
    def test_redis_rename_rollback(self):
        """测试RENAME回滚"""
        gen = RollbackGenerator()
        result = gen.generate_redis_rollback("RENAME old_key new_key")
        
        assert result.success is True
        assert "old_key" in result.rollback_sql
    
    def test_redis_unknown_command(self):
        """测试未知命令"""
        gen = RollbackGenerator()
        result = gen.generate_redis_rollback("UNKNOWN cmd")
        
        assert result.success is False
    
    def test_redis_empty_command(self):
        """测试空命令"""
        gen = RollbackGenerator()
        result = gen.generate_redis_rollback("")
        
        assert result.success is False


class TestGlobalInstance:
    """测试全局实例"""
    
    def test_global_instance_exists(self):
        """测试全局实例存在"""
        assert rollback_generator is not None
        assert isinstance(rollback_generator, RollbackGenerator)
    
    def test_global_instance_functionality(self):
        """测试全局实例功能"""
        results = rollback_generator.generate_rollback_sql("CREATE TABLE test (id INT);")
        assert len(results) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
