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
| **数据库** | **生产环境: Amazon RDS + Amazon ElastiCache** / 开发环境: 内置 PostgreSQL + Redis |
| **部署方式** | Kubernetes (生产) / Docker Compose (开发) |
| **端口** | 后端 5000 / 前端开发 3000 |
| **环境变量** | `DEPLOY_RUN_PORT=5000`, `COZE_PROJECT_DOMAIN_DEFAULT` |

### 1.2 部署架构

```
⚠️ 生产环境架构（云原生） - 重要！

Kubernetes 集群
├── opscenter-backend (Deployment + HPA + PDB)
├── opscenter-frontend (Deployment + HPA)
└── 外部依赖（AWS 托管服务）
    ├── Amazon RDS PostgreSQL（元数据库，必需）
    └── Amazon ElastiCache Redis（缓存，可选）

特点：
- 使用 Kubernetes 原生资源（Deployment、HPA、PDB）
- 支持弹性伸缩、滚动更新、自我修复
- 使用 AWS 托管服务（RDS + 可选的 ElastiCache）提供高可用数据库
- 不再部署内置数据库（PostgreSQL/Redis StatefulSet）
- Redis 可选配置，不配置时禁用缓存功能

### 1.3 核心能力

- **数据库管理**: MySQL/PostgreSQL/Redis 多实例管理
- **SQL 工具**: SQL 编辑器、SQL 优化器、慢查询分析
- **变更管理**: DDL/DML 变更审批、变更窗口管理
- **监控告警**: 性能监控、慢查询监控、告警规则
- **自动化**: 脚本管理、定时任务、定时巡检
- **权限管理**: RBAC 权限模型、环境权限隔离

### 1.4 架构特点

```
⚠️ 数据库驱动设计 - 重要！

菜单配置 → menu_configs 表 (不是前端硬编码)
权限配置 → permissions 表 + role_permissions 表
系统配置 → system_configs 表

特点：前端不硬编码配置，全部从数据库动态加载
```

---

## 云原生部署（生产环境）

**⚠️ 重要**: 所有部署相关文件已统一移至 `release/` 目录，项目根目录更清晰。

### release/ 目录结构

```
release/
├── k8s/              # Kubernetes 部署清单（生产环境）
│   ├── 00-namespace.yaml
│   ├── 01-configmap.yaml
│   ├── 02-secret.yaml
│   ├── 03-backend-deployment.yaml
│   ├── 04-backend-service.yaml
│   ├── 05-frontend-deployment.yaml
│   ├── 06-frontend-service.yaml
│   └── 09-rbac.yaml
├── helm/opscenter/   # Helm Chart
├── docs/             # 部署文档
│   ├── KUBERNETES_DEPLOYMENT.md
│   ├── KUBERNETES.md
│   └── MIGRATION_GUIDE.md
├── docker/           # Docker 配置
│   ├── entrypoint.sh
│   └── nginx.conf
├── Dockerfile        # Docker 镜像构建文件
├── docker-compose.yml # Docker Compose 配置（开发环境）
├── deploy-k8s.sh     # Kubernetes 部署脚本
└── README.md         # 部署说明
```

### 快速开始

```bash
# 进入 release 目录
cd release

# 使用部署脚本
./deploy-k8s.sh

# 或查看部署文档
cat docs/KUBERNETES.md
```

### 部署架构

OpsCenter 支持云原生部署，使用 Kubernetes 和 AWS 托管服务。

**架构图**:
```
Kubernetes Cluster
├── Namespace: opscenter
│   ├── Deployment: opscenter-backend (3 replicas)
│   ├── Deployment: opscenter-frontend (2 replicas)
│   ├── Service: opscenter-backend-service
│   ├── Service: opscenter-frontend-service
│   ├── HPA: opscenter-backend-hpa
│   ├── HPA: opscenter-frontend-hpa
│   ├── PDB: opscenter-backend-pdb
│   └── Ingress: opscenter-ingress
│
└── External (AWS)
    ├── Amazon RDS PostgreSQL (Multi-AZ) - 必需
    └── Amazon ElastiCache Redis (Replication) - 可选
