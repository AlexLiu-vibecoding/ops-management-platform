# 开发规范与工作模式

本文档定义了运维管理平台的开发规范、设计方法和工作模式，确保团队协作一致性和代码质量。

---

## 一、项目概述

### 1.1 项目定位
企业级一站式运维管理平台，支持 MySQL/PostgreSQL/Redis 多实例管理、监控告警、变更审批等功能。

### 1.2 技术栈

| 层级 | 技术选型 |
|------|----------|
| 前端 | Vue 3 + Vite + Element Plus + Pinia + ECharts |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy |
| 数据库 | PostgreSQL (元数据) + MySQL/PostgreSQL/Redis (监控实例) |
| AI 集成 | coze-coding-dev-sdk (豆包大模型) |
| 定时任务 | APScheduler |
| AWS 集成 | boto3 (RDS CloudWatch) |
| 存储 | 本地文件系统 / AWS S3 / 阿里云 OSS |
| 测试 | pytest |

---

## 二、分支管理

### 2.1 分支策略
采用 **master + develop** 双分支模式：

```
master (生产环境)
   │
   └── develop (开发环境)
          │
          ├── feature/xxx (功能分支)
          ├── fix/xxx (修复分支)
          └── refactor/xxx (重构分支)
```

### 2.2 分支说明

| 分支 | 用途 | 保护 |
|------|------|------|
| `master` | 生产环境代码，只能通过 PR 合并 | ✅ 禁止直接推送 |
| `develop` | 开发环境，日常开发基础分支 | ✅ 禁止直接推送 |
| `feature/*` | 新功能开发 | 完成后合并到 develop |
| `fix/*` | Bug 修复 | 完成后合并到 develop |
| `refactor/*` | 代码重构 | 完成后合并到 develop |

### 2.3 工作流程

1. 从 `develop` 创建功能分支
2. 开发完成后提交 PR 到 `develop`
3. Code Review 通过后合并
4. 发布时从 `develop` 合并到 `master`

---

## 三、代码规范

### 3.1 Python 代码规范

使用 **Ruff** 作为代码格式化和检查工具。

**核心规则：**
- 缩进：4 空格
- 行宽：120 字符
- 导入排序：标准库 → 第三方库 → 本地模块
- 类型注解：函数参数和返回值必须添加类型注解

**示例：**
```python
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """根据ID获取用户"""
    return db.query(User).filter(User.id == user_id).first()
```

**命名规范：**
- 函数/变量：`snake_case`
- 类名：`PascalCase`
- 常量：`UPPER_SNAKE_CASE`
- 私有方法：`_leading_underscore`

### 3.2 Vue 代码规范

**组件命名：**
- 组件文件：`PascalCase.vue`（如 `UserList.vue`）
- 组件注册：`PascalCase`

**目录结构：**
```
frontend/src/
├── api/           # API 请求封装
├── assets/        # 静态资源
├── components/    # 公共组件
├── layouts/       # 布局组件
├── router/        # 路由配置
├── stores/        # Pinia 状态管理
├── views/         # 页面组件
└── utils/         # 工具函数
```

**Vue 3 组合式 API 规范：**
```vue
<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/api/index'

// 响应式数据
const loading = ref(false)
const dataList = ref([])

// 方法定义
const fetchData = async () => {
  loading.value = true
  try {
    dataList.value = await request.get('/api/xxx')
  } finally {
    loading.value = false
  }
}

// 生命周期
onMounted(() => {
  fetchData()
})
</script>
```

---

## 四、API 设计规范

### 4.1 RESTful 风格

| 操作 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 列表查询 | GET | `/api/v1/users` | 支持分页、筛选 |
| 详情查询 | GET | `/api/v1/users/{id}` | 单条记录 |
| 创建 | POST | `/api/v1/users` | 创建资源 |
| 更新 | PUT | `/api/v1/users/{id}` | 全量更新 |
| 部分更新 | PATCH | `/api/v1/users/{id}` | 部分更新 |
| 删除 | DELETE | `/api/v1/users/{id}` | 删除资源 |

### 4.2 响应格式

