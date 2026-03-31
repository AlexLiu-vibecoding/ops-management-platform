# AGENTS.md - 项目导航与开发指南

> 本文档帮助 AI 快速理解项目全貌、定位代码、遵循规范。

---

## 一、项目概览

### 1.1 基本信息

| 项目 | 说明 |
|------|------|
| **名称** | OpsCenter - 一站式运维管理平台 |
| **技术栈** | Vue 3 + FastAPI + PostgreSQL + Redis |
| **端口** | 后端 5000 / 前端开发 3000 |
| **环境变量** | `DEPLOY_RUN_PORT=5000`, `COZE_PROJECT_DOMAIN_DEFAULT` |

### 1.2 核心能力

- **数据库管理**: MySQL/PostgreSQL/Redis 多实例管理
- **SQL 工具**: SQL 编辑器、SQL 优化器、慢查询分析
- **变更管理**: DDL/DML 变更审批、变更窗口管理
- **监控告警**: 性能监控、慢查询监控、告警规则
- **自动化**: 脚本管理、定时任务、定时巡检
- **权限管理**: RBAC 权限模型、环境权限隔离

---

## 二、目录结构

```
.
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── api/               # API 路由 (35个模块)
│   │   ├── models/            # 数据模型
│   │   ├── schemas/           # Pydantic Schema
│   │   ├── services/          # 业务服务
│   │   ├── utils/             # 工具函数
│   │   ├── config.py          # 配置管理
│   │   ├── database.py        # 数据库连接
│   │   ├── main.py            # FastAPI 入口
│   │   └── startup_check.py   # 启动自检
│   └── requirements.txt       # Python 依赖
│
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── api/               # API 封装
│   │   ├── components/        # 公共组件
│   │   ├── layouts/           # 布局组件
│   │   ├── router/            # 路由配置
│   │   ├── stores/            # Pinia 状态
│   │   ├── styles/            # 样式文件
│   │   └── views/             # 页面组件 (31个)
│   └── package.json
│
├── .vibecoding/               # 协作文档
│   ├── specs/                 # 功能规格 (16个)
│   ├── DEVELOPMENT.md         # 开发规范
│   └── README.md              # 文档导航
│
├── .coze                      # 项目配置 (启动/构建)
├── AGENTS.md                  # 本文件
└── README.md                  # 项目说明
```

---

## 三、功能模块索引

### 3.1 核心功能模块

| 模块 | 前端路径 | 后端 API | 规格文档 |
|------|----------|----------|----------|
| 认证与权限 | `views/login/` | `api/auth.py` | [SPEC-001](.vibecoding/specs/001-认证与权限.md) |
| 实例管理 | `views/instances/` | `api/instances.py`, `api/rdb_instances.py`, `api/redis_instances.py` | [SPEC-002](.vibecoding/specs/002-实例管理.md) |
| 环境管理 | `views/environments/` | `api/environments.py` | [SPEC-003](.vibecoding/specs/003-环境管理.md) |
| SQL 编辑器 | `views/sql-editor/` | `api/sql.py` | [SPEC-004](.vibecoding/specs/004-SQL编辑器.md) |
| 变更审批 | `views/change/` | `api/approval.py` | [SPEC-005](.vibecoding/specs/005-变更审批.md) |
| 监控中心 | `views/monitor/` | `api/monitor.py`, `api/monitor_ext.py` | [SPEC-006](.vibecoding/specs/006-监控中心.md) |
| Redis 管理 | `views/instances/redis-detail.vue` | `api/redis.py` | [SPEC-007](.vibecoding/specs/007-Redis管理.md) |
| 消息通知 | `views/notification/` | `api/notification.py` | [SPEC-008](.vibecoding/specs/008-消息通知.md) |
| 脚本管理 | `views/scripts/` | `api/scripts.py` | [SPEC-009](.vibecoding/specs/009-脚本管理.md) |
| 定时任务 | `views/scheduled-tasks/` | `api/scheduled_tasks.py` | [SPEC-010](.vibecoding/specs/010-定时任务.md) |
| 审计日志 | `views/audit/` | `api/audit.py` | [SPEC-011](.vibecoding/specs/011-审计日志.md) |
| 系统配置 | `views/system/` | `api/system.py` | [SPEC-012](.vibecoding/specs/012-系统配置.md) |
| 巡检报告 | `views/inspection/` | `api/inspection.py` | [SPEC-013](.vibecoding/specs/013-巡检报告.md) |
| SQL 优化器 | `views/sql-optimizer/` | `api/sql_optimizer.py` | [SPEC-014](.vibecoding/specs/014-SQL优化器.md) |
| 权限管理 | `views/permissions/` | `api/permissions.py` | [SPEC-015](.vibecoding/specs/015-权限管理.md) |

### 3.2 新增功能模块

