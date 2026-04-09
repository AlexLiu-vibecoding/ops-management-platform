# AGENTS.md - 项目导航与开发指南

> **⚠️ AI 开发前必读此文件！**
> 
> 本文档包含项目全貌、开发规范和常见问题。详细文档见 `.vibecoding/CODE_MAP.md`。

---

## 一、核心原则

| 原则 | 说明 |
|------|------|
| **先读后做** | 开发前必须先读取本文档和 CODE_MAP.md |
| **先确认后开发** | 不确定的需求，先确认再动手 |
| **不擅自扩展** | 用户说什么做什么，不猜测不扩展 |
| **改完要验证** | 让用户验证效果，不自己认为完成 |

### 开发前必查

```
□ 读取本文档了解项目结构
□ 读取相关规格文件（.vibecoding/specs/xxx.md）
□ 确认需求范围，不擅自扩展
□ 检查现有代码，避免重复造轮子
□ 列出将要修改的文件清单
```

### 开发后必查

```
□ 确认改动范围与需求一致
□ 没有引入硬编码
□ 没有遗漏 import 语句
□ 没有残留的废弃代码
□ 让用户验证效果
```

---

## 二、项目概览

| 项目 | 说明 |
|------|------|
| **名称** | OpsCenter - 一站式运维管理平台 |
| **技术栈** | Vue 3 + Vite + Element Plus / Python 3.11 + FastAPI + SQLAlchemy |
| **数据库** | PostgreSQL + Redis（生产使用 AWS RDS/ElastiCache） |
| **端口** | 后端 5000 |
| **环境变量** | `DEPLOY_RUN_PORT=5000`, `COZE_PROJECT_DOMAIN_DEFAULT` |

### 架构特点

```
⚠️ 数据库驱动设计 - 重要！

菜单配置 → menu_configs 表 (不是前端硬编码)
权限配置 → permissions 表 + role_permissions 表
系统配置 → system_configs 表

特点：前端不硬编码配置，全部从数据库动态加载
```

### 角色体系

| 角色 | 权限范围 |
|------|----------|
| `super_admin` | 超级管理员，全部权限 |
| `approval_admin` | 审批管理员，审批+执行 |
| `operator` | 运维人员，执行操作 |
| `developer` | 开发人员，查看+申请 |
| `readonly` | 只读用户 |

---

## 三、功能模块索引

| 模块 | 前端 | 后端 API | 规格 |
|------|------|----------|------|
| 认证与权限 | `views/login/` | `api/auth.py` | SPEC-001 |
| 实例管理 | `views/instances/` | `api/instances.py` | SPEC-002 |
| 环境管理 | `views/environments/` | `api/environments.py` | SPEC-003 |
| SQL 编辑器 | `views/sql-editor/` | `api/sql.py` | SPEC-004 |
| 变更审批 | `views/change/` | `api/approval.py` | SPEC-005 |
| 监控中心 | `views/monitor/` | `api/monitor.py` | SPEC-006 |
| Redis 管理 | `views/instances/redis-detail.vue` | `api/redis.py` | SPEC-007 |
| 消息通知 | `views/notification/` | `api/notification_channels.py` | SPEC-008 |
| 脚本管理 | `views/scripts/` | `api/scripts.py` | SPEC-009 |
| 定时任务 | `views/scheduled-tasks/` | `api/scheduled_tasks.py` | SPEC-010 |
| 审计日志 | `views/audit/` | `api/audit.py` | SPEC-011 |
| 系统配置 | `views/system/` | `api/system.py` | SPEC-012 |
| 巡检报告 | `views/inspection/` | `api/inspection.py` | SPEC-013 |
| SQL 优化器 | `views/sql-optimizer/` | `api/sql_optimizer.py` | SPEC-014 |
| 权限管理 | `views/permissions/` | `api/permissions.py` | SPEC-015 |
| AI 模型配置 | `views/system/ai-models.vue` | `api/ai_models.py` | SPEC-017 |

详细文件路径见 `.vibecoding/CODE_MAP.md`

---

## 四、新增页面 CheckList（强制执行）

### 1. 路由配置
```
□ router/index.js 添加路由
□ 路由 path 与后端 API 路径对应
```

### 2. API 封装
```
□ frontend/src/api/xxx.js 封装
□ ⚠️ 不要重复 /api/v1 前缀（baseURL 已包含）
```

### 3. 数据初始化
```
□ ref() 显式初始化（ref(false), ref([])）
□ 404 处理：error.response?.status === 404 → 显示空数据
```

### 4. 页面结构
```
□ onMounted 调用 fetchData
□ loading 状态
□ 空数据展示
□ TableActions 组件用于操作列
```

### 5. 权限配置（缺一不可）
```
□ menu_configs 表配置（调用 /api/v1/menu/add-missing）
□ permissions 表配置
□ role_permissions 绑定
```

### 6. 表单功能
```
□ 新建/编辑回显
□ 表单验证
□ 提交后刷新列表
```

---

## 五、常见错误速查

### 错误1: API 路径重复

```javascript
// ❌ 错误：实际请求 /api/v1/api/v1/xxx
const res = await request.get('/api/v1/xxx')

// ✅ 正确：直接写路径
const res = await request.get('/xxx')
```

### 错误2: 404 处理不当

```javascript
// ❌ 错误：404 也弹错误
} catch (error) {
  ElMessage.error(...)
}

// ✅ 正确：404 显示空数据
} catch (error) {
  if (error.response?.status === 404) {
    dataList.value = []
  } else {
    ElMessage.error(...)
  }
}
```

