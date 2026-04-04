# OpsCenter Backend - 架构规范

## 项目概览

OpsCenter 是一站式运维管理平台，采用 Python FastAPI + SQLAlchemy 技术栈。

## 测试覆盖率

### 当前状态

- **覆盖率目标**: 30% (pytest.ini 配置)
- **当前覆盖率**: 35.49%
- **测试文件位置**: `tests/`

### 已覆盖模块

| 模块 | 覆盖率 | 测试数 | 说明 |
|------|--------|--------|------|
| app/utils/auth.py | 83% | 12 | 密码哈希、JWT、AES加密 |
| app/utils/api_response.py | 85% | 15 | 错误码、响应格式 |
| app/services/user_service.py | 69% | 18 | 用户CRUD、认证 |
| app/services/permission_service.py | 52% | 16 | 权限检查 |
| app/services/base.py | 52% | 12 | Service基类 |
| app/services/instance_service.py | 28% | 15 | 实例管理 |
| app/services/storage.py | 37% | 12 | 文件存储 |
| app/services/notification.py | 32% | 12 | 通知服务、钉钉消息 |
| app/services/sql_optimization_service.py | 22% | 15 | 采集任务、优化建议 |
| app/services/sql_executor.py | 32% | 15 | SQL执行器 |
| app/services/scheduler.py | 48% | 20 | 定时任务调度器 |
| app/services/db_connection.py | 35% | 25 | 数据库连接管理 |
| app/utils/audit_decorator.py | 77% | 20 | 审计日志装饰器 |

### 新增测试文件

本次补充的测试文件：
- `test_notification_service.py` - 通知服务完整测试 (12个)
- `test_sql_optimization_service.py` - SQL优化服务测试 (15个)
- `test_sql_executor.py` - SQL执行器测试 (15个)
- `test_api_response.py` - API响应工具测试 (15个)
- `test_storage.py` - 存储服务测试 (15个)
- `test_scheduler.py` - 定时任务调度器测试 (20个)
- `test_db_connection.py` - 数据库连接管理测试 (25个)
- `test_audit_decorator.py` - 审计日志装饰器测试 (20个)

### 测试结构

```
tests/
├── conftest.py                    # 测试配置和 fixtures (15+ fixtures)
├── pytest.ini                     # pytest 配置
├── unit/                          # 单元测试
│   ├── test_auth.py               # 认证工具测试 (8个)
│   ├── test_auth_utils.py         # 认证工具详细测试 (12个)
│   ├── test_base_service.py       # Service基类测试 (12个)
│   ├── test_permission_service.py # 权限服务测试 (16个)
│   ├── test_user_service.py       # 用户服务测试 (18个)
│   ├── test_instance_service.py   # 实例服务测试 (15个)
│   ├── test_storage.py            # 存储服务测试 (15个)
│   ├── test_scheduler.py          # 定时任务调度器测试 (20个)
│   ├── test_db_connection.py      # 数据库连接管理测试 (25个)
│   ├── test_audit_decorator.py    # 审计日志装饰器测试 (20个)
│   ├── test_storage.py            # 存储服务测试 (12个)
│   ├── test_notification_service.py # 通知服务测试 (7个)
│   ├── test_cache_service.py      # 缓存服务测试 (8个)
│   └── test_config.py             # 配置测试 (7个)
└── integration/                   # 集成测试
    ├── test_auth_api.py           # 认证接口测试
    ├── test_users_api.py          # 用户管理测试
    ├── test_environments_api.py   # 环境管理测试
    ├── test_scripts_api.py        # 脚本管理测试
    └── test_instances_api.py      # 实例管理测试
```

### 运行测试

```bash
# 运行所有测试
cd backend && python -m pytest tests/

# 运行单元测试
python -m pytest tests/unit/ -v

# 运行带覆盖率报告
python -m pytest tests/ --cov=app --cov-report=html

# 查看 HTML 覆盖率报告
open htmlcov/index.html
```

### Fixtures 说明

conftest.py 提供的 fixtures:

