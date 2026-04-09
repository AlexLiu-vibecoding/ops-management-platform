# 测试生成模板 (Test Generation Template)

> 基于生成代码的完整测试用例，确保代码质量。

---

## 模板元数据

```
版本: v1.0
创建日期: 2026-04
适用阶段: 代码生成 → 测试执行
目标: 可运行代码 → 测试用例
前置条件: 完成代码生成
```

---

## 🎯 核心原则

1. **测试金字塔** - 单元测试 > 集成测试 > E2E 测试
2. **AAA 模式** - Arrange（准备）、Act（执行）、Assert（断言）
3. **测试独立** - 每个测试独立，无依赖
4. **覆盖率优先** - 优先覆盖核心逻辑和边界情况

---

## 📥 输入定义

```yaml
生成代码:
  type: object
  required: true
  properties:
    模型定义: array
    API 定义: array
    服务定义: array
    前端组件: array

测试要求:
  type: object
  required: true
  properties:
    覆盖率目标: number
    测试类型: array
    边界条件: array
```

---

## 🧠 结构化思维 (SoT) 流程

### Step 1: 单元测试生成 (3 分钟)

```
目标: 生成服务层单元测试

思考框架:
1. 测试类定义: 使用 pytest 测试类
2. Mock 设置: Mock 数据库和依赖
3. 测试方法: 正常情况、异常情况、边界情况
4. 断言验证: 验证返回值和副作用
5. 清理操作: 每个测试后清理数据

输出格式:

# tests/services/test_[service].py
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from app.services.[service] import [Service]
from app.schemas import [Create], [Update]
from app.core.exceptions import [Exception]
from tests.helpers.base_service_test import BaseServiceTest

class Test[Service](BaseServiceTest):
    """[服务]单元测试"""

    @pytest.fixture
    def service(self, db_session):
        """创建服务实例"""
        return [Service](db_session)

    def test_create_[resource]_success(self, service):
        """测试创建[资源] - 成功"""
        # Arrange (准备)
        data = [Create](
            field1="value1",
            field2="value2"
        )

        # Act (执行)
        result = service.create_[resource](data)

        # Assert (断言)
        assert result is not None
        assert result.field1 == "value1"
        assert result.field2 == "value2"

    def test_create_[resource]_invalid_data(self, service):
        """测试创建[资源] - 数据无效"""
        # Arrange
        data = [Create](
            field1="",  # 无效值
            field2="value2"
        )

        # Act & Assert
        with pytest.raises([Exception]) as exc_info:
            service.create_[resource](data)

        assert "无效" in str(exc_info.value)

    def test_get_[resource]_found(self, service, db_session):
        """测试获取[资源] - 找到"""
        # Arrange
        item = service.create_[resource]([Create](field1="value1"))

        # Act
        result = service.get_[resource](item.id)

        # Assert
        assert result is not None
        assert result.id == item.id

    def test_get_[resource]_not_found(self, service):
        """测试获取[资源] - 未找到"""
        # Act & Assert
        result = service.get_[resource](99999)
        assert result is None

    def test_update_[resource]_success(self, service, db_session):
        """测试更新[资源] - 成功"""
        # Arrange
        item = service.create_[resource]([Create](field1="old_value"))
        update_data = [Update](field1="new_value")

        # Act
        result = service.update_[resource](item.id, update_data)

        # Assert
        assert result.field1 == "new_value"

    def test_update_[resource]_not_found(self, service):
        """测试更新[资源] - 未找到"""
        # Arrange
        update_data = [Update](field1="new_value")

        # Act & Assert
        with pytest.raises([Exception]) as exc_info:
            service.update_[resource](99999, update_data)

        assert "不存在" in str(exc_info.value)

    def test_delete_[resource]_success(self, service, db_session):
        """测试删除[资源] - 成功"""
        # Arrange
        item = service.create_[resource]([Create](field1="value1"))

        # Act
        result = service.delete_[resource](item.id)

        # Assert
        assert result is True
        assert service.get_[resource](item.id) is None

    def test_delete_[resource]_not_found(self, service):
        """测试删除[资源] - 未找到"""
        # Act & Assert
        with pytest.raises([Exception]) as exc_info:
            service.delete_[resource](99999)

        assert "不存在" in str(exc_info.value)

    def test_list_[resource]_empty(self, service):
        """测试获取[资源]列表 - 空列表"""
        # Act
        result = service.list_[resource]()

        # Assert
        assert len(result) == 0

    def test_list_[resource]_with_data(self, service, db_session):
        """测试获取[资源]列表 - 有数据"""
        # Arrange
        service.create_[resource]([Create](field1="value1"))
        service.create_[resource]([Create](field1="value2"))

        # Act
        result = service.list_[resource]()

        # Assert
        assert len(result) == 2

    def test_list_[resource]_with_pagination(self, service, db_session):
        """测试获取[资源]列表 - 分页"""
        # Arrange
        for i in range(5):
            service.create_[resource]([Create](field1=f"value{i}"))

        # Act
        result = service.list_[resource](page=1, page_size=2)

        # Assert
        assert len(result) == 2

    def test_list_[resource]_with_filters(self, service, db_session):
        """测试获取[资源]列表 - 过滤"""
        # Arrange
        service.create_[resource]([Create](field1="value1", status="active"))
        service.create_[resource]([Create](field1="value2", status="inactive"))

        # Act
        result = service.list_[resource](status="active")

        # Assert
        assert len(result) == 1
        assert result[0].status == "active"

    @patch('app.services.[service].logger')
    def test_create_[resource]_database_error(self, mock_logger, service, db_session):
        """测试创建[资源] - 数据库错误"""
        # Arrange
        data = [Create](field1="value1")

        # Mock 数据库错误
        with patch.object(db_session, 'commit', side_effect=Exception("DB Error")):
            # Act & Assert
            with pytest.raises([Exception]):
                service.create_[resource](data)

            # 验证日志记录
            mock_logger.error.assert_called_once()
```

