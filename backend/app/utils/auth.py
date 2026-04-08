"""
认证和加密工具模块
"""
import os
import hashlib
import base64
import logging
from datetime import datetime, timedelta, timezone, UTC
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from app.config import settings


logger = logging.getLogger(__name__)


# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordDecryptionError(Exception):
    """密码解密失败异常"""
    pass


def hash_password(password: str) -> str:
    """
    对密码进行加盐哈希
    
    Args:
        password: 明文密码
    
    Returns:
        哈希后的密码
    """
    return pwd_context.hash(password + settings.PASSWORD_SALT)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码
    
    Returns:
        是否验证通过
    """
    return pwd_context.verify(plain_password + settings.PASSWORD_SALT, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT访问令牌
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
    
    Returns:
        JWT令牌
    """
    to_encode = data.copy()
    # JWT sub 字段必须是字符串
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """
    解码JWT访问令牌
    
    Args:
        token: JWT令牌
    
    Returns:
        解码后的数据，如果无效则返回None
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


class AESCipher:
    """
    AES加密解密工具类（支持密钥轮换）
    
    加密数据格式：
    - v1$base64(iv+ciphertext): 使用 v1 密钥加密
    - v2$base64(iv+ciphertext): 使用 v2 密钥加密
    - base64(iv+ciphertext): 无版本前缀（旧格式，使用 v1 密钥解密）
    """
    
    # 无版本前缀的旧格式
    LEGACY_PREFIX = "legacy$"
    
    def __init__(self, key: Optional[str] = None, version: str = "v1"):
        """
        初始化AES加密器
        
        Args:
            key: 加密密钥（必须为32字节）
            version: 密钥版本（v1 或 v2）
        """
        self.key = (key or settings.AES_KEY).encode('utf-8')
        if len(self.key) != 32:
            self.key = self.key.ljust(32, b'0')[:32]
        self.version = version
    
    def _get_key_for_version(self, version: str) -> bytes:
        """获取指定版本的密钥"""
        if version == "v2":
            key = settings.security.get_aes_key_by_version("v2")
        else:
            key = settings.security.get_aes_key_by_version("v1")
        
        if key:
            return key.encode('utf-8')
        
        # 如果指定版本没有密钥，回退到当前密钥
        return settings.AES_KEY.encode('utf-8')
    
    def encrypt(self, plaintext: str) -> str:
        """
        AES加密
        
        Args:
            plaintext: 明文
        
        Returns:
            加密后的字符串，格式：v{version}$base64(iv+ciphertext)
        """
        # 使用最新密钥版本
        version = settings.security.AES_CURRENT_VERSION
        if version == "v2" and settings.security.AES_KEY_V2:
            key = settings.security.AES_KEY_V2.encode('utf-8')
        else:
            key = self.key
        
        # 生成随机IV
        iv = os.urandom(16)
        
        # 填充明文到16字节的倍数
        plaintext_bytes = plaintext.encode('utf-8')
        padding_length = 16 - (len(plaintext_bytes) % 16)
        padded_plaintext = plaintext_bytes + bytes([padding_length] * padding_length)
        
        # 加密
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()
        
        # 返回版本前缀 + Base64编码
        encoded = base64.b64encode(iv + ciphertext).decode('utf-8')
        return f"v{version[1]}${encoded}"
    
    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        """
        解密（自动检测版本）
        
        Args:
            encrypted_text: 加密后的字符串
        
        Returns:
            解密后的明文
        """
        if not encrypted_text:
            raise ValueError("加密文本不能为空")
        
        # 检测版本前缀
        version = "v1"
        data = encrypted_text
        
        if encrypted_text.startswith("v1$"):
            version = "v1"
            data = encrypted_text[3:]
        elif encrypted_text.startswith("v2$"):
            version = "v2"
            data = encrypted_text[3:]
        elif encrypted_text.startswith(cls.LEGACY_PREFIX):
            # 旧格式，无版本前缀
            data = encrypted_text[len(cls.LEGACY_PREFIX):]
        
        # 获取对应版本的密钥
        if version == "v2" and settings.security.AES_KEY_V2:
            key = settings.security.AES_KEY_V2.encode('utf-8')
        else:
            key = settings.AES_KEY.encode('utf-8')
        
        if len(key) != 32:
            key = key.ljust(32, b'0')[:32]
        
        try:
            # Base64解码
            encrypted_data = base64.b64decode(data)
            
            # 检查数据长度
            if len(encrypted_data) < 17:
                raise ValueError(f"加密数据长度不足: {len(encrypted_data)} 字节")
            
            # 提取IV和密文
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            
            # 解密
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # 去除填充
            padding_length = padded_plaintext[-1]
            plaintext = padded_plaintext[:-padding_length]
            
            return plaintext.decode('utf-8')
        except Exception as e:
            logger.error(f"解密失败 (version={version}): {e}")
            raise ValueError(f"解密失败: {e}")
    
    @staticmethod
    def detect_version(encrypted_text: str) -> str:
        """
        检测加密数据的密钥版本
        
        Args:
            encrypted_text: 加密后的字符串
        
        Returns:
            版本标识：v1, v2, 或 legacy
        """
        if encrypted_text.startswith("v1$"):
            return "v1"
        elif encrypted_text.startswith("v2$"):
            return "v2"
        elif encrypted_text.startswith(AESCipher.LEGACY_PREFIX):
            return "legacy"
        else:
            # 无前缀的旧格式
            return "legacy"
    
    @staticmethod
    def needs_migration(encrypted_text: str) -> bool:
        """
        检查数据是否需要迁移到新密钥
        
        Args:
            encrypted_text: 加密后的字符串
        
        Returns:
            True 如果数据需要迁移到当前版本
        """
        current_version = settings.security.AES_CURRENT_VERSION
        data_version = AESCipher.detect_version(encrypted_text)
        
        # 转换为统一格式比较
        data_version_normalized = data_version if data_version != "legacy" else "v1"
        
        return data_version_normalized != current_version
    
    @staticmethod
    def re_encrypt(encrypted_text: str) -> str:
        """
        使用当前密钥重新加密数据
        
        Args:
            encrypted_text: 旧加密数据
        
        Returns:
            新加密数据
        """
        # 先解密
        plaintext = AESCipher.decrypt(encrypted_text)
        # 再用新密钥加密
        cipher = AESCipher()
        return cipher.encrypt(plaintext)


# 创建全局AES加密实例
aes_cipher = AESCipher()


def encrypt_instance_password(password: str) -> str:
    """
    加密MySQL实例密码
    
    Args:
        password: 明文密码
    
    Returns:
        加密后的密码
    """
    return aes_cipher.encrypt(password)


def decrypt_instance_password(encrypted_password: str) -> str:
    """
    解密实例密码

    Args:
        encrypted_password: 加密后的密码

    Returns:
        明文密码

    Raises:
        ValueError: 密码为空时
        PasswordDecryptionError: 解密失败时
    """
    # 空密码直接抛出异常（不允许使用未加密的密码）
    if not encrypted_password:
        raise ValueError("实例密码未配置")

    try:
        return aes_cipher.decrypt(encrypted_password)
    except Exception as e:
        logger.error(f"密码解密失败: {e}", exc_info=True)
        raise PasswordDecryptionError("实例密码解密失败，请联系管理员") from e


def get_instance_password(encrypted_password: Optional[str], allow_empty: bool = True) -> Optional[str]:
    """
    获取实例密码（统一的密码处理接口）

    Args:
        encrypted_password: 加密后的密码
        allow_empty: 是否允许空密码（Redis 等实例可能不需要密码）

    Returns:
        解密后的密码，如果允许空且密码为空则返回 None

    Raises:
        PasswordDecryptionError: 密码解密失败时
        ValueError: 密码未配置且不允许为空时
    """
    if not encrypted_password:
        if allow_empty:
            return None
        raise ValueError("实例密码未配置")

    try:
        return aes_cipher.decrypt(encrypted_password)
    except Exception as e:
        logger.error(f"密码解密失败: {e}", exc_info=True)
        raise PasswordDecryptionError("实例密码解密失败，请联系管理员") from e


def encrypt_dingtalk_webhook(webhook: str) -> str:
    """
    加密钉钉Webhook地址
    
    Args:
        webhook: Webhook地址
    
    Returns:
        加密后的地址
    """
    return aes_cipher.encrypt(webhook)


def decrypt_dingtalk_webhook(encrypted_webhook: str) -> str:
    """
    解密钉钉Webhook地址
    
    Args:
        encrypted_webhook: 加密后的地址
    
    Returns:
        Webhook地址
    """
    return aes_cipher.decrypt(encrypted_webhook)


def generate_md5(text: str) -> str:
    """
    生成MD5哈希值
    
    Args:
        text: 文本内容
    
    Returns:
        MD5哈希值
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def generate_sql_fingerprint(sql: str) -> str:
    """
    生成SQL指纹（用于慢查询去重）
    将SQL中的具体值替换为占位符
    
    Args:
        sql: SQL语句
    
    Returns:
        SQL指纹
    """
    import re
    
    # 替换数字
    sql = re.sub(r'\b\d+\b', '?', sql)
    
    # 替换字符串
    sql = re.sub(r"'[^']*'", "'?'", sql)
    sql = re.sub(r'"[^"]*"', '"?"', sql)
    
    # 替换IN列表
    sql = re.sub(r'\bIN\s*\([^)]+\)', 'IN (?)', sql, flags=re.IGNORECASE)
    
    # 去除多余空格
    sql = re.sub(r'\s+', ' ', sql).strip()
    
    return sql
