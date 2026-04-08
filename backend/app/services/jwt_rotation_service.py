"""
JWT 轮换服务
"""

import secrets
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.models.key_rotation import JWTRotationKey, JWTRotationConfig
from app.config import settings


class JWTRotationService:
    """JWT 轮换服务"""
    
    def __init__(self, db: Session, operator_id: Optional[int] = None):
        self.db = db
        self.operator_id = operator_id
    
    def get_config(self) -> JWTRotationConfig:
        """获取配置"""
        config = self.db.query(JWTRotationConfig).first()
        if not config:
            # 初始化配置
            config = JWTRotationConfig(
                id=1,
                enabled=True,
                current_key_id="v1"
            )
            self.db.add(config)
            self.db.commit()
            self.db.refresh(config)
        return config
    
    def get_all_keys(self) -> list[JWTRotationKey]:
        """获取所有密钥"""
        return self.db.query(JWTRotationKey).order_by(JWTRotationKey.key_id).all()
    
    def get_key_by_id(self, key_id: str) -> Optional[JWTRotationKey]:
        """根据版本获取密钥"""
        return self.db.query(JWTRotationKey).filter(
            JWTRotationKey.key_id == key_id
        ).first()
    
    def get_active_key(self) -> Optional[JWTRotationKey]:
        """获取当前活跃密钥"""
        config = self.get_config()
        return self.get_key_by_id(config.current_key_id)
    
    def get_current_version(self) -> str:
        """获取当前版本"""
        config = self.get_config()
        return config.current_key_id or "v1"
    
    def _generate_key_value(self) -> str:
        """生成安全的 JWT 密钥"""
        return secrets.token_urlsafe(64)  # 生成 64 字符的安全密钥
    
    def _get_next_key_id(self) -> str:
        """获取下一个密钥版本号"""
        all_keys = self.get_all_keys()
        if not all_keys:
            return "v1"
        
        # 解析现有版本号
        versions = []
        for k in all_keys:
            try:
                v = int(k.key_id.replace("v", ""))
                versions.append(v)
            except ValueError:
                continue
        
        if versions:
            return f"v{max(versions) + 1}"
        return "v1"
    
    def generate_key(self, key_id: Optional[str] = None) -> JWTRotationKey:
        """生成新的 JWT 密钥"""
        if key_id is None:
            key_id = self._get_next_key_id()
        
        # 检查是否已存在
        existing = self.get_key_by_id(key_id)
        if existing:
            raise ValueError(f"密钥版本 {key_id} 已存在")
        
        # 生成新密钥
        key_value = self._generate_key_value()
        
        key = JWTRotationKey(
            key_id=key_id,
            key_value=key_value,
            is_active=False,
            created_by=self.operator_id
        )
        self.db.add(key)
        self.db.commit()
        self.db.refresh(key)
        
        return key
    
    def switch_version(self, target_version: str) -> bool:
        """切换到指定版本"""
        target_key = self.get_key_by_id(target_version)
        if not target_key:
            return False
        
        # 更新配置
        config = self.get_config()
        old_version = config.current_key_id
        config.current_key_id = target_version
        config.last_rotation_at = datetime.now()
        
        self.db.commit()
        
        return True
    
    def get_status(self) -> dict:
        """获取轮换状态"""
        config = self.get_config()
        all_keys = self.get_all_keys()
        
        # 如果没有密钥，创建默认密钥
        if not all_keys:
            # 使用 settings 中的密钥作为 v1
            default_key = self.generate_key("v1")
            default_key.key_value = settings.SECRET_KEY
            self.db.commit()
            all_keys = self.get_all_keys()
        
        current_version = config.current_key_id or "v1"
        
        return {
            "enabled": config.enabled,
            "current_version": current_version,
            "total_keys": len(all_keys),
            "keys": [k.to_dict() for k in all_keys],
            "last_rotation_at": config.last_rotation_at.isoformat() if config.last_rotation_at else None
        }
    
    def full_rotation(self) -> dict:
        """一键轮换：生成新密钥并切换"""
        # 生成新密钥
        new_key = self.generate_key()
        
        # 切换到新密钥
        self.switch_version(new_key.key_id)
        
        return {
            "success": True,
            "new_version": new_key.key_id,
            "key_preview": new_key.key_value[:4] + "***" + new_key.key_value[-4:]
        }
