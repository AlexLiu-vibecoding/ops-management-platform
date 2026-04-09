# Code Map - 代码地图

> 快速定位：打开这个文档，找到你要改的东西，直接去对应的文件和行号！

---

## 一、后端（Backend）

### 1.1 核心入口

| 文件 | 说明 | 关键内容 |
|------|------|----------|
| `backend/app/main.py` | FastAPI 入口 | 路由注册、中间件、启动事件 |
| `backend/app/database.py` | 数据库连接 | Session、连接池管理 |
| `backend/app/config.py` | 配置管理 | 环境变量、默认值 |

### 1.2 API 路由（按模块）

| 模块 | 文件路径 | 说明 |
|------|----------|------|
| 认证 | `backend/app/api/auth.py` | 登录、登出、Token 刷新 |
| 用户管理 | `backend/app/api/users.py` | 用户 CRUD、密码修改 |
| 菜单管理 | `backend/app/api/menu.py` | 动态菜单、权限码 |
| 实例管理 | `backend/app/api/instances.py` | RDB 实例 CRUD |
| Redis 管理 | `backend/app/api/redis.py` | Redis 实例 CRUD、Keys 操作 |
| 环境管理 | `backend/app/api/environments.py` | 环境变量 CRUD |
| SQL 编辑器 | `backend/app/api/sql.py` | SQL 执行、结果集 |
| 变更审批 | `backend/app/api/approval.py` | 工单 CRUD、审批流程 |
| 监控中心 | `backend/app/api/monitor.py` | 性能指标、慢查询 |
| 通知通道 | `backend/app/api/notification_channels.py` | 钉钉/企微/飞书/邮件/Webhook |
| 通知规则 | `backend/app/api/notification_rules.py` | 告警规则、静默规则 |
| 脚本管理 | `backend/app/api/scripts.py` | 脚本 CRUD、执行 |
| 定时任务 | `backend/app/api/scheduled_tasks.py` | 定时任务 CRUD、调度器 |
| 审计日志 | `backend/app/api/audit.py` | 操作记录查询 |
| 系统配置 | `backend/app/api/system.py` | 系统参数配置 |
| 巡检报告 | `backend/app/api/inspection.py` | 巡检任务、报告生成 |
| SQL 优化器 | `backend/app/api/sql_optimizer.py` | 优化建议、索引分析 |
| 权限管理 | `backend/app/api/permissions.py` | RBAC 权限配置 |
| AI 模型 | `backend/app/api/ai_models.py` | AI 模型配置、密钥管理 |
| 密钥轮换 | `backend/app/api/key_rotation.py` | AES 密钥版本管理 |
| AI 对话 | `backend/app/api/ai_chat.py` | AI 对话接口 |

### 1.3 数据模型

| 模块 | 文件路径 | 说明 |
|------|----------|------|
| 用户 | `backend/app/models/user.py` | User、UserRole |
| 菜单 | `backend/app/models/menu.py` | MenuConfig、Permission |
| 实例 | `backend/app/models/instance.py` | RDBInstance、RedisInstance |
| 审批 | `backend/app/models/approval.py` | ApprovalWorkflow、ApprovalStep |
| 通知 | `backend/app/models/notification.py` | NotificationChannel、NotificationRule |
| 脚本 | `backend/app/models/script.py` | Script、ScheduledTask |
| 巡检 | `backend/app/models/inspection.py` | InspectionTask、InspectionReport |
| AI | `backend/app/models/ai.py` | AIModel、AIModelConfig |

### 1.4 服务层