#### 🔥 SQL 优化闭环 (SPEC-016)

> 自动采集慢SQL → 周期性分析 → 优化建议 → 一键提交变更 → 效果验证

| 组件 | 路径 | 说明 |
|------|------|------|
| 慢查询列表 | `views/monitor/slow-query/SlowQueryList.vue` | 慢查询数据展示 |
| 优化建议 | `views/monitor/slow-query/OptimizationSuggestions.vue` | AI 优化建议列表 |
| 采集任务 | `views/monitor/slow-query/CollectionTasks.vue` | 自动采集配置 |
| 分析历史 | `views/monitor/slow-query/AnalysisHistory.vue` | 历史分析记录 |
| 主页面 | `views/monitor/slow-query/index.vue` | Tab 整合页面 |
| API | `api/sql_optimization.py` | 后端接口 |
| 服务 | `services/sql_optimization_service.py` | 核心服务 |

**关键功能**:
- 定时采集慢 SQL
- LLM 自动分析生成优化建议
- 一键采用建议创建变更申请
- 变更执行后验证效果

**相关文档**: [SPEC-016](.vibecoding/specs/016-SQL优化闭环.md)

#### 🔥 告警规则管理

| 组件 | 路径 | 说明 |
|------|------|------|
| 告警规则 | `views/alerts/rules/index.vue` | 规则配置页面 |
| API | `api/alert_rules.py` | 后端接口 |

**关键功能**:
- 配置告警规则（指标、阈值、级别）
- 关联通知通道
- 告警触发与通知

#### 🔥 定时巡检

| 组件 | 路径 | 说明 |
|------|------|------|
| 定时巡检 | `views/inspection/scheduled/index.vue` | 定时巡检配置 |
| API | `api/scheduled_inspection.py` | 后端接口 |

**关键功能**:
- 配置定时巡检任务
- 自动生成巡检报告
- 支持多种巡检类型

#### 🔥 变更窗口

| 组件 | 路径 | 说明 |
|------|------|------|
| 变更窗口 | `views/change/windows/index.vue` | 窗口管理页面 |
| API | `api/change_windows.py` | 后端接口 |

**关键功能**:
- 定义变更时间窗口
- 关联环境/实例
- 窗口内变更自动审批

---

## 四、路由配置规范

### 4.1 路由规则

| 场景 | 规则 | 示例 |
|------|------|------|
| 单页面 | 使用一级路由 | `/users`, `/notification` |
| 多个相关页面 | 使用嵌套路由 | `/monitor/performance`, `/monitor/slow-query` |

### 4.2 路由结构

```
/                              # 主布局
├── /dashboard                 # 仪表盘
├── /instances                 # 实例管理
├── /instances/:id             # 实例详情 (动态路由)
├── /redis/:id                 # Redis 详情 (动态路由)
├── /environments              # 环境管理
├── /sql-editor                # SQL 编辑器
├── /sql-optimizer             # SQL 优化器
├── /change/                   # 变更管理 (嵌套路由)
│   ├── /change/requests       # DB 变更
│   ├── /change/redis-requests # Redis 变更
│   └── /change/windows        # 变更窗口
├── /monitor/                  # 监控中心 (嵌套路由)
│   ├── /monitor/performance   # 性能监控
│   ├── /monitor/slow-query    # 慢查询监控
│   ├── /monitor/alerts        # 告警中心
│   ├── /monitor/replication   # 主从复制
│   ├── /monitor/locks         # 事务与锁
│   ├── /monitor/inspection    # 巡检报告
│   ├── /monitor/scheduled-inspection  # 定时巡检
│   ├── /monitor/alert-rules   # 告警规则
│   └── /monitor/settings      # 监控配置
├── /scripts                   # 脚本管理
├── /scheduled-tasks           # 定时任务
├── /users                     # 用户管理
├── /permissions               # 权限管理
├── /menu-config               # 菜单配置
├── /audit                     # 审计日志
├── /system                    # 系统设置
└── /notification              # 通知管理
```

### 4.3 路由守卫

```
启动检查 (initChecked)
    │
    ├── 未初始化 → /init
    │
    └── 已初始化
        │
        ├── 未登录 → /login
        │
        └── 已登录
            │
            └── 权限检查 (roles)
                │
                ├── 无权限 → /dashboard
                │
                └── 有权限 → 目标页面
```

---

## 五、开发规范

### 5.1 前端开发

#### 组件规范

```vue
<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/api/index'
import { ElMessage } from 'element-plus'

// 1. 响应式数据
const loading = ref(false)
const dataList = ref([])

// 2. 方法定义
const fetchData = async () => {
  loading.value = true
  try {
    dataList.value = await request.get('/api/xxx')
  } catch (error) {
    // 404 特殊处理：显示空数据而非错误提示
    if (error.response?.status === 404) {
      dataList.value = []
    } else {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
  } finally {
    loading.value = false
  }
}

// 3. 生命周期
onMounted(() => {
  fetchData()
})
</script>
```

