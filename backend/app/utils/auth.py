"""
认证和加密工具模块
"""
import os
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from app.config import settings


# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
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
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
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
    """AES加密解密工具类"""
    
    def __init__(self, key: Optional[str] = None):
        """
        初始化AES加密器
        
        Args:
            key: 加密密钥（必须为32字节）
        """
        self.key = (key or settings.AES_KEY).encode('utf-8')
        if len(self.key) != 32:
            # 如果密钥长度不是32字节，进行填充或截断
            self.key = self.key.ljust(32, b'0')[:32]
    
    def encrypt(self, plaintext: str) -> str:
        """
        AES加密
        
        Args:
            plaintext: 明文
        
        Returns:
            加密后的Base64字符串
        """
        # 生成随机IV
        iv = os.urandom(16)
        
        # 填充明文到16字节的倍数
        plaintext_bytes = plaintext.encode('utf-8')
        padding_length = 16 - (len(plaintext_bytes) % 16)
        padded_plaintext = plaintext_bytes + bytes([padding_length] * padding_length)
        
        # 加密
        cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()
        
        # 返回IV + 密文的Base64编码
        return base64.b64encode(iv + ciphertext).decode('utf-8')
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        AES解密
        
        Args:
            encrypted_text: 加密后的Base64字符串
        
        Returns:
            解密后的明文
        """
        if not encrypted_text:
            raise ValueError("加密文本不能为空")
        
        try:
            # Base64解码
            encrypted_data = base64.b64decode(encrypted_text)
            
            # 检查数据长度是否足够
            if len(encrypted_data) < 17:  # 至少需要 16 字节 IV + 1 字节密文
                raise ValueError(f"加密数据长度不足: {len(encrypted_data)} 字节")
            
            # 提取IV和密文
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            
            # 解密
            cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # 去除填充
            padding_length = padded_plaintext[-1]
            plaintext = padded_plaintext[:-padding_length]
            
            return plaintext.decode('utf-8')
        except Exception as e:
            raise ValueError(f"解密失败: {str(e)}")


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
    解密MySQL实例密码
    
    Args:
        encrypted_password: 加密后的密码
    
    Returns:
        明文密码
    """
    return aes_cipher.decrypt(encrypted_password)


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
