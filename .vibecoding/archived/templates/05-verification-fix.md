# 验证与修复模板 (Verification & Fix Template)

> 自动验证代码质量，识别问题并提供修复方案。

---

## 模板元数据

```
版本: v1.0
创建日期: 2026-04
适用阶段: 测试执行 → 代码修复
目标: 测试失败 → 问题定位 → 代码修复 → 测试通过
前置条件: 完成测试执行
```

---

## 🎯 核心原则

1. **自动验证** - 自动运行测试和检查
2. **问题定位** - 精确定位问题位置
3. **快速修复** - 提供修复方案
4. **回归测试** - 修复后重新验证

---

## 📥 输入定义

```yaml
测试结果:
  type: object
  required: true
  properties:
    测试通过: boolean
    失败数量: number
    失败信息: array
    覆盖率: number

代码检查结果:
  type: object
  properties:
    lint_错误: array
    类型错误: array
    安全警告: array
```

---

## 🧠 结构化思维 (SoT) 流程

### Step 1: 测试结果分析 (1 分钟)

```
目标: 分析测试失败原因

思考框架:
1. 失败分类: 语法错误、逻辑错误、断言失败
2. 失败定位: 定位到具体代码行
3. 根因分析: 分析根本原因
4. 影响范围: 分析影响范围

输出格式:

测试失败分析:
  总测试数: [数量]
  通过数: [数量]
  失败数: [数量]
  跳过数: [数量]
  覆盖率: [百分比]

失败详情:
  - 测试名: [TestX.test_method]
    错误类型: [AssertionError/TypeError/ValueError]
    错误信息: [错误信息]
    堆栈信息:
      File "[文件路径]", line [行号], in [方法]
        [代码行]
    根因分析: [根因描述]
    影响范围: [影响范围]

分类统计:
  - 语法错误: [数量]
  - 逻辑错误: [数量]
  - 断言失败: [数量]
  - 超时错误: [数量]

优先级排序:
  1. [最高优先级失败]
  2. [次高优先级失败]
  ...
```

**验证检查点**:
- [ ] 失败原因分析正确？
- [ ] 根因定位准确？
- [ ] 影响范围明确？
- [ ] 优先级排序合理？

---

### Step 2: 代码质量检查 (2 分钟)

```
目标: 检查代码质量问题

思考框架:
1. 代码风格: 检查是否符合规范
2. 类型安全: 检查类型注解是否完整
3. 安全问题: 检查是否有安全漏洞
4. 性能问题: 检查是否有性能隐患

输出格式:

代码质量检查报告:

1. 代码风格检查 (ruff/black)
   - 错误数: [数量]
   - 警告数: [数量]
   - 问题列表:
     - 文件: [文件路径]
       行号: [行号]
       错误码: [错误码]
       错误信息: [错误信息]
       严重性: [error/warning]
       修复建议: [建议]

2. 类型检查 (mypy/pyright)
   - 错误数: [数量]
   - 问题列表:
     - 文件: [文件路径]
       行号: [行号]
       错误类型: [类型不匹配/缺失类型注解]
       错误信息: [错误信息]
       修复建议: [建议]

3. 安全检查 (bandit/safety)
   - 漏洞数: [数量]
   - 问题列表:
     - 漏洞类型: [SQL注入/XSS/硬编码密钥]
     - 严重性: [high/medium/low]
     - 文件: [文件路径]
       行号: [行号]
       修复建议: [建议]

4. 性能检查 (pylint/radon)
   - 复杂度过高: [数量]
   - 潜在性能问题: [数量]
   - 问题列表:
     - 文件: [文件路径]
       方法: [方法名]
       圈复杂度: [数值]
       修复建议: [建议]
```

**验证检查点**:
- [ ] 所有检查都执行？
- [ ] 问题定位准确？
- [ ] 修复建议可行？
- [ ] 优先级排序合理？

---

### Step 3: 问题修复 (3 分钟)