| Fixture | 说明 |
|---------|------|
| `db_session` | 内存 SQLite 数据库会话 |
| `client` | 同步测试客户端 |
| `super_admin_token` | 超级管理员 JWT Token |
| `operator_token` | 普通运维用户 Token |
| `approval_admin_token` | 审批管理员 Token |
| `auth_headers` | 普通用户认证头 |
| `admin_headers` | 管理员认证头 |
| `create_test_user` | 创建测试用户的工厂函数 |
| `create_test_environment` | 创建测试环境的工厂函数 |
| `create_test_script` | 创建测试脚本的工厂函数 |

## 分层架构

```
┌─────────────────────────────────────────────────────────────┐
│  API Layer (app/api/)                                        │
│  - 接收 HTTP 请求、参数校验                                   │
│  - 调用 Service 层处理业务                                    │
│  - 返回 HTTP 响应                                            │
│  - 禁止直接操作数据库                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Service Layer (app/services/)                              │
│  - 业务逻辑处理                                               │
│  - 事务管理                                                   │
│  - 跨模块协调                                                 │
│  - 权限检查                                                   │
│  - 数据访问封装                                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Model Layer (app/models/)                                  │
│  - SQLAlchemy ORM 模型定义                                   │
│  - 数据库表映射                                               │
│  - 关联关系定义                                               │
└─────────────────────────────────────────────────────────────┘
```

## 配置管理

### 配置架构

使用 pydantic-settings 进行类型安全的配置管理：

```
app/config/
├── __init__.py     # 配置入口
├── core.py         # 核心配置（应用、数据库、安全等）
└── storage.py      # 存储配置（本地/S3/OSS）
```

### 配置分类

| 配置类 | 前缀 | 说明 |
|--------|------|------|
| `AppSettings` | `APP_` | 应用基础配置 |
| `DatabaseSettings` | - | 数据库配置（PostgreSQL/MySQL） |
| `RedisSettings` | `REDIS_` | Redis 配置 |
| `SecuritySettings` | - | 安全配置（JWT、AES、密码盐值） |
| `StorageSettings` | `STORAGE_` | 文件存储配置 |
| `AWSSettings` | `AWS_` | AWS RDS 配置 |
| `NotificationSettings` | `NOTIFICATION_` | 通知配置 |

### 使用方式

```python
from app.config import settings

# 获取配置
db_url = settings.database.url
jwt_key = settings.security.get_jwt_secret_key()

# 兼容旧代码
db_url = settings.DATABASE_URL  # 等同于 settings.database.url
```

### 环境变量

参考 `.env.example` 文件配置环境变量：

```bash
# 数据库
DATABASE_URL=postgresql://user:pass@host:5432/db

# 安全配置（生产环境必须设置）
JWT_SECRET_KEY=your-jwt-secret-key
AES_KEY=your-32-character-aes-key-here!
PASSWORD_SALT=your-password-salt

# 存储
STORAGE_TYPE=local  # 或 s3, oss
```

### 生产环境检查

```python
issues = settings.check_production_config()
if issues:
    print(f"配置问题: {issues}")
```

## 目录结构

```
backend/
├── app/
│   ├── api/              # API 层 - HTTP 路由处理
│   │   ├── users.py      # 用户 API
│   │   ├── approval.py   # 审批 API
│   │   └── ...
│   ├── config/           # 配置管理
│   │   ├── __init__.py   # 配置入口
│   │   ├── core.py       # 核心配置
│   │   └── storage.py    # 存储配置
│   ├── services/         # Service 层 - 业务逻辑
│   │   ├── base.py       # Service 基类
│   │   ├── user_service.py
│   │   ├── instance_service.py
│   │   └── permission_service.py
│   ├── models/           # Model 层 - 数据模型
│   │   ├── __init__.py   # 模型定义
│   │   └── instances.py
│   ├── schemas/          # Schema 层 - 请求/响应模型
│   ├── utils/            # 工具函数
│   └── config/           # 配置管理
└── tests/
```

## 编码规范

### 1. API 层规范

**✅ 正确示例：API 层调用 Service 层**

```python
from app.services import UserService

@router.get("")
async def list_users(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    user_service = UserService(db)
    users, total = user_service.get_multi_with_count(skip, limit)
    return {"total": total, "items": [UserResponse.from_orm(u) for u in users]}
```

