# 功能规格模板

> 所有新功能开发前，先填写此规格，用户确认后再开发。
> 
> **核心原则**：不追求代码相同，追求行为一致。

---

## 基本信息

- **规格编号**: `SPEC-XXX`
- **功能名称**: 
- **优先级**: P0(紧急) / P1(重要) / P2(一般)
- **预计影响范围**: 前端 / 后端 / 数据库 / 全部
- **状态**: 待开发 / 开发中 / ✅ 已完成

---

## 一、需求背景

### 1.1 问题描述
<!-- 当前存在什么问题，为什么需要这个功能 -->


### 1.2 目标
<!-- 这个功能要达成什么效果 -->


### 1.3 不做的事（边界）
<!-- 明确排除的范围，防止擅自扩展 -->



---

## 二、数据模型（精确约束）

### 2.1 数据库表结构

```sql
CREATE TABLE xxx (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    -- 精确定义每个字段
);
```

### 2.2 Pydantic Schema

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class XxxCreate(BaseModel):
    name: str
    description: Optional[str] = None

class XxxResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
```

---

## 三、API 接口定义（精确约束）

### 3.1 接口列表

| 接口 | 方法 | 说明 | 权限 |
|------|------|------|------|
| `/api/v1/xxx` | GET | 列表查询 | 登录用户 |
| `/api/v1/xxx` | POST | 创建 | admin |
| `/api/v1/xxx/{id}` | GET | 详情 | 登录用户 |
| `/api/v1/xxx/{id}` | PUT | 更新 | admin |
| `/api/v1/xxx/{id}` | DELETE | 删除 | admin |

### 3.2 接口详细定义

#### GET /api/v1/xxx（列表查询）

**请求参数：**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | int | 否 | 1 | 页码 |
| page_size | int | 否 | 20 | 每页数量，最大100 |
| name | string | 否 | - | 名称筛选（模糊匹配） |

**成功响应：**
```json
{
  "items": [
    {
      "id": 1,
      "name": "xxx",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

**错误响应：**
```json
{
  "error": "VALIDATION_ERROR",
  "message": "page_size 超过最大值100"
}
```

#### POST /api/v1/xxx（创建）

**请求体：**
```json
{
  "name": "xxx",
  "description": "xxx"
}
```

**成功响应（201）：**
```json
{
  "id": 1,
  "name": "xxx",
  "description": "xxx",
  "created_at": "2024-01-01T00:00:00Z"
}
```

**错误响应（400）：**
```json
{
  "error": "DUPLICATE_NAME",
  "message": "名称已存在"
}
```

---

## 四、测试用例（行为约束）

> ⚠️ 这是确保行为一致性的核心，AI 生成的代码必须通过以下测试

### 4.1 接口测试用例

#### 用例1：创建成功
```python
def test_create_success(client, admin_token):
    """测试创建成功"""
    response = client.post(
        "/api/v1/xxx",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "test", "description": "test desc"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test"
    assert data["description"] == "test desc"
    assert "id" in data
    assert "created_at" in data
```

#### 用例2：创建失败-名称重复
```python
def test_create_duplicate_name(client, admin_token):
    """测试创建失败-名称重复"""
    # 先创建一个
    client.post(
        "/api/v1/xxx",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "test"}
    )
    # 再创建同名
    response = client.post(
        "/api/v1/xxx",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "test"}
    )
    assert response.status_code == 400
    assert response.json()["error"] == "DUPLICATE_NAME"
```

#### 用例3：列表查询-分页
```python
def test_list_pagination(client, admin_token):
    """测试列表分页"""
    # 创建25条数据
    for i in range(25):
        client.post(
            "/api/v1/xxx",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": f"test{i}"}
        )
    
    # 查询第一页
    response = client.get(
        "/api/v1/xxx?page=1&page_size=20",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 20
    assert data["total"] == 25
    assert data["page"] == 1
    assert data["page_size"] == 20
```

#### 用例4：权限校验-未登录
```python
def test_list_unauthorized(client):
    """测试未登录访问"""
    response = client.get("/api/v1/xxx")
    assert response.status_code == 401
```

#### 用例5：权限校验-非管理员
```python
def test_create_forbidden(client, developer_token):
    """测试非管理员创建"""
    response = client.post(
        "/api/v1/xxx",
        headers={"Authorization": f"Bearer {developer_token}"},
        json={"name": "test"}
    )
    assert response.status_code == 403
```

### 4.2 边界测试

```python
def test_page_size_max(client, admin_token):
    """测试分页最大值"""
    response = client.get(
        "/api/v1/xxx?page_size=101",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400

def test_name_too_long(client, admin_token):
    """测试名称超长"""
    response = client.post(
        "/api/v1/xxx",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": "a" * 101}
    )
    assert response.status_code == 422
```

---

## 五、实现位置

### 5.1 后端文件

| 文件 | 说明 |
|------|------|
| `backend/app/api/xxx.py` | API 路由 |
| `backend/app/models/xxx.py` | 数据模型 |
| `backend/app/schemas/xxx.py` | Pydantic Schema |
| `backend/tests/test_xxx_api.py` | 测试用例 |

### 5.2 前端文件

| 文件 | 说明 |
|------|------|
| `frontend/src/views/xxx/index.vue` | 页面组件 |
| `frontend/src/api/xxx.js` | API 封装 |

---

## 六、验收标准

### 6.1 功能验收
- [ ] 所有测试用例通过
- [ ] API 行为符合定义
- [ ] 错误处理正确

### 6.2 非功能验收
- [ ] 日志记录正确
- [ ] 权限控制正确

---

## 七、用户确认

- **确认状态**: 待确认 / 已确认 / 需修改
- **确认时间**: 
- **修改意见**: 

---

*规格原则：数据结构精确 + API 签名精确 + 测试用例约束行为*