```
目标: 修复发现的问题

思考框架:
1. 修复策略: 按优先级修复
2. 修复方案: 提供具体修复代码
3. 回归测试: 修复后重新测试
4. 验证通过: 确保修复有效

输出格式:

修复计划:

P0 - 立即修复:
  1. 问题: [问题描述]
     文件: [文件路径]
     行号: [行号]
     原因: [原因]
     修复代码:
       ```diff
       - 原代码
       + 新代码
       ```
     验证方法: [验证方法]

P1 - 近期修复:
  2. 问题: [问题描述]
     ...

P2 - 中期修复:
  3. 问题: [问题描述]
     ...

修复执行:

修复 #1: [问题描述]
  状态: [进行中/已完成/失败]
  修复时间: [时间戳]

  原代码:
    ```python
    [原代码]
    ```

  修复后代码:
    ```python
    [修复后代码]
    ```

  验证结果:
    - 测试通过: [是/否]
    - 代码检查通过: [是/否]
    - 覆盖率变化: [变化百分比]

修复 #2: [问题描述]
  ...
```

**验证检查点**:
- [ ] 修复方案可行？
- [ ] 修复代码正确？
- [ ] 验证方法有效？
- [ ] 回归测试通过？

---

### Step 4: 回归验证 (2 分钟)

```
目标: 验证修复后的问题

思考框架:
1. 重新测试: 运行所有测试
2. 检查覆盖率: 确保覆盖率不下降
3. 检查性能: 确保性能不下降
4. 检查安全: 确保没有新安全问题

输出格式:

回归验证报告:

1. 测试结果
   - 总测试数: [数量]
   - 通过数: [数量]
   - 失败数: [数量]
   - 覆盖率: [百分比]
   - 变化: [+X% / -X%]

2. 代码质量
   - 代码风格: [通过/失败]
   - 类型检查: [通过/失败]
   - 安全检查: [通过/失败]
   - 性能检查: [通过/失败]

3. 性能指标
   - 测试耗时: [时间]
   - 内存占用: [大小]
   - 变化: [+X% / -X%]

4. 问题验证
   - 已修复: [数量]
   - 未修复: [数量]
   - 新问题: [数量]
   - 问题列表:
     - 问题: [问题描述]
       状态: [已修复/未修复/新问题]
       原因: [原因]

验证结论:
  - 所有问题已修复: [是/否]
  - 测试全部通过: [是/否]
  - 代码质量达标: [是/否]
  - 可以交付: [是/否]
```

**验证检查点**:
- [ ] 所有测试通过？
- [ ] 覆盖率不下降？
- [ ] 性能不下降？
- [ ] 没有新问题？

---

## 📤 输出格式

```markdown
# 验证与修复报告

## 1. 测试结果分析

### 1.1 测试概况
[测试概况]

### 1.2 失败详情
[失败详情]

### 1.3 根因分析
[根因分析]

## 2. 代码质量检查

### 2.1 代码风格
[代码风格检查结果]

### 2.2 类型检查
[类型检查结果]

### 2.3 安全检查
[安全检查结果]

### 2.4 性能检查
[性能检查结果]

## 3. 问题修复

### 3.1 修复计划
[修复计划]

### 3.2 修复执行
[修复执行记录]

## 4. 回归验证

### 4.1 测试结果
[测试结果]

### 4.2 代码质量
[代码质量检查结果]

### 4.3 性能指标
[性能指标]

### 4.4 验证结论
[验证结论]

## 5. 交付建议

### 5.1 可以交付
- [ ] 所有测试通过
- [ ] 覆盖率达标
- [ ] 代码质量达标
- [ ] 性能达标

### 5.2 需要修复
- [ ] 测试失败
- [ ] 覆盖率不足
- [ ] 代码质量问题
- [ ] 性能问题

### 5.3 建议优化
- [ ] 代码优化建议
- [ ] 性能优化建议
- [ ] 安全加固建议
```

---

## 🔍 自我验证清单

