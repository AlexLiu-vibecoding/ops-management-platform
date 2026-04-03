"""
AI 模型配置 API

架构：
- AIModelConfig: AI 模型配置（底座）
- AISceneConfig: 场景配置，关联到具体的模型
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, Integer
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import time
import logging

from app.database import get_db
from app.deps import get_current_user, get_super_admin
from app.models import User
from app.models.ai_model import (
    AIModelConfig, AISceneConfig, AICallLog,
    PROVIDER_LABELS, SCENE_LABELS, AI_MODEL_TEMPLATES,
    init_default_scene_configs
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
    priority: int = Field(0, ge=0, le=100, description="优先级")
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
    priority: Optional[int] = Field(None, ge=0, le=100)
    description: Optional[str] = Field(None, max_length=200)


class AISceneConfigUpdate(BaseModel):
    """更新场景配置"""
    model_config_id: int = Field(..., description="关联的模型配置ID")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词")
    custom_params: Optional[Dict[str, Any]] = Field(None, description="自定义参数")
    is_enabled: bool = Field(True, description="是否启用")


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
        "priority": config.priority,
        "description": config.description,
        "created_by": config.created_by,
        "created_at": config.created_at,
        "updated_at": config.updated_at
    }


def scene_config_to_response(scene_config: AISceneConfig) -> dict:
    """转换场景配置为响应格式"""
    model_info = None
    if scene_config.model_config:
        model_info = {
            "id": scene_config.model_config.id,
            "name": scene_config.model_config.name,
            "provider": scene_config.model_config.provider,
            "model_name": scene_config.model_config.model_name,
            "is_enabled": scene_config.model_config.is_enabled
        }
    
    return {
        "id": scene_config.id,
        "scene": scene_config.scene,
        "scene_label": SCENE_LABELS.get(scene_config.scene, scene_config.scene),
        "model_config_id": scene_config.model_config_id,
        "model_config": model_info,
        "custom_prompt": scene_config.custom_prompt,
        "custom_params": scene_config.custom_params,
        "is_enabled": scene_config.is_enabled,
        "created_at": scene_config.created_at,
        "updated_at": scene_config.updated_at
    }


# ==================== 模型配置 API ====================

@router.get("")
async def list_ai_models(
    is_enabled: Optional[bool] = None,
    provider: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 AI 模型配置列表"""
    query = db.query(AIModelConfig)
    
    if is_enabled is not None:
        query = query.filter(AIModelConfig.is_enabled == is_enabled)
    
    if provider:
        query = query.filter(AIModelConfig.provider == provider)
    
    configs = query.order_by(desc(AIModelConfig.priority), desc(AIModelConfig.created_at)).all()
    
    return [config_to_response(c) for c in configs]


@router.get("/providers")
async def get_providers(current_user: User = Depends(get_current_user)):
    """获取支持的提供商列表"""
    return [
        {"value": k, "label": v}
        for k, v in PROVIDER_LABELS.items()
    ]


@router.get("/scenes")
async def get_scenes(current_user: User = Depends(get_current_user)):
    """获取支持的场景列表"""
    return [
        {"value": k, "label": v}
        for k, v in SCENE_LABELS.items()
    ]


@router.get("/templates")
async def get_templates(current_user: User = Depends(get_current_user)):
    """获取预设模板列表"""
    return AI_MODEL_TEMPLATES


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
        priority=data.priority,
        description=data.description,
        created_by=current_user.id
    )
    
    db.add(config)
    db.commit()
    db.refresh(config)
    
    # 如果是第一个模型，自动初始化场景配置
    total_models = db.query(AIModelConfig).count()
    if total_models == 1:
        init_default_scene_configs(db)
    
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
    
    # 检查是否有关联的场景配置
    linked_scenes = db.query(AISceneConfig).filter(
        AISceneConfig.model_config_id == model_id
    ).count()
    
    if linked_scenes > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"该模型被 {linked_scenes} 个场景使用，请先修改场景配置"
        )
    
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
    
    start_time = time.time()
    
    # 豆包模型使用 LLMClient 调用
    if config.provider == "doubao":
        return await _test_doubao_model(config, data.prompt, start_time, db)
    
    # 其他模型使用标准 OpenAI 格式调用
    return await _test_openai_compatible_model(config, data.prompt, start_time, db)


