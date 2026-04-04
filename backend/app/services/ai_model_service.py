"""
AI 模型服务

通过场景配置获取模型，实现多模型调用、主备切换。
模型作为底座，场景关联到具体模型。

注意：不再有硬编码的默认模型，必须通过场景配置关联。
"""
import time
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.ai_model import AIModelConfig, AISceneConfig, AICallLog
from app.utils.auth import aes_cipher

logger = logging.getLogger(__name__)


def decrypt_api_key(encrypted: str) -> str:
    """解密 API 密钥"""
    if not encrypted:
        return ""
    try:
        return aes_cipher.decrypt(encrypted)
    except Exception:
        return ""


def _call_doubao_model(
    config: AIModelConfig,
    messages: list[dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> str:
    """
    调用豆包模型（使用 coze_coding_dev_sdk）
    """
    from app.utils.llm_client import get_llm_client
    
    client = get_llm_client()
    
    # 豆包模型名
    model_name = config.model_name
    
    # 参数
    actual_temp = temperature if temperature is not None else config.temperature
    actual_max_tokens = max_tokens or config.max_tokens
    
    # 同步调用
    response = client.invoke(
        messages=messages,
        model=model_name,
        temperature=actual_temp,
        max_tokens=actual_max_tokens
    )
    
    return response


def get_scene_model(db: Session, scene: str) -> Optional[AIModelConfig]:
    """
    获取场景关联的模型配置
    
    Args:
        db: 数据库会话
        scene: 场景标识 (如 'sql_optimize', 'alert_analysis')
        
    Returns:
        AIModelConfig 或 None
    """
    scene_config = db.query(AISceneConfig).filter(
        AISceneConfig.scene == scene,
        AISceneConfig.is_enabled
    ).first()
    
    if not scene_config:
        return None
    
    return db.query(AIModelConfig).filter(
        AIModelConfig.id == scene_config.model_config_id,
        AIModelConfig.is_enabled
    ).first()


def get_all_scene_models(db: Session, scene: str) -> list[AIModelConfig]:
    """
    获取场景可用的所有模型（用于备用切换）
    
    目前每个场景只关联一个模型，后续可扩展为多模型主备
    
    Args:
        db: 数据库会话
        scene: 场景标识
        
    Returns:
        模型配置列表
    """
    model = get_scene_model(db, scene)
    return [model] if model else []


def call_model(
    config: AIModelConfig,
    messages: list[dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout: Optional[int] = None
) -> str:
    """
    调用单个模型
    
    Args:
        config: 模型配置
        messages: 消息列表
        temperature: 温度参数（覆盖配置）
        max_tokens: 最大 token 数（覆盖配置）
        timeout: 超时时间（覆盖配置）
    
    Returns:
        模型响应文本
        
    Raises:
        RuntimeError: 模型调用失败
    """
    # 豆包模型使用特殊的 LLM Client
    if config.provider == "doubao":
        return _call_doubao_model(config, messages, temperature, max_tokens)
    
    # 其他模型使用标准 OpenAI 格式
    import httpx
    
    api_key = decrypt_api_key(config.api_key_encrypted) if config.api_key_encrypted else ""
    
    # 构建请求
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    payload = {
        "model": config.model_name,
        "messages": messages,
        "temperature": temperature if temperature is not None else config.temperature,
        "max_tokens": max_tokens or config.max_tokens
    }
    
    # 构建 API URL
    base_url = config.base_url.rstrip('/')
    if not base_url.endswith('/chat/completions'):
        if base_url.endswith('/v1') or base_url.endswith('/v3'):
            api_url = f"{base_url}/chat/completions"
        else:
            api_url = f"{base_url}/v1/chat/completions"
    else:
        api_url = base_url
    
    actual_timeout = timeout or config.timeout
    
    try:
        with httpx.Client(timeout=actual_timeout) as client:
            response = client.post(api_url, headers=headers, json=payload)
        
        if response.status_code != 200:
            error_detail = response.text
            try:
                error_json = response.json()
                if "error" in error_json:
                    error_detail = error_json["error"].get("message", str(error_json["error"]))
            except Exception:
                pass
            raise RuntimeError(f"API 错误 ({response.status_code}): {error_detail}")
        
        result = response.json()
        
        # 处理 OpenAI 格式响应
        if "choices" in result and result["choices"]:
            return result["choices"][0].get("message", {}).get("content", "")
        
        return str(result)
        
    except httpx.TimeoutException:
        raise RuntimeError(f"请求超时（{actual_timeout}秒）")


def call_with_scene(
    db: Session,
    scene: str,
    messages: list[dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> tuple[str, Optional[AIModelConfig]]:
    """
    通过场景配置调用模型
    
    Args:
        db: 数据库会话
        scene: 场景标识
        messages: 消息列表
        temperature: 温度参数
        max_tokens: 最大 token 数
    
    Returns:
        (响应文本, 使用的模型配置)
        
    Raises:
        RuntimeError: 未配置场景或模型调用失败
    """
    model = get_scene_model(db, scene)
    
    if not model:
        scene_config = db.query(AISceneConfig).filter(AISceneConfig.scene == scene).first()
        if not scene_config:
            raise RuntimeError(
                f"场景「{scene}」未配置，请在「系统管理 > AI模型配置」中配置场景关联的模型"
            )
        else:
            linked_model = db.query(AIModelConfig).filter(
                AIModelConfig.id == scene_config.model_config_id
            ).first()
            if linked_model and not linked_model.is_enabled:
                raise RuntimeError(
                    f"场景「{scene}」关联的模型「{linked_model.name}」已被禁用，请启用或更换模型"
                )
            raise RuntimeError(
                f"场景「{scene}」配置无效，请检查模型配置"
            )
    
    start_time = time.time()
    
    try:
        result = call_model(model, messages, temperature, max_tokens)
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 记录成功日志
        log = AICallLog(
            model_config_id=model.id,
            scene=scene,
            latency_ms=latency_ms,
            success=True
        )
        db.add(log)
        db.commit()
        
        logger.info(f"模型 {model.name} 调用成功，耗时 {latency_ms}ms")
        return result, model
        
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        
        # 记录失败日志
        log = AICallLog(
            model_config_id=model.id,
            scene=scene,
            latency_ms=latency_ms,
            success=False,
            error_message=str(e)
        )
        db.add(log)
        db.commit()
        
        logger.error(f"模型 {model.name} 调用失败: {e}")
        raise RuntimeError(f"模型「{model.name}」调用失败: {e}")


async def call_with_scene_async(
    db: Session,
    scene: str,
    messages: list[dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> tuple[str, Optional[AIModelConfig]]:
    """
    异步调用模型（通过场景配置）
    """
    import asyncio
    return await asyncio.to_thread(
        call_with_scene,
        db, scene, messages, temperature, max_tokens
    )


# ========== 兼容旧 API ==========

def get_available_model(db: Session, use_case: str) -> Optional[AIModelConfig]:
    """兼容旧 API：获取可用的模型配置"""
    return get_scene_model(db, use_case)


def get_all_available_models(db: Session, use_case: str) -> list[AIModelConfig]:
    """兼容旧 API：获取所有可用的模型配置"""
    return get_all_scene_models(db, use_case)


def call_with_fallback(
    db: Session,
    use_case: str,
    messages: list[dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> tuple[str, Optional[AIModelConfig]]:
    """兼容旧 API：带降级的模型调用"""
    return call_with_scene(db, use_case, messages, temperature, max_tokens)


async def call_with_fallback_async(
    db: Session,
    use_case: str,
    messages: list[dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> tuple[str, Optional[AIModelConfig]]:
    """兼容旧 API：异步带降级的模型调用"""
    return await call_with_scene_async(db, use_case, messages, temperature, max_tokens)
