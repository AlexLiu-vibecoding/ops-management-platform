"""
AI 模型配置模型

支持配置多个 AI 模型通道，包括：
- 云端模型：豆包、OpenAI 等
- 本地模型：Ollama、vLLM 等
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class AIProvider(str, enum.Enum):
    """AI 模型提供商"""
    OPENAI = "openai"
    DOUBAO = "doubao"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class AIModelType(str, enum.Enum):
    """模型类型"""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"


class AIModelConfig(Base):
    """AI 模型配置表"""
    __tablename__ = "ai_model_configs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="配置名称")
    provider = Column(String(50), nullable=False, comment="提供商: openai/doubao/ollama/custom")
    base_url = Column(String(500), nullable=False, comment="API 地址")
    api_key_encrypted = Column(String(500), comment="加密后的 API 密钥")
    model_name = Column(String(100), nullable=False, comment="模型标识")
    model_type = Column(String(30), default="chat", comment="模型类型: chat/completion/embedding")
    
    # 调用参数
    max_tokens = Column(Integer, default=4096, comment="最大 token 数")
    temperature = Column(Float, default=0.7, comment="温度参数")
    timeout = Column(Integer, default=30, comment="超时时间(秒)")
    
    # 状态与优先级
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    is_default = Column(Boolean, default=False, comment="是否默认通道")
    priority = Column(Integer, default=0, comment="优先级(越大越高)")
    
    # 使用场景
    use_cases = Column(JSON, default=list, comment="使用场景: ['alert_analysis', 'sql_optimize']")
    
    # 元数据
    description = Column(String(200), comment="描述")
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    creator = relationship("User", foreign_keys=[created_by])


class AICallLog(Base):
    """AI 调用日志表"""
    __tablename__ = "ai_call_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_config_id = Column(Integer, ForeignKey("ai_model_configs.id", ondelete="SET NULL"), comment="模型配置ID")
    use_case = Column(String(50), nullable=False, comment="使用场景")
    input_tokens = Column(Integer, comment="输入 token 数")
    output_tokens = Column(Integer, comment="输出 token 数")
    latency_ms = Column(Integer, comment="响应耗时(毫秒)")
    success = Column(Boolean, nullable=False, comment="是否成功")
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")
    
    # 关联
    model_config = relationship("AIModelConfig", backref="call_logs")


# 提供商标签映射
PROVIDER_LABELS = {
    "openai": "OpenAI",
    "doubao": "豆包/火山引擎",
    "ollama": "Ollama (本地)",
    "custom": "自定义"
}

# 使用场景标签映射
USE_CASE_LABELS = {
    "alert_analysis": "告警分析",
    "sql_optimize": "SQL 优化",
    "inspection": "智能巡检"
}

# 预设模板
AI_MODEL_TEMPLATES = [
    {
        "name": "豆包 Flash",
        "provider": "doubao",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "model_name": "doubao-seed-1-6-flash-250615",
        "description": "豆包 Flash 模型，速度快，适合实时分析",
        "use_cases": ["alert_analysis"]
    },
    {
        "name": "OpenAI GPT-4",
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-4o",
        "description": "OpenAI GPT-4 模型，能力强",
        "use_cases": ["alert_analysis", "sql_optimize"]
    },
    {
        "name": "Ollama 本地",
        "provider": "ollama",
        "base_url": "http://localhost:11434/v1",
        "model_name": "",
        "description": "Ollama 本地模型，私有化部署",
        "use_cases": ["alert_analysis", "sql_optimize"]
    }
]