**验证检查点**:
- [ ] 每个方法都有对应的测试？
- [ ] 正常情况和异常情况都覆盖？
- [ ] 边界条件都测试？
- [ ] Mock 使用正确？
- [ ] 断言完整？

---

### Step 2: API 测试生成 (3 分钟)

```
目标: 生成 API 层测试

思考框架:
1. 测试客户端: 使用 TestClient
2. 认证设置: Mock 认证依赖
3. 请求构造: 构造各种请求
4. 响应验证: 验证状态码和响应体
5. 权限测试: 测试权限控制

输出格式:

# tests/api/test_[resource].py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models import User
from app.database import get_db

client = TestClient(app)

@pytest.fixture
def mock_db():
    """Mock 数据库"""
    db = Mock(spec=Session)
    app.dependency_overrides[get_db] = lambda: db
    yield db
    app.dependency_overrides.clear()

@pytest.fixture
def mock_user():
    """Mock 用户"""
    return User(id=1, username="test", email="test@example.com", status=True)

class Test[ListResource]:
    """测试获取[资源]列表"""

    def test_list_[resource]_success(self, mock_db, mock_user):
        """测试获取[资源]列表 - 成功"""
        # Arrange
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = []

        # Act
        response = client.get(
            "/api/v1/[resource]",
            headers={"Authorization": "Bearer token"}
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["code"] == 200
        assert response.json()["data"] == []

    def test_list_[resource]_unauthorized(self):
        """测试获取[资源]列表 - 未认证"""
        # Act
        response = client.get("/api/v1/[resource]")

        # Assert
        assert response.status_code == 401

class TestCreate[Resource]:
    """测试创建[资源]"""

    def test_create_[resource]_success(self, mock_db, mock_user):
        """测试创建[资源] - 成功"""
        # Arrange
        data = {
            "field1": "value1",
            "field2": "value2"
        }

        # Act
        response = client.post(
            "/api/v1/[resource]",
            json=data,
            headers={"Authorization": "Bearer token"}
        )

        # Assert
        assert response.status_code == 201
        assert response.json()["code"] == 201

    def test_create_[resource]_invalid_data(self, mock_db, mock_user):
        """测试创建[资源] - 数据无效"""
        # Arrange
        data = {
            "field1": "",  # 无效值
        }

        # Act
        response = client.post(
            "/api/v1/[resource]",
            json=data,
            headers={"Authorization": "Bearer token"}
        )

        # Assert
        assert response.status_code == 422

class TestGet[Resource]:
    """测试获取[资源]详情"""

    def test_get_[resource]_found(self, mock_db, mock_user):
        """测试获取[资源]详情 - 找到"""
        # Arrange
        mock_item = Mock(id=1, field1="value1")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        # Act
        response = client.get(
            "/api/v1/[resource]/1",
            headers={"Authorization": "Bearer token"}
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["data"]["id"] == 1

    def test_get_[resource]_not_found(self, mock_db, mock_user):
        """测试获取[资源]详情 - 未找到"""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Act
        response = client.get(
            "/api/v1/[resource]/99999",
            headers={"Authorization": "Bearer token"}
        )

        # Assert
        assert response.status_code == 404

class TestUpdate[Resource]:
    """测试更新[资源]"""

    def test_update_[resource]_success(self, mock_db, mock_user):
        """测试更新[资源] - 成功"""
        # Arrange
        data = {
            "field1": "new_value"
        }

        mock_item = Mock(id=1, field1="old_value")
        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        # Act
        response = client.put(
            "/api/v1/[resource]/1",
            json=data,
            headers={"Authorization": "Bearer token"}
        )

        # Assert
        assert response.status_code == 200

class TestDelete[Resource]:
    """测试删除[资源]"""

    def test_delete_[resource]_success(self, mock_db, mock_user):
        """测试删除[资源] - 成功"""
        # Arrange
        mock_item = Mock(id=1)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        # Act
        response = client.delete(
            "/api/v1/[resource]/1",
            headers={"Authorization": "Bearer token"}
        )

        # Assert
        assert response.status_code == 204
```

