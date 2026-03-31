# AGENTS.md - 项目导航与开发指南

> 本文档帮助 AI 快速理解项目全貌、定位代码、遵循规范。
> 
> **⚠️ AI 开发前必读此文件！**

---

## 一、项目概览

### 1.1 基本信息

| 项目 | 说明 |
|------|------|
| **名称** | OpsCenter - 一站式运维管理平台 |
| **技术栈** | Vue 3 + Vite + Element Plus / Python 3.11 + FastAPI + SQLAlchemy |
| **数据库** | PostgreSQL (元数据) + MySQL/PostgreSQL/Redis (监控实例) |
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
│   └── requirements.txt
│
├── frontend/                   # 前端代码
│   ├── src/
│   │   ├── api/               # API 封装
│   │   ├── components/        # 公共组件
│   │   ├── layouts/           # 布局组件
│   │   ├── router/            # 路由配置
│   │   ├── stores/            # Pinia 状态
│   │   └── views/             # 页面组件 (31个)
│   └── package.json
│
├── .vibecoding/               # 协作文档
│   ├── specs/                 # 功能规格 (16个)
│   └── VIBECODING.md          # 协作经验
│
├── .coze                      # 项目配置
└── AGENTS.md                  # 本文件
```

---

## 三、功能模块索引

### 3.1 核心模块

| 模块 | 前端 | 后端 API | 规格 |
|------|------|----------|------|
| 认证与权限 | `views/login/` | `api/auth.py` | [SPEC-001](.vibecoding/specs/001-认证与权限.md) |
| 实例管理 | `views/instances/` | `api/instances.py`, `rdb_instances.py`, `redis_instances.py` | [SPEC-002](.vibecoding/specs/002-实例管理.md) |
| 环境管理 | `views/environments/` | `api/environments.py` | [SPEC-003](.vibecoding/specs/003-环境管理.md) |
| SQL 编辑器 | `views/sql-editor/` | `api/sql.py` | [SPEC-004](.vibecoding/specs/004-SQL编辑器.md) |
| 变更审批 | `views/change/` | `api/approval.py` | [SPEC-005](.vibecoding/specs/005-变更审批.md) |
| 监控中心 | `views/monitor/` | `api/monitor.py`, `monitor_ext.py` | [SPEC-006](.vibecoding/specs/006-监控中心.md) |
| Redis 管理 | `views/instances/redis-detail.vue` | `api/redis.py` | [SPEC-007](.vibecoding/specs/007-Redis管理.md) |
| 消息通知 | `views/notification/` | `api/notification.py` | [SPEC-008](.vibecoding/specs/008-消息通知.md) |
| 脚本管理 | `views/scripts/` | `api/scripts.py` | [SPEC-009](.vibecoding/specs/009-脚本管理.md) |
| 定时任务 | `views/scheduled-tasks/` | `api/scheduled_tasks.py` | [SPEC-010](.vibecoding/specs/010-定时任务.md) |
| 审计日志 | `views/audit/` | `api/audit.py` | [SPEC-011](.vibecoding/specs/011-审计日志.md) |
| 系统配置 | `views/system/` | `api/system.py` | [SPEC-012](.vibecoding/specs/012-系统配置.md) |
| 巡检报告 | `views/inspection/` | `api/inspection.py` | [SPEC-013](.vibecoding/specs/013-巡检报告.md) |
| SQL 优化器 | `views/sql-optimizer/` | `api/sql_optimizer.py` | [SPEC-014](.vibecoding/specs/014-SQL优化器.md) |
| 权限管理 | `views/permissions/` | `api/permissions.py` | [SPEC-015](.vibecoding/specs/015-权限管理.md) |

### 3.2 新增功能

| 功能 | 前端 | 说明 |
|------|------|------|
| **SQL 优化闭环** | `views/monitor/slow-query/` | 慢查询列表、优化建议、采集任务、分析历史 |
| **告警规则** | `views/alerts/rules/` | 规则配置、通知关联 |
| **定时巡检** | `views/inspection/scheduled/` | 定时任务、自动报告 |
| **变更窗口** | `views/change/windows/` | 窗口定义、全局策略、紧急变更支持 |

---

## 四、路由配置

### 4.1 路由规则

| 场景 | 规则 | 示例 |
|------|------|------|
| 单页面 | 一级路由 | `/users`, `/notification` |
| 多个相关页面 | 嵌套路由 | `/monitor/performance`, `/monitor/slow-query` |

### 4.2 路由结构

```
/                              # 主布局
├── /dashboard                 # 仪表盘
├── /instances                 # 实例管理
├── /instances/:id             # 实例详情 (动态路由)
├── /environments              # 环境管理
├── /sql-editor                # SQL 编辑器
├── /sql-optimizer             # SQL 优化器
├── /change/                   # 变更管理
│   ├── /change/requests       # DB 变更
│   ├── /change/redis-requests # Redis 变更
│   └── /change/windows        # 变更窗口
├── /monitor/                  # 监控中心
│   ├── /monitor/performance   # 性能监控
│   ├── /monitor/slow-query    # 慢查询监控
│   ├── /monitor/alerts        # 告警中心
│   ├── /monitor/replication   # 主从复制
│   ├── /monitor/locks         # 事务与锁
│   ├── /monitor/inspection    # 巡检报告
│   └── /monitor/alert-rules   # 告警规则
├── /scripts                   # 脚本管理
├── /scheduled-tasks           # 定时任务
├── /users                     # 用户管理
├── /permissions               # 权限管理
├── /audit                     # 审计日志
├── /system                    # 系统设置
└── /notification              # 通知管理
```

### 4.3 路由守卫

```
启动检查 → 未初始化 → /init
         → 已初始化 → 未登录 → /login
                    → 已登录 → 权限检查 → 无权限 → /dashboard
                                      → 有权限 → 目标页面
