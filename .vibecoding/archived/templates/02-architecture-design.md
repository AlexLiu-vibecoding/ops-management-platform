# 架构设计模板 (Architecture Design Template)

> 基于需求分析的架构设计，输出可直接落地的技术方案。

---

## 模板元数据

```
版本: v1.0
创建日期: 2026-04
适用阶段: 架构设计 → 代码生成
目标: 需求规格 → 技术方案
前置条件: 完成需求分析报告
```

---

## 🎯 核心原则

1. **分层清晰** - 按照数据库 → API → 前端三层设计
2. **约束优先** - 所有约束在设计时明确
3. **可测试性** - 设计考虑测试便利性
4. **可维护性** - 遵循项目规范和最佳实践

---

## 📥 输入定义

```yaml
需求分析报告:
  type: object
  required: true
  properties:
    核心功能: string
    验收标准: array
    技术方案: object
    实施计划: array
    风险评估: array

项目规范:
  type: object
  required: true
  properties:
    数据库规范:
      - 字段命名规范
      - 索引设计规范
      - 约束命名规范
    API 规范:
      - 路由命名规范
      - 响应格式规范
      - 错误码规范
    前端规范:
      - 组件命名规范
      - 路由配置规范
      - 样式规范
```

---

## 🧠 结构化思维 (SoT) 流程

### Step 1: 数据库设计 (3 分钟)

```
目标: 设计数据库表结构和关系

思考框架:
1. 实体识别: 需要哪些表？
2. 属性设计: 每个表需要哪些字段？
3. 关系设计: 表之间如何关联？
4. 约束设计: 需要哪些约束（主键、外键、唯一、非空）？
5. 索引设计: 需要哪些索引优化查询？

输出格式:
表名: [表名]
  描述: [表用途]
  字段:
    - name: [字段名]
      type: [数据类型]
      nullable: [是否可为空]
      default: [默认值]
      index: [是否索引]
      comment: [字段说明]
  约束:
    - PK: [主键]
    - FK: [外键: table.column]
    - UNIQUE: [唯一约束]
    - CHECK: [检查约束]
  索引:
    - name: [索引名]
      columns: [列名列表]
      type: [BTREE/HASH/GIN]
      comment: [索引说明]
  关系:
    - to: [关联表]
      type: [ONE_TO_ONE/ONE_TO_MANY/MANY_TO_MANY]
      via: [关联字段/中间表]
```

**验证检查点**:
- [ ] 字段命名是否符合规范？
- [ ] 是否有冗余字段？
- [ ] 索引是否覆盖查询场景？
- [ ] 是否有外键约束？
- [ ] 是否考虑了数据迁移？

---

### Step 2: API 设计 (3 分钟)

```
目标: 设计 RESTful API 接口

思考框架:
1. 资源识别: 有哪些资源？
2. 操作识别: 每个资源支持哪些操作？
3. 路由设计: 如何组织路由？
4. 参数设计: 请求参数如何传递？
5. 响应设计: 响应格式如何统一？

输出格式:
资源名: [资源名]
  描述: [资源说明]
  路由:
    - GET /api/v1/[resource]
      描述: [查询资源列表]
      权限: [权限码]
      参数:
        - name: [参数名]
          type: [类型]
          required: [是否必填]
          description: [参数说明]
      响应:
        type: [列表/分页/详情]
        schema: |
          {
            "code": 200,
            "message": "success",
            "data": [...]
          }

    - POST /api/v1/[resource]
      描述: [创建资源]
      权限: [权限码]
      请求体:
        schema: |
          {
            "field1": "value1",
            "field2": "value2"
          }
      响应:
        schema: |
          {
            "code": 201,
            "message": "created",
            "data": {"id": 1}
          }

    - PUT /api/v1/[resource]/{id}
      描述: [更新资源]
      权限: [权限码]
      请求体: [同 POST]

    - DELETE /api/v1/[resource]/{id}
      描述: [删除资源]
      权限: [权限码]
      响应:
        schema: |
          {
            "code": 204,
            "message": "deleted"
          }
```

**验证检查点**:
- [ ] 路由是否符合 RESTful 规范？
- [ ] 是否有权限控制？
- [ ] 参数验证是否完整？
- [ ] 响应格式是否统一？
- [ ] 错误处理是否完善？

---

### Step 3: 服务层设计 (2 分钟)