**验证检查点**:
- [ ] 所有 API 端点都测试？
- [ ] 权限测试完整？
- [ ] 参数验证测试？
- [ ] 错误处理测试？
- [ ] 响应格式验证？

---

### Step 3: 集成测试生成 (2 分钟)

```
目标: 生成集成测试

思考框架:
1. 测试环境: 使用测试数据库
2. 数据准备: 准备测试数据
3. 流程测试: 测试完整业务流程
4. 清理操作: 每个测试后清理
5. 独立性: 每个测试独立运行

输出格式:

# tests/integration/test_[feature].py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import [Model]
from app.services.[service] import [Service]
from app.schemas import [Create]

# 测试数据库
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

class Test[Feature]Workflow:
    """测试[功能]完整流程"""

    def test_create_and_[action]_workflow(self, db_session):
        """测试创建和[操作]完整流程"""
        # Arrange
        service = [Service](db_session)

        # Act 1: 创建[资源]
        data = [Create](field1="value1", field2="value2")
        item = service.create_[resource](data)

        # Assert 1
        assert item.id is not None
        assert item.field1 == "value1"

        # Act 2: 更新[资源]
        update_data = [Update](field1="new_value")
        updated_item = service.update_[resource](item.id, update_data)

        # Assert 2
        assert updated_item.field1 == "new_value"

        # Act 3: 删除[资源]
        result = service.delete_[resource](item.id)

        # Assert 3
        assert result is True
        assert service.get_[resource](item.id) is None

    def test_[feature]_with_error_handling(self, db_session):
        """测试[功能]错误处理"""
        # Arrange
        service = [Service](db_session)

        # Act & Assert 1: 创建无效数据
        with pytest.raises([Exception]):
            service.create_[resource]([Create](field1=""))

        # Act & Assert 2: 获取不存在的资源
        result = service.get_[resource](99999)
        assert result is None

        # Act & Assert 3: 更新不存在的资源
        with pytest.raises([Exception]):
            service.update_[resource](99999, [Update](field1="value1"))

        # Act & Assert 4: 删除不存在的资源
        with pytest.raises([Exception]):
            service.delete_[resource](99999)

    def test_[feature]_concurrent_operations(self, db_session):
        """测试[功能]并发操作"""
        # Arrange
        service = [Service](db_session)

        # Act: 并发创建多个资源
        items = []
        for i in range(10):
            item = service.create_[resource]([Create](field1=f"value{i}"))
            items.append(item)

        # Assert
        assert len(items) == 10

        # Act: 并发更新
        for item in items:
            service.update_[resource](item.id, [Update](field1="updated"))

        # Assert
        updated_items = service.list_[resource]()
        assert all(item.field1 == "updated" for item in updated_items)
```