```

### 部署清单

| 文件 | 说明 |
|------|------|
| `k8s/00-namespace.yaml` | 命名空间配置 |
| `k8s/01-configmap.yaml` | 应用配置（包含 AWS RDS/ElastiCache endpoint） |
| `k8s/02-secret.yaml` | 敏感配置（包含数据库密码） |
| `k8s/03-backend-deployment.yaml` | 后端部署配置 |
| `k8s/04-backend-service.yaml` | 后端服务 + HPA + PDB |
| `k8s/05-frontend-deployment.yaml` | 前端部署配置 |
| `k8s/06-frontend-service.yaml` | 前端服务 + Ingress |
| `k8s/09-rbac.yaml` | RBAC 权限配置 |

**注意**:
- 已移除内置数据库部署清单（`07-postgresql.yaml`, `08-redis.yaml`）
- 生产环境强制使用 AWS RDS PostgreSQL
- Amazon ElastiCache Redis 为可选组件，不配置时禁用缓存功能

### 部署步骤

```bash
# 1. 创建 AWS RDS PostgreSQL（必需）和 ElastiCache Redis（可选）
#    （详见 MIGRATION_GUIDE.md）

# 2. 更新配置
vim k8s/01-configmap.yaml  # 配置 AWS endpoint（必需 RDS，可选 Redis）
vim k8s/02-secret.yaml     # 配置密码（RDS 必需，Redis 可选）

# 3. 部署应用
./deploy-k8s.sh

# 4. 验证部署
kubectl get pods -n opscenter
kubectl get services -n opscenter
```

### 云原生特性

| 特性 | 实现方式 | 说明 |
|------|---------|------|
| **弹性伸缩** | HPA | 基于 CPU/内存使用率自动扩缩容 |
| **滚动更新** | Deployment | 零停机更新应用 |
| **自我修复** | Liveness Probe + Readiness Probe | 自动重启不健康的 Pod |
| **高可用** | PDB + Multi-AZ RDS | 确保最小可用副本 |
| **负载均衡** | Service + Ingress | 自动分配流量 |
| **服务发现** | Kubernetes DNS | 内部服务自动发现 |

### Helm Chart

提供 Helm Chart 简化部署管理:

```bash
helm install opscenter ./helm/opscenter \
  --namespace opscenter \
  --create-namespace \
  --set postgresql.enabled=false \
  --set redis.enabled=false \
  --set config.aws.rds.endpoint="your-rds-endpoint" \
  --set config.aws.redis.endpoint="your-redis-endpoint"
