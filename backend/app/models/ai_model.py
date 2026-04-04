"""
AI 模型配置模型

架构设计：
- AIModelConfig: AI 模型配置（底座）
- AISceneConfig: 场景配置，关联到具体的模型

这样用户可以：
1. 配置多个 AI 模型（底座）
2. 为每个场景独立选择使用哪个模型
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class AIProvider(enum.StrEnum):
    """AI 模型提供商"""
    OPENAI = "openai"
    DOUBAO = "doubao"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class AIModelType(enum.StrEnum):
    """模型类型"""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"


class AIScene(enum.StrEnum):
    """AI 使用场景"""
    SQL_OPTIMIZE = "sql_optimize"       # SQL 优化
    ALERT_ANALYSIS = "alert_analysis"   # 告警分析
    INSPECTION = "inspection"           # 智能巡检


class AIModelConfig(Base):
    """AI 模型配置表（底座）"""
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
    
    # 状态
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    priority = Column(Integer, default=0, comment="优先级(越大越高)")
    
    # 兼容旧字段（已弃用，由 AISceneConfig 替代）
    is_default = Column(Boolean, default=False, comment="是否默认通道（已弃用）")
    use_cases = Column(JSON, default=list, comment="使用场景（已弃用）")
    
    # 元数据
    description = Column(String(200), comment="描述")
    created_by = Column(Integer, ForeignKey("users.id"), comment="创建人")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    creator = relationship("User", foreign_keys=[created_by])
    scene_configs = relationship("AISceneConfig", back_populates="model_config")


class AISceneConfig(Base):
    """AI 场景配置表 - 定义场景使用哪个模型"""
    __tablename__ = "ai_scene_configs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    scene = Column(String(50), nullable=False, unique=True, comment="场景标识: sql_optimize/alert_analysis/inspection")
    model_config_id = Column(Integer, ForeignKey("ai_model_configs.id"), nullable=False, comment="关联的模型配置ID")
    custom_prompt = Column(Text, comment="自定义提示词(可选)")
    custom_params = Column(JSON, comment="自定义参数(可选): {temperature, max_tokens等}")
    is_enabled = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    model_config = relationship("AIModelConfig", back_populates="scene_configs")


class AICallLog(Base):
    """AI 调用日志表"""
    __tablename__ = "ai_call_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_config_id = Column(Integer, ForeignKey("ai_model_configs.id", ondelete="SET NULL"), comment="模型配置ID")
    scene = Column(String(50), nullable=False, comment="使用场景")
    input_tokens = Column(Integer, comment="输入 token 数")
    output_tokens = Column(Integer, comment="输出 token 数")
    latency_ms = Column(Integer, comment="响应耗时(毫秒)")
    success = Column(Boolean, nullable=False, comment="是否成功")
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime, default=datetime.now, index=True, comment="创建时间")
    
    # 关联
    model_config = relationship("AIModelConfig", backref="call_logs")


class AIAvailableModel(Base):
    """可用模型列表 - 从提供商获取的模型清单"""
    __tablename__ = "ai_available_models"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    provider = Column(String(50), nullable=False, index=True, comment="提供商: openai/doubao/ollama/custom")
    model_id = Column(String(100), nullable=False, comment="模型标识")
    model_name = Column(String(200), nullable=False, comment="模型显示名称")
    model_type = Column(String(30), default="chat", comment="模型类型: chat/completion/embedding")
    context_window = Column(Integer, comment="上下文窗口大小")
    is_available = Column(Boolean, default=True, comment="是否可用")
    raw_data = Column(JSON, comment="原始数据(提供商返回的完整信息)")
    fetched_at = Column(DateTime, default=datetime.now, comment="获取时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 联合唯一约束：同一提供商下模型 ID 唯一
    __table_args__ = (
        {"unique_constraint": ("provider", "model_id")},
    )


# 提供商标签映射
PROVIDER_LABELS = {
    "openai": "OpenAI",
    "doubao": "豆包/火山引擎",
    "ollama": "Ollama (本地)",
    "custom": "自定义"
}

# 场景标签映射
SCENE_LABELS = {
    "sql_optimize": "SQL 优化",
    "alert_analysis": "告警分析",
    "inspection": "智能巡检"
}

# 兼容旧代码
USE_CASE_LABELS = SCENE_LABELS

# 预设模板（model_name 留空，用户需要根据实际情况填写）
AI_MODEL_TEMPLATES = [
    {
        "name": "豆包",
        "provider": "doubao",
        "base_url": "https://integration.coze.cn/api/v3",
        "model_name": "",
        "description": "豆包模型，通过 coze_coding_dev_sdk 调用"
    },
    {
        "name": "OpenAI",
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "model_name": "",
        "description": "OpenAI GPT 系列模型"
    },
    {
        "name": "Ollama 本地",
        "provider": "ollama",
        "base_url": "http://localhost:11434/v1",
        "model_name": "",
        "description": "Ollama 本地模型，私有化部署"
    }
]


# ============ 工具函数 ============

def get_ai_config_for_scene(db, scene: str):
    """
    获取指定场景的 AI 配置
    
    Args:
        db: 数据库会话
        scene: 场景标识 (如 'sql_optimize', 'alert_analysis')
        
    Returns:
        tuple: (AIModelConfig, AISceneConfig) 或 (None, None)
    """
    scene_config = db.query(AISceneConfig).filter(
        AISceneConfig.scene == scene,
        AISceneConfig.is_enabled
    ).first()
    
    if not scene_config:
        return None, None
    
    # 获取关联的模型配置
    model_config = db.query(AIModelConfig).filter(
        AIModelConfig.id == scene_config.model_config_id,
        AIModelConfig.is_enabled
    ).first()
    
    return model_config, scene_config


def get_ai_model_config_for_use_case(db, use_case: str):
    """
    获取指定使用场景的 AI 模型配置（兼容旧代码）
    
    Args:
        db: 数据库会话
        use_case: 使用场景 (如 'sql_optimize', 'alert_analysis')
        
    Returns:
        AIModelConfig 对象或 None
    """
    model_config, _ = get_ai_config_for_scene(db, use_case)
    return model_config


def init_default_scene_configs(db):
    """
    初始化默认场景配置
    
    在数据库初始化时调用，为每个场景创建默认配置
    """
    # 获取第一个可用的模型配置
    first_model = db.query(AIModelConfig).filter(
        AIModelConfig.is_enabled
    ).order_by(AIModelConfig.priority.desc()).first()
    
    if not first_model:
        return
    
    # 为每个场景创建默认配置
    for scene_key in SCENE_LABELS.keys():
        existing = db.query(AISceneConfig).filter(
            AISceneConfig.scene == scene_key
        ).first()
        
        if not existing:
            scene_config = AISceneConfig(
                scene=scene_key,
                model_config_id=first_model.id,
                is_enabled=True
            )
            db.add(scene_config)
    
    db.commit()