```
目标: 设计业务逻辑服务

思考框架:
1. 服务识别: 需要哪些服务？
2. 方法设计: 每个服务需要哪些方法？
3. 依赖设计: 服务之间如何依赖？
4. 异常设计: 需要哪些自定义异常？
5. 审计设计: 哪些操作需要审计？

输出格式:
服务名: [服务名]
  描述: [服务用途]
  依赖:
    - [依赖1]
    - [依赖2]
  方法:
    - name: [方法名]
      description: [方法说明]
      input:
        type: [输入类型]
        schema: |
          {
            "param1": "value1"
          }
      output:
        type: [输出类型]
        schema: |
          {
            "result": "value"
          }
      exceptions:
        - [异常类型]: [触发条件]
      audit:
        operation: [操作类型]
        fields: [需要记录的字段]

  异常定义:
    - name: [异常名]
      code: [错误码]
      message: [错误信息]
      http_status: [HTTP状态码]
```

**验证检查点**:
- [ ] 方法职责是否单一？
- [ ] 依赖是否合理？
- [ ] 异常是否完善？
- [ ] 审计是否完整？
- [ ] 是否可测试？

---

### Step 4: 前端设计 (2 分钟)

```
目标: 设计前端页面和组件

思考框架:
1. 页面识别: 需要哪些页面？
2. 路由设计: 如何组织路由？
3. 组件设计: 需要哪些组件？
4. 状态设计: 需要哪些状态？
5. 交互设计: 用户如何交互？

输出格式:
页面: [页面名]
  路由: [路由路径]
  描述: [页面用途]
  权限: [权限码]
  组件:
    - name: [组件名]
      type: [页面组件/业务组件/基础组件]
      props:
        - name: [属性名]
          type: [类型]
          required: [是否必填]
          description: [属性说明]
      events:
        - name: [事件名]
          description: [事件说明]
          payload: [事件数据]
  状态:
    - name: [状态名]
      type: [类型]
      initial: [初始值]
  API:
    - method: [GET/POST/PUT/DELETE]
      endpoint: [API端点]
      request: [请求参数]
      response: [响应数据]
```

**验证检查点**:
- [ ] 路由是否规范？
- [ ] 组件是否可复用？
- [ ] 状态管理是否合理？
- [ ] API 封装是否正确？
- [ ] 交互是否友好？

---

### Step 5: 安全设计 (2 分钟)

```
目标: 设计安全防护措施

思考框架:
1. 权限控制: 需要什么级别的权限？
2. 数据加密: 哪些数据需要加密？
3. 输入验证: 需要验证哪些输入？
4. SQL 防护: 如何防止 SQL 注入？
5. XSS 防护: 如何防止 XSS 攻击？

输出格式:
权限控制:
  - 资源: [资源名]
    操作:
      - name: [操作名]
        code: [权限码]
        roles: [允许的角色]
        environments: [允许的环境]

数据加密:
  - 字段: [字段名]
    algorithm: [加密算法]
    key: [密钥来源]

输入验证:
  - 输入: [输入名]
    type: [类型]
    range: [范围]
    format: [格式]

SQL 防护:
  - 参数化查询: [是/否]
  - ORM 使用: [是/否]
  - 输入过滤: [是/否]

XSS 防护:
  - 输入转义: [是/否]
  - 输出过滤: [是/否]
  - CSP 配置: [配置]
```

**验证检查点**:
- [ ] 权限是否足够？
- [ ] 敏感数据是否加密？
- [ ] 输入验证是否完整？
- [ ] SQL 注入防护是否完善？
- [ ] XSS 防护是否完善？

---

## 📤 输出格式

```markdown
# 架构设计文档

## 1. 概述

### 1.1 设计目标
[设计目标]

### 1.2 技术栈
- 后端: Python 3.11 + FastAPI + SQLAlchemy
- 前端: Vue 3 + Vite + Element Plus
- 数据库: PostgreSQL

## 2. 数据库设计

### 2.1 ER 图
[ER 图]

### 2.2 表结构
[表结构定义]

### 2.3 数据迁移
[迁移脚本]

## 3. API 设计

### 3.1 API 列表
[API 列表]

### 3.2 请求/响应示例
[示例]

### 3.3 错误码定义
[错误码表]

## 4. 服务层设计

### 4.1 服务列表
[服务列表]

### 4.2 服务接口
[服务接口定义]

### 4.3 异常定义
[异常定义]

## 5. 前端设计

### 5.1 页面结构
[页面结构图]

### 5.2 组件设计
[组件列表]

### 5.3 路由配置
[路由配置]

### 5.4 状态管理
[状态设计]

## 6. 安全设计

### 6.1 权限控制
[权限矩阵]

### 6.2 数据加密
[加密方案]

### 6.3 安全措施
[安全措施清单]

## 7. 性能设计

### 7.1 索引设计
[索引列表]

### 7.2 缓存设计
[缓存策略]

### 7.3 分页设计
[分页方案]

## 8. 部署设计

### 8.1 环境变量
[环境变量列表]

### 8.2 配置文件
[配置示例]

### 8.3 迁移脚本
[迁移脚本]
```