| 服务 | 文件路径 | 说明 |
|------|----------|------|
| 数据库连接 | `backend/app/services/db_connection.py` | MySQL/PostgreSQL 连接池 |
| Redis 连接 | `backend/app/services/redis_connection.py` | Redis 客户端封装 |
| SQL 执行 | `backend/app/services/sql_executor.py` | SQL 解析、执行、结果转换 |
| 加密服务 | `backend/app/services/encryption.py` | AES-256-CBC 加密解密 |
| 密钥轮换 | `backend/app/services/key_rotation.py` | 密钥版本管理、数据迁移 |
| 通知发送 | `backend/app/services/notification.py` | 钉钉/企微/飞书/邮件发送 |
| 调度器 | `backend/app/services/scheduler.py` | APScheduler 调度器管理 |
| AI 服务 | `backend/app/services/ai_service.py` | AI 模型调用、对话管理 |

### 1.5 工具函数

| 文件 | 说明 |
|------|------|
| `backend/app/utils/logging.py` | 日志配置 |
| `backend/app/utils/crypto.py` | 加密工具 |
| `backend/app/utils/validators.py` | 数据验证 |
| `backend/app/deps.py` | 依赖注入（认证、权限） |

---

## 二、前端（Frontend）

### 2.1 核心配置

| 文件 | 说明 | 关键内容 |
|------|------|----------|
| `frontend/src/api/index.js` | API 封装 | baseURL、拦截器 |
| `frontend/src/router/index.js` | 路由配置 | 路由表、导航守卫 |
| `frontend/src/main.js` | Vue 入口 | 组件注册、插件初始化 |
| `frontend/vite.config.js` | Vite 配置 | 代理、别名 |

### 2.2 API 封装

| 模块 | 文件路径 | 说明 |
|------|----------|------|
| 通用 | `frontend/src/api/index.js` | request 实例、全局拦截器 |
| 认证 | `frontend/src/api/auth.js` | 登录、登出 |
| 用户 | `frontend/src/api/user.js` | 用户管理 |
| 实例 | `frontend/src/api/instance.js` | 实例管理 |
| SQL | `frontend/src/api/sql.js` | SQL 编辑器 |
| 审批 | `frontend/src/api/approval.js` | 变更审批 |
| 监控 | `frontend/src/api/monitor.js` | 监控数据 |
| 通知 | `frontend/src/api/notification.js` | 通知配置 |
| 脚本 | `frontend/src/api/script.js` | 脚本管理 |
| 巡检 | `frontend/src/api/inspection.js` | 巡检报告 |
| AI | `frontend/src/api/ai.js` | AI 模型、对话 |
| 密钥 | `frontend/src/api/keyRotation.js` | 密钥轮换 |

### 2.3 页面组件（按模块）

| 模块 | 文件路径 | 说明 |
|------|----------|------|
| 登录 | `frontend/src/views/login/index.vue` | 登录页面 |
| 首页 | `frontend/src/views/dashboard/index.vue` | 仪表盘 |
| 实例管理 | `frontend/src/views/instances/` | RDB 实例列表、详情 |
| Redis 管理 | `frontend/src/views/instances/redis-detail.vue` | Redis 详情、Keys 操作 |
| 环境管理 | `frontend/src/views/environments/` | 环境变量 |
| SQL 编辑器 | `frontend/src/views/sql-editor/` | SQL 编辑、结果展示 |
| 变更审批 | `frontend/src/views/change/` | 工单列表、审批流程 |
| 监控中心 | `frontend/src/views/monitor/` | 性能监控、慢查询 |
| 通知配置 | `frontend/src/views/notification/` | 通道管理、规则配置 |
| 脚本管理 | `frontend/src/views/scripts/` | 脚本列表、编辑器 |
| 定时任务 | `frontend/src/views/scheduled-tasks/` | 任务列表、执行日志 |
| 审计日志 | `frontend/src/views/audit/` | 日志查询 |
| 系统配置 | `frontend/src/views/system/` | 系统参数、AI 模型 |
| 巡检报告 | `frontend/src/views/inspection/` | 巡检任务、报告 |
| 权限管理 | `frontend/src/views/permissions/` | RBAC 配置 |
| AI 对话 | `frontend/src/views/ai-chat/` | AI 对话界面 |

