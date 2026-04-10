# Code Map - 代码地图

> 快速定位：打开这个文档，找到你要改的东西，直接去对应的文件和行号！

---

## 一、后端（Backend）

### 1.1 核心入口

| 文件 | 说明 |
|------|------|
| `backend/app/main.py` | FastAPI 入口、路由注册、中间件 |
| `backend/app/database.py` | 数据库连接、Session 管理 |
| `backend/app/config.py` | 环境变量、配置管理 |

### 1.2 API 路由

| 模块 | 文件路径 |
|------|----------|
| 认证 | `backend/app/api/auth.py` |
| 用户管理 | `backend/app/api/users.py` |
| 菜单管理 | `backend/app/api/menu.py` |
| 实例管理 | `backend/app/api/instances.py` |
| Redis 管理 | `backend/app/api/redis.py` |
| 环境管理 | `backend/app/api/environments.py` |
| SQL 编辑器 | `backend/app/api/sql.py` |
| 变更审批 | `backend/app/api/approval.py` |
| 监控中心 | `backend/app/api/monitor.py` |
| 通知通道 | `backend/app/api/notification_channels.py` |
| 脚本管理 | `backend/app/api/scripts.py` |
| 定时任务 | `backend/app/api/scheduled_tasks.py` |
| 审计日志 | `backend/app/api/audit.py` |
| 系统配置 | `backend/app/api/system.py` |
| 巡检报告 | `backend/app/api/inspection.py` |
| SQL 优化器 | `backend/app/api/sql_optimizer.py` |
| 权限管理 | `backend/app/api/permissions.py` |
| AI 模型 | `backend/app/api/ai_models.py` |
| 密钥轮换 | `backend/app/api/key_rotation.py` |

### 1.3 数据模型

| 模块 | 文件路径 |
|------|----------|
| 用户/角色 | `backend/app/models/user.py` |
| 菜单/权限 | `backend/app/models/menu.py` |
| 实例 | `backend/app/models/instance.py` |
| 审批 | `backend/app/models/approval.py` |
| 通知 | `backend/app/models/notification.py` |
| 脚本 | `backend/app/models/script.py` |
| 巡检 | `backend/app/models/inspection.py` |
| AI | `backend/app/models/ai.py` |

### 1.4 服务层

| 服务 | 文件路径 |
|------|----------|
| 数据库连接 | `backend/app/services/db_connection.py` |
| Redis 连接 | `backend/app/services/redis_connection.py` |
| SQL 执行 | `backend/app/services/sql_executor.py` |
| 加密服务 | `backend/app/services/encryption.py` |
| 密钥轮换 | `backend/app/services/key_rotation.py` |
| 通知发送 | `backend/app/services/notification.py` |
| 调度器 | `backend/app/services/scheduler.py` |
| AI 服务 | `backend/app/services/ai_service.py` |

### 1.5 工具函数

| 文件 | 说明 |
|------|------|
| `backend/app/utils/logging.py` | 日志配置 |
| `backend/app/utils/crypto.py` | 加密工具 |
| `backend/app/deps.py` | 依赖注入（认证、权限） |

---

## 二、前端（Frontend）

### 2.1 核心配置

| 文件 | 说明 |
|------|------|
| `frontend/src/api/index.js` | API 封装、拦截器 |
| `frontend/src/router/index.js` | 路由配置、导航守卫 |
| `frontend/src/main.js` | Vue 入口 |
| `frontend/vite.config.js` | Vite 配置 |

### 2.2 页面组件

| 模块 | 文件路径 |
|------|----------|
| 登录 | `frontend/src/views/login/index.vue` |
| 首页 | `frontend/src/views/dashboard/index.vue` |
| 实例管理 | `frontend/src/views/instances/` |
| Redis 管理 | `frontend/src/views/instances/redis-detail.vue` |
| SQL 编辑器 | `frontend/src/views/sql-editor/` |
| 变更审批 | `frontend/src/views/change/` |
| 监控中心 | `frontend/src/views/monitor/` |
| 通知配置 | `frontend/src/views/notification/` |
| 脚本管理 | `frontend/src/views/scripts/` |
| 定时任务 | `frontend/src/views/scheduled-tasks/` |
| 审计日志 | `frontend/src/views/audit/` |
| 系统配置 | `frontend/src/views/system/` |
| 权限管理 | `frontend/src/views/permissions/` |

### 2.3 公共组件

| 组件 | 文件路径 |
|------|----------|
| 表格操作列 | `frontend/src/components/TableActions.vue` |
| 代码编辑器 | `frontend/src/components/CodeEditor.vue` |
| 权限指令 | `frontend/src/directives/permission.js` |

### 2.4 布局

| 文件 | 说明 |
|------|------|
| `frontend/src/layouts/MainLayout.vue` | 主布局（侧边栏 + 头部） |
| `frontend/src/layouts/BlankLayout.vue` | 空白布局（登录页） |

---

## 三、数据库

### 3.1 核心表

| 表名 | 说明 |
|------|------|
| `users` | 用户表 |
| `permissions` | 权限表 |
| `role_permissions` | 角色权限关联 |
| `menu_configs` | 菜单配置 |
| `rdb_instances` | RDB 实例 |
| `redis_instances` | Redis 实例 |
| `approval_flows` | 审批工单 |
| `notification_channels` | 通知通道 |
| `scripts` | 脚本表 |
| `scheduled_tasks` | 定时任务 |
| `audit_logs` | 审计日志 |
| `ai_models` | AI 模型 |
| `key_rotation_keys` | 密钥版本 |

### 3.2 加密字段

| 表名 | 字段 | 说明 |
|------|------|------|
| `rdb_instances` | password_encrypted | 数据库密码 |
| `redis_instances` | password_encrypted | Redis 密码 |
| `ai_models` | api_key_encrypted | AI API 密钥 |

---

## 四、常用操作对照

| 操作 | 后端文件 | 前端文件 |
|------|----------|----------|
| 新增菜单 | - | `menu_configs` 表 |
| 新增 API | `backend/app/api/xxx.py` | - |
| 修改加密 | `backend/app/services/encryption.py` | - |
| 修改登录 | `backend/app/api/auth.py` | `frontend/src/views/login/` |

---

## 五、规格文档

| 规格 | 文件 |
|------|------|
| 认证与权限 | `.vibecoding/specs/001-认证与权限.md` |
| 实例管理 | `.vibecoding/specs/002-实例管理.md` |
| 变更审批 | `.vibecoding/specs/005-变更审批.md` |
| 监控中心 | `.vibecoding/specs/006-监控中心.md` |
| 通知系统 | `.vibecoding/specs/008-消息通知-重新设计.md` |
| SQL 优化 | `.vibecoding/specs/016-SQL优化闭环.md` |

---

## 六、部署文件

| 文件 | 说明 |
|------|------|
| `release/k8s/*.yaml` | K8s 部署清单 |
| `release/helm/opscenter/` | Helm Chart |
| `release/docker/` | Docker 配置 |
| `release/docs/KUBERNETES_DEPLOYMENT.md` | K8s 部署文档 |

---

*文档版本：v2.0*
*最后更新：2026-04-10*
