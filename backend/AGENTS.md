# OpsCenter Backend - 架构规范

## 项目概览

OpsCenter 是一站式运维管理平台，采用 Python FastAPI + SQLAlchemy 技术栈。

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