**❌ 错误示例：API 层直接操作数据库**

```python
@router.get("")
async def list_users(db: Session = Depends(get_db)):
    # 禁止：API 层直接查询数据库
    users = db.query(User).offset(0).limit(20).all()
    return {"items": users}
```

### 2. Service 层规范

**✅ 正确示例：Service 封装业务逻辑**

```python
class UserService(BaseService[User]):
    def create_user(self, username: str, password: str, ...) -> User:
        # 业务校验
        if self.get_by_username(username):
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        # 创建用户
        return self.create({
            "username": username,
            "password_hash": hash_password(password),
            ...
        })
```

### 3. 数据库查询优化

**使用 joinedload 预加载关联对象，避免 N+1 问题：**

```python
# Service 层
def get_with_environment(self, instance_id: int) -> Optional[RDBInstance]:
    return self.db.query(RDBInstance).options(
        joinedload(RDBInstance.environment)
    ).filter(RDBInstance.id == instance_id).first()
```

### 4. 事务管理

**Service 层负责事务管理：**

```python
def transfer_ownership(self, from_user_id: int, to_user_id: int, resource_id: int):
    try:
        # 业务操作
        self.update(resource_id, {"owner_id": to_user_id})
        self.log_transfer(from_user_id, to_user_id, resource_id)
        self.db.commit()  # Service 层控制事务提交
    except Exception as e:
        self.db.rollback()
        raise
```

## Service 层清单

| Service | 职责 | 对应 API |
|---------|------|----------|
| `UserService` | 用户 CRUD、认证、权限检查 | `/api/v1/users` |
| `RDBInstanceService` | MySQL/PostgreSQL 实例管理 | `/api/v1/rdb-instances` |
| `RedisInstanceService` | Redis 实例管理 | `/api/v1/redis-instances` |
| `PermissionService` | 权限检查、环境权限 | 全局 |

## 异步数据库操作

### 架构设计

采用渐进式迁移方案，同步和异步 API 并存：

```
同步 API (现有)              异步 API (推荐)
     ↓                           ↓
Session                      AsyncSession
     ↓                           ↓
psycopg2 / pymysql           asyncpg / aiomysql
```

### 使用方式

**异步 API 端点：**

```python
from app.database_async import get_async_db
from app.services import AsyncUserService

@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_async_db)):
    user_service = AsyncUserService(db)
    users, total = await user_service.get_multi_with_count()
    return {"total": total, "items": users}
```

**后台任务：**

```python
from app.database_async import get_async_db_context
from app.services import AsyncUserService

async def background_task():
    async with get_async_db_context() as db:
        user_service = AsyncUserService(db)
        users = await user_service.get_multi()
        return users
```

### 异步 Service 清单

| Service | 同步版本 | 异步版本 |
|---------|---------|---------|
| 用户服务 | `UserService` | `AsyncUserService` |
| 实例服务 | `RDBInstanceService` | 待实现 |
| 权限服务 | `PermissionService` | 待实现 |

### 迁移指南

1. **新增 API**：推荐使用异步 API
2. **高频 API**：优先迁移到异步（用户列表、实例列表等）
3. **低频 API**：可保持同步，逐步迁移

### 注意事项

- 异步操作中禁止使用同步阻塞代码
- 同一会话中不要混用同步和异步操作
- 异步 Service 的方法都是 `async` 方法，需要 `await`

## 常见问题修复

### 问题 1：API 层直接操作数据库

**定位**：搜索 `db.query` 出现在 API 文件中
**修复**：将数据访问逻辑迁移到 Service 层

### 问题 2：N+1 查询问题

**定位**：在循环中访问关联属性（如 `for i in instances: i.environment.name`）
**修复**：在 Service 层使用 `joinedload` 预加载

### 问题 3：业务逻辑散落在 API 层

**定位**：API 函数过长（超过 50 行），包含复杂业务判断
**修复**：提取业务逻辑到 Service 层方法

## 依赖安装

```bash
cd backend
pip install -r requirements.txt
```

## 运行测试

```bash
pytest tests/
```

## 代码检查

```bash
# Python 语法检查
python -m py_compile app/api/*.py app/services/*.py

# 类型检查（可选）
mypy app/
```
