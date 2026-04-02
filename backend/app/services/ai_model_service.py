"""
AI 模型服务

支持从数据库加载模型配置，实现多模型调用、主备切换、交叉验证。
"""
import os
import time
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from openai import OpenAI

from app.models.ai_model import AIModelConfig, AICallLog
from app.utils.auth import aes_cipher

logger = logging.getLogger(__name__)

# 默认配置（作为兜底）
DEFAULT_BASE_URL = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL", "https://integration.coze.cn/api/v3")
DEFAULT_API_KEY = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY", "")
DEFAULT_MODEL = "doubao-pro-32k"


def decrypt_api_key(encrypted: str) -> str:
    """解密 API 密钥"""
    if not encrypted:
        return ""
    try:
        return aes_cipher.decrypt(encrypted)
    except Exception:
        return ""


def get_available_model(db: Session, use_case: str) -> Optional[AIModelConfig]:
    """
    获取可用的模型配置
    
    优先级策略:
    1. 优先使用默认模型
    2. 按优先级降序排列
    3. 只选择启用且匹配使用场景的模型
    """
    # 先尝试获取默认模型
    default_model = db.query(AIModelConfig).filter(
        AIModelConfig.is_enabled == True,
        AIModelConfig.is_default == True,
        AIModelConfig.use_cases.contains([use_case])
    ).first()
    
    if default_model:
        return default_model
    
    # 没有默认模型，按优先级获取
    return db.query(AIModelConfig).filter(
        AIModelConfig.is_enabled == True,
        AIModelConfig.use_cases.contains([use_case])
    ).order_by(desc(AIModelConfig.priority)).first()


def get_all_available_models(db: Session, use_case: str) -> List[AIModelConfig]:
    """获取所有可用的模型配置（用于主备切换）"""
    return db.query(AIModelConfig).filter(
        AIModelConfig.is_enabled == True,
        AIModelConfig.use_cases.contains([use_case])
    ).order_by(desc(AIModelConfig.priority)).all()


def call_model(
    config: AIModelConfig,
    messages: List[Dict[str, str]],
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
    """
    api_key = decrypt_api_key(config.api_key_encrypted) if config.api_key_encrypted else ""
    
    client = OpenAI(
        api_key=api_key or "no-key",
        base_url=config.base_url,
        timeout=timeout or config.timeout
    )
    
    try:
        stream = client.chat.completions.create(
            model=config.model_name,
            messages=messages,
            temperature=temperature if temperature is not None else config.temperature,
            max_tokens=max_tokens or config.max_tokens,
            stream=True
        )
        
        content_parts = []
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content_parts.append(chunk.choices[0].delta.content)
        
        return ''.join(content_parts)
        
    except Exception as e:
        logger.error(f"模型 {config.name} 调用失败: {e}")
        raise


def call_with_fallback(
    db: Session,
    use_case: str,
    messages: List[Dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> tuple[str, Optional[AIModelConfig]]:
    """
    带降级的模型调用
    
    主模型失败时自动切换到备用模型
    
    Args:
        db: 数据库会话
        use_case: 使用场景
        messages: 消息列表
        temperature: 温度参数
        max_tokens: 最大 token 数
    
    Returns:
        (响应文本, 使用的模型配置)
    """
    models = get_all_available_models(db, use_case)
    
    if not models:
        # 没有配置的模型，使用默认兜底
        logger.warning(f"没有配置 {use_case} 的模型，使用默认兜底")
        try:
            client = OpenAI(
                api_key=DEFAULT_API_KEY or "no-key",
                base_url=DEFAULT_BASE_URL
            )
            stream = client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                temperature=temperature or 0.7,
                max_tokens=max_tokens or 4096,
                stream=True
            )
            content_parts = []
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content_parts.append(chunk.choices[0].delta.content)
            return ''.join(content_parts), None
        except Exception as e:
            logger.error(f"默认模型调用也失败: {e}")
            raise RuntimeError(f"没有可用的 AI 模型: {e}")
    
    errors = []
    for model in models:
        start_time = time.time()
        try:
            result = call_model(model, messages, temperature, max_tokens)
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 记录成功日志
            log = AICallLog(
                model_config_id=model.id,
                use_case=use_case,
                latency_ms=latency_ms,
                success=True
            )
            db.add(log)
            db.commit()
            
            logger.info(f"模型 {model.name} 调用成功，耗时 {latency_ms}ms")
            return result, model
            
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            errors.append((model.name, str(e)))
            
            # 记录失败日志
            log = AICallLog(
                model_config_id=model.id,
                use_case=use_case,
                latency_ms=latency_ms,
                success=False,
                error_message=str(e)
            )
            db.add(log)
            db.commit()
            
            logger.warning(f"模型 {model.name} 调用失败: {e}")
            continue
    
    raise RuntimeError(f"所有模型都不可用: {errors}")


async def call_with_fallback_async(
    db: Session,
    use_case: str,
    messages: List[Dict[str, str]],
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> tuple[str, Optional[AIModelConfig]]:
    """
    异步带降级的模型调用
    
    使用 asyncio 包装同步调用
    """
    import asyncio
    return await asyncio.to_thread(
        call_with_fallback,
        db, use_case, messages, temperature, max_tokens
    )


def call_multiple_models(
    db: Session,
    use_case: str,
    messages: List[Dict[str, str]],
    model_count: int = 2,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    多模型交叉验证调用
    
    同时调用多个模型，返回所有结果供对比
    
    Args:
        db: 数据库会话
        use_case: 使用场景
        messages: 消息列表
        model_count: 调用模型数量
        temperature: 温度参数
        max_tokens: 最大 token 数
    
    Returns:
        [{"model_name": str, "response": str, "latency_ms": int, "success": bool, "error": str}]
    """
    import concurrent.futures
    
    models = get_all_available_models(db, use_case)[:model_count]
    
    if not models:
        return []
    
    results = []
    
    def call_single(model: AIModelConfig) -> Dict[str, Any]:
        start_time = time.time()
        try:
            response = call_model(model, messages, temperature, max_tokens)
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 记录日志
            log = AICallLog(
                model_config_id=model.id,
                use_case=use_case,
                latency_ms=latency_ms,
                success=True
            )
            db.add(log)
            db.commit()
            
            return {
                "model_id": model.id,
                "model_name": model.name,
                "response": response,
                "latency_ms": latency_ms,
                "success": True,
                "error": None
            }
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            
            # 记录失败日志
            log = AICallLog(
                model_config_id=model.id,
                use_case=use_case,
                latency_ms=latency_ms,
                success=False,
                error_message=str(e)
            )
            db.add(log)
            db.commit()
            
            return {
                "model_id": model.id,
                "model_name": model.name,
                "response": None,
                "latency_ms": latency_ms,
                "success": False,
                "error": str(e)
            }
    
    # 并行调用
    with concurrent.futures.ThreadPoolExecutor(max_workers=model_count) as executor:
        futures = [executor.submit(call_single, model) for model in models]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    return results
