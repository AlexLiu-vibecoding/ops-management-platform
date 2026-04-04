"""
实例服务层

负责数据库实例（RDB/Redis）相关的业务逻辑处理，包括：
- 实例 CRUD 操作
- 实例连接测试
- 实例状态检查
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.services.base import BaseService
from app.models import RDBInstance, RedisInstance, Environment
from app.utils.auth import encrypt_instance_password, decrypt_instance_password


class RDBInstanceService(BaseService[RDBInstance]):
    """
    RDB 实例服务类
    
    处理 MySQL/PostgreSQL 实例的业务逻辑
    """
    
    def __init__(self, db: Session):
        super().__init__(RDBInstance, db)
    
    # ==================== 查询方法 ====================
    
    def get_with_environment(self, instance_id: int) -> Optional[RDBInstance]:
        """
        获取实例详情（预加载环境信息）
        
        Args:
            instance_id: 实例 ID
        
        Returns:
            实例实例或 None
        """
        return self.db.query(RDBInstance).options(
            joinedload(RDBInstance.environment)
        ).filter(RDBInstance.id == instance_id).first()
    
    def get_multi_with_environment(
        self,
        skip: int = 0,
        limit: int = 20,
        environment_id: Optional[int] = None,
        group_id: Optional[int] = None,
        db_type: Optional[str] = None,
        status: Optional[bool] = None
    ) -> tuple[list[RDBInstance], int]:
        """
        获取实例列表（预加载环境信息）
        
        Args:
            skip: 跳过记录数
            limit: 返回记录数
            environment_id: 环境ID过滤
            group_id: 分组ID过滤
            db_type: 数据库类型过滤
            status: 状态过滤
        
        Returns:
            (实例列表, 总数)
        """
        query = self.db.query(RDBInstance).options(
            joinedload(RDBInstance.environment)
        )
        
        if environment_id:
            query = query.filter(RDBInstance.environment_id == environment_id)
        if group_id:
            query = query.filter(RDBInstance.group_id == group_id)
        if db_type:
            query = query.filter(RDBInstance.db_type == db_type)
        if status is not None:
            query = query.filter(RDBInstance.status == status)
        
        total = query.count()
        instances = query.offset(skip).limit(limit).all()
        
        return instances, total
    
    def get_by_name(self, name: str) -> Optional[RDBInstance]:
        """
        根据名称获取实例
        
        Args:
            name: 实例名称
        
        Returns:
            实例实例或 None
        """
        return self.db.query(RDBInstance).filter(RDBInstance.name == name).first()
    
    # ==================== 创建方法 ====================
    
    def create_instance(
        self,
        name: str,
        host: str,
        port: int,
        username: str,
        password: str,
        db_type: str = "MYSQL",
        environment_id: Optional[int] = None,
        group_id: Optional[int] = None,
        description: Optional[str] = None,
        is_rds: bool = False,
        rds_instance_id: Optional[str] = None,
        aws_region: Optional[str] = None,
        slow_query_threshold: int = 3,
        **kwargs
    ) -> RDBInstance:
        """
        创建 RDB 实例（包含业务校验）
        
        Args:
            name: 实例名称
            host: 主机地址
            port: 端口
            username: 用户名
            password: 密码
            db_type: 数据库类型
            environment_id: 环境ID
            group_id: 分组ID
            description: 描述
            is_rds: 是否为 RDS 实例
            rds_instance_id: RDS 实例标识符
            aws_region: AWS 区域
            slow_query_threshold: 慢查询阈值
            **kwargs: 其他参数
        
        Returns:
            创建的实例实例
        
        Raises:
            HTTPException: 实例名称已存在
        """
        # 检查名称是否已存在
        if self.get_by_name(name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"实例名称 '{name}' 已存在"
            )
        
        # 加密密码
        encrypted_password = encrypt_instance_password(password)
        
        instance_data = {
            "name": name,
            "host": host,
            "port": port,
            "username": username,
            "password_encrypted": encrypted_password,
            "db_type": db_type,
            "environment_id": environment_id,
            "group_id": group_id,
            "description": description,
            "is_rds": is_rds,
            "rds_instance_id": rds_instance_id,
            "aws_region": aws_region,
            "slow_query_threshold": slow_query_threshold,
            "status": True,
            "enable_monitoring": True,
        }
        instance_data.update(kwargs)
        
        return self.create(instance_data)
    
    # ==================== 更新方法 ====================
    
    def update_instance(
        self,
        instance_id: int,
        name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        environment_id: Optional[int] = None,
        group_id: Optional[int] = None,
        description: Optional[str] = None,
        status: Optional[bool] = None,
        **kwargs
    ) -> Optional[RDBInstance]:
        """
        更新实例信息
        
        Args:
            instance_id: 实例 ID
            name: 实例名称
            host: 主机地址
            port: 端口
            username: 用户名
            password: 密码
            environment_id: 环境ID
            group_id: 分组ID
            description: 描述
            status: 状态
            **kwargs: 其他参数
        
        Returns:
            更新后的实例实例
        
        Raises:
            HTTPException: 实例不存在或名称已存在
        """
        instance = self.get(instance_id)
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="实例不存在"
            )
        
        # 检查名称是否被其他实例使用
        if name and name != instance.name:
            existing = self.get_by_name(name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"实例名称 '{name}' 已存在"
                )
        
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if host is not None:
            update_data["host"] = host
        if port is not None:
            update_data["port"] = port
        if username is not None:
            update_data["username"] = username
        if password is not None:
            update_data["password_encrypted"] = encrypt_instance_password(password)
        if environment_id is not None:
            update_data["environment_id"] = environment_id
        if group_id is not None:
            update_data["group_id"] = group_id
        if description is not None:
            update_data["description"] = description
        if status is not None:
            update_data["status"] = status
        update_data.update(kwargs)
        
        return self.update(instance_id, update_data)
    
    # ==================== 工具方法 ====================
    
    def get_decrypted_password(self, instance: RDBInstance) -> str:
        """
        获取解密后的密码
        
        Args:
            instance: 实例实例
        
        Returns:
            解密后的密码
        """
        return decrypt_instance_password(instance.password_encrypted)
    
    def to_dict(self, instance: RDBInstance) -> dict[str, Any]:
        """
        将实例转换为字典（用于 API 响应）
        
        Args:
            instance: 实例实例
        
        Returns:
            字典表示
        """
        env_data = None
        if instance.environment:
            env_data = {
                "id": instance.environment.id,
                "name": instance.environment.name,
                "color": instance.environment.color
            }
        
        return {
            "id": instance.id,
            "name": instance.name,
            "db_type": instance.db_type.value if hasattr(instance.db_type, 'value') else str(instance.db_type),
            "host": instance.host,
            "port": instance.port,
            "username": instance.username,
            "environment_id": instance.environment_id,
            "environment": env_data,
            "group_id": instance.group_id,
            "description": instance.description,
            "status": instance.status,
            "is_rds": instance.is_rds,
            "rds_instance_id": instance.rds_instance_id,
            "aws_region": instance.aws_region,
            "slow_query_threshold": instance.slow_query_threshold,
            "enable_monitoring": instance.enable_monitoring,
            "last_check_time": instance.last_check_time,
            "created_at": instance.created_at,
            "updated_at": instance.updated_at,
        }


class InstanceGroupService:
    """
    实例分组服务类
    
    处理实例分组的业务逻辑
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self) -> list[Any]:
        """
        获取所有分组
        
        Returns:
            分组列表
        """
        from app.models import InstanceGroup
        return self.db.query(InstanceGroup).all()
    
    def get_by_id(self, group_id: int) -> Optional[Any]:
        """
        根据 ID 获取分组
        
        Args:
            group_id: 分组 ID
        
        Returns:
            分组或 None
        """
        from app.models import InstanceGroup
        return self.db.query(InstanceGroup).filter(InstanceGroup.id == group_id).first()
    
    def get_by_name(self, name: str) -> Optional[Any]:
        """
        根据名称获取分组
        
        Args:
            name: 分组名称
        
        Returns:
            分组或 None
        """
        from app.models import InstanceGroup
        return self.db.query(InstanceGroup).filter(InstanceGroup.name == name).first()
    
    def create(self, name: str, description: str = "") -> Any:
        """
        创建分组
        
        Args:
            name: 分组名称
            description: 分组描述
        
        Returns:
            创建的分组
        
        Raises:
            HTTPException: 分组名称已存在
        """
        from app.models import InstanceGroup
        
        if self.get_by_name(name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="分组名称已存在"
            )
        
        group = InstanceGroup(name=name, description=description)
        self.db.add(group)
        self.db.commit()
        self.db.refresh(group)
        
        return group
    
    def update(self, group_id: int, name: Optional[str] = None, description: Optional[str] = None) -> Optional[Any]:
        """
        更新分组
        
        Args:
            group_id: 分组 ID
            name: 分组名称
            description: 分组描述
        
        Returns:
            更新后的分组或 None
        
        Raises:
            HTTPException: 分组不存在或名称已存在
        """
        from app.models import InstanceGroup
        
        group = self.get_by_id(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分组不存在"
            )
        
        if name and name != group.name:
            if self.get_by_name(name):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="分组名称已存在"
                )
            group.name = name
        
        if description is not None:
            group.description = description
        
        self.db.commit()
        self.db.refresh(group)
        
        return group
    
    def delete(self, group_id: int) -> bool:
        """
        删除分组
        
        Args:
            group_id: 分组 ID
        
        Returns:
            是否删除成功
        
        Raises:
            HTTPException: 分组不存在
        """
        from app.models import InstanceGroup
        
        group = self.get_by_id(group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分组不存在"
            )
        
        self.db.delete(group)
        self.db.commit()
        
        return True
    
    def to_dict(self, group: Any) -> dict[str, Any]:
        """
        将分组转换为字典（用于 API 响应）
        
        Args:
            group: 分组实例
        
        Returns:
            字典表示
        """
        return {
            "id": group.id,
            "name": group.name,
            "description": group.description
        }
    
    def get_all_with_environment(
        self,
        environment_id: Optional[int] = None,
        group_id: Optional[int] = None,
        redis_mode: Optional[str] = None,
        status: Optional[bool] = None
    ) -> list[RedisInstance]:
        """
        获取所有实例（预加载环境信息，不分页）
        
        Args:
            environment_id: 环境ID过滤
            group_id: 分组ID过滤
            redis_mode: Redis模式过滤
            status: 状态过滤
        
        Returns:
            实例列表
        """
        query = self.db.query(RedisInstance).options(
            joinedload(RedisInstance.environment)
        )
        
        if environment_id:
            query = query.filter(RedisInstance.environment_id == environment_id)
        if group_id:
            query = query.filter(RedisInstance.group_id == group_id)
        if redis_mode:
            query = query.filter(RedisInstance.redis_mode == redis_mode)
        if status is not None:
            query = query.filter(RedisInstance.status == status)
        
        return query.all()
    
    def update_status(self, instance_id: int, status: bool) -> bool:
        """
        更新实例状态
        
        Args:
            instance_id: 实例 ID
            status: 新状态
        
        Returns:
            是否更新成功
        """
        return self.update(instance_id, {"status": status}) is not None
    
    def update_instance(
        self,
        instance_id: int,
        name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        environment_id: Optional[int] = None,
        group_id: Optional[int] = None,
        description: Optional[str] = None,
        status: Optional[bool] = None,
        **kwargs
    ) -> Optional[RedisInstance]:
        """
        更新实例信息
        
        Args:
            instance_id: 实例 ID
            name: 实例名称
            host: 主机地址
            port: 端口
            password: 密码
            environment_id: 环境ID
            group_id: 分组ID
            description: 描述
            status: 状态
            **kwargs: 其他参数
        
        Returns:
            更新后的实例实例
        
        Raises:
            HTTPException: 实例不存在或名称已存在
        """
        instance = self.get(instance_id)
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="实例不存在"
            )
        
        # 检查名称是否被其他实例使用
        if name and name != instance.name:
            existing = self.get_by_name(name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"实例名称 '{name}' 已存在"
                )
        
        update_data = {}
        if name is not None:
            update_data["name"] = name
        if host is not None:
            update_data["host"] = host
        if port is not None:
            update_data["port"] = port
        if password is not None:
            update_data["password_encrypted"] = encrypt_instance_password(password)
        if environment_id is not None:
            update_data["environment_id"] = environment_id
        if group_id is not None:
            update_data["group_id"] = group_id
        if description is not None:
            update_data["description"] = description
        if status is not None:
            update_data["status"] = status
        update_data.update(kwargs)
        
        return self.update(instance_id, update_data)
    
    def get_all_with_environment(
        self,
        environment_id: Optional[int] = None,
        group_id: Optional[int] = None,
        db_type: Optional[str] = None,
        status: Optional[bool] = None
    ) -> list[RDBInstance]:
        """
        获取所有实例（预加载环境信息，不分页）
        
        Args:
            environment_id: 环境ID过滤
            group_id: 分组ID过滤
            db_type: 数据库类型过滤
            status: 状态过滤
        
        Returns:
            实例列表
        """
        query = self.db.query(RDBInstance).options(
            joinedload(RDBInstance.environment)
        )
        
        if environment_id:
            query = query.filter(RDBInstance.environment_id == environment_id)
        if group_id:
            query = query.filter(RDBInstance.group_id == group_id)
        if db_type:
            query = query.filter(RDBInstance.db_type == db_type)
        if status is not None:
            query = query.filter(RDBInstance.status == status)
        
        return query.all()
    
    def update_status(self, instance_id: int, status: bool) -> bool:
        """
        更新实例状态
        
        Args:
            instance_id: 实例 ID
            status: 新状态
        
        Returns:
            是否更新成功
        """
        return self.update(instance_id, {"status": status}) is not None
    
    def update_last_check_time(self, instance_id: int) -> bool:
        """
        更新最后检查时间
        
        Args:
            instance_id: 实例 ID
        
        Returns:
            是否更新成功
        """
        from datetime import datetime
        return self.update(instance_id, {"last_check_time": datetime.now()}) is not None


