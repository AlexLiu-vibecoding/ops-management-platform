# 代码生成模板 (Code Generation Template)

> 基于架构设计生成可直接运行的代码，遵循项目规范和最佳实践。

---

## 模板元数据

```
版本: v1.0
创建日期: 2026-04
适用阶段: 代码生成 → 单元测试
目标: 架构设计 → 可运行代码
前置条件: 完成架构设计文档
```

---

## 🎯 核心原则

1. **规范优先** - 严格遵守项目代码规范
2. **类型安全** - 完整的类型注解
3. **文档完善** - 每个函数都有文档字符串
4. **可测试性** - 代码结构便于测试

---

## 📥 输入定义

```yaml
架构设计文档:
  type: object
  required: true
  properties:
    数据库设计:
      表结构: array
      索引设计: array
    API 设计:
      路由列表: array
      请求响应定义: object
    服务层设计:
      服务列表: array
      方法定义: array
    前端设计:
      页面结构: object
      组件定义: array

项目规范:
  type: object
  required: true
  properties:
    编码规范: object
    文件结构: object
    导入规范: array
    命名规范: object
```

---

## 🧠 结构化思维 (SoT) 流程

### Step 1: 数据模型生成 (2 分钟)

```
目标: 生成 SQLAlchemy 模型和 Pydantic Schema

思考框架:
1. 模型定义: 使用 Base 定义模型
2. 字段定义: 根据表结构定义字段
3. 关系定义: 使用 relationship 定义关系
4. 约束定义: 使用 UniqueConstraint, Index 定义约束
5. Schema 定义: 创建对应的 Pydantic Schema

输出格式:

# backend/app/models/[table].py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class [Table](Base):
    """[表描述]"""
    __tablename__ = "[table_name]"

    # 主键
    id = Column(Integer, primary_key=True, index=True)

    # 字段定义
    [field] = Column([Type], nullable=[bool], default=[value], comment="[comment]")

    # 外键
    [fk_field] = Column(Integer, ForeignKey("[table].[field]"))

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    [relation] = relationship("[RelatedTable]", back_populates="[field]")

    # 索引
    __table_args__ = (
        Index("ix_[table]_[field]", "[field]"),
        UniqueConstraint("[field1]", "[field2]", name="uq_[table]_[field1]_[field2]"),
    )

    def __repr__(self):
        return f"<[Table](id={self.id})>"

# backend/app/schemas/[table].py
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime

class [Table]Base(BaseModel):
    """[表]基础模型"""
    [field]: [Type] = Field(..., description="[描述]")

    class Config:
        from_attributes = True

class [Table]Create([Table]Base):
    """创建[表]请求"""
    pass

class [Table]Update([Table]Base):
    """更新[表]请求"""
    [field]: Optional[Type] = Field(None, description="[描述]")

class [Table]Response([Table]Base):
    """[表]响应"""
    id: int
    created_at: datetime
    updated_at: datetime
```

**验证检查点**:
- [ ] 所有字段都有类型注解？
- [ ] 所有字段都有注释？
- [ ] 关系定义是否正确？
- [ ] Schema 是否完整？
- [ ] 是否遵循命名规范？

---

### Step 2: API 层生成 (3 分钟)