### 错误3: 空值解包

```javascript
// ❌ 错误：id 为 null 时报错
const key = channel.id.toString()

// ✅ 正确：使用 String()
const key = String(channel.id)
```

### 错误4: 忘记导入

```javascript
// 完整导入示例
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/index'
```

### 错误5: 编辑弹窗没有回显

```javascript
// ✅ 正确：深拷贝数据
const handleEdit = (row) => {
  dialogVisible.value = true
  formData.value = { ...row }
}
```

---

## 六、开发规范

### 6.1 前端规范

| 类型 | 规范 |
|------|------|
| 框架 | Vue 3 组合式 API，`<script setup>` |
| 表格操作列 | 统一使用 `TableActions` 组件 |
| API 调用 | `request.get('/xxx')` 不带 `/api/v1` 前缀 |

#### 页面模板

```vue
<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/index'

const loading = ref(false)
const dataList = ref([])

const fetchData = async () => {
  loading.value = true
  try {
    dataList.value = await request.get('/xxx')
  } catch (error) {
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

### 6.2 后端规范

| 类型 | 规范 |
|------|------|
| 路由注册 | 在 `main.py` 中注册路由 |
| Schema | 放在 `schemas/` 目录或与路由同文件 |
| 依赖注入 | 使用 `Depends(get_current_user)` 获取当前用户 |

---

## 七、避坑指南

| 场景 | ❌ 错误 | ✅ 正确 |
|------|---------|---------|
| 端口检测 | `lsof -i:5000` | `curl -I http://localhost:5000` |
| 文件下载 | `<a href=url download>` | `fetch + blob + createObjectURL` |
| 读取文件 | `cat file.txt` | `read_file` 工具 |
| 搜索内容 | `grep` 命令 | `grep_file` 工具 |
| 修改文件 | 直接 write_file 覆盖 | 先 read_file 再 edit_file |
| API调用 | `request.get('/api/v1/xxx')` | `request.get('/xxx')` |
| 新增菜单 | 只配置前端路由 | 数据库 + 前端双端配置 |
| 删除字段 | 只删模型 | 同步删 Schema 和引用 |

### 菜单不显示？

1. **检查数据库 menu_configs 表是否有记录** ⬅️ 最常见
2. 调用 `/api/v1/menu/add-missing` 同步
3. 检查前端路由是否配置

### API 返回 404？

1. 检查后端路由是否注册
2. **检查前端调用是否重复 /api/v1** ⬅️ 常见错误
3. 查看浏览器 Network 面板确认实际请求路径

---

## 八、快速定位

| 需求 | 文件位置 |
|------|----------|
| 修改路由 | `frontend/src/router/index.js` |
| 添加菜单 | `menu_configs 表` 或 `/api/v1/menu/add-missing` |
| 修改布局 | `frontend/src/layouts/MainLayout.vue` |
| 公共组件 | `frontend/src/components/` |
| API 封装 | `frontend/src/api/index.js` |
| 后端入口 | `backend/app/main.py` |
| 数据库模型 | `backend/app/models/__init__.py` |
| 权限配置 | `backend/app/models/permissions.py` |
| 日志文件 | `/app/work/logs/bypass/app.log` |
| 部署文档 | `release/docs/KUBERNETES_DEPLOYMENT.md` |

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

## 九、经验教训

> ⚠️ **重要**: 以下是踩过的坑，务必避免！

### 案例1: 菜单不显示

**原因**: 只配置前端路由，未配置数据库菜单。

**解决**:
```
1. INSERT INTO menu_configs (name, path, icon, permission) VALUES (...);
2. router/index.js 配置路由
3. permissions 表配置权限码
4. 同步菜单: /api/v1/menu/add-missing
```

### 案例2: API 404

**原因**: baseURL 已包含 `/api/v1`，代码又拼接一次。

### 案例3: 通知系统重构

**旧设计**: 静默规则/频率限制是全局的

**新设计**: 绑定到具体通道（channel_silence_rules, channel_rate_limits）

### 案例4: 新增页面 10 大错误

1. API 路径重复 `/api/v1`
2. 404 没处理 → 显示空数据
3. 空值解包 `.toString()` → `String()`
4. 忘记导入 ElMessage
5. 响应字段不匹配
6. 状态没初始化 `ref(false)`, `ref([])`
7. 缺少 `onMounted`
8. 权限没配置
9. 没封装 API
10. 编辑弹窗没回显

---

## 十、RIPER 流程（简化版）

```
准备 → 研究 → 创新 → 计划（审批） → 执行 → 校验
```

| 阶段 | 核心任务 | 产出物 |
|------|----------|--------|
| 准备 | 理解代码，准备 Context | Context Bundle |
| 研究 | 扫描代码，锁定事实 | Code Facts |
| 创新 | 提出 2-3 个方案 | Options + Analysis |
| 计划 | 原子级拆解，精确到文件 | **Spec 文档** |
| 执行 | 按图施工，AI 是打字员 | 代码 |
| 校验 | Spec vs Code 一致性验证 | 验证报告 |

**⚠️ 门禁**: 未完成 Plan 审批，不得进入 Execute！

详细见 `.vibecoding/template.md`（规格模板）

---

*文档版本：v9.0*
*最后更新：2026-04-09*
*冗余内容已移至 `.vibecoding/CODE_MAP.md`*
