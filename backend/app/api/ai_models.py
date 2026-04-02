"""
AI 模型配置 API

管理 AI 模型通道配置，支持多模型、主备切换、交叉验证。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import time
import logging

from app.database import get_db
from app.deps import get_current_user, get_super_admin
from app.models import User
from app.models.ai_model import (
    AIModelConfig, AICallLog, AIProvider, AIModelType,
    PROVIDER_LABELS, USE_CASE_LABELS, AI_MODEL_TEMPLATES
)
from app.utils.auth import aes_cipher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-models", tags=["AI 模型配置"])


# ==================== Schemas ====================

class AIModelConfigCreate(BaseModel):
    """创建 AI 模型配置"""
    name: str = Field(..., max_length=100, description="配置名称")
    provider: str = Field(..., description="提供商")
    base_url: str = Field(..., max_length=500, description="API 地址")
    api_key: Optional[str] = Field(None, max_length=500, description="API 密钥")
    model_name: str = Field(..., max_length=100, description="模型标识")
    model_type: str = Field("chat", description="模型类型")
    max_tokens: int = Field(4096, ge=1, le=128000, description="最大 token 数")
    temperature: float = Field(0.7, ge=0, le=2, description="温度参数")
    timeout: int = Field(30, ge=1, le=300, description="超时时间")
    is_enabled: bool = Field(True, description="是否启用")
    is_default: bool = Field(False, description="是否默认通道")
    priority: int = Field(0, ge=0, le=100, description="优先级")
    use_cases: List[str] = Field(default_factory=list, description="使用场景")
    description: Optional[str] = Field(None, max_length=200, description="描述")


class AIModelConfigUpdate(BaseModel):
    """更新 AI 模型配置"""
    name: Optional[str] = Field(None, max_length=100)
    base_url: Optional[str] = Field(None, max_length=500)
    api_key: Optional[str] = Field(None, max_length=500)
    model_name: Optional[str] = Field(None, max_length=100)
    max_tokens: Optional[int] = Field(None, ge=1, le=128000)
    temperature: Optional[float] = Field(None, ge=0, le=2)
    timeout: Optional[int] = Field(None, ge=1, le=300)
    is_enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=100)
    use_cases: Optional[List[str]] = None
    description: Optional[str] = Field(None, max_length=200)


class AIModelTestRequest(BaseModel):
    """测试模型请求"""
    prompt: str = Field(..., max_length=2000, description="测试提示词")


# ==================== Helper Functions ====================

def mask_api_key(api_key: str) -> str:
    """脱敏 API 密钥"""
    if not api_key or len(api_key) < 8:
        return ""
    return f"{api_key[:4]}****{api_key[-4:]}"


def encrypt_api_key(api_key: str) -> str:
    """加密 API 密钥"""
    if not api_key:
        return ""
    return aes_cipher.encrypt(api_key)


def decrypt_api_key(encrypted: str) -> str:
    """解密 API 密钥"""
    if not encrypted:
        return ""
    try:
        return aes_cipher.decrypt(encrypted)
    except Exception:
        return ""


def config_to_response(config: AIModelConfig) -> dict:
    """转换配置为响应格式"""
    use_cases = config.use_cases or []
    return {
        "id": config.id,
        "name": config.name,
        "provider": config.provider,
        "provider_label": PROVIDER_LABELS.get(config.provider, config.provider),
        "base_url": config.base_url,
        "api_key_masked": mask_api_key(decrypt_api_key(config.api_key_encrypted)) if config.api_key_encrypted else None,
        "model_name": config.model_name,
        "model_type": config.model_type,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "timeout": config.timeout,
        "is_enabled": config.is_enabled,
        "is_default": config.is_default,
        "priority": config.priority,
        "use_cases": use_cases,
        "use_case_labels": [USE_CASE_LABELS.get(uc, uc) for uc in use_cases],
        "description": config.description,
        "created_by": config.created_by,
        "created_at": config.created_at,
        "updated_at": config.updated_at
    }


# ==================== API Endpoints ====================

@router.get("")
async def list_ai_models(
    is_enabled: Optional[bool] = None,
    provider: Optional[str] = None,
    use_case: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 AI 模型配置列表"""
    query = db.query(AIModelConfig)
    
    if is_enabled is not None:
        query = query.filter(AIModelConfig.is_enabled == is_enabled)
    
    if provider:
        query = query.filter(AIModelConfig.provider == provider)
    
    if use_case:
        query = query.filter(AIModelConfig.use_cases.contains([use_case]))
    
    configs = query.order_by(desc(AIModelConfig.priority), desc(AIModelConfig.created_at)).all()
    
    return [config_to_response(c) for c in configs]


