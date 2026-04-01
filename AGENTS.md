# AGENTS.md - 项目导航与开发指南

> **⚠️ AI 开发前必读此文件！**
> 
> 本文档包含项目全貌、开发规范、检查清单和经验教训。

---

## 零、开发必读

### 核心原则

| 原则 | 说明 |
|------|------|
| **先读后做** | 开发前必须先读取本文档 |
| **先确认后开发** | 不确定的需求，先确认再动手 |
| **不擅自扩展** | 用户说什么做什么，不猜测不扩展 |
| **改完要验证** | 让用户验证效果，不自己认为完成 |
| **经验要沉淀** | 踩坑/学到的经验，记录到本文档 |

### 开发前检查清单

```
□ 读取本文档了解项目结构
□ 读取相关规格文件（.vibecoding/specs/xxx.md）
□ 确认需求范围，不擅自扩展
□ 检查现有代码，避免重复造轮子
□ 列出将要修改的文件清单
```

### 开发后检查清单

```
□ 确认改动范围与需求一致
□ 没有引入硬编码
□ 没有遗漏 import 语句
□ 没有残留的废弃代码（注释、未使用的变量、已移除功能的引用）
□ 让用户验证效果
```

### 代码整洁规范

> ⚠️ **重要**: 代码整洁是长期可维护性的基础，必须养成习惯！

#### 移除功能时的清理清单

```
□ 删除模型字段 → 同步删除 Schema 中的字段
□ 删除模型字段 → 同步删除 API 中的引用
□ 删除功能 → 删除相关注释和文档说明
□ 删除功能 → 删除测试用例（或标记跳过）
□ 检查是否有其他文件引用了被删除的内容
```

#### 残留代码的危害

```
1. 编译/运行时报错
   - 例：删除字段后，代码仍在赋值该字段

2. 误导后续开发者
   - 例：注释提到已移除的功能，让人误以为还存在

3. 增加代码理解成本
   - 例：未使用的 import、注释掉的代码块
```

#### 检查残留代码的方法

```bash
# 1. 搜索已删除字段/函数名
grep -r "deleted_field" backend/

# 2. 检查未使用的 import
# Python: 使用 ruff 或 pylint
ruff check --select F401

# 3. IDE 警告
# 信任 IDE 的 "unused variable" 警告
```

#### 本次案例：MenuConfig.roles 字段残留

```
问题：roles 字段已从模型和 Schema 中移除，但以下位置仍有残留：
- menu.py 第 167 行：roles=menu_data.roles（会报错）
- menu.py 第 4-7 行：注释中提到 roles 过滤（误导）

教训：移除字段时要全局搜索，确保彻底清理
```

### 验收模板

开发完成后，按以下格式向用户确认：

```markdown
## 完成内容

1. 修改文件：
   - frontend/src/xxx.vue - 改动说明
   - backend/app/api/xxx.py - 改动说明

2. 验收要点：
   - [ ] 功能点1
   - [ ] 功能点2

3. 请验证：
   - 刷新页面查看 xxx 功能
   - 测试 xxx 场景
```

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

### 1.3 架构特点

