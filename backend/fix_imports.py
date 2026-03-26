#!/usr/bin/env python3
"""
批量修复 Instance 导入和使用的脚本
"""
import os
import re

# 需要修复的文件列表
files_to_fix = [
    'app/api/inspection.py',
    'app/api/monitor_ext.py', 
    'app/api/dashboard.py',
    'app/api/performance.py',
    'app/api/approval.py',
    'app/api/sql_optimizer.py',
    'app/api/sql.py',
    'app/api/redis.py',
    'app/api/slow_query.py',
    'app/api/alerts.py',
]

def fix_file(filepath):
    """修复单个文件"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    
    # 1. 修复导入语句
    # 匹配: from app.models import Instance
    if re.search(r'from app\.models import.*\bInstance\b', content):
        # 检查是否已经导入了 RDBInstance
        if 'RDBInstance' not in content:
            # 替换 Instance 为 RDBInstance, RedisInstance
            content = re.sub(
                r'from app\.models import \((.*)\bInstance\b(.*)\)',
                r'from app.models import (\1RDBInstance, RedisInstance\2)',
                content
            )
            content = re.sub(
                r'from app\.models import (.*)\bInstance\b(.*)(?=\n)',
                r'from app.models import \1RDBInstance, RedisInstance\2',
                content
            )
            # 清理可能的重复
            content = content.replace('RDBInstance, RedisInstance, RDBInstance', 'RDBInstance, RedisInstance')
            content = content.replace('RedisInstance, RDBInstance, RedisInstance', 'RDBInstance, RedisInstance')
    
    # 2. 修复 db.query(Instance) 为 db.query(RDBInstance)
    # 对于 redis.py，需要特殊处理
    if 'redis.py' in filepath:
        content = re.sub(r'db\.query\(Instance\)', 'db.query(RedisInstance)', content)
    else:
        content = re.sub(r'db\.query\(Instance\)', 'db.query(RDBInstance)', content)
    
    # 3. 修复 Instance.id 为 RDBInstance.id 或 RedisInstance.id
    if 'redis.py' in filepath:
        content = re.sub(r'Instance\.id', 'RedisInstance.id', content)
        content = re.sub(r'Instance\.name', 'RedisInstance.name', content)
        content = re.sub(r'Instance\.status', 'RedisInstance.status', content)
    else:
        content = re.sub(r'Instance\.id', 'RDBInstance.id', content)
        content = re.sub(r'Instance\.name', 'RDBInstance.name', content)
        content = re.sub(r'Instance\.status', 'RDBInstance.status', content)
        content = re.sub(r'Instance\.db_type', 'RDBInstance.db_type', content)
        content = re.sub(r'Instance\.host', 'RDBInstance.host', content)
        content = re.sub(r'Instance\.port', 'RDBInstance.port', content)
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"Fixed: {filepath}")
        return True
    else:
        print(f"No changes: {filepath}")
        return False

if __name__ == '__main__':
    fixed_count = 0
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            if fix_file(filepath):
                fixed_count += 1
        else:
            print(f"Not found: {filepath}")
    
    print(f"\nTotal files fixed: {fixed_count}")