**成功响应：**
```json
{
  "id": 1,
  "name": "xxx",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**列表响应：**
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

**错误响应：**
```json
{
  "error": "VALIDATION_ERROR",
  "message": "参数验证失败",
  "detail": {
    "field": "name",
    "reason": "名称不能为空"
  }
}
```

### 4.3 状态码规范

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 业务逻辑错误 |
| 500 | 服务器内部错误 |

---

## 五、前端 UI 规范

### 5.1 组件库
使用 **Element Plus** 作为 UI 组件库。

### 5.2 表格操作列统一化
所有表格的操作列使用 `TableActions` 组件，确保样式一致：

```vue
<template>
  <el-table-column label="操作" width="160" fixed="right" align="center">
    <template #default="{ row }">
      <TableActions :row="row" :actions="actions" :max-primary="2"
        @edit="handleEdit" @delete="handleDelete" />
    </template>
  </el-table-column>
</template>

<script setup>
import TableActions from '@/components/TableActions.vue'

const actions = [
  { key: 'edit', label: '编辑', event: 'edit', primary: true },
  { key: 'delete', label: '删除', event: 'delete', danger: true }
]
</script>
```

### 5.3 表单布局
- 筛选区域：使用 `el-form inline` 布局
- 弹窗表单：使用 `el-form` + `label-width="100px"`
- 统一间距：`margin-bottom: 16px`

---

## 六、数据库规范

### 6.1 表命名
- 使用 `snake_case`
- 多对多关联表：`user_roles`（用户-角色）
- 表名使用复数形式：`users`、`instances`

### 6.2 字段规范
- 主键：`id` (自增 INT 或 UUID)
- 外键：`{table}_id`（如 `user_id`）
- 时间字段：`created_at`、`updated_at`
- 软删除：`is_deleted` + `deleted_at`

### 6.3 SQLAlchemy 模型示例
```python
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True)
    role = Column(Enum(UserRole), default=UserRole.VIEWER)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## 七、Git 提交规范

### 7.1 Commit Message 格式

```
<type>(<scope>): <subject>

<body>
```

### 7.2 Type 类型

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `refactor` | 代码重构 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能） |
| `test` | 测试相关 |
| `chore` | 构建/工具变更 |
| `perf` | 性能优化 |

### 7.3 示例

```bash
feat(notification): 新增飞书通知渠道支持

- 添加飞书 Webhook 配置
- 支持签名验证
- 更新通知管理页面 UI
```

---

## 八、部署规范

### 8.1 部署方式
- 容器内热更新，支持优雅重载 (`kill -HUP`)
- 使用 Docker Compose 管理服务

### 8.2 环境变量
敏感配置通过环境变量管理：
- 数据库连接串
- JWT 密钥
- AWS 凭证
- 存储配置

### 8.3 日志规范
- 日志级别：DEBUG / INFO / WARNING / ERROR
- 日志格式：JSON 结构化日志
- 日志目录：`/app/work/logs/`

---

## 九、权限模型

### 9.1 角色定义

| 角色 | 权限范围 |
|------|----------|
| `super_admin` | 超级管理员，全部权限 |
| `approval_admin` | 审批管理员，审批+执行 |
| `operator` | 运维人员，执行操作 |
| `developer` | 开发人员，查看+申请 |

### 9.2 数据权限
- 环境权限：基于环境隔离数据访问
- 实例权限：基于实例级别控制操作

---

## 十、工作模式

### 10.1 需求处理流程
1. 需求分析 → 确认技术方案
2. 创建功能分支 → 开发实现
3. 自测通过 → 提交 PR
4. Code Review → 修改完善
5. 合并到 develop → 验证测试
6. 发布到 master → 生产部署

### 10.2 沟通协作
- 功能设计先讨论再开发
- 不确定的技术方案先确认
- 遇到阻塞问题及时反馈

### 10.3 代码审查重点
- 功能是否完整实现
- 是否有安全风险
- 代码是否符合规范
- 是否有性能问题
- 是否有足够的错误处理

---

## 十一、常见问题

### Q1: 如何添加新的 API 接口？
1. 在 `backend/app/schemas/` 定义请求/响应模型
2. 在 `backend/app/api/` 创建路由文件
3. 在 `backend/app/main.py` 注册路由
4. 在 `frontend/src/api/` 封装请求方法

### Q2: 如何添加新的菜单？
1. 数据库 `menu_configs` 表添加记录
2. 前端 `router/index.js` 添加路由配置
3. 创建对应的页面组件

### Q3: 如何添加新的通知渠道？
1. 后端 `notification.py` 添加发送逻辑
2. 前端 `notification.vue` 添加配置选项
3. 更新通道类型枚举

---

*文档版本：v1.0*
*最后更新：2024年*