```
目标: 生成 FastAPI 路由和依赖

思考框架:
1. 路由定义: 使用 APIRouter 定义路由
2. 依赖注入: 使用 Depends 注入依赖
3. 权限控制: 使用自定义依赖检查权限
4. 参数验证: 使用 Pydantic Schema 验证参数
5. 响应处理: 统一响应格式

输出格式:

# backend/app/api/[resource].py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import [Model]
from app.schemas import [Create], [Update], [Response]
from app.deps import get_current_user, require_permission
from app.utils.structured_logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/[resource]", tags=["[资源]"])

@router.get("", response_model=List[[Response]])
async def list_[resource](
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _ = Depends(require_permission("[resource]:list"))
):
    """
    获取[资源]列表

    Args:
        page: 页码
        page_size: 每页数量
        db: 数据库会话
        current_user: 当前用户
        _: 权限检查

    Returns:
        [资源]列表
    """
    offset = (page - 1) * page_size
    items = db.query([Model]).offset(offset).limit(page_size).all()
    return items

@router.post("", response_model=[Response], status_code=status.HTTP_201_CREATED)
async def create_[resource](
    data: [Create],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _ = Depends(require_permission("[resource]:create"))
):
    """
    创建[资源]

    Args:
        data: 创建数据
        db: 数据库会话
        current_user: 当前用户
        _: 权限检查

    Returns:
        创建的[资源]
    """
    try:
        item = [Model](**data.model_dump())
        db.add(item)
        db.commit()
        db.refresh(item)
        logger.info(f"[操作] 创建[资源]成功: {item.id}")
        return item
    except Exception as e:
        db.rollback()
        logger.error(f"[操作] 创建[资源]失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{item_id}", response_model=[Response])
async def get_[resource](
    item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _ = Depends(require_permission("[resource]:view"))
):
    """
    获取[资源]详情

    Args:
        item_id: 资源ID
        db: 数据库会话
        current_user: 当前用户
        _: 权限检查

    Returns:
        [资源]详情
    """
    item = db.query([Model]).filter([Model].id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="[资源]不存在")
    return item

@router.put("/{item_id}", response_model=[Response])
async def update_[resource](
    item_id: int,
    data: [Update],
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _ = Depends(require_permission("[resource]:update"))
):
    """
    更新[资源]

    Args:
        item_id: 资源ID
        data: 更新数据
        db: 数据库会话
        current_user: 当前用户
        _: 权限检查

    Returns:
        更新后的[资源]
    """
    item = db.query([Model]).filter([Model].id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="[资源]不存在")

    try:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(item, key, value)

        db.commit()
        db.refresh(item)
        logger.info(f"[操作] 更新[资源]成功: {item_id}")
        return item
    except Exception as e:
        db.rollback()
        logger.error(f"[操作] 更新[资源]失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_[resource](
    item_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    _ = Depends(require_permission("[resource]:delete"))
):
    """
    删除[资源]

    Args:
        item_id: 资源ID
        db: 数据库会话
        current_user: 当前用户
        _: 权限检查
    """
    item = db.query([Model]).filter([Model].id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="[资源]不存在")

    try:
        db.delete(item)
        db.commit()
        logger.info(f"[操作] 删除[资源]成功: {item_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"[操作] 删除[资源]失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**验证检查点**:
- [ ] 所有路由都有权限检查？
- [ ] 所有参数都有类型注解？
- [ ] 错误处理是否完善？
- [ ] 日志记录是否完整？
- [ ] 响应格式是否统一？

---

### Step 3: 服务层生成 (2 分钟)

```
目标: 生成业务逻辑服务

思考框架:
1. 服务定义: 使用类定义服务
2. 依赖注入: 注入数据库会话和其他服务
3. 异常处理: 定义和使用自定义异常
4. 审计日志: 使用装饰器记录审计
5. 事务管理: 使用数据库事务

输出格式:

# backend/app/services/[service].py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models import [Model]
from app.schemas import [Create], [Update]
from app.core.exceptions import [Exception]
from app.utils.audit_decorator import async_audit_log
from app.utils.structured_logger import get_logger

logger = get_logger(__name__)

class [Service]:
    """[服务描述]"""

    def __init__(self, db: Session):
        self.db = db

    @async_audit_log(
        operation="[OPERATION]",
        field_extractor=lambda self, result: {"id": result.id}
    )
    async def create_[resource](self, data: [Create]) -> [Model]:
        """
        创建[资源]

        Args:
            data: 创建数据

        Returns:
            创建的[资源]

        Raises:
            [Exception]: [异常描述]
        """
        try:
            item = [Model](**data.model_dump())
            self.db.add(item)
            self.db.commit()
            self.db.refresh(item)
            logger.info(f"[操作] 创建[资源]成功: {item.id}")
            return item
        except Exception as e:
            self.db.rollback()
            logger.error(f"[操作] 创建[资源]失败: {e}", exc_info=True)
            raise [Exception](f"创建[资源]失败: {str(e)}") from e

    async def get_[resource](self, item_id: int) -> Optional[[Model]]:
        """
        获取[资源]

        Args:
            item_id: 资源ID

        Returns:
            [资源]或 None
        """
        return self.db.query([Model]).filter([Model].id == item_id).first()

    async def list_[resource](
        self,
        page: int = 1,
        page_size: int = 20,
        **filters
    ) -> List[[Model]]:
        """
        获取[资源]列表

        Args:
            page: 页码
            page_size: 每页数量
            **filters: 过滤条件

        Returns:
            [资源]列表
        """
        query = self.db.query([Model])

        # 应用过滤条件
        for key, value in filters.items():
            if hasattr([Model], key) and value is not None:
                query = query.filter(getattr([Model], key) == value)

        offset = (page - 1) * page_size
        return query.offset(offset).limit(page_size).all()

    async def update_[resource](
        self,
        item_id: int,
        data: [Update]
    ) -> [Model]:
        """
        更新[资源]

        Args:
            item_id: 资源ID
            data: 更新数据

        Returns:
            更新后的[资源]

        Raises:
            [Exception]: [异常描述]
        """
        item = await self.get_[resource](item_id)
        if not item:
            raise [Exception]("[资源]不存在")

        try:
            for key, value in data.model_dump(exclude_unset=True).items():
                setattr(item, key, value)

            self.db.commit()
            self.db.refresh(item)
            logger.info(f"[操作] 更新[资源]成功: {item_id}")
            return item
        except Exception as e:
            self.db.rollback()
            logger.error(f"[操作] 更新[资源]失败: {e}", exc_info=True)
            raise [Exception](f"更新[资源]失败: {str(e)}") from e

    async def delete_[resource](self, item_id: int) -> bool:
        """
        删除[资源]

        Args:
            item_id: 资源ID

        Returns:
            是否删除成功

        Raises:
            [Exception]: [异常描述]
        """
        item = await self.get_[resource](item_id)
        if not item:
            raise [Exception]("[资源]不存在")

        try:
            self.db.delete(item)
            self.db.commit()
            logger.info(f"[操作] 删除[资源]成功: {item_id}")
            return True
        except Exception as e:
            self.db.rollback()
            logger.error(f"[操作] 删除[资源]失败: {e}", exc_info=True)
            raise [Exception](f"删除[资源]失败: {str(e)}") from e