```

**详细文档**: 见 `KUBERNETES_DEPLOYMENT.md`

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
├── release/                   # 部署相关文件
│   ├── k8s/                   # Kubernetes 部署清单（生产环境）
│   │   ├── 00-namespace.yaml  # 命名空间配置
│   │   ├── 01-configmap.yaml  # 应用配置
│   │   ├── 02-secret.yaml     # 敏感配置
│   │   ├── 03-backend-deployment.yaml
│   │   ├── 04-backend-service.yaml
│   │   ├── 05-frontend-deployment.yaml
│   │   ├── 06-frontend-service.yaml
│   │   └── 09-rbac.yaml
│   ├── helm/opscenter/        # Helm Chart
│   ├── docs/                  # 部署文档
│   │   ├── KUBERNETES_DEPLOYMENT.md  # 详细部署文档
│   │   ├── KUBERNETES.md             # 快速部署指南
│   │   └── MIGRATION_GUIDE.md        # AWS 托管服务迁移指南
│   ├── docker/                # Docker 配置
│   │   ├── entrypoint.sh      # 容器启动脚本
│   │   └── nginx.conf         # Nginx 配置
│   ├── Dockerfile             # Docker 镜像构建文件
│   ├── docker-compose.yml     # Docker Compose 配置（开发环境）
│   ├── deploy-k8s.sh          # Kubernetes 部署脚本
│   └── README.md              # 部署说明
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
| AI 模型配置 | `views/system/ai-models.vue` | `api/ai_models.py` | [SPEC-017](.vibecoding/specs/017-AI模型配置.md) |

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

## 九、AI 助手工作指南

> ⚠️ **重要**: 以下内容帮助 AI 助手更好地理解项目、避免常见错误！

### 9.1 自我介绍

每次开始工作时，请先说明：
```
我是你的通用网页搭建专家，已阅读项目 AGENTS.md 文档。
```

### 9.2 AI 助手常见错误模式总结

> 不同 AI 模型有不同的行为特点，以下总结本项目踩过的坑，供后续参考。

#### 错误类型 A：需求理解偏差

| 表现 | 根因 | 解决方案 |
|------|------|----------|
| 擅自扩展需求 | 想要"做得更多" | 用户说什么做什么，不猜测不扩展 |
| 遗漏隐含步骤 | 只看了表面需求 | 对照 Checklist 确认完整流程 |
| 误解优先级 | 没有确认重点 | 先问"最紧急的是什么" |

**本项目案例**: 新增菜单功能时，只配置了前端路由，遗漏了数据库配置。

#### 错误类型 B：架构理解不足

| 表现 | 根因 | 解决方案 |
|------|------|----------|
| 硬编码配置 | 不知道项目用数据库驱动 | 先读 AGENTS.md 了解架构 |
| 路径重复拼接 | 不了解 baseURL 配置 | 使用 API 前先检查封装层 |
| 跨文件引用错误 | 不了解模块依赖关系 | 修改前搜索相关引用 |

**本项目案例**: API 调用重复 `/api/v1` 前缀，导致 404。

#### 错误类型 C：代码质量疏忽

| 表现 | 根因 | 解决方案 |
|------|------|----------|
| 残留废弃代码 | 删除不彻底 | 全局搜索确认清理干净 |
| 遗漏 import | 添加代码但忘记导入 | 改完检查 import 语句 |
| 类型不匹配 | Schema 与 Model 不一致 | 改模型时同步改 Schema |

**本项目案例**: MenuConfig.roles 字段删除后，代码中仍有引用。

#### 错误类型 D：验证不充分

| 表现 | 根因 | 解决方案 |
|------|------|----------|
| 未测试就交付 | 认为"应该没问题" | 改完必须验证，让用户确认 |
| 只测正常路径 | 忽略边界情况 | 考虑空值、异常、权限等场景 |
| 没看日志 | 不知道运行时错误 | 交付前检查日志有无报错 |

**本项目案例**: 菜单 created_at 为 NULL 导致接口 500 错误。

### 9.3 提效建议

根据本项目实践经验，以下做法能显著提高效率：

#### 高效做法 ✅

```
1. 开发前先读 AGENTS.md - 了解架构和规范
2. 列出修改清单 - 明确要改哪些文件
3. 复用现有组件 - 不重复造轮子
4. 小步提交 - 每个功能点独立验证
5. 善用搜索 - grep_file 找引用，glob_file 找文件
6. 看日志排错 - tail 日志定位问题
```

#### 低效做法 ❌

```
1. 不读文档直接开发 - 返工率高
2. 盲目写新组件 - 忽略已有组件
3. 大改动一次提交 - 出错难以定位
4. 只改代码不看日志 - 问题遗留到测试阶段
5. 手动 cat/grep 大量文件 - 效率低，应用专用工具
```

### 9.4 关键提醒

```
⚠️ 本项目特殊点（容易踩坑）：