### 2.4 公共组件

| 组件 | 文件路径 | 说明 |
|------|----------|------|
| 表格操作列 | `frontend/src/components/TableActions.vue` | 统一的编辑/删除按钮 |
| 弹窗表单 | `frontend/src/components/DialogForm.vue` | 通用弹窗表单 |
| 代码编辑器 | `frontend/src/components/CodeEditor.vue` | Monaco Editor 封装 |
| 权限指令 | `frontend/src/directives/permission.js` | v-permission 指令 |

### 2.5 布局组件

| 文件 | 说明 |
|------|------|
| `frontend/src/layouts/MainLayout.vue` | 主布局（侧边栏 + 头部） |
| `frontend/src/layouts/BlankLayout.vue` | 空白布局（登录页用） |

---

## 三、数据库（Database）

### 3.1 核心表

| 表名 | 说明 | 关键字段 |
|------|------|----------|
| `users` | 用户表 | id, username, email, password_hash |
| `user_roles` | 用户角色关联 | user_id, role_id |
| `roles` | 角色表 | id, name, description |
| `permissions` | 权限表 | id, code, name, resource |
| `role_permissions` | 角色权限关联 | role_id, permission_id |
| `menu_configs` | 菜单配置 | id, name, path, icon, parent_id |
| `rdb_instances` | RDB 实例 | id, name, host, port, db_type |
| `redis_instances` | Redis 实例 | id, name, host, port |
| `approval_workflows` | 审批工单 | id, title, type, status |
| `approval_steps` | 审批步骤 | id, workflow_id, step_order |
| `notification_channels` | 通知通道 | id, name, channel_type, config |
| `notification_rules` | 通知规则 | id, name, channel_id, conditions |
| `scripts` | 脚本表 | id, name, content, language |
| `scheduled_tasks` | 定时任务 | id, name, cron_expr, script_id |
| `inspection_tasks` | 巡检任务 | id, name, task_type, schedule |
| `ai_models` | AI 模型 | id, name, provider, model_id, api_key_encrypted |
| `key_rotation_keys` | 密钥版本 | id, version, key_hash |
| `key_rotation_config` | 密钥配置 | id, current_version |
| `audit_logs` | 审计日志 | id, user_id, action, resource |

### 3.2 加密字段

| 表名 | 字段 | 说明 |
|------|------|------|
| `rdb_instances` | password_encrypted | 数据库密码 |
| `redis_instances` | password_encrypted | Redis 密码 |
| `ai_models` | api_key_encrypted | AI API 密钥 |
| `notification_channels` | config_encrypted | Webhook 密钥等 |

---

## 四、部署文件（Release）

| 文件 | 说明 |
|------|------|
| `release/k8s/00-namespace.yaml` | K8s 命名空间 |
| `release/k8s/01-configmap.yaml` | 应用配置 |
| `release/k8s/02-secret.yaml` | 敏感配置 |
| `release/k8s/03-backend-deployment.yaml` | 后端 Deployment |
| `release/k8s/04-backend-service.yaml` | 后端 Service + HPA + PDB |
| `release/k8s/05-frontend-deployment.yaml` | 前端 Deployment |
| `release/k8s/06-frontend-service.yaml` | 前端 Service + Ingress |
| `release/helm/opscenter/` | Helm Chart |
| `release/docker/entrypoint.sh` | 容器启动脚本 |
| `release/docker/nginx.conf` | Nginx 配置 |
| `release/Dockerfile` | Docker 镜像构建 |

---

## 五、规格文档（Specs）