```

**验证检查点**:
- [ ] 所有方法都有文档字符串？
- [ ] 所有方法都有类型注解？
- [ ] 异常处理是否完善？
- [ ] 审计日志是否完整？
- [ ] 事务管理是否正确？

---

### Step 4: 前端生成 (2 分钟)

```
目标: 生成 Vue 3 组件

思考框架:
1. 组件定义: 使用 defineComponent 定义组件
2. Props 定义: 使用 defineProps 定义属性
3. Emits 定义: 使用 defineEmits 定义事件
4. 状态管理: 使用 ref/reactive 管理状态
5. API 封装: 封装 API 调用

输出格式:

# frontend/src/views/[resource]/index.vue
<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/index'

// 状态定义
const loading = ref(false)
const dataList = ref([])
const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

// 获取数据
const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      page_size: pagination.value.pageSize
    }

    // 注意：baseURL 已包含 /api/v1，不要再加前缀
    const response = await request.get('/[resource]', { params })
    dataList.value = response.data
    pagination.value.total = response.total
  } catch (error) {
    console.error('获取数据失败:', error)
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    loading.value = false
  }
}

// 分页改变
const handlePageChange = (page) => {
  pagination.value.page = page
  fetchData()
}

// 创建
const handleCreate = async (data) => {
  try {
    await request.post('/[resource]', data)
    ElMessage.success('创建成功')
    fetchData()
  } catch (error) {
    console.error('创建失败:', error)
    ElMessage.error(error.response?.data?.detail || '创建失败')
  }
}

// 更新
const handleUpdate = async (id, data) => {
  try {
    await request.put(`/[resource]/${id}`, data)
    ElMessage.success('更新成功')
    fetchData()
  } catch (error) {
    console.error('更新失败:', error)
    ElMessage.error(error.response?.data?.detail || '更新失败')
  }
}