1. 菜单配置在数据库，不是前端硬编码
2. 前端 API baseURL 已包含 /api/v1
3. 权限码在 permissions 表，需要与菜单关联
4. 环境变量通过 process.env 获取，禁止硬编码
5. 数据库字段删除时要同步清理 Schema 和引用
```

---

## 十、经验教训

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

## 十一、架构设计与优化

> **⚠️ 重要**: 本章节分析系统当前架构设计，识别不符合设计原则的地方，并提供优化方案。

### 11.1 开闭原则（Open-Closed Principle）分析

**开闭原则定义**：软件实体（类、模块、函数等）应该对扩展开放，对修改关闭。即在不修改现有代码的情况下，通过扩展来增加新功能。

#### 11.1.1 当前系统开闭原则评估

| 模块 | 符合程度 | 说明 |
|------|----------|------|
| **数据库连接管理** | ❌ 部分符合 | 有 `DatabaseConnectionManager`，但 MySQL/PostgreSQL/Redis 没有统一接口 |
| **通知渠道** | ⚠️ 基本符合 | 有统一模型，但发送逻辑没有适配器抽象 |
| **权限管理** | ✅ 符合 | 基于 RBAC 模型，权限配置在数据库，扩展性好 |
| **菜单系统** | ✅ 符合 | 数据库驱动菜单，新增菜单无需修改代码 |
| **实例管理** | ❌ 不符合 | RDB 和 Redis 实例分开管理，没有统一接口 |

#### 11.1.2 不符合开闭原则的具体问题

##### 问题1: 数据源连接缺乏统一抽象

**现状**：
- MySQL/PostgreSQL 由 `DatabaseConnectionManager` 管理
- Redis 由 `RedisClient` 管理
- 新增数据源（如 MongoDB、Elasticsearch）需要修改核心代码

**影响**：
```python
# 当前实现：新增数据源需修改 DatabaseConnectionManager
class DatabaseConnectionManager:
    def _create_mysql_pool(self, instance):
        # MySQL 逻辑
        pass
    
    def _create_postgresql_pool(self, instance):
        # PostgreSQL 逻辑
        pass
    
    # ❌ 新增 MongoDB 需要在这里添加方法
    def _create_mongodb_pool(self, instance):
        pass
```

**违反原则**：对修改开放（需修改此类），对扩展关闭（不能外部注册）

##### 问题2: 通知渠道发送逻辑分散

**现状**：
- 支持 5 种通道：钉钉、企业微信、飞书、邮件、Webhook
- 发送逻辑分散在 `notification.py` 的不同方法中
- 新增通道需要修改多处代码

**影响**：
```python
# 当前实现：每种通道的发送逻辑是独立的
async def send_dingtalk_message(webhook, message, auth_type, secret, keywords):
    # 钉钉特定逻辑
    pass

async def send_wechat_message(webhook, message):
    # 企业微信特定逻辑
    pass

# ❌ 新增 Slack 需要添加新方法并修改调用方
async def send_slack_message(webhook, message):
    pass
```

**违反原则**：对修改开放（需添加新方法），对扩展关闭（不能外部注册）

##### 问题3: 实例管理类型耦合

**现状**：
- `RDBInstance` 和 `RedisInstance` 分开管理
- 前端路由、API、服务都分别处理
- 新增实例类型（如 MongoDB 实例）需要大量修改

**影响**：
- 代码重复（测试连接、监控、操作等功能）
- 维护成本高
- 难以统一管理

#### 11.1.3 优化方案

##### 优化1: 引入数据源适配器模式

**目标**：统一 MySQL/PostgreSQL/Redis/MongoDB 等数据源的连接和操作接口

**实现步骤**：

1. 定义统一接口：
```python
# backend/app/adapters/datasource/base.py
from abc import ABC, abstractmethod

class DataSourceAdapter(ABC):
    @abstractmethod
    def connect(self) -> bool:
        """建立连接"""
        pass
    
    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """执行查询"""
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """获取监控指标"""
        pass
    
    @abstractmethod
    def get_adapter_type(self) -> str:
        """获取适配器类型"""
        pass
```

2. 实现各类型适配器：
```python
# backend/app/adapters/datasource/mysql_adapter.py
class MySQLAdapter(DataSourceAdapter):
    def get_adapter_type(self) -> str:
        return "mysql"

# backend/app/adapters/datasource/redis_adapter.py
class RedisAdapter(DataSourceAdapter):
    def get_adapter_type(self) -> str:
        return "redis"
