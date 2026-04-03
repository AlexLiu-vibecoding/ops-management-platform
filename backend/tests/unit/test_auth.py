"""
认证模块单元测试
"""
import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt

from app.utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)
from app.config import settings


class TestPasswordUtils:
    """密码工具测试"""

    def test_hash_password(self):
        """测试密码哈希"""
        password = "test_password123"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$")  # bcrypt 哈希以 $ 开头

    def test_verify_password_success(self):
        """测试密码验证成功"""
        password = "test_password123"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_failure(self):
        """测试密码验证失败"""
        password = "test_password123"
        wrong_password = "wrong_password"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False


class TestJWTToken:
    """JWT Token 测试"""

    def test_create_access_token(self):
        """测试创建访问令牌"""
        data = {"sub": "test_user", "role": "admin"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        
        # 验证令牌可以解码
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == "test_user"
        assert payload["role"] == "admin"

    def test_create_access_token_with_expiry(self):
        """测试创建带过期时间的令牌"""
        data = {"sub": "test_user"}
        expires = timedelta(minutes=5)
        token = create_access_token(data, expires_delta=expires)
        
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        
        # 验证过期时间存在
        assert "exp" in payload

    def test_decode_token_success(self):
        """测试解码有效令牌"""
        data = {"sub": "test_user", "role": "admin"}
        token = create_access_token(data)
        
        payload = decode_access_token(token)
        
        assert payload is not None
        assert payload["sub"] == "test_user"

    def test_decode_token_invalid(self):
        """测试解码无效令牌"""
        invalid_token = "invalid.token.here"
        
        payload = decode_access_token(invalid_token)
        
        assert payload is None

    def test_decode_token_expired(self):
        """测试解码过期令牌"""
        # 创建一个已经过期的令牌
        expired_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        data = {"sub": "test_user", "exp": expired_time}
        token = jwt.encode(
            data,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        payload = decode_access_token(token)
        
        assert payload is None