class RedisInstanceService(BaseService[RedisInstance]):
    """
    Redis 实例服务类
    
    处理 Redis 实例的业务逻辑
    """
    
    def __init__(self, db: Session):
        super().__init__(RedisInstance, db)
    
    # ==================== 查询方法 ====================
    
    def get_with_environment(self, instance_id: int) -> Optional[RedisInstance]:
        """
        获取实例详情（预加载环境信息）
        
        Args:
            instance_id: 实例 ID
        
        Returns:
            实例实例或 None
        """
        return self.db.query(RedisInstance).options(
            joinedload(RedisInstance.environment)
        ).filter(RedisInstance.id == instance_id).first()
    
    def get_multi_with_environment(
        self,
        skip: int = 0,
        limit: int = 20,
        environment_id: Optional[int] = None,
        group_id: Optional[int] = None,
        redis_mode: Optional[str] = None,
        status: Optional[bool] = None
    ) -> tuple[list[RedisInstance], int]:
        """
        获取实例列表（预加载环境信息）
        
        Args:
            skip: 跳过记录数
            limit: 返回记录数
            environment_id: 环境ID过滤
            group_id: 分组ID过滤
            redis_mode: Redis模式过滤
            status: 状态过滤
        
        Returns:
            (实例列表, 总数)
        """
        query = self.db.query(RedisInstance).options(
            joinedload(RedisInstance.environment)
        )
        
        if environment_id:
            query = query.filter(RedisInstance.environment_id == environment_id)
        if group_id:
            query = query.filter(RedisInstance.group_id == group_id)
        if redis_mode:
            query = query.filter(RedisInstance.redis_mode == redis_mode)
        if status is not None:
            query = query.filter(RedisInstance.status == status)
        
        total = query.count()
        instances = query.offset(skip).limit(limit).all()
        
        return instances, total
    
    def get_by_name(self, name: str) -> Optional[RedisInstance]:
        """
        根据名称获取实例
        
        Args:
            name: 实例名称
        
        Returns:
            实例实例或 None
        """
        return self.db.query(RedisInstance).filter(RedisInstance.name == name).first()
    
    # ==================== 创建方法 ====================
    
    def create_instance(
        self,
        name: str,
        host: str,
        port: int = 6379,
        password: Optional[str] = None,
        redis_mode: str = "STANDALONE",
        redis_db: int = 0,
        environment_id: Optional[int] = None,
        group_id: Optional[int] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> RedisInstance:
        """
        创建 Redis 实例（包含业务校验）
        
        Args:
            name: 实例名称
            host: 主机地址
            port: 端口
            password: 密码
            redis_mode: Redis模式
            redis_db: Redis数据库索引
            environment_id: 环境ID
            group_id: 分组ID
            description: 描述
            **kwargs: 其他参数
        
        Returns:
            创建的实例实例
        
        Raises:
            HTTPException: 实例名称已存在
        """
        # 检查名称是否已存在
        if self.get_by_name(name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"实例名称 '{name}' 已存在"
            )
        
        # 加密密码
        encrypted_password = encrypt_instance_password(password) if password else None
        
        instance_data = {
            "name": name,
            "host": host,
            "port": port,
            "password_encrypted": encrypted_password,
            "redis_mode": redis_mode,
            "redis_db": redis_db,
            "environment_id": environment_id,
            "group_id": group_id,
            "description": description,
            "status": True,
            "enable_monitoring": True,
        }
        instance_data.update(kwargs)
        
        return self.create(instance_data)
    
    # ==================== 工具方法 ====================
    
    def get_decrypted_password(self, instance: RedisInstance) -> Optional[str]:
        """
        获取解密后的密码
        
        Args:
            instance: 实例实例
        
        Returns:
            解密后的密码
        """
        if not instance.password_encrypted:
            return None
        return decrypt_instance_password(instance.password_encrypted)
    
    def to_dict(self, instance: RedisInstance) -> dict[str, Any]:
        """
        将实例转换为字典（用于 API 响应）
        
        Args:
            instance: 实例实例
        
        Returns:
            字典表示
        """
        env_data = None
        if instance.environment:
            env_data = {
                "id": instance.environment.id,
                "name": instance.environment.name,
                "color": instance.environment.color
            }
        
        return {
            "id": instance.id,
            "name": instance.name,
            "host": instance.host,
            "port": instance.port,
            "redis_mode": instance.redis_mode.value if hasattr(instance.redis_mode, 'value') else str(instance.redis_mode),
            "redis_db": instance.redis_db,
            "cluster_nodes": instance.cluster_nodes,
            "sentinel_master_name": instance.sentinel_master_name,
            "sentinel_hosts": instance.sentinel_hosts,
            "environment_id": instance.environment_id,
            "environment": env_data,
            "group_id": instance.group_id,
            "description": instance.description,
            "status": instance.status,
            "slowlog_threshold": instance.slowlog_threshold,
            "enable_monitoring": instance.enable_monitoring,
            "last_check_time": instance.last_check_time,
            "created_at": instance.created_at,
            "updated_at": instance.updated_at,
        }