```yaml
问题分析:
  - 失败原因分析正确? [是/否]
  - 根因定位准确? [是/否]
  - 影响范围明确? [是/否]
  - 优先级排序合理? [是/否]

代码检查:
  - 所有检查都执行? [是/否]
  - 问题定位准确? [是/否]
  - 修复建议可行? [是/否]
  - 优先级排序合理? [是/否]

问题修复:
  - 修复方案可行? [是/否]
  - 修复代码正确? [是/否]
  - 验证方法有效? [是/否]
  - 回归测试通过? [是/否]

回归验证:
  - 所有测试通过? [是/否]
  - 覆盖率不下降? [是/否]
  - 性能不下降? [是/否]
  - 没有新问题? [是/否]
```

---

## 💡 常见问题修复方案

### 问题 1: 测试断言失败

```python
# 问题
def test_create_user():
    user = create_user(email="test@example.com")
    assert user.email == "wrong@example.com"  # 断言失败

# 修复
def test_create_user():
    user = create_user(email="test@example.com")
    assert user.email == "test@example.com"  # 正确的预期值
```

### 问题 2: 类型不匹配

```python
# 问题
def get_user(user_id: str) -> User:  # 参数类型错误
    return db.query(User).filter(User.id == user_id).first()

# 修复
def get_user(user_id: int) -> User:  # 正确的参数类型
    return db.query(User).filter(User.id == user_id).first()
```

### 问题 3: 缺少导入

```python
# 问题
def create_user():
    return User(username="test")  # NameError: name 'User' is not defined

# 修复
from app.models import User  # 添加导入

def create_user():
    return User(username="test")
```

### 问题 4: 异常处理不当

```python
# 问题
try:
    result = some_operation()
except:  # 裸 except
    raise Exception("Operation failed")

# 修复
try:
    result = some_operation()
except ValueError as e:  # 捕获具体异常
    logger.error(f"Operation failed: {e}", exc_info=True)
    raise OperationFailedError("Operation failed") from e
```

### 问题 5: SQL 注入风险

```python
# 问题
query = f"SELECT * FROM users WHERE name = '{name}'"  # SQL 注入风险
result = db.execute(query)

# 修复
result = db.query(User).filter(User.name == name).all()  # 使用 ORM
```

---

## 📊 Token 优化策略

1. **使用简洁格式**
   ```
   ❌: 详细的错误描述
   ✅: 表格格式展示错误
   ```

2. **引用代码**
   ```
   ❌: 重复完整代码
   ✅: 只展示差异部分
   ```

3. **分类汇总**
   ```
   ❌: 逐个列出问题
   ✅: 按类型分组汇总
   ```

---

## 🔄 模板使用示例

### 输入

```yaml
测试结果:
  测试通过: false
  失败数量: 3
  失败信息:
    - 测试名: TestUserService.test_create_user
      错误信息: AssertionError: assert 'test@example.com' == 'wrong@example.com'
    - 测试名: TestUserService.test_get_user
      错误信息: TypeError: 'str' object is not callable
    - 测试名: TestUserService.test_delete_user
      错误信息: AttributeError: 'NoneType' object has no attribute 'delete'
```

### 输出

```markdown
# 验证与修复报告

## 1. 测试结果分析

### 1.1 失败详情

1. **test_create_user** - AssertionError
   - 错误: 预期值错误
   - 修复: 修改断言预期值

2. **test_get_user** - TypeError
   - 错误: 变量名冲突
   - 修复: 重命名变量

3. **test_delete_user** - AttributeError
   - 错误: 用户不存在
   - 修复: 添加存在性检查

## 3. 问题修复

### 修复 #1: test_create_user 断言失败
```python
# 原代码
assert user.email == "wrong@example.com"

# 修复后
assert user.email == "test@example.com"
```

### 修复 #2: test_get_user 类型错误
```python
# 原代码
def get_user(user: str):  # 参数名冲突

# 修复后
def get_user(user_data: User):  # 避免冲突
```

### 修复 #3: test_delete_user 空指针
```python
# 原代码
db.delete(user)  # user 可能为 None

# 修复后
if user is not None:
    db.delete(user)
```

## 4. 回归验证

- 测试通过: ✅ 3/3
- 覆盖率: 85% (+5%)
- 可以交付: ✅
```

---

## 📝 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2026-04 | 初始版本 |

---

**提示**: 使用此模板时，请确保修复后重新运行所有测试，验证没有引入新问题。