```
⚠️ 数据库驱动设计 - 重要！

菜单配置 → menu_configs 表 (不是前端硬编码)
权限配置 → permissions 表 + role_permissions 表
系统配置 → system_configs 表

特点：前端不硬编码配置，全部从数据库动态加载
```

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
│   │   ├── api/               # API 封装 (baseURL 已包含 /api/v1)
│   │   ├── components/        # 公共组件
│   │   ├── layouts/           # 布局组件
│   │   ├── router/            # 路由配置
│   │   ├── stores/            # Pinia 状态
│   │   └── views/             # 页面组件 (30个)
│   └── package.json
│
├── .vibecoding/               # 协作文档
│   ├── specs/                 # 功能规格 (16个)
│   └── template.md            # 规格模板
│
├── .coze                      # 项目配置
└── AGENTS.md                  # 本文件
```

---

## 三、功能模块索引

| 模块 | 前端 | 后端 API | 规格 |
|------|------|----------|------|
| 认证与权限 | `views/login/` | `api/auth.py` | [SPEC-001](.vibecoding/specs/001-认证与权限.md) |
| 实例管理 | `views/instances/` | `api/instances.py` | [SPEC-002](.vibecoding/specs/002-实例管理.md) |
| 环境管理 | `views/environments/` | `api/environments.py` | [SPEC-003](.vibecoding/specs/003-环境管理.md) |
| SQL 编辑器 | `views/sql-editor/` | `api/sql.py` | [SPEC-004](.vibecoding/specs/004-SQL编辑器.md) |
| 变更审批 | `views/change/` | `api/approval.py` | [SPEC-005](.vibecoding/specs/005-变更审批.md) |
| 监控中心 | `views/monitor/` | `api/monitor.py` | [SPEC-006](.vibecoding/specs/006-监控中心.md) |
| Redis 管理 | `views/instances/redis-detail.vue` | `api/redis.py` | [SPEC-007](.vibecoding/specs/007-Redis管理.md) |
| 消息通知 | `views/notification/` | `api/notification_channels.py`, `api/notification_rules.py` | [SPEC-008](.vibecoding/specs/008-消息通知-重新设计.md) |
| 脚本管理 | `views/scripts/` | `api/scripts.py` | [SPEC-009](.vibecoding/specs/009-脚本管理.md) |
| 定时任务 | `views/scheduled-tasks/` | `api/scheduled_tasks.py` | [SPEC-010](.vibecoding/specs/010-定时任务.md) |
| 审计日志 | `views/audit/` | `api/audit.py` | [SPEC-011](.vibecoding/specs/011-审计日志.md) |
| 系统配置 | `views/system/` | `api/system.py` | [SPEC-012](.vibecoding/specs/012-系统配置.md) |
| 巡检报告 | `views/inspection/` | `api/inspection.py` | [SPEC-013](.vibecoding/specs/013-巡检报告.md) |
| SQL 优化器 | `views/sql-optimizer/` | `api/sql_optimizer.py` | [SPEC-014](.vibecoding/specs/014-SQL优化器.md) |
| 权限管理 | `views/permissions/` | `api/permissions.py` | [SPEC-015](.vibecoding/specs/015-权限管理.md) |

---

## 四、特定场景 Checklist

### 新增菜单 (三步骤，缺一不可)

```
□ 数据库配置
  - INSERT INTO menu_configs (name, path, icon, ...) VALUES (...);
  - 或调用 POST /api/v1/menu/add-missing

□ 前端路由配置
  - 在 router/index.js 中添加路由

□ 验证菜单显示
  - 登录系统，检查导航栏
```

### 新增 API

```
□ 创建路由文件 backend/app/api/xxx.py
□ 在 main.py 中注册路由
□ 创建 Schema backend/app/schemas/xxx.py
□ 前端封装 API frontend/src/api/xxx.js
□ 注意：前端调用时不要重复 /api/v1 前缀
```

### 新增数据库字段

```
□ 更新 SQLAlchemy 模型
□ 更新 Pydantic Schema
□ 考虑数据迁移（已有数据的默认值）
```

### 新增完整功能

```
后端：
□ 数据模型 (models/)
□ API接口 (api/)
□ 数据库迁移/初始化数据
□ 菜单配置 (menu_configs表)
□ 权限配置 (permissions表)

前端：
□ 路由配置 (router/index.js)
□ 页面组件 (views/)
□ API封装 (api/)

