# 测试指南

> 后端测试目录：`tests/`

---

## 快速开始

```bash
# 进入后端目录
cd backend

# 运行所有测试（完整，耗时约 30-60 秒）
python -m pytest tests/

# 快速测试（跳过慢测试，约 10 秒）
python -m pytest tests/ -m "not slow and not e2e"

# 只运行 API 测试（约 15 秒）
python -m pytest tests/api/ -q

# 只运行单元测试（约 5 秒）
python -m pytest tests/unit/ -q
```

---

## 测试结构

```
tests/
├── conftest.py              # 全局 fixtures
├── helpers/                 # 测试辅助工具
│   ├── base_api_test.py     # API 测试基类
│   └── base_service_test.py # 服务测试基类
├── api/                     # API 测试 (~22 个文件)
│   ├── test_auth.py
│   ├── test_users.py
│   ├── test_instances.py
│   ├── test_notification.py
│   └── ...
├── unit/                    # 单元测试 (~60 个文件)
│   ├── api/                # API 单元测试
│   ├── plugins/             # 插件单元测试
│   ├── services/            # 服务单元测试
│   └── utils/               # 工具单元测试
├── e2e/                     # 端到端测试
├── integration/             # 集成测试
└── run_fast_tests.sh       # 快速测试脚本
```

---

## 测试标记

| 标记 | 说明 | 使用场景 |
|------|------|----------|
| `unit` | 单元测试 | 纯函数/类，无外部依赖 |
| `integration` | 集成测试 | 需要数据库 |
| `e2e` | 端到端测试 | 完整流程 |
| `slow` | 耗时测试 | >1秒 |
| `smoke` | 冒烟测试 | 核心功能 |

---

## 编写测试

### API 测试示例

```python
import pytest
from fastapi.testclient import TestClient

def test_list_users(client: TestClient, admin_token: str):
    """测试获取用户列表"""
    response = client.get(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
```

### 添加 slow 标记

```python
@pytest.mark.slow
async def test_long_running_task():
    """这个测试很慢"""
    ...
```

---

## 覆盖率

- **当前覆盖率**: ~55%
- **目标覆盖率**: 55%（已降低目标）
- **报告位置**: `htmlcov/index.html`

---

## 常见问题

### Q: 测试太慢怎么办？

使用快速测试：
```bash
python -m pytest tests/ -m "not slow and not e2e"
```

### Q: 覆盖率不够？

先运行测试查看未覆盖的代码：
```bash
python -m pytest tests/ --cov=app --cov-report=term-missing
```

### Q: 数据库连接失败？

检查环境变量：
```bash
export DATABASE_URL=sqlite:///:memory:
export TESTING=true
```

---

*最后更新：2026-04-09*