| 规格 | 文件路径 | 说明 |
|------|----------|------|
| SPEC-001 | `.vibecoding/specs/001-认证与权限.md` | 认证与权限 |
| SPEC-002 | `.vibecoding/specs/002-实例管理.md` | RDB/Redis 实例管理 |
| SPEC-003 | `.vibecoding/specs/003-环境管理.md` | 环境变量管理 |
| SPEC-004 | `.vibecoding/specs/004-SQL编辑器.md` | SQL 编辑器 |
| SPEC-005 | `.vibecoding/specs/005-变更审批.md` | 审批流程 |
| SPEC-006 | `.vibecoding/specs/006-监控中心.md` | 性能监控 |
| SPEC-007 | `.vibecoding/specs/007-Redis管理.md` | Redis 管理 |
| SPEC-008 | `.vibecoding/specs/008-消息通知-重新设计.md` | 通知系统 |
| SPEC-009 | `.vibecoding/specs/009-脚本管理.md` | 脚本管理 |
| SPEC-010 | `.vibecoding/specs/010-定时任务.md` | 定时任务 |
| SPEC-011 | `.vibecoding/specs/011-审计日志.md` | 审计日志 |
| SPEC-012 | `.vibecoding/specs/012-系统配置.md` | 系统配置 |
| SPEC-013 | `.vibecoding/specs/013-巡检报告.md` | 巡检报告 |
| SPEC-014 | `.vibecoding/specs/014-SQL优化器.md` | SQL 优化 |
| SPEC-015 | `.vibecoding/specs/015-权限管理.md` | RBAC 权限 |
| SPEC-016 | `.vibecoding/specs/016-SQL优化闭环.md` | SQL 优化闭环 |
| SPEC-017 | `.vibecoding/specs/017-AI模型配置.md` | AI 模型配置 |

---

## 六、常用操作对照

| 操作 | 后端文件 | 前端文件 |
|------|----------|----------|
| 新增菜单项 | - | `menu_configs` 表 |
| 新增用户角色 | `backend/app/api/users.py` | `frontend/src/views/system/users.vue` |
| 新增 API 路由 | `backend/app/api/xxx.py` + `main.py` | - |
| 修改加密逻辑 | `backend/app/services/encryption.py` | - |
| 修改登录逻辑 | `backend/app/api/auth.py` | `frontend/src/views/login/` |
| 新增实例类型 | `backend/app/services/db_connection.py` | `frontend/src/views/instances/` |
| 新增通知渠道 | `backend/app/services/notification.py` | `frontend/src/views/notification/` |

---

## 七、部署架构（详细版）

> ⚠️ 详细文档见 `release/docs/KUBERNETES_DEPLOYMENT.md`

### 7.1 生产环境架构

```
Kubernetes Cluster
├── Namespace: opscenter
│   ├── Deployment: opscenter-backend (3 replicas)
│   ├── Deployment: opscenter-frontend (2 replicas)
│   ├── Service: opscenter-backend-service
│   ├── Service: opscenter-frontend-service
│   ├── HPA: opscenter-backend-hpa
│   ├── HPA: opscenter-frontend-hpa
│   └── Ingress: opscenter-ingress
│
└── External (AWS)
    ├── Amazon RDS PostgreSQL (Multi-AZ) - 必需
    └── Amazon ElastiCache Redis (Replication) - 可选
```

### 7.2 部署文件

| 文件 | 说明 |
|------|------|
| `release/k8s/00-namespace.yaml` | 命名空间配置 |
| `release/k8s/01-configmap.yaml` | 应用配置（AWS RDS/ElastiCache endpoint） |
| `release/k8s/02-secret.yaml` | 敏感配置（数据库密码） |
| `release/k8s/03-backend-deployment.yaml` | 后端部署配置 |
| `release/k8s/04-backend-service.yaml` | 后端服务 + HPA + PDB |
| `release/k8s/05-frontend-deployment.yaml` | 前端部署配置 |
| `release/k8s/06-frontend-service.yaml` | 前端服务 + Ingress |
| `release/helm/opscenter/` | Helm Chart |

### 7.3 部署命令