#### 表格操作列

使用 `TableActions` 组件统一操作按钮：

```vue
<el-table-column label="操作" width="180" fixed="right" align="center">
  <template #default="{ row }">
    <TableActions :row="row" :actions="actions" :max-primary="3"
      @edit="handleEdit" @delete="handleDelete" />
  </template>
</el-table-column>

<script setup>
const actions = [
  { key: 'edit', label: '编辑', event: 'edit', primary: true },
  { key: 'delete', label: '删除', event: 'delete', danger: true }
]
</script>
```

### 5.2 后端开发

#### API 规范

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user, get_super_admin

router = APIRouter(prefix="/xxx", tags=["模块名"])

@router.get("")
async def list_items(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列表查询"""
    items = db.query(Item).all()
    return items

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_item(
    data: ItemCreate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """创建资源（需要管理员权限）"""
    item = Item(**data.model_dump())
    db.add(item)
    db.commit()
    return {"id": item.id, "message": "创建成功"}
```

### 5.3 启动自检

服务启动时自动执行依赖检查：

```python
# backend/app/startup_check.py
# 启动时自动检查：
# - Python 版本 (>= 3.11)
# - 依赖包 (FastAPI, SQLAlchemy, Pydantic 等 18 个)
# - Pydantic 版本兼容性
# - 数据库配置
# - Redis 配置
# - 前端构建产物
# - 核心模块导入
```

---

## 六、API 端点索引

### 6.1 认证相关

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/auth/login` | POST | 登录 |
| `/api/v1/auth/logout` | POST | 登出 |
| `/api/v1/auth/me` | GET | 当前用户 |

### 6.2 实例管理

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/instances` | GET | 实例列表 |
| `/api/v1/rdb-instances` | GET/POST | RDS 实例 |
| `/api/v1/redis-instances` | GET/POST | Redis 实例 |

### 6.3 SQL 工具

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/sql/execute` | POST | 执行 SQL |
| `/api/v1/sql/validate` | POST | 验证 SQL |
| `/api/v1/sql-optimizer/analyze` | POST | AI 分析 |

### 6.4 监控中心

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/monitor/performance/{id}` | GET | 性能指标 |
| `/api/v1/slow-queries/{id}` | GET | 慢查询列表 |
| `/api/v1/alerts` | GET | 告警列表 |
| `/api/v1/alert-rules` | GET/POST | 告警规则 |

### 6.5 SQL 优化闭环

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/sql-optimization/tasks` | GET/POST | 采集任务 |
| `/api/v1/sql-optimization/suggestions` | GET | 优化建议 |
| `/api/v1/sql-optimization/suggestions/{id}/adopt` | POST | 采用建议 |
| `/api/v1/sql-optimization/suggestions/{id}/verify` | POST | 验证效果 |

---

## 七、常见问题

### Q1: 如何添加新页面？

1. 创建页面组件 `frontend/src/views/xxx/index.vue`
2. 添加路由配置 `frontend/src/router/index.js`
3. 添加菜单配置 `backend/app/api/menu.py`
4. 调用 `/api/v1/menu/add-missing` 同步菜单

### Q2: 如何添加新 API？

1. 创建路由文件 `backend/app/api/xxx.py`
2. 在 `main.py` 中注册路由
3. 创建 Schema `backend/app/schemas/xxx.py`
4. 前端封装 API `frontend/src/api/xxx.js`

### Q3: 页面访问白屏？

1. 检查路由是否正确配置
2. 检查组件文件是否存在
3. 查看浏览器控制台错误
4. 确认前端已构建 `pnpm build`

### Q4: API 返回 401？

1. 检查是否已登录
2. 检查 Token 是否过期
3. 确认接口权限要求

### Q5: 如何测试 API？

```bash
# 获取 Token
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "xxx"}'

# 使用 Token
curl http://localhost:5000/api/v1/users \
  -H "Authorization: Bearer <token>"
```

---

## 八、快速定位

| 需求 | 文件位置 |
|------|----------|
| 修改路由 | `frontend/src/router/index.js` |
| 添加菜单 | `backend/app/api/menu.py` |
| 修改布局 | `frontend/src/layouts/MainLayout.vue` |
| 公共组件 | `frontend/src/components/` |
| API 封装 | `frontend/src/api/index.js` |
| 后端入口 | `backend/app/main.py` |
| 数据库模型 | `backend/app/models/` |
| 业务服务 | `backend/app/services/` |
| 启动自检 | `backend/app/startup_check.py` |

---

*文档版本：v1.0*
*最后更新：2025-03*