```

3. 适配器工厂（开闭原则核心）：
```python
# backend/app/adapters/datasource/factory.py
class DataSourceAdapterFactory:
    _adapters = {
        "mysql": MySQLAdapter,
        "postgresql": PostgreSQLAdapter,
        "redis": RedisAdapter,
    }
    
    @classmethod
    def create(cls, adapter_type: str, config: Dict[str, Any]) -> DataSourceAdapter:
        adapter_class = cls._adapters.get(adapter_type)
        if not adapter_class:
            raise ValueError(f"Unsupported adapter type: {adapter_type}")
        return adapter_class(config)
    
    @classmethod
    def register(cls, adapter_type: str, adapter_class: type):
        """✅ 对扩展开放：新增适配器只需注册，无需修改核心代码"""
        cls._adapters[adapter_type] = adapter_class
```

4. 使用示例：
```python
# 新增 MongoDB 适配器，无需修改核心代码
from backend.app.adapters.datasource.factory import DataSourceAdapterFactory

DataSourceAdapterFactory.register("mongodb", MongoDBAdapter)

# 使用
adapter = DataSourceAdapterFactory.create("mongodb", config={"host": "..."})
adapter.connect()
result = adapter.execute_query("db.collection.find()")
```

**收益**：
- 新增数据源无需修改核心代码（对修改关闭）
- 只需实现适配器并注册（对扩展开放）
- 统一的接口，易于测试和维护

##### 优化2: 引入通知渠道适配器模式

**目标**：统一各通知渠道的发送逻辑

**实现步骤**：

1. 定义统一接口：
```python
# backend/app/adapters/notification/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class NotificationMessage:
    title: str
    content: str
    markdown: bool = True
    extra: Dict[str, Any] = None

@dataclass
class NotificationResult:
    success: bool
    channel_id: int
    channel_type: str
    error_message: str = None

class NotificationAdapter(ABC):
    @abstractmethod
    async def send(self, message: NotificationMessage) -> NotificationResult:
        """发送消息"""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """验证配置"""
        pass
    
    @abstractmethod
    def get_adapter_type(self) -> str:
        """获取适配器类型"""
        pass
```

2. 实现各渠道适配器：
```python
# backend/app/adapters/notification/dingtalk_adapter.py
class DingTalkAdapter(NotificationAdapter):
    def get_adapter_type(self) -> str:
        return "dingtalk"
    
    async def send(self, message: NotificationMessage) -> NotificationResult:
        # 转换为钉钉格式并发送
        pass
```

3. 适配器工厂：
```python
# backend/app/adapters/notification/factory.py
class NotificationAdapterFactory:
    _adapters = {
        "dingtalk": DingTalkAdapter,
        "wechat": WeChatAdapter,
        "feishu": FeishuAdapter,
        "email": EmailAdapter,
        "webhook": WebhookAdapter,
    }
    
    @classmethod
    def register(cls, channel_type: str, adapter_class: type):
        """✅ 对扩展开放：新增渠道只需注册"""
        cls._adapters[channel_type] = adapter_class
```

4. 统一分发器：
```python
# backend/app/services/notification_dispatcher.py
class NotificationDispatcher:
    async def send_to_channel(self, channel_id: int, message: NotificationMessage):
        channel = self.db.query(NotificationChannel).filter(
            NotificationChannel.id == channel_id
        ).first()
        
        # 创建适配器
        adapter = NotificationAdapterFactory.create(
            channel.channel_type,
            channel.config
        )
        
        return await adapter.send(message)