```bash
# 进入 release 目录
cd release

# 使用部署脚本
./deploy-k8s.sh

# 查看状态
kubectl get pods -n opscenter

# 重启
kubectl rollout restart deployment/opscenter-backend -n opscenter
```

---

## 八、密钥轮换机制

> ⚠️ 详细实现见 `backend/app/api/key_rotation.py`

### 8.1 概述

系统使用 AES-256-CBC 加密敏感数据，支持**动态多版本**密钥轮换。

### 8.2 加密字段

| 表名 | 字段 | 用途 |
|------|------|------|
| `rdb_instances` | password_encrypted | 数据库密码 |
| `redis_instances` | password_encrypted | Redis 密码 |
| `ai_models` | api_key_encrypted | AI API 密钥 |
| `aws_credentials` | aws_secret_access_key | AWS 访问密钥 |

### 8.3 加密数据格式

```
v{version}$base64(iv + ciphertext)

示例：
- v1$xxxxxx  → V1 密钥加密
- v2$xxxxxx  → V2 密钥加密
- xxxxxx     → 旧格式（无前缀）
```

### 8.4 轮换流程

```
一键轮换（推荐）：
1. 点击「一键轮换」
2. 自动生成新密钥版本
3. 执行数据迁移
4. 自动切换到新密钥版本
```

### 8.5 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/key-rotation/overview` | 密钥轮换概览 |
| GET | `/api/v1/key-rotation/versions` | 密钥版本列表 |
| POST | `/api/v1/key-rotation/full-rotation` | 一键轮换 |
| POST | `/api/v1/key-rotation/migrate` | 执行迁移 |

### 8.6 密钥读取优先级

```
1. 优先从 key_rotation_keys 表读取对应版本的密钥
2. 如果表中没有，回退到环境变量 AES_KEY / AES_KEY_V2
```

---

## 九、架构设计分析

> ⚠️ 以下是理论分析，暂未实施，仅供架构优化参考

### 9.1 开闭原则评估

| 模块 | 符合程度 | 说明 |
|------|----------|------|
| **数据库连接管理** | ⚠️ 部分符合 | MySQL/PostgreSQL/Redis 没有统一接口 |
| **通知渠道** | ⚠️ 基本符合 | 有统一模型，但发送逻辑没有适配器抽象 |
| **权限管理** | ✅ 符合 | RBAC 模型，权限配置在数据库 |
| **菜单系统** | ✅ 符合 | 数据库驱动，新增菜单无需改代码 |
| **实例管理** | ⚠️ 部分符合 | RDB 和 Redis 分开管理 |

### 9.2 可优化方向

| 优先级 | 优化项 | 说明 |
|--------|--------|------|
| P1 | 数据源适配器模式 | 统一 MySQL/PostgreSQL/Redis/MongoDB 接口 |
| P1 | 通知渠道适配器模式 | 统一钉钉/企微/飞书/邮件发送逻辑 |
| P2 | 监控指标收集抽象 | MetricsCollector 接口 |
| P2 | 脚本执行器抽象 | ScriptExecutor 接口 |

### 9.3 适配器模式示例

```python
# 工厂模式（开闭原则核心）
class DataSourceAdapterFactory:
    _adapters = {
        "mysql": MySQLAdapter,
        "postgresql": PostgreSQLAdapter,
        "redis": RedisAdapter,
    }
    
    @classmethod
    def create(cls, adapter_type: str, config: Dict) -> DataSourceAdapter:
        adapter_class = cls._adapters.get(adapter_type)
        if not adapter_class:
            raise ValueError(f"Unsupported adapter type: {adapter_type}")
        return adapter_class(config)
    
    @classmethod
    def register(cls, adapter_type: str, adapter_class: type):
        """对扩展开放：新增适配器只需注册"""
        cls._adapters[adapter_type] = adapter_class
```

---

*文档版本：v1.1*
*最后更新：2026-04-09*
*AGENTS.md 精简版已将核心内容提取至此*