@router.get("/providers")
async def get_providers(current_user: User = Depends(get_current_user)):
    """获取支持的提供商列表"""
    return [
        {"value": k, "label": v}
        for k, v in PROVIDER_LABELS.items()
    ]


@router.get("/use-cases")
async def get_use_cases(current_user: User = Depends(get_current_user)):
    """获取使用场景列表"""
    return [
        {"value": k, "label": v}
        for k, v in USE_CASE_LABELS.items()
    ]


@router.get("/templates")
async def get_templates(current_user: User = Depends(get_current_user)):
    """获取预设模板列表"""
    return AI_MODEL_TEMPLATES


@router.get("/{model_id}")
async def get_ai_model(
    model_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单个 AI 模型配置"""
    config = db.query(AIModelConfig).filter(AIModelConfig.id == model_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    return config_to_response(config)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_ai_model(
    data: AIModelConfigCreate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """创建 AI 模型配置（仅超级管理员）"""
    # 检查名称是否重复
    existing = db.query(AIModelConfig).filter(AIModelConfig.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="配置名称已存在")
    
    # 如果设为默认，取消其他默认
    if data.is_default:
        db.query(AIModelConfig).filter(AIModelConfig.is_default == True).update({"is_default": False})
    
    # 创建配置
    config = AIModelConfig(
        name=data.name,
        provider=data.provider,
        base_url=data.base_url,
        api_key_encrypted=encrypt_api_key(data.api_key) if data.api_key else None,
        model_name=data.model_name,
        model_type=data.model_type,
        max_tokens=data.max_tokens,
        temperature=data.temperature,
        timeout=data.timeout,
        is_enabled=data.is_enabled,
        is_default=data.is_default,
        priority=data.priority,
        use_cases=data.use_cases,
        description=data.description,
        created_by=current_user.id
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    return {"id": config.id, "message": "创建成功"}


@router.put("/{model_id}")
async def update_ai_model(
    model_id: int,
    data: AIModelConfigUpdate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """更新 AI 模型配置（仅超级管理员）"""
    config = db.query(AIModelConfig).filter(AIModelConfig.id == model_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    
    # 检查名称是否重复
    if data.name and data.name != config.name:
        existing = db.query(AIModelConfig).filter(AIModelConfig.name == data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="配置名称已存在")
    
    # 如果设为默认，取消其他默认
    if data.is_default:
        db.query(AIModelConfig).filter(
            AIModelConfig.is_default == True,
            AIModelConfig.id != model_id
        ).update({"is_default": False})
    
    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    
    # 特殊处理 API 密钥
    if "api_key" in update_data:
        api_key = update_data.pop("api_key")
        if api_key:
            config.api_key_encrypted = encrypt_api_key(api_key)
    
    for key, value in update_data.items():
        setattr(config, key, value)
    
    db.commit()
    
    return {"message": "更新成功"}


@router.delete("/{model_id}")
async def delete_ai_model(
    model_id: int,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """删除 AI 模型配置（仅超级管理员）"""
    config = db.query(AIModelConfig).filter(AIModelConfig.id == model_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    
    # 不允许删除默认配置
    if config.is_default:
        raise HTTPException(status_code=400, detail="不能删除默认模型配置")
    
    db.delete(config)
    db.commit()
    
    return {"message": "删除成功"}


@router.post("/{model_id}/test")
async def test_ai_model(
    model_id: int,
    data: AIModelTestRequest,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """测试 AI 模型连接（仅超级管理员）"""
    config = db.query(AIModelConfig).filter(AIModelConfig.id == model_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    
    # 获取解密后的 API 密钥
    api_key = decrypt_api_key(config.api_key_encrypted) if config.api_key_encrypted else ""
    
    start_time = time.time()
    
    # 检查 API Key 是否配置
    if not api_key:
        return {
            "success": False,
            "response": None,
            "latency_ms": 0,
            "error": "未配置 API Key，请编辑模型配置并填入有效的 API 密钥"
        }
    
    try:
        import httpx
        
        # 直接使用 httpx 调用 API，更好地处理各种响应格式
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": config.model_name,
            "messages": [{"role": "user", "content": data.prompt}],
            "max_tokens": 100
        }
        
        # 构建完整的 API URL
        base_url = config.base_url.rstrip('/')
        if not base_url.endswith('/chat/completions'):
            if base_url.endswith('/v1') or base_url.endswith('/v3'):
                api_url = f"{base_url}/chat/completions"
            else:
                api_url = f"{base_url}/v1/chat/completions"
        else:
            api_url = base_url
        
        logger.info(f"Testing AI model: {config.name}, URL: {api_url}, Model: {config.model_name}")
        
        with httpx.Client(timeout=config.timeout) as client:
            response = client.post(api_url, headers=headers, json=payload)
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        logger.info(f"AI model test response status: {response.status_code}")
        
        if response.status_code != 200:
            error_detail = response.text
            try:
                error_json = response.json()
                if "error" in error_json:
                    error_detail = error_json["error"].get("message", str(error_json["error"]))
                elif "message" in error_json:
                    error_detail = error_json["message"]
                elif "code" in error_json:
                    error_detail = f"错误码: {error_json.get('code')}, 消息: {error_json.get('message', response.text)}"
            except:
                pass
            
            # 记录失败日志
            log = AICallLog(
                model_config_id=config.id,
                use_case="test",
                latency_ms=latency_ms,
                success=False,
                error_message=error_detail
            )
            db.add(log)
            db.commit()
            
            return {
                "success": False,
                "response": None,
                "latency_ms": latency_ms,
                "error": f"API 错误 ({response.status_code}): {error_detail}"
            }
        
        # 解析响应
        result = response.json()
        
        # 处理不同格式的响应
        response_text = ""
        if "choices" in result and result["choices"]:
            # OpenAI 标准格式
            response_text = result["choices"][0].get("message", {}).get("content", "")
        elif "data" in result:
            # 某些 API 返回 data 字段
            response_text = str(result["data"])
        elif "output" in result:
            # 豆包/火山引擎格式
            response_text = str(result["output"])
        elif "result" in result:
            response_text = str(result["result"])
        else:
            response_text = str(result)
        
        # 记录成功日志
        log = AICallLog(
            model_config_id=config.id,
            use_case="test",
            latency_ms=latency_ms,
            success=True
        )
        db.add(log)
        db.commit()
        
        return {
            "success": True,
            "response": response_text[:500],  # 限制响应长度
            "latency_ms": latency_ms,
            "error": None
        }
        
    except httpx.TimeoutException:
        latency_ms = int((time.time() - start_time) * 1000)
        return {
            "success": False,
            "response": None,
            "latency_ms": latency_ms,
            "error": f"请求超时（{config.timeout}秒）"
        }
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        logger.error(f"AI model test error: {str(e)}")
        
        # 记录失败日志
        log = AICallLog(
            model_config_id=config.id,
            use_case="test",
            latency_ms=latency_ms,
            success=False,
            error_message=str(e)
        )
        db.add(log)
        db.commit()
        
        return {
            "success": False,
            "response": None,
            "latency_ms": latency_ms,
            "error": str(e)
        }


@router.post("/{model_id}/set-default")
async def set_default_model(
    model_id: int,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """设置默认模型（仅超级管理员）"""
    config = db.query(AIModelConfig).filter(AIModelConfig.id == model_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="模型配置不存在")
    
    if not config.is_enabled:
        raise HTTPException(status_code=400, detail="不能将禁用的模型设为默认")
    
    # 取消其他默认
    db.query(AIModelConfig).filter(AIModelConfig.is_default == True).update({"is_default": False})
    
    # 设置当前为默认
    config.is_default = True
    config.priority = 100  # 默认模型优先级最高
    db.commit()
    
    return {"message": f"已将 {config.name} 设为默认模型"}


@router.get("/stats/call-logs")
async def get_call_stats(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 AI 调用统计"""
    from datetime import timedelta
    from sqlalchemy import func
    
    start_date = datetime.now() - timedelta(days=days)
    
    # 按模型统计
    model_stats = db.query(
        AIModelConfig.name,
        func.count(AICallLog.id).label("total_calls"),
        func.sum(func.cast(AICallLog.success, Integer)).label("success_calls"),
        func.avg(AICallLog.latency_ms).label("avg_latency"),
        func.sum(func.coalesce(AICallLog.input_tokens, 0)).label("total_input_tokens"),
        func.sum(func.coalesce(AICallLog.output_tokens, 0)).label("total_output_tokens")
    ).join(
        AICallLog, AIModelConfig.id == AICallLog.model_config_id
    ).filter(
        AICallLog.created_at >= start_date
    ).group_by(AIModelConfig.id).all()
    
    return [
        {
            "model_name": stat.name,
            "total_calls": stat.total_calls,
            "success_calls": stat.success_calls or 0,
            "success_rate": round((stat.success_calls or 0) / stat.total_calls * 100, 1) if stat.total_calls else 0,
            "avg_latency_ms": round(stat.avg_latency, 1) if stat.avg_latency else 0,
            "total_tokens": (stat.total_input_tokens or 0) + (stat.total_output_tokens or 0)
        }
        for stat in model_stats
    ]