验证：
□ 功能测试
□ 菜单显示
□ 权限控制
```

---

## 五、开发规范

### 5.1 前端开发

#### 代码风格

| 类型 | 规范 |
|------|------|
| 框架 | Vue 3 组合式 API，`<script setup>` |
| 表格操作列 | 统一使用 `TableActions` 组件 |
| 筛选区域 | 使用 `el-form inline` 布局 |
| 格式化 | Ruff 格式化，行宽 120 |

#### 组件模板

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
    // 注意：request 的 baseURL 已包含 /api/v1，不要再加前缀
    dataList.value = await request.get('/xxx')
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

#### API 模板

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

### 5.3 路由配置规则

| 场景 | 规则 | 示例 |
|------|------|------|
| 单页面 | 一级路由 | `/users`, `/notification` |
| 多个相关页面 | 嵌套路由 | `/monitor/performance`, `/monitor/slow-query` |

---

## 六、权限模型

| 角色 | 权限范围 |
|------|----------|
| `super_admin` | 超级管理员，全部权限 |
| `approval_admin` | 审批管理员，审批+执行 |
| `operator` | 运维人员，执行操作 |
| `developer` | 开发人员，查看+申请 |

---

## 七、常见问题

### Q1: 如何添加新页面？
1. 创建页面组件 `frontend/src/views/xxx/index.vue`
2. 添加路由配置 `frontend/src/router/index.js`
3. **添加菜单配置** `menu_configs 表` ⬅️ 容易遗漏
4. 调用 `/api/v1/menu/add-missing` 同步菜单

### Q2: API 返回 404？
1. 检查后端路由是否注册
2. **检查前端调用是否重复了 /api/v1 前缀** ⬅️ 常见错误
3. 查看浏览器 Network 面板确认实际请求路径

### Q3: 页面访问白屏？
1. 检查路由是否正确配置
2. 检查组件文件是否存在
3. 查看浏览器控制台错误

### Q4: 菜单不显示？
1. **检查数据库 menu_configs 表是否有记录** ⬅️ 最常见
2. 检查前端路由是否配置
3. 调用 `/api/v1/menu/add-missing` 同步

---

## 八、避坑指南

| 场景 | ❌ 错误 | ✅ 正确 |
|------|---------|---------|
| 端口检测 | `lsof -i:5000` | `curl -I http://localhost:5000` |
| 文件下载 | `<a href=url download>` | `fetch + blob + createObjectURL` |
| 读取文件 | `cat file.txt` | `read_file` 工具 |
| 搜索内容 | `grep "xxx" file` | `grep_file` 工具 |
| 修改文件 | 直接 write_file 覆盖 | 先 read_file 再 edit_file |
| 需求理解 | 猜测用户意图 | 先确认，再开发 |
| 服务重启 | 每次改代码都重启 | 利用热更新 |
| API调用 | `request.get('/api/v1/xxx')` | `request.get('/xxx')` |
| 新增菜单 | 只配置前端路由 | 数据库 + 前端双端配置 |

---

## 九、经验教训

> ⚠️ **重要**: 以下案例来自实际开发中的踩坑经历，务必引以为戒！

### 案例1: 菜单不显示问题 (2026-04)

**问题现象**: 新增功能后，前端路由配置正确，页面可以访问，但导航栏菜单不显示。

**根本原因**: 只修改了前端路由，未配置数据库菜单。项目采用**数据库驱动菜单**架构。

**正确流程**:
```
1. 数据库配置: INSERT INTO menu_configs ...
2. 前端路由: router/index.js
3. 验证: 登录系统检查导航栏
```

**关键教训**:
- 开发前必读本文档
- 理解项目架构（数据库驱动）
- 完整验证全流程

### 案例2: API路径重复导致404 (2026-04)

**问题现象**: 前端调用 API 返回 404，但后端接口存在。

**根本原因**: `request` 的 baseURL 已包含 `/api/v1`，代码又手动拼接。

```javascript
// ❌ 错误：实际请求 /api/v1/api/v1/xxx
const res = await request.get('/api/v1/notification/channels')

// ✅ 正确：实际请求 /api/v1/notification/channels
const res = await request.get('/notification/channels')
```

**关键教训**: 使用 API 前先了解 baseURL 配置

### 案例3: 通知系统重构 (2026-04)

**问题现象**: 通知配置页面 500 错误，数据库表结构与模型定义不一致。

**根本原因**: 原通知系统设计不合理，静默规则和频率限制未关联到通道，导致规则无法精确控制。

**重构方案**:
```
旧设计:
- silence_rules (全局规则)
- rate_limits (全局规则)

新设计:
- notification_channels (通道管理)
  ├── channel_silence_rules (通道级静默规则)
  └── channel_rate_limits (通道级频率限制)
```

**关键变更**:
1. 新增表: `notification_channels`, `channel_silence_rules`, `channel_rate_limits`
2. 新增 API: `/api/v1/notification/channels`, `/api/v1/notification/channels/{id}/silence-rules`
3. 新增前端: `views/notification/channels.vue` (统一管理页面)
4. 迁移脚本: `migrations/migrate.py` (migration_007)

**关键教训**:
- 系统设计要考虑关联性，规则应绑定到具体通道
- 重构时要保留数据迁移能力
- 新旧系统并存期间要做好兼容处理

---

## 十、快速定位

| 需求 | 文件位置 |
|------|----------|
| 修改路由 | `frontend/src/router/index.js` |
| 添加菜单 | `menu_configs 表` 或 `/api/v1/menu/add-missing` |
| 修改布局 | `frontend/src/layouts/MainLayout.vue` |
| 公共组件 | `frontend/src/components/` |
| API 封装 | `frontend/src/api/index.js` (baseURL 在此定义) |
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

*文档版本：v4.0*
*最后更新：2026-04*
