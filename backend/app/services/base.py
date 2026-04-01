"""
Service 层基类

提供通用的 CRUD 操作和业务逻辑封装

分层架构规范：
┌─────────────────────────────────────────────────────────────┐
│  API Layer (Controller)                                      │
│  - 接收请求、参数校验                                         │
│  - 调用 Service 层处理业务                                    │
│  - 返回响应                                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Service Layer (Business Logic)                              │
│  - 业务逻辑处理                                               │
│  - 事务管理                                                   │
│  - 跨模块协调                                                 │
│  - 权限检查                                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Model Layer (Data Access)                                   │
│  - SQLAlchemy ORM 模型                                       │
│  - 数据库操作                                                 │
└─────────────────────────────────────────────────────────────┘

使用规范：
1. API 层禁止直接操作数据库，必须通过 Service 层
2. Service 层负责业务逻辑，返回业务对象或 DTO
3. 复杂查询可在 Service 层使用 joinedload 预加载
"""
from typing import TypeVar, Generic, Type, List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.database import Base


# 泛型类型变量
ModelType = TypeVar("ModelType", bound=Base)


class BaseService(Generic[ModelType]):
    """
    Service 层基类
    
    提供通用的 CRUD 操作封装，子类可继承并扩展
    
    使用示例：
    ```python
    class UserService(BaseService[User]):
        def __init__(self, db: Session):
            super().__init__(User, db)
        
        def get_by_username(self, username: str) -> Optional[User]:
            return self.db.query(self.model).filter(
                self.model.username == username
            ).first()
    ```
    """
    
    def __init__(self, model: Type[ModelType], db: Session):
        """
        初始化 Service
        
        Args:
            model: SQLAlchemy 模型类
            db: 数据库会话
        """
        self.model = model
        self.db = db
    
    def get(self, id: int) -> Optional[ModelType]:
        """
        根据 ID 获取单个记录
        
        Args:
            id: 记录 ID
        
        Returns:
            模型实例或 None
        """
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        order_by: Any = None
    ) -> List[ModelType]:
        """
        获取多条记录（分页）
        
        Args:
            skip: 跳过记录数
            limit: 返回记录数
            order_by: 排序字段
        
        Returns:
            模型实例列表
        """
        query = self.db.query(self.model)
        if order_by is not None:
            query = query.order_by(order_by)
        return query.offset(skip).limit(limit).all()
    
    def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        创建记录
        
        Args:
            obj_in: 创建数据字典
        
        Returns:
            创建的模型实例
        """
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def update(self, id: int, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """
        更新记录
        
        Args:
            id: 记录 ID
            obj_in: 更新数据字典
        
        Returns:
            更新后的模型实例或 None
        """
        db_obj = self.get(id)
        if db_obj is None:
            return None
        
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        self.db.commit()
        self.db.refresh(db_obj)
        return db_obj
    
    def delete(self, id: int) -> bool:
        """
        删除记录
        
        Args:
            id: 记录 ID
        
        Returns:
            是否删除成功
        """
        db_obj = self.get(id)
        if db_obj is None:
            return False
        
        self.db.delete(db_obj)
        self.db.commit()
        return True
    
    def count(self) -> int:
        """
        获取记录总数
        
        Returns:
            记录总数
        """
        return self.db.query(self.model).count()
    
    def exists(self, id: int) -> bool:
        """
        检查记录是否存在
        
        Args:
            id: 记录 ID
        
        Returns:
            是否存在
        """
        return self.db.query(self.model).filter(self.model.id == id).count() > 0