```

**收益**：
- 新增渠道无需修改核心代码（对修改关闭）
- 只需实现适配器并注册（对扩展开放）
- 统一的消息格式和结果处理

##### 优化3: 统一实例管理接口

**目标**：消除 RDB 和 Redis 实例管理的代码重复

**实现步骤**：

1. 定义实例基类：
```python
# backend/app/models/instance_base.py
class InstanceBase(ABC):
    @abstractmethod
    def get_adapter_type(self) -> str:
        """获取实例类型"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """测试连接"""
        pass
```

2. 统一实例服务：
```python
# backend/app/services/instance_service_unified.py
class InstanceServiceUnified:
    def test_instance(self, instance: InstanceBase) -> Dict[str, Any]:
        """统一的实例测试接口"""
        adapter = DataSourceAdapterFactory.create(
            instance.get_adapter_type(),
            instance.to_config()
        )
        return adapter.test_connection()
```

**收益**：
- 消除代码重复
- 统一操作接口
- 易于扩展新实例类型

### 11.2 其他设计优化建议

#### 优化4: 监控指标收集抽象

**问题**：不同数据源的监控指标收集逻辑分散

**方案**：引入 `MetricsCollector` 接口
```python
class MetricsCollector(ABC):
    @abstractmethod
    def collect_metrics(self, instance: InstanceBase) -> Dict[str, Any]:
        """收集监控指标"""
        pass
```

#### 优化5: 脚本执行器抽象

**问题**：SQL 脚本和 Shell 脚本执行逻辑混合

**方案**：引入 `ScriptExecutor` 接口
```python
class ScriptExecutor(ABC):
    @abstractmethod
    async def execute(self, script: str, params: Dict) -> ScriptResult:
        """执行脚本"""
        pass
```

### 11.3 优化优先级

| 优先级 | 优化项 | 预期收益 | 实施难度 |
|--------|--------|----------|----------|
| **P0** | 数据源适配器模式 | 高 | 中 |
| **P1** | 通知渠道适配器模式 | 中 | 低 |
| **P1** | 统一实例管理接口 | 中 | 中 |
| **P2** | 监控指标收集抽象 | 中 | 中 |
| **P3** | 脚本执行器抽象 | 低 | 高 |

### 11.4 优化实施检查清单

```
□ 定义适配器基类接口
□ 实现现有类型的适配器
□ 创建适配器工厂
□ 重构现有代码使用适配器
□ 添加单元测试
□ 更新文档和示例
□ 性能测试（无回归）
```

### 11.5 设计原则总结

| 原则 | 评估 | 说明 |
|------|------|------|
| **开闭原则** | ⚠️ 部分符合 | 需引入适配器模式改进 |
| **单一职责原则** | ✅ 符合 | 各模块职责清晰 |
| **里氏替换原则** | ⚠️ 部分符合 | 需统一实例基类 |
| **接口隔离原则** | ✅ 符合 | 接口设计合理 |
| **依赖倒置原则** | ⚠️ 部分符合 | 需引入抽象接口 |

---

## 十二、快速定位

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
| K8s 配置 | `release/k8s/01-configmap.yaml`, `release/k8s/02-secret.yaml` |
| K8s 部署清单 | `release/k8s/` 目录 |
| Helm Chart | `release/helm/opscenter/` |
| 部署文档 | `release/docs/KUBERNETES_DEPLOYMENT.md` |
| 迁移指南 | `release/docs/MIGRATION_GUIDE.md` |

### 常用命令

```bash
# 本地开发
# 查看服务状态
curl -I http://localhost:5000

# 查看日志
tail -n 50 /app/work/logs/bypass/app.log

# 前端构建
cd frontend && pnpm build

# 云原生部署（生产环境）
# 部署到 Kubernetes
cd release && ./deploy-k8s.sh

# 查看部署状态
kubectl get pods -n opscenter
kubectl get services -n opscenter

# 查看日志
kubectl logs -f deployment/opscenter-backend -n opscenter

# 重启部署
kubectl rollout restart deployment opscenter-backend -n opscenter

# Helm 部署
helm install opscenter ./helm/opscenter --namespace opscenter --create-namespace
```

---

*文档版本：v7.0*
*最后更新：2026-04-05*

### 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v7.0 | 2026-04-05 | 新增架构设计与优化章节，分析开闭原则并提供适配器模式优化方案 |
| v6.0 | 2026-04-02 | 新增云原生部署章节，移除内置数据库，使用 AWS 托管服务 |
| v5.0 | 2026-04-02 | 新增 AI 助手工作指南，总结常见错误模式 |
| v4.0 | 2026-04 | 新增代码整洁规范，案例：MenuConfig.roles 残留 |
| v3.0 | 2026-04 | 新增通知系统重构案例 |
| v2.0 | 2026-04 | 新增验收模板，完善 Checklist |
| v1.0 | 2026-03 | 初始版本 |
