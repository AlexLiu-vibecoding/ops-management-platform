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

### 1.3 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| 后端 API | 5000 | FastAPI 服务 |
| 前端开发 | 3000 | Vite 开发服务器（热更新） |

---

## 二、AI 协作开发指南

> ⚠️ **重要**：本节专门针对 AI 辅助开发场景，确保高效协作，减少 token 消耗。

### 2.1 AI 启动开发前必做

AI 在开始任何开发任务前，**必须按顺序执行以下检查**：

```
1. 读取上下文
   - 检查是否有压缩摘要 (last_compress_result)
   - 了解当前项目状态和最近的修改
   
2. 确认项目结构
   - 执行 `ls -la` 确认工作目录
   - 检查关键配置文件是否存在 (.coze, package.json, requirements.txt)
   
3. 检查服务状态
   - 后端：curl -I http://localhost:5000
   - 前端：curl -I http://localhost:3000
   - 如果服务未启动，查看 .coze 或 package.json 中的启动命令
   
4. 明确需求范围
   - 确认具体要做什么，不要擅自扩展范围
   - 不确定的地方先问用户
```

### 2.2 AI 开发工作流程

```
┌─────────────────────────────────────────────────────────────┐
│                     开发任务开始                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  1. 需求确认                                                 │
│     - 明确要做什么，不要猜测                                  │
│     - 涉及多个文件时，先列出修改清单                          │
│     - 复杂任务创建 TODO 列表跟踪进度                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  2. 先读后写                                                 │
│     - 修改文件前必须先 read_file 读取当前内容                 │
│     - 了解文件结构后再进行修改                                │
│     - 避免覆盖已有功能                                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  3. 代码修改                                                 │
│     - 优先使用 edit_file 精准修改                            │
│     - 大改动考虑 write_file 覆盖                             │
│     - 保持代码风格一致                                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  4. 验证测试                                                 │
│     - 前端：利用 Vite 热更新，刷新页面查看                    │
│     - 后端：检查日志 tail -n 20 /app/work/logs/bypass/app.log│
│     - API：curl 测试接口                                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  5. 确认完成                                                 │
│     - 向用户展示修改内容                                      │
│     - 等待用户确认或反馈                                      │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 常见错误与避坑指南

#### ❌ 错误做法 → ✅ 正确做法

| 场景 | ❌ 错误 | ✅ 正确 |
|------|---------|---------|
| 端口检测 | `lsof -i:5000` | `curl -I http://localhost:5000` 或 `ss -tuln \| grep :5000` |
| 文件下载 | `<a href=url download>` | `fetch + blob + createObjectURL` |
| 读取文件 | `cat file.txt` | `read_file` 工具 |
| 搜索内容 | `grep "xxx" file` | `grep_file` 工具 |
| 修改文件 | 直接 write_file 覆盖 | 先 read_file 再 edit_file |
| 需求理解 | 猜测用户意图，擅自扩展 | 先确认，再开发 |
| 服务重启 | 每次改代码都重启 | 利用热更新，无需重启 |
| 批量操作 | 多次调用工具 | 并行调用无依赖的工具 |

### 2.4 减少 Token 消耗技巧

```
1. 精准定位
   - 使用 grep_file 搜索关键字定位文件
   - 读取文件时指定行范围，不要全文件读取
   - 例：read_file(file_path, start_line=100, end_line=150)

2. 避免重复操作
   - 记住已读取过的文件内容
   - 同一文件的多次修改合并为一次 edit_file

3. 减少无效对话
   - 不确定的地方一次性问清楚
   - 避免来回确认多次

4. 合理使用工具
   - 简单任务直接执行，不创建 TODO
   - 复杂任务创建 TODO，避免遗漏步骤
```

---

## 三、开发经验总结

### 3.1 前端开发经验

#### 表格操作列统一化
所有表格操作列使用 `TableActions` 组件，避免换行和样式不一致：

```vue
<!-- ✅ 正确 -->
<el-table-column label="操作" width="180" fixed="right" align="center">
  <template #default="{ row }">
    <TableActions :row="row" :actions="actions" :max-primary="3"
      @edit="handleEdit" @delete="handleDelete" @test="handleTest" />
  </template>
</el-table-column>

<!-- ❌ 错误 - 自定义按钮容易换行 -->
<el-table-column label="操作" width="160">
  <template #default="{ row }">
    <el-button link @click="handleEdit(row)">编辑</el-button>
    <el-button link @click="handleDelete(row)">删除</el-button>
  </template>
</el-table-column>
```

#### 筛选区域布局
使用 `el-form inline` 布局，统一控件宽度和间距：

```vue
<el-form :inline="true" class="filter-form">
  <el-form-item label="名称">
    <el-input v-model="filter.name" placeholder="请输入" style="width: 200px" />
  </el-form-item>
  <el-form-item label="状态">
    <el-select v-model="filter.status" style="width: 150px">
      <el-option label="全部" value="" />
      <el-option label="启用" value="1" />
    </el-select>
  </el-form-item>
  <el-form-item>
    <el-button type="primary" @click="handleSearch">查询</el-button>
  </el-form-item>
</el-form>
```

#### 路由和菜单联动
**新增菜单必须同时修改三处：**
1. 后端：`backend/app/api/menu.py` - 菜单初始化数据
2. 前端：`frontend/src/router/index.js` - 路由配置
3. 数据库：调用 `/api/v1/menu/add-missing` API 或手动添加

```javascript
// router/index.js 示例
{
  path: 'notification',
  name: 'NotificationManage',
  component: () => import('@/views/config/notification.vue'),
  meta: { title: '通知管理', icon: 'Bell' }
}
```

