# 测试指南

> 后端测试目录：`tests/`

---

## 快速开始

```bash
cd backend

# 运行所有测试
python -m pytest tests/

# 运行测试（跳过慢测试）
python -m pytest tests/ -m "not slow"

# 只运行 API 测试
python -m pytest tests/api/ -q

# 只运行单元测试
python -m pytest tests/unit/ -q

# 跳过需要真实数据库的测试
python -m pytest tests/ -m "not requires_db and not requires_redis"
```

---

## 测试结构

```
tests/
├── api/                     # API 测试
│   ├── test_auth_core_api.py
│   ├── test_instances_core_api.py
│   └── ...
├── unit/                    # 单元测试
│   ├── test_auth.py
│   ├── test_rollback_generator.py
│   ├── test_datasource_factory.py
│   └── ...
├── e2e/                     # 端到端测试
│   ├── flows/              # 流程测试
│   └── test_*.py
├── integration/             # 集成测试
├── services/               # 服务测试
├── utils/                  # 工具测试
├── helpers/                # 测试辅助工具
└── conftest.py             # 全局 fixtures
```

---

## 测试标记

| 标记 | 说明 |
|------|------|
| `unit` | 单元测试（纯函数/类） |
| `integration` | 集成测试（需要数据库） |
| `e2e` | 端到端测试 |
| `slow` | 耗时测试（>1秒） |
| `requires_db` | 需要真实数据库 |
| `requires_redis` | 需要真实 Redis |
| `requires_mysql` | 需要 MySQL |
| `requires_postgresql` | 需要 PostgreSQL |
