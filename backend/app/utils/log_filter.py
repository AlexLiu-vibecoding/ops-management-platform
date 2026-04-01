"""
日志安全过滤器

提供日志敏感信息脱敏功能，防止敏感信息泄露到日志中

使用示例:
    # 在 main.py 中配置
    from app.utils.log_filter import SensitiveDataFilter
    
    # 为所有 logger 添加过滤器
    for handler in logging.root.handlers:
        handler.addFilter(SensitiveDataFilter())
"""
import re
import logging
from datetime import datetime, timezone
from typing import Any, Optional


class SensitiveDataFilter(logging.Filter):
    """
    敏感数据过滤器
    
    自动检测并脱敏日志中的敏感信息：
    - 密码
    - Token
    - API Key
    - 连接字符串
    - 信用卡号
    - 手机号
    - 身份证号
    """
    
    # 敏感数据模式（正则表达式）
    SENSITIVE_PATTERNS = [
        # 密码模式
        (r'password["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', r'password=***'),
        (r'passwd["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', r'passwd=***'),
        (r'pwd["\']?\s*[:=]\s*["\']?([^"\'\s,}]+)', r'pwd=***'),
        
        # Token 模式
        (r'token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{10,})', r'token=***'),
        (r'access_token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]+)', r'access_token=***'),
        (r'refresh_token["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]+)', r'refresh_token=***'),
        (r'authorization["\']?\s*[:=]\s*["\']?Bearer\s+[a-zA-Z0-9_\-\.]+', r'authorization=Bearer ***'),
        
        # API Key 模式
        (r'api_key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{10,})', r'api_key=***'),
        (r'apikey["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{10,})', r'apikey=***'),
        (r'aws_access_key_id["\']?\s*[:=]\s*["\']?([A-Z0-9]{20})', r'aws_access_key_id=***'),
        (r'aws_secret_access_key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9/+=]{40})', r'aws_secret_access_key=***'),
        
        # 数据库连接字符串
        (r'(mysql|postgresql|redis)://([^:]+):([^@]+)@', r'\1://\2:***@'),
        (r'jdbc:mysql://([^:]+):([^@]+)@', r'jdbc:mysql://\1:***@'),
        
        # 手机号（中国）- 使用函数处理
        # 身份证号 - 使用函数处理
        # 银行卡号 - 使用函数处理
    ]
    
    # 需要函数处理的模式
    FUNCTIONAL_PATTERNS = [
        # 手机号（中国）：保留前3后4
        (r'1[3-9]\d{9}', lambda m: m.group(0)[:3] + '****' + m.group(0)[-4:]),
        # 身份证号：保留前2后2
        (r'\d{17}[\dXx]', lambda m: m.group(0)[:2] + '*************' + m.group(0)[-2:]),
        # 银行卡号：保留前4后4
        (r'\d{16,19}', lambda m: m.group(0)[:4] + '****' + m.group(0)[-4:] if len(m.group(0)) >= 8 else '****'),
    ]
    
    # 编译后的正则模式（性能优化）
    _compiled_patterns = None
    _compiled_functional_patterns = None
    
    @classmethod
    def _get_compiled_patterns(cls):
        """获取编译后的正则模式（懒加载）"""
        if cls._compiled_patterns is None:
            cls._compiled_patterns = [
                (re.compile(pattern, re.IGNORECASE), replacement)
                for pattern, replacement in cls.SENSITIVE_PATTERNS
            ]
        return cls._compiled_patterns
    
    @classmethod
    def _get_compiled_functional_patterns(cls):
        """获取编译后的函数处理模式（懒加载）"""
        if cls._compiled_functional_patterns is None:
            cls._compiled_functional_patterns = [
                (re.compile(pattern), replacement)
                for pattern, replacement in cls.FUNCTIONAL_PATTERNS
            ]
        return cls._compiled_functional_patterns
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        过滤日志记录中的敏感信息
        
        Args:
            record: 日志记录对象
        
        Returns:
            bool: 总是返回 True（不过滤记录，只修改内容）
        """
        # 处理日志消息
        if isinstance(record.msg, str):
            record.msg = self._mask_sensitive(record.msg)
        
        # 处理格式化参数
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: self._mask_sensitive(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    self._mask_sensitive(arg) if isinstance(arg, str) else arg
                    for arg in record.args
                )
        
        return True
    
    def _mask_sensitive(self, text: str) -> str:
        """
        脱敏敏感信息
        
        Args:
            text: 原始文本
        
        Returns:
            str: 脱敏后的文本
        """
        if not text or not isinstance(text, str):
            return text
        
        masked_text = text
        
        # 首先处理字符串替换模式
        for pattern, replacement in self._get_compiled_patterns():
            if callable(replacement):
                masked_text = pattern.sub(replacement, masked_text)
            else:
                masked_text = pattern.sub(replacement, masked_text)
        
        # 然后处理函数处理模式（手机号、身份证、银行卡等）
        for pattern, replacement in self._get_compiled_functional_patterns():
            masked_text = pattern.sub(replacement, masked_text)
        
        return masked_text


class StructuredLogFormatter(logging.Formatter):
    """
    结构化日志格式器
    
    输出 JSON 格式的日志，便于日志收集和分析
    """
    
    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime
        
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 添加额外字段
        if hasattr(record, 'request_id'):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_secure_logging(
    level: int = logging.INFO,
    use_json: bool = False,
    log_file: Optional[str] = None
):
    """
    配置安全的日志系统
    
    Args:
        level: 日志级别
        use_json: 是否使用 JSON 格式
        log_file: 日志文件路径（可选）
    """
    import sys
    
    # 创建过滤器
    sensitive_filter = SensitiveDataFilter()
    
    # 创建格式器
    if use_json:
        formatter = StructuredLogFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(sensitive_filter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（可选）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        root_logger.addHandler(file_handler)
    
    # 为特定库设置日志级别
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    
    return root_logger


# 便捷函数
def mask_sensitive_data(text: str) -> str:
    """
    脱敏敏感数据（便捷函数）
    
    Args:
        text: 原始文本
    
    Returns:
        str: 脱敏后的文本
    """
    filter_instance = SensitiveDataFilter()
    return filter_instance._mask_sensitive(text)


__all__ = [
    'SensitiveDataFilter',
    'StructuredLogFormatter',
    'setup_secure_logging',
    'mask_sensitive_data'
]