async def _test_doubao_model(
    config: AIModelConfig,
    prompt: str,
    start_time: float,
    db: Session
) -> dict:
    """测试豆包模型（使用 coze_coding_dev_sdk）"""
    try:
        from app.utils.llm_client import get_llm_client
        
        logger.info(f"Testing Doubao model: {config.name}, Model: {config.model_name}")
        
        llm_client = get_llm_client()
        
        # 使用 ainvoke 异步调用
        response = await llm_client.ainvoke(
            user_message=prompt,
            model=config.model_name,
            temperature=config.temperature,
            max_tokens=100  # 测试时限制输出长度
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 记录成功日志
        log = AICallLog(
            model_config_id=config.id,
            scene="test",
            latency_ms=latency_ms,
            success=True
        )
        db.add(log)
        db.commit()
        
        return {
            "success": True,
            "response": response[:500] if response else "模型返回空响应",
            "latency_ms": latency_ms,
            "error": None
        }
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        error_msg = str(e)
        logger.error(f"Doubao model test error: {error_msg}")
        
        # 记录失败日志
        log = AICallLog(
            model_config_id=config.id,
            scene="test",
            latency_ms=latency_ms,
            success=False,
            error_message=error_msg
        )
        db.add(log)
        db.commit()
        
        return {
            "success": False,
            "response": None,
            "latency_ms": latency_ms,
            "error": f"豆包模型调用失败: {error_msg}"
        }


async def _test_openai_compatible_model(
    config: AIModelConfig,
    prompt: str,
    start_time: float,
    db: Session
) -> dict:
    """测试 OpenAI 兼容模型"""
    import httpx
    
    # 获取解密后的 API 密钥
    api_key = decrypt_api_key(config.api_key_encrypted) if config.api_key_encrypted else ""
    
    # 检查 API Key 是否配置
    if not api_key:
        return {
            "success": False,
            "response": None,
            "latency_ms": 0,
            "error": "未配置 API Key，请编辑模型配置并填入有效的 API 密钥"
        }
    
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        payload = {
            "model": config.model_name,
            "messages": [{"role": "user", "content": prompt}],
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
        
        if response.status_code != 200:
            error_detail = response.text
            try:
                error_json = response.json()
                if "error" in error_json:
                    error_detail = error_json["error"].get("message", str(error_json["error"]))
                elif "message" in error_json:
                    error_detail = error_json["message"]
            except:
                pass
            
            log = AICallLog(
                model_config_id=config.id,
                scene="test",
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
        response_text = ""
        if "choices" in result and result["choices"]:
            response_text = result["choices"][0].get("message", {}).get("content", "")
        else:
            response_text = str(result)
        
        log = AICallLog(
            model_config_id=config.id,
            scene="test",
            latency_ms=latency_ms,
            success=True
        )
        db.add(log)
        db.commit()
        
        return {
            "success": True,
            "response": response_text[:500],
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
        
        log = AICallLog(
            model_config_id=config.id,
            scene="test",
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


# ==================== 场景配置 API ====================

@router.get("/scene-configs/list")
async def list_scene_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有场景配置"""
    # 确保所有场景都有配置
    init_default_scene_configs(db)
    
    configs = db.query(AISceneConfig).all()
    return [scene_config_to_response(c) for c in configs]


@router.get("/scene-configs/{scene}")
async def get_scene_config(
    scene: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单个场景配置"""
    config = db.query(AISceneConfig).filter(AISceneConfig.scene == scene).first()
    if not config:
        raise HTTPException(status_code=404, detail="场景配置不存在")
    return scene_config_to_response(config)


@router.put("/scene-configs/{scene}")
async def update_scene_config(
    scene: str,
    data: AISceneConfigUpdate,
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """更新场景配置（仅超级管理员）"""
    # 验证场景是否有效
    if scene not in SCENE_LABELS:
        raise HTTPException(status_code=400, detail="无效的场景标识")
    
    # 验证模型配置是否存在
    model_config = db.query(AIModelConfig).filter(AIModelConfig.id == data.model_config_id).first()
    if not model_config:
        raise HTTPException(status_code=400, detail="模型配置不存在")
    
    if not model_config.is_enabled:
        raise HTTPException(status_code=400, detail="不能使用已禁用的模型")
    
    # 获取或创建场景配置
    scene_config = db.query(AISceneConfig).filter(AISceneConfig.scene == scene).first()
    
    if not scene_config:
        scene_config = AISceneConfig(
            scene=scene,
            model_config_id=data.model_config_id,
            custom_prompt=data.custom_prompt,
            custom_params=data.custom_params,
            is_enabled=data.is_enabled
        )
        db.add(scene_config)
    else:
        scene_config.model_config_id = data.model_config_id
        scene_config.custom_prompt = data.custom_prompt
        scene_config.custom_params = data.custom_params
        scene_config.is_enabled = data.is_enabled
    
    db.commit()
    
    return {"message": "更新成功"}


# ==================== 调用统计 API ====================

@router.get("/stats/call-logs")
async def get_call_stats(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取 AI 调用统计"""
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


# ==================== 兼容旧 API ====================

@router.get("/use-cases")
async def get_use_cases(current_user: User = Depends(get_current_user)):
    """获取使用场景列表（兼容旧 API）"""
    return [
        {"value": k, "label": v}
        for k, v in SCENE_LABELS.items()
    ]


# ==================== 可用模型管理 ====================

@router.get("/available-models")
async def list_available_models(
    provider: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取可用模型列表
    
    返回从提供商获取的模型清单，用于前端下拉框选择
    """
    from app.models.ai_model import AIAvailableModel
    
    query = db.query(AIAvailableModel).filter(AIAvailableModel.is_available == True)
    
    if provider:
        query = query.filter(AIAvailableModel.provider == provider)
    
    models = query.order_by(AIAvailableModel.provider, AIAvailableModel.model_name).all()
    
    # 按提供商分组
    result = {}
    for model in models:
        if model.provider not in result:
            result[model.provider] = []
        result[model.provider].append({
            "id": model.id,
            "model_id": model.model_id,
            "model_name": model.model_name,
            "model_type": model.model_type,
            "context_window": model.context_window,
            "fetched_at": model.fetched_at.isoformat() if model.fetched_at else None
        })
    
    return {
        "total": len(models),
        "by_provider": result,
        "providers": list(result.keys())
    }


@router.post("/available-models/refresh")
async def refresh_available_models(
    current_user: User = Depends(get_super_admin),
    db: Session = Depends(get_db)
):
    """
    刷新可用模型列表（从提供商 API 拉取）
    
    仅超级管理员可调用
    """
    from app.models.ai_model import AIAvailableModel
    import httpx
    
    refreshed = {}
    errors = []
    
    # 1. 获取所有启用的模型配置，按提供商分组
    configs = db.query(AIModelConfig).filter(AIModelConfig.is_enabled == True).all()
    
    providers_to_fetch = set(c.provider for c in configs)
    
    for provider in providers_to_fetch:
        try:
            if provider == "doubao":
                # 豆包模型列表（通过 SDK 内置列表）
                models = _fetch_doubao_models()
            else:
                # OpenAI 兼容 API
                provider_configs = [c for c in configs if c.provider == provider]
                if provider_configs:
                    models = await _fetch_openai_models(provider_configs[0])
                else:
                    models = []
            
            # 更新数据库
            for model_info in models:
                existing = db.query(AIAvailableModel).filter(
                    AIAvailableModel.provider == provider,
                    AIAvailableModel.model_id == model_info["model_id"]
                ).first()
                
                if existing:
                    existing.model_name = model_info.get("model_name", existing.model_name)
                    existing.model_type = model_info.get("model_type", existing.model_type)
                    existing.context_window = model_info.get("context_window")
                    existing.is_available = model_info.get("is_available", True)
                    existing.raw_data = model_info.get("raw_data")
                    existing.fetched_at = datetime.now()
                    existing.updated_at = datetime.now()
                else:
                    new_model = AIAvailableModel(
                        provider=provider,
                        model_id=model_info["model_id"],
                        model_name=model_info.get("model_name", model_info["model_id"]),
                        model_type=model_info.get("model_type", "chat"),
                        context_window=model_info.get("context_window"),
                        is_available=model_info.get("is_available", True),
                        raw_data=model_info.get("raw_data"),
                        fetched_at=datetime.now()
                    )
                    db.add(new_model)
            
            db.commit()
            refreshed[provider] = len(models)
            
        except Exception as e:
            errors.append(f"{provider}: {str(e)}")
            logger.error(f"刷新 {provider} 模型列表失败: {e}")
    
    return {
        "message": "刷新完成",
        "refreshed": refreshed,
        "errors": errors if errors else None
    }


def _fetch_doubao_models() -> List[Dict]:
    """
    获取豆包可用模型列表

    豆包模型通过 SDK 调用，这里返回 SDK 支持的标准模型列表
    参考: /skills/public/prod/llm/python/README.md
    """
    # SDK 支持的标准豆包模型列表
    return [
        # Seed 2.0 系列
        {"model_id": "doubao-seed-2-0-pro-260215", "model_name": "Doubao Seed 2.0 Pro (旗舰)", "model_type": "chat", "context_window": 128000, "is_recommended": True},
        {"model_id": "doubao-seed-2-0-lite-260215", "model_name": "Doubao Seed 2.0 Lite (均衡)", "model_type": "chat", "context_window": 128000},
        {"model_id": "doubao-seed-2-0-mini-260215", "model_name": "Doubao Seed 2.0 Mini (轻量)", "model_type": "chat", "context_window": 256000},
        # Seed 1.8 系列
        {"model_id": "doubao-seed-1-8-251228", "model_name": "Doubao Seed 1.8 (多模态Agent)", "model_type": "chat", "context_window": 128000},
        # Seed 1.6 系列
        {"model_id": "doubao-seed-1-6-251015", "model_name": "Doubao Seed 1.6 (通用)", "model_type": "chat", "context_window": 128000},
        {"model_id": "doubao-seed-1-6-lite-251015", "model_name": "Doubao Seed 1.6 Lite (高性价比)", "model_type": "chat", "context_window": 128000},
        {"model_id": "doubao-seed-1-6-vision-250815", "model_name": "Doubao Seed 1.6 Vision (视觉)", "model_type": "chat", "context_window": 128000},
        {"model_id": "doubao-seed-1-6-flash-250615", "model_name": "Doubao Seed 1.6 Flash (极速)", "model_type": "chat", "context_window": 128000},
        {"model_id": "doubao-seed-1-6-thinking-250715", "model_name": "Doubao Seed 1.6 Thinking (深度)", "model_type": "chat", "context_window": 128000},
    ]


async def _fetch_openai_models(config: AIModelConfig) -> List[Dict]:
    """
    从 OpenAI 兼容 API 获取模型列表
    """
    from app.services.ai_model_service import decrypt_api_key
    import httpx
    
    api_key = decrypt_api_key(config.api_key_encrypted) if config.api_key_encrypted else ""
    
    base_url = config.base_url.rstrip('/')
    models_url = f"{base_url}/models"
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(models_url, headers=headers)
        
        if response.status_code != 200:
            logger.warning(f"获取 {config.provider} 模型列表失败: {response.status_code}")
            return []
        
        data = response.json()
        models = []
        
        # OpenAI 格式: {"data": [{"id": "gpt-4", ...}, ...]}
        model_list = data.get("data", data) if isinstance(data, dict) else data
        
        for model in model_list:
            if isinstance(model, dict):
                model_id = model.get("id", model.get("name", ""))
                if model_id:
                    # 过滤掉 embedding/whisper 等非对话模型
                    model_type = "chat"
                    if "embed" in model_id.lower():
                        model_type = "embedding"
                    elif "whisper" in model_id.lower() or "tts" in model_id.lower():
                        continue  # 跳过语音模型
                    
                    models.append({
                        "model_id": model_id,
                        "model_name": model.get("name", model_id),
                        "model_type": model_type,
                        "context_window": model.get("context_window"),
                        "raw_data": model
                    })
        
        return models
        
    except Exception as e:
        logger.error(f"获取 {config.provider} 模型列表异常: {e}")
        return []


# ==================== 动态路由（必须放在最后）====================

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
