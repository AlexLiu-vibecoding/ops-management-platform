# 代码品质问题清单

> 记录项目中不优雅、没有品味的代码和功能，供后续改进参考

## 一、架构与设计问题

### 1. 上帝文件 (God File) 反模式 🔴

| 文件 | 行数 | 类/函数数量 | 问题描述 |
|------|------|-------------|----------|
| `app/models/__init__.py` | 1169行 | 48个类 | 模型定义过于集中，违反单一职责原则。应拆分为 `models/user.py`, `models/instance.py` 等独立模块 |
| `app/schemas/__init__.py` | 836行 | 64个类 | Schema定义过于集中，应按功能模块拆分 |
| `app/services/notification.py` | 1069行 | - | 通知服务过于复杂，承载了太多功能（钉钉、邮件、Webhook、模板渲染等） |
| `app/api/approval.py` | 1291行 | - | 审批API过于庞大，应拆分为多个子模块 |

**改进建议**: 按业务领域拆分，每个文件不超过300行，单一职责。

---

### 2. 重复代码泛滥 🔴

#### 数据库查询模式重复
- **200+ 处** `db.query(Model).filter(Model.id == xxx).first()`
- **redis.py** 中 13 处相同的实例查询逻辑
- **slow_query.py** 中 10+ 处相同的实例查询逻辑

**示例**:
```python
# 在 redis.py 中重复了13次:
instance = db.query(RedisInstance).filter(RedisInstance.id == instance_id).first()
if not instance:
    raise HTTPException(status_code=404, detail="Instance not found")
```

**改进建议**: 
- 创建通用查询函数或基类方法
- 使用 `get_by_id_or_404()` 通用方法

#### 权限检查代码重复
每个API都重复编写权限检查逻辑，应使用装饰器统一处理。

---

## 二、代码规范问题

### 3. 异常处理不规范 🟡

- **94处** `except Exception` 捕获所有异常
- 大量空的 except 块，静默吞掉异常
- 缺乏具体的异常类型处理

**反例**:
```python
try:
    # 某些操作
except Exception:
    pass  # 静默吞掉异常，没有日志记录
```

**正例**:
```python
try:
    # 某些操作
except ValueError as e:
    logger.warning(f"参数错误: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"操作失败: {e}", exc_info=True)
    raise
```

---

### 4. 比较运算符不规范 🟡

- **16处** 使用 `== None` / `!= None`
- 应使用 `is None` / `is not None`

---

### 5. 硬编码和魔法数字 🟡

| 位置 | 问题 | 建议 |
|------|------|------|
| `main.py:189` | 硬编码默认密码 `admin123` | 使用随机生成或强制首次修改 |
| `main.py:158` | 硬编码用户名 `admin` | 配置化或可配置 |
| 多处 | 魔法数字 `500`（错误信息截断） | 定义为常量 `ERROR_PREVIEW_LENGTH = 500` |
| 多处 | 魔法数字 `10`（超时秒数） | 定义为常量 `DEFAULT_TIMEOUT = 10` |
| 多处 | 状态码如 `200`, `404` | 使用 `status.HTTP_200_OK` |

---

## 三、待办事项 (TODO) 遗留

### 6. 未完成的功能 🟡

```python
# approval.py:253
# TODO: 实际连接数据库获取数据库列表

# batch_operations.py:368
# TODO: 触发异步执行

# inspection_service.py:373
# TODO: 实现通知发送逻辑

# alert_aggregation.py:322
# TODO: 实现特定通道的通知发送
```

---

## 四、设计模式问题

### 7. 重复的数据库会话管理 🔴

每个API函数都重复以下模式：
```python
db = SessionLocal()
try:
    # 操作
    db.commit()
except Exception as e:
    db.rollback()
    raise
finally:
    db.close()
```

**改进建议**: 
- 使用装饰器统一处理
- 或使用上下文管理器 `with get_db() as db:`

---

### 8. 缺乏统一的响应封装 🟡

- 有些API直接返回字典
- 有些使用 `MessageResponse`
- 有些返回原始对象
- 错误响应格式不一致