### 3.2 后端开发经验

#### API 路由注册
新 API 必须在 `main.py` 中注册：

```python
# main.py
from app.api import new_module

app.include_router(new_module.router, prefix="/api/v1")
```

#### 数据库模型修改
1. 修改 `models/` 下的模型文件
2. 创建迁移脚本或直接执行 DDL
3. 重启服务生效

#### 环境变量使用
```python
# ✅ 正确 - 从环境变量读取
import os
port = int(os.getenv("DEPLOY_RUN_PORT", "5000"))

# ❌ 错误 - 硬编码
port = 5000
```

### 3.3 调试技巧

#### 日志查看
```bash
# 查看最新日志
tail -n 50 /app/work/logs/bypass/app.log

# 搜索错误
grep -iE "error|exception|warn" /app/work/logs/bypass/app.log | tail -n 20

# 查看前端控制台日志（如果有的话）
tail -n 50 /app/work/logs/bypass/console.log
```

#### API 测试
```bash
# GET 请求
curl -s http://localhost:5000/api/v1/users | jq

# POST 请求
curl -s -X POST http://localhost:5000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{"name": "test"}' | jq

# 带 Token
curl -s -H "Authorization: Bearer xxx" http://localhost:5000/api/v1/users
```

---

## 四、分支管理

### 4.1 分支策略
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

### 4.2 分支说明

| 分支 | 用途 | 保护 |
|------|------|------|
| `master` | 生产环境代码，只能通过 PR 合并 | ✅ 禁止直接推送 |
| `develop` | 开发环境，日常开发基础分支 | ✅ 禁止直接推送 |
| `feature/*` | 新功能开发 | 完成后合并到 develop |
| `fix/*` | Bug 修复 | 完成后合并到 develop |
| `refactor/*` | 代码重构 | 完成后合并到 develop |

---

## 五、代码规范

### 5.1 Python 代码规范

使用 **Ruff** 作为代码格式化和检查工具。

**核心规则：**
- 缩进：4 空格
- 行宽：120 字符
- 导入排序：标准库 → 第三方库 → 本地模块
- 类型注解：函数参数和返回值必须添加类型注解

### 5.2 Vue 代码规范

**组件命名：**
- 组件文件：`PascalCase.vue`（如 `UserList.vue`）
- 组件注册：`PascalCase`

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

## 六、API 设计规范

### 6.1 RESTful 风格

| 操作 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 列表查询 | GET | `/api/v1/users` | 支持分页、筛选 |
| 详情查询 | GET | `/api/v1/users/{id}` | 单条记录 |
| 创建 | POST | `/api/v1/users` | 创建资源 |
| 更新 | PUT | `/api/v1/users/{id}` | 全量更新 |
| 删除 | DELETE | `/api/v1/users/{id}` | 删除资源 |

### 6.2 响应格式

**成功响应：**
```json
{
  "id": 1,
  "name": "xxx",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**错误响应：**
```json
{
  "error": "VALIDATION_ERROR",
  "message": "参数验证失败"
}
```

---

## 七、Git 提交规范

### 7.1 Commit Message 格式

```
<type>(<scope>): <subject>
```

### 7.2 Type 类型

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `refactor` | 代码重构 |
| `docs` | 文档更新 |
| `style` | 代码格式 |
| `test` | 测试相关 |
| `chore` | 构建/工具变更 |

---

## 八、权限模型

### 8.1 角色定义

| 角色 | 权限范围 |
|------|----------|
| `super_admin` | 超级管理员，全部权限 |
| `approval_admin` | 审批管理员，审批+执行 |
| `operator` | 运维人员，执行操作 |
| `developer` | 开发人员，查看+申请 |

---

## 九、常见问题 FAQ

### Q1: 如何添加新的 API 接口？
1. 在 `backend/app/schemas/` 定义请求/响应模型
2. 在 `backend/app/api/` 创建路由文件
3. 在 `backend/app/main.py` 注册路由
4. 在 `frontend/src/api/` 封装请求方法

### Q2: 如何添加新的菜单？
1. 后端 `menu.py` 的 `required_menus` 数组添加菜单配置
2. 前端 `router/index.js` 添加路由配置
3. 创建对应的页面组件
4. 调用 `/api/v1/menu/add-missing` API 更新数据库

### Q3: 前端修改后页面没变化？
- Vite 支持热更新，保存后自动刷新
- 如果没变化，检查浏览器控制台是否有报错
- 尝试手动刷新页面

### Q4: 后端修改后接口没生效？
- FastAPI 使用 uvicorn，默认热重载
- 检查日志 `tail -n 20 /app/work/logs/bypass/app.log`
- 确认修改的文件已保存

---

## 十、快速参考

### 常用命令

```bash
# 查看服务状态
curl -I http://localhost:5000    # 后端
curl -I http://localhost:3000    # 前端

# 查看日志
tail -n 50 /app/work/logs/bypass/app.log

# Git 操作
git status
git add .
git commit -m "feat(xxx): 描述"
git push origin develop
```

### 文件快速定位

| 功能 | 文件路径 |
|------|----------|
| 后端路由注册 | `backend/app/main.py` |
| 前端路由配置 | `frontend/src/router/index.js` |
| 菜单配置 | `backend/app/api/menu.py` |
| 公共组件 | `frontend/src/components/` |
| API 封装 | `frontend/src/api/index.js` |
| 数据库模型 | `backend/app/models/` |

---

*文档版本：v2.0*
*最后更新：2024年*