**验证检查点**:
- [ ] 完整流程测试？
- [ ] 错误处理测试？
- [ ] 并发操作测试？
- [ ] 数据清理完整？
- [ ] 测试独立运行？

---

### Step 4: 测试配置生成 (1 分钟)

```
目标: 生成测试配置

输出格式:

# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.deps import get_current_user
from app.models import User

# 测试数据库
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    """创建测试数据库"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db):
    """创建测试客户端"""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    from fastapi.testclient import TestClient
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db):
    """创建测试用户"""
    user = User(
        username="testuser",
        email="test@example.com",
        status=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def authenticated_client(client, test_user):
    """创建认证测试客户端"""

    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_current_user] = override_get_current_user
    yield client
    app.dependency_overrides.clear()

# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=70
    --tb=short
markers =
    unit: 单元测试
    integration: 集成测试
    e2e: 端到端测试
    slow: 慢速测试
```

---

## 📤 输出格式

```
tests/
  __init__.py
  conftest.py
  unit/
    services/
      test_[service].py
    utils/
      test_[util].py
  integration/
    test_[feature].py
  api/
    test_[resource].py
  helpers/
    base_service_test.py
    base_api_test.py
```

---

## 🔍 自我验证清单

```yaml
单元测试:
  - 测试类结构清晰? [是/否]
  - Mock 使用正确? [是/否]
  - AAA 模式遵守? [是/否]
  - 断言完整? [是/否]
  - 边界条件覆盖? [是/否]

API 测试:
  - 所有端点测试? [是/否]
  - 权限测试完整? [是/否]
  - 参数验证测试? [是/否]
  - 响应格式验证? [是/否]
  - 错误处理测试? [是/否]

集成测试:
  - 完整流程测试? [是/否]
  - 错误处理测试? [是/否]
  - 并发操作测试? [是/否]
  - 数据清理完整? [是/否]
  - 测试独立运行? [是/否]

测试配置:
  - Fixture 定义完整? [是/否]
  - 数据库隔离? [是/否]
  - Mock 设置正确? [是/否]
  - pytest 配置正确? [是/否]
  - 覆盖率目标设置? [是/否]
```

---

## 💡 测试最佳实践

### 测试命名规范

```python
# 格式: test_<被测试方法>_<场景>_<预期结果>
def test_create_user_success():
    """测试创建用户 - 成功"""
    pass

def test_create_user_invalid_email():
    """测试创建用户 - 邮箱无效"""
    pass

def test_get_user_not_found():
    """测试获取用户 - 未找到"""
    pass
```

### AAA 模式

```python
def test_update_user_email():
    """测试更新用户邮箱"""

    # Arrange (准备)
    user = create_user(email="old@example.com")
    new_email = "new@example.com"

    # Act (执行)
    result = update_user(user.id, email=new_email)

    # Assert (断言)
    assert result.email == new_email
```

### 测试隔离

```python
@pytest.fixture(scope="function")
def db_session():
    """每个测试独立数据库"""
    # 创建
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    # 清理
    db.close()
    Base.metadata.drop_all(bind=engine)
```

---

## 📊 Token 优化策略

1. **使用测试基类**
   ```
   ❌: 重复编写 Mock 设置
   ✅: 使用 BaseServiceTest 提供通用 Mock
   ```

2. **使用参数化测试**
   ```
   ❌: 多个测试方法
   ✅: 使用 pytest.mark.parametrize
   ```

3. **复用测试数据**
   ```
   ❌: 每个测试重复创建数据
   ✅: 使用 fixture 共享数据
   ```

---

## 🔄 模板使用示例

### 输入

```yaml
生成代码:
  服务定义:
    - name: ExportService
      methods:
        - create_export
        - get_export
        - list_exports
        - delete_export

测试要求:
  覆盖率目标: 80
  测试类型: [unit, integration]
```

### 输出

```python
# tests/services/test_export_service.py
class TestExportService(BaseServiceTest):

    def test_create_export_success(self, service):
        # Arrange
        data = ExportCreate(filename="test.csv")

        # Act
        result = service.create_export(data)

        # Assert
        assert result.filename == "test.csv"
```

---

## 📝 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2026-04 | 初始版本 |

---

**提示**: 使用此模板时，请确保测试覆盖率达到目标，每个测试都是独立的。
