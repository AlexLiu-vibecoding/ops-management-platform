# 通知功能架构优化 - 功能演示指南

## 功能概述

本次更新实现了通知功能的架构优化，包括：
1. **静默规则管理** - 支持按时间段、告警条件静默通知
2. **频率限制管理** - 防止通知轰炸，限制通知频率
3. **权限关联管理** - 细粒度的权限控制

## 访问路径

### 前端页面

**通知配置页面**：`http://localhost:5000/notification-config`

**权限要求**：
- super_admin（超级管理员）
- approval_admin（审批管理员）

### API接口

#### 静默规则管理

```bash
# 获取静默规则列表
GET /api/v1/notification/config/silence-rules

# 创建静默规则
POST /api/v1/notification/config/silence-rules
{
  "name": "周末维护窗口静默",
  "description": "周末维护时间段静默所有告警",
  "silence_type": "weekly",
  "time_start": "02:00",
  "time_end": "06:00",
  "weekdays": [5, 6],  # 周六、周日
  "is_enabled": true,
  "priority": 10
}

# 更新静默规则
PUT /api/v1/notification/config/silence-rules/{rule_id}

# 删除静默规则
DELETE /api/v1/notification/config/silence-rules/{rule_id}
```

#### 频率限制管理

```bash
# 获取频率限制规则列表
GET /api/v1/notification/config/rate-limit-rules

# 创建频率限制规则
POST /api/v1/notification/config/rate-limit-rules
{
  "name": "告警频率限制",
  "description": "限制相同告警的发送频率",
  "limit_window": 300,      # 5分钟时间窗口
  "max_notifications": 5,    # 最多发送5次
  "cooldown_period": 600,    # 冷却期10分钟
  "is_enabled": true,
  "priority": 10
}

# 更新频率限制规则
PUT /api/v1/notification/config/rate-limit-rules/{rule_id}

# 删除频率限制规则
DELETE /api/v1/notification/config/rate-limit-rules/{rule_id}
```

## 功能演示步骤

### 1. 登录系统

```bash
# 使用超级管理员账号登录
用户名: admin
密码: admin123
```

### 2. 访问通知配置页面

登录后，在左侧菜单找到：
- **系统管理** → **通知配置**

或直接访问：`http://localhost:5000/notification-config`

### 3. 创建静默规则示例

**场景1：每日维护窗口静默**
- 规则名称：每日维护窗口
- 静默类型：每日重复
- 时间段：02:00 - 06:00
- 匹配条件：全部告警

**场景2：周末全天静默**
- 规则名称：周末静默
- 静默类型：每周重复
- 时间段：00:00 - 23:59
- 生效星期：周六、周日

**场景3：一次性静默**
- 规则名称：系统升级静默
- 静默类型：一次性
- 生效日期：2024-04-02 至 2024-04-03

### 4. 创建频率限制规则示例

**场景1：防止重复告警**
- 规则名称：重复告警限制
- 时间窗口：300秒（5分钟）
- 最大通知数：3次
- 冷却期：600秒（10分钟）

**场景2：严重告警特殊处理**
- 规则名称：严重告警频率限制
- 告警级别：critical
- 时间窗口：600秒（10分钟）
- 最大通知数：10次
- 冷却期：300秒（5分钟）

## 权限配置说明

### 权限编码

| 权限编码 | 权限名称 | 说明 |
|---------|---------|------|
| notification:view | 查看通知 | 查看通知配置 |
| notification:channel_manage | 管理通道 | 创建、编辑、删除通知通道 |
| notification:binding_manage | 管理绑定 | 创建、编辑、删除通知绑定 |
| notification:template_manage | 管理模板 | 创建、编辑、删除通知模板 |
| notification:silence_manage | 管理静默 | 创建、编辑、删除静默规则 |
| notification:rate_limit_manage | 管理频率限制 | 创建、编辑、删除频率限制规则 |

### 角色权限

| 角色 | 权限 |
|-----|------|
| super_admin | 全部权限 |
| approval_admin | 查看 + 模板管理 |
| operator | 仅查看 |
| developer | 仅查看 |

## 技术实现

### 后端架构

```
backend/
├── app/
│   ├── api/
│   │   └── notification_config.py  # 通知配置API
│   ├── models/
│   │   └── permissions.py          # 权限模型（新增权限编码）
│   ├── deps.py                      # 依赖注入（新增require_permissions）
│   └── main.py                      # 路由注册
```

### 前端架构

```
frontend/
├── src/
│   ├── views/
│   │   └── notification/
│   │       └── config.vue           # 通知配置页面
│   ├── router/
│   │   └── index.js                 # 路由配置
│   └── utils/
│       └── format.js                # 格式化工具
```

### 数据库迁移

```bash
# 执行迁移
cd backend
alembic upgrade head
```

## 验证清单

- [x] 后端API已加载（/api/v1/notification/config/*）
- [x] 前端页面已构建（dist/assets/config-*.js）
- [x] 路由已配置（/notification-config）
- [x] 权限已配置（6个新增权限编码）
- [x] 构建成功验证（npm run build）

## 下一步操作

1. **启动服务**（如果未启动）：
   ```bash
   cd /workspace/projects/backend
   python -m uvicorn app.main:app --host 0.0.0.0 --port 5000 --reload
   ```

2. **访问页面**：
   - 打开浏览器访问：`http://localhost:5000`
   - 使用admin账号登录
   - 导航到"通知配置"页面

3. **测试功能**：
   - 创建静默规则
   - 创建频率限制规则
   - 验证权限控制

## 注意事项

1. 需要使用具有相应权限的账号登录才能看到页面
2. 所有API接口都需要认证（Bearer Token）
3. 静默规则和频率限制规则的优先级越高，优先级越高
4. 时间格式为HH:MM（24小时制）