---

## 🔍 自我验证清单

```yaml
数据库层:
  - 表结构是否合理? [是/否]
  - 索引是否覆盖查询? [是/否]
  - 外键约束是否完整? [是/否]
  - 数据迁移是否考虑? [是/否]

API 层:
  - 路由是否 RESTful? [是/否]
  - 权限控制是否完善? [是/否]
  - 参数验证是否完整? [是/否]
  - 响应格式是否统一? [是/否]

服务层:
  - 职责是否单一? [是/否]
  - 依赖是否合理? [是/否]
  - 异常是否完善? [是/否]
  - 审计是否完整? [是/否]

前端层:
  - 路由是否规范? [是/否]
  - 组件是否可复用? [是/否]
  - 状态管理是否合理? [是/否]
  - API 封装是否正确? [是/否]

安全层:
  - 权限是否足够? [是/否]
  - 数据是否加密? [是/否]
  - 输入是否验证? [是/否]
  - SQL 是否防护? [是/否]
```

---

## 💡 OpsCenter 项目规范

### 数据库规范

```python
# 字段命名: snake_case
created_at: datetime
updated_at: datetime
deleted_at: datetime | None

# 索引命名: ix_表名_字段名
ix_users_email
ix_users_status

# 外键命名: fk_表名_字段名
fk_orders_user_id

# 唯一约束: uq_表名_字段名
uq_users_username
```

### API 规范

```python
# 路由命名: kebab-case
GET /api/v1/users
GET /api/v1/users/{id}
POST /api/v1/users
PUT /api/v1/users/{id}
DELETE /api/v1/users/{id}

# 响应格式统一
{
  "code": 200,
  "message": "success",
  "data": {...}
}

# 错误响应
{
  "code": 400,
  "message": "Bad Request",
  "detail": "Invalid parameter: email"
}
```

### 前端规范

```javascript
// 组件命名: PascalCase
export default defineComponent({
  name: 'UserList'
})

// 路由命名: kebab-case
{
  path: '/users',
  name: 'user-list',
  component: () => import('@/views/users/index.vue')
}

// API 封装
import request from '@/api/index'

// baseURL 已包含 /api/v1，不要再加前缀
export const getUserList = (params) => request.get('/users', { params })
```

---

## 📊 Token 优化策略

1. **使用表格替代文字**
   ```
   ❌: 用户表包含 id、name、email、status 等字段
   ✅:
   | 字段 | 类型 | 说明 |
   |------|------|------|
   | id | int | 主键 |
   | name | varchar | 姓名 |
   ```

2. **使用代码块**
   ```
   ❌: 响应格式是 {"code": 200, "message": "success"}
   ✅:
   ```json
   {
     "code": 200,
     "message": "success"
   }
   ```

3. **引用复用**
   ```
   ❌: 重复定义用户模型
   ✅: 引用 `app/models/user.py`
   ```

---

## 🔄 模板使用示例

### 输入

```yaml
需求分析报告:
  核心功能: "批量导出用户数据为 CSV 文件"
  技术方案:
    架构设计:
      - 新增服务: ExportService
      - 新增 API: POST /api/v1/users/export
      - 新增前端组件: ExportDialog
```

### 输出

```markdown
# 架构设计文档

## 2. 数据库设计

### 2.1 表结构
无需新增表，使用现有 User 表

### 2.2 索引设计
无需新增索引

## 3. API 设计

### 3.1 API 列表

**POST /api/v1/users/export**
- 描述: 批量导出用户数据
- 权限: user:export
- 请求体:
  ```json
  {
    "filters": {
      "status": "active",
      "created_after": "2024-01-01"
    },
    "fields": ["id", "name", "email", "status", "created_at"]
  }
  ```
- 响应:
  ```
  Content-Type: text/csv
  Content-Disposition: attachment; filename=users_20240402.csv
  ```

## 4. 服务层设计

### 4.1 服务接口

```python
class ExportService:
    async def export_users(
        self,
        filters: dict,
        fields: list[str],
        format: str = "csv"
    ) -> bytes:
        """导出用户数据"""
        pass
```

## 5. 前端设计

### 5.1 组件设计

**ExportDialog.vue**
```vue
<script setup>
const props = defineProps({
  visible: Boolean,
  fields: Array
})

const emit = defineEmits(['export', 'close'])
</script>
```

## 6. 安全设计

### 6.1 权限控制
- 资源: users
- 操作: export
- 权限码: user:export
- 允许角色: admin

### 6.2 数据加密
- CSV 文件中的敏感字段脱敏显示
- 手机号: 138****1234
```

---

## 📝 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2026-04 | 初始版本 |

---

**提示**: 使用此模板时，请确保遵循 OpsCenter 项目的规范，不要重复造轮子。