**改进建议**: 定义统一的响应模型：
```python
class APIResponse(BaseModel):
    code: int
    message: str
    data: Optional[Any]
```

---

### 9. Session 绑定问题 🔴

异步函数中传递 ORM 对象会导致 Session 绑定问题：
```python
# 问题代码
async def execute_script_async(execution_id: int, script: Script, ...):
    # script 是从其他 Session 传入的对象
    script.script_type.value  # 报错：Instance is not bound to a Session
```

**改进建议**: 传递 ID 而非对象，在函数内部重新查询。

---

## 五、命名和一致性问题

### 10. 命名不一致 🟡

| 方面 | 问题示例 |
|------|----------|
| 文件名 | 单数 `permission.py` vs 复数 `permissions.py` |
| 分隔符 | 下划线 `scheduled_tasks.py` vs 连字符目录名 |
| 装饰器 | `require_permission` vs `get_current_user` |
| 变量名 | `user_id` vs `uid` vs `id` |
| 状态值 | `"enabled"` vs `"active"` vs `True` |

---

## 六、性能问题

### 11. N+1 查询问题 🔴

在循环中查询数据库：
```python
for b in bindings:
    channel = db.query(DingTalkChannel).filter(...).first()  # N次查询
```

**改进建议**: 使用 `joinedload` 或 `in_` 查询优化

---

### 12. 大量数据查询未分页 🔴

多处 `.all()` 查询没有限制返回数量，可能导致内存溢出。

---

## 七、安全与维护问题

### 13. 默认安全配置不当 🔴

- 默认密码 `admin123` 过于简单
- AES_KEY 使用开发默认值
- 敏感信息可能记录在日志中

---

### 14. 缺乏输入验证 🟡

- 部分接口缺少参数校验
- SQL 注入风险（虽然已经使用了参数化查询）

---

## 八、文档和注释问题

### 15. 注释率过低 🟡

抽查文件注释率：
- `container.py`: 4.5%
- `scheduler.py`: 5.8%
- `ai_model_service.py`: 3.5%

**改进建议**: 关键函数和复杂逻辑应添加文档字符串。

---

### 16. 文档与代码不同步 🟡

- 部分函数的 docstring 与实际参数不匹配
- AGENTS.md 中的信息可能已过时

---

## 九、前端代码问题

### 17. 前端组件同样庞大 🔴

- 视图组件行数过多
- 缺乏组件拆分
- 重复的逻辑未提取为 composables

---

## 十、其他问题

### 18. 导入混乱 🟡

- 循环导入风险
- 相对导入和绝对导入混用
- 大量导入放在函数内部（虽然是为了避免循环导入）

---

### 19. 配置分散 🟡

配置散落在多个地方：
- `config/core.py`
- `main.py`
- 数据库 `GlobalConfig` 表
- 环境变量

---

### 20. 测试覆盖不足 🔴

- 缺乏单元测试
- 缺乏集成测试
- 没有自动化测试流程

---

## 改进优先级

| 优先级 | 问题 | 影响 | 预估工作量 |
|--------|------|------|-----------|
| P0 | 上帝文件拆分 | 可维护性 | 2-3天 |
| P0 | 重复代码抽象 | 可维护性 | 1-2天 |
| P0 | Session 绑定问题 | 稳定性 | 半天 |
| P1 | 异常处理规范化 | 稳定性 | 1天 |
| P1 | N+1 查询优化 | 性能 | 1天 |
| P1 | 统一响应封装 | 一致性 | 半天 |
| P2 | 命名规范化 | 可读性 | 1天 |
| P2 | 硬编码提取 | 可配置性 | 半天 |
| P2 | 数据库会话管理统一 | 可维护性 | 1天 |
| P3 | 注释完善 | 可维护性 | 持续 |
| P3 | 测试覆盖 | 质量 | 1周+ |

---

## 备注

- 生成时间: 2026-04-04
- 统计范围: backend/app 目录下的 Python 代码
- 问题数量统计: 🔴 严重(12个) | 🟡 中等(8个)