// 删除
const handleDelete = async (id) => {
  try {
    await request.delete(`/[resource]/${id}`)
    ElMessage.success('删除成功')
    fetchData()
  } catch (error) {
    console.error('删除失败:', error)
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}

// 初始化
onMounted(() => {
  fetchData()
})
</script>

<template>
  <div class="[resource]-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>[资源]管理</h2>
    </div>

    <!-- 操作栏 -->
    <div class="action-bar">
      <el-button type="primary" @click="handleCreate">
        新增[资源]
      </el-button>
    </div>

    <!-- 数据表格 -->
    <el-table
      v-loading="loading"
      :data="dataList"
      border
      stripe
    >
      <!-- 表格列 -->
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="名称" />

      <!-- 操作列 -->
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleUpdate(row.id, row)">
            编辑
          </el-button>
          <el-button
            size="small"
            type="danger"
            @click="handleDelete(row.id)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      v-model:current-page="pagination.page"
      v-model:page-size="pagination.pageSize"
      :total="pagination.total"
      :page-sizes="[20, 50, 100]"
      layout="total, sizes, prev, pager, next, jumper"
      @current-change="handlePageChange"
      @size-change="handlePageChange"
    />
  </div>
</template>

<style scoped>
.[resource]-page {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.action-bar {
  margin-bottom: 20px;
}

.el-pagination {
  margin-top: 20px;
  text-align: right;
}
</style>
```

**验证检查点**:
- [ ] 组件是否使用 `<script setup>`？
- [ ] API 调用是否正确？
- [ ] 状态管理是否合理？
- [ ] 错误处理是否完善？
- [ ] 样式是否 scoped？

---

## 📤 输出格式

```
backend/
  app/
    models/
      [table].py
    schemas/
      [table].py
    api/
      [resource].py
    services/
      [service].py
    core/
      exceptions.py

frontend/
  src/
    views/
      [resource]/
        index.vue
    api/
      [resource].js
```

---

## 🔍 自我验证清单

```yaml
代码质量:
  - 类型注解完整? [是/否]
  - 文档字符串完整? [是/否]
  - 命名符合规范? [是/否]
  - 代码格式正确? [是/否]

功能完整性:
  - CRUD 完整? [是/否]
  - 权限控制完整? [是/否]
  - 异常处理完整? [是/否]
  - 日志记录完整? [是/否]

可测试性:
  - 依赖注入合理? [是/否]
  - 方法职责单一? [是/否]
  - 代码可模拟? [是/否]

安全性:
  - 参数验证完整? [是/否]
  - SQL 注入防护? [是/否]
  - XSS 防护? [是/否]
  - 权限检查完整? [是/否]
```

---

## 💡 代码规范速查

### Python 代码规范

```python
# 1. 导入顺序
# 标准库
import os
from typing import Optional

# 第三方库
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

# 本地模块
from app.database import get_db
from app.models import User

# 2. 类型注解
def get_user(user_id: int) -> Optional[User]:
    pass

# 3. 文档字符串
def get_user(user_id: int) -> Optional[User]:
    """
    获取用户

    Args:
        user_id: 用户ID

    Returns:
        用户对象或 None

    Raises:
        ValueError: 用户不存在
    """
    pass

# 4. 异常处理
try:
    # 操作
    pass
except ValueError as e:
    # 具体异常
    raise Exception("操作失败") from e
except Exception as e:
    # 通用异常
    logger.error(f"未知错误: {e}", exc_info=True)
    raise

# 5. 日志记录
logger.info(f"[操作] 描述: {params}")
logger.error(f"[操作] 失败: {error}", exc_info=True)
```

### JavaScript 代码规范

```javascript
// 1. 导入顺序
// Vue 核心
import { ref, onMounted } from 'vue'

// UI 组件
import { ElMessage } from 'element-plus'

// 工具函数
import request from '@/api/index'

// 2. 组件定义
<script setup>
// Props
const props = defineProps({
  visible: Boolean,
  data: Object
})

// Emits
const emit = defineEmits(['submit', 'cancel'])

// 状态
const loading = ref(false)
const form = ref({})

// 方法
const handleSubmit = async () => {
  try {
    loading.value = true
    await request.post('/api', form.value)
    ElMessage.success('操作成功')
    emit('submit')
  } catch (error) {
    ElMessage.error('操作失败')
  } finally {
    loading.value = false
  }
}

// 生命周期
onMounted(() => {
  // 初始化
})
</script>
```

---

## 📊 Token 优化策略

1. **使用模板**
   ```
   ❌: 重复写完整的函数模板
   ✅: 使用代码模板，只填差异部分
   ```

2. **压缩注释**
   ```
   ❌: 非常详细的注释
   ✅: 简洁的注释，重点说明逻辑
   ```

3. **引用复用**
   ```
   ❌: 重复相同的代码块
   ✅: 提取公共方法
   ```

---

## 🔄 模板使用示例

### 输入

```yaml
架构设计文档:
  数据库设计:
    表结构:
      - name: exports
        fields:
          - name: id, type: int
          - name: filename, type: varchar
          - name: status, type: varchar
  API 设计:
    路由列表:
      - POST /api/v1/exports
  服务层设计:
    服务列表:
      - name: ExportService
```

### 输出

```python
# backend/app/models/export.py
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.database import Base

class Export(Base):
    """导出记录"""
    __tablename__ = "exports"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False, comment="文件名")
    status = Column(String(50), nullable=False, comment="状态")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Export(id={self.id}, filename={self.filename})>"
```

---

## 📝 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2026-04 | 初始版本 |

---

**提示**: 使用此模板时，请确保遵循 OpsCenter 项目的代码规范，不要重复造轮子。