```

---

## 五、开发规范

### 5.1 前端开发

#### 组件规范

```vue
<script setup>
import { ref, onMounted } from 'vue'
import request from '@/api/index'
import { ElMessage } from 'element-plus'

const loading = ref(false)
const dataList = ref([])

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

onMounted(() => fetchData())
</script>
```

#### 表格操作列

统一使用 `TableActions` 组件：

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

#### 新增菜单

修改三处：
1. 后端 `backend/app/api/menu.py` - 菜单初始化数据
2. 前端 `frontend/src/router/index.js` - 路由配置
3. 调用 `/api/v1/menu/add-missing` API

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
    return db.query(Item).all()

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_item(
    data: ItemCreate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    item = Item(**data.model_dump())
    db.add(item)
    db.commit()
    return {"id": item.id}
```

#### 新增 API

1. 创建路由文件 `backend/app/api/xxx.py`
2. 在 `main.py` 中注册路由
3. 创建 Schema `backend/app/schemas/xxx.py`
4. 前端封装 API `frontend/src/api/xxx.js`

### 5.3 启动自检

服务启动时自动执行：
- Python 版本 (>= 3.11)
- 依赖包 (FastAPI, SQLAlchemy, Pydantic 等 18 个)
- Pydantic 版本兼容性
- 数据库配置
- 前端构建产物

---

## 六、权限模型

| 角色 | 权限范围 |
|------|----------|
| `super_admin` | 超级管理员，全部权限 |
| `approval_admin` | 审批管理员，审批+执行 |
| `operator` | 运维人员，执行操作 |
| `developer` | 开发人员，查看+申请 |

---

## 七、API 端点索引

| 模块 | 端点 | 说明 |
|------|------|------|
| 认证 | `/api/v1/auth/login` | 登录 |
| 实例 | `/api/v1/instances`, `/api/v1/rdb-instances`, `/api/v1/redis-instances` | 实例管理 |
| SQL | `/api/v1/sql/execute`, `/api/v1/sql/validate` | SQL 执行 |
| 监控 | `/api/v1/monitor/performance/{id}`, `/api/v1/slow-queries/{id}` | 性能监控 |
| 告警 | `/api/v1/alerts`, `/api/v1/alert-rules` | 告警管理 |
| 优化 | `/api/v1/sql-optimization/tasks`, `/api/v1/sql-optimization/suggestions` | SQL 优化闭环 |

---

## 八、常见问题

### Q1: 如何添加新页面？
1. 创建页面组件 `frontend/src/views/xxx/index.vue`
2. 添加路由配置 `frontend/src/router/index.js`
3. 添加菜单配置 `backend/app/api/menu.py`
4. 调用 `/api/v1/menu/add-missing` 同步菜单

### Q2: 如何添加新 API？
1. 创建路由文件 `backend/app/api/xxx.py`
2. 在 `main.py` 中注册路由
3. 创建 Schema
4. 前端封装 API

### Q3: 页面访问白屏？
1. 检查路由是否正确配置
2. 检查组件文件是否存在
3. 查看浏览器控制台错误
4. 确认前端已构建 `pnpm build`

### Q4: API 返回 401？
1. 检查是否已登录
2. 检查 Token 是否过期
3. 确认接口权限要求

### Q5: 前端修改后页面没变化？
- Vite 支持热更新，保存后自动刷新
- 检查浏览器控制台是否有报错

---

## 九、快速定位

| 需求 | 文件位置 |
|------|----------|
| 修改路由 | `frontend/src/router/index.js` |
| 添加菜单 | `backend/app/api/menu.py` |
| 修改布局 | `frontend/src/layouts/MainLayout.vue` |
| 公共组件 | `frontend/src/components/` |
| API 封装 | `frontend/src/api/index.js` |
| 后端入口 | `backend/app/main.py` |
| 数据库模型 | `backend/app/models/` |
| 日志文件 | `/app/work/logs/bypass/app.log` |

### 常用命令

```bash
# 查看服务状态
curl -I http://localhost:5000

# 查看日志
tail -n 50 /app/work/logs/bypass/app.log

# 前端构建
cd frontend && pnpm build
```

---

## 十、避坑指南

| 场景 | ❌ 错误 | ✅ 正确 |
|------|---------|---------|
| 端口检测 | `lsof -i:5000` | `curl -I http://localhost:5000` |
| 文件下载 | `<a href=url download>` | `fetch + blob + createObjectURL` |
| 读取文件 | `cat file.txt` | `read_file` 工具 |
| 搜索内容 | `grep "xxx" file` | `grep_file` 工具 |
| 修改文件 | 直接 write_file 覆盖 | 先 read_file 再 edit_file |
| 需求理解 | 猜测用户意图 | 先确认，再开发 |
| 服务重启 | 每次改代码都重启 | 利用热更新 |

---

*文档版本：v3.0*
*最后更新：2025-03*
