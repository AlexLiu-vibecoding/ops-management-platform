"""
LLM 客户端工具

使用 coze_coding_dev_sdk 调用豆包大模型
"""
import os
import time
import logging
from typing import List, Optional, Dict, Any, AsyncGenerator

logger = logging.getLogger(__name__)

# 默认模型配置
DEFAULT_MODEL = "doubao-seed-1-8-251228"  # Multimodal Agent 优化模型
DEFAULT_MODEL_LITE = "doubao-seed-1-6-lite-251015"  # Lite 模型，更轻量


class LLMClient:
    """LLM 客户端，使用 coze_coding_dev_sdk 调用豆包模型"""
    
    def __init__(self):
        """初始化客户端"""
        try:
            from coze_coding_dev_sdk import LLMClient as CozeLLMClient
            from coze_coding_utils.runtime_ctx.context import new_context
            
            self._coze_client = CozeLLMClient
            self._new_context = new_context
        except ImportError as e:
            logger.error(f"导入 coze_coding_dev_sdk 失败: {e}")
            raise
        
    def _convert_messages(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None
    ) -> List:
        """转换消息格式为 LangChain 格式"""
        from langchain_core.messages import SystemMessage, HumanMessage
        
        result = []
        
        if messages:
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    result.append(SystemMessage(content=content))
                elif role == "user":
                    result.append(HumanMessage(content=content))
                # 忽略其他角色，因为 AIMessage 通常用于多轮对话
        else:
            if system_prompt:
                result.append(SystemMessage(content=system_prompt))
            if user_message:
                result.append(HumanMessage(content=user_message))
        
        return result
    
    def _extract_content(self, response) -> str:
        """从响应中提取文本内容"""
        content = response.content
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            # 处理 multimodal 响应
            if content and isinstance(content[0], str):
                return " ".join(content)
            else:
                return " ".join(
                    item.get("text", "") 
                    for item in content 
                    if isinstance(item, dict) and item.get("type") == "text"
                )
        return str(content)
    
    def invoke(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> str:
        """
        同步调用 LLM
        
        Args:
            messages: 消息列表，格式 [{"role": "user", "content": "..."}]
            system_prompt: 系统提示词
            user_message: 用户消息
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大输出 token 数
            
        Returns:
            模型响应文本
        """
        start_time = time.time()
        
        try:
            ctx = self._new_context(method="invoke")
            client = self._coze_client(ctx=ctx)
            
            formatted_messages = self._convert_messages(
                system_prompt=system_prompt,
                user_message=user_message,
                messages=messages
            )
            
            logger.info(f"[LLM] 开始同步调用模型: {model}, 消息数: {len(formatted_messages)}")
            
            response = client.invoke(
                messages=formatted_messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            result = self._extract_content(response)
            logger.info(f"[LLM] 同步调用完成，耗时: {time.time() - start_time:.2f}秒, 输出长度: {len(result)}字符")
            
            return result
            
        except Exception as e:
            logger.error(f"[LLM] 同步调用失败: {e}, 耗时: {time.time() - start_time:.2f}秒")
            raise
    
    async def ainvoke(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> str:
        """
        异步调用 LLM（使用线程池包装同步调用）
        
        Args:
            messages: 消息列表
            system_prompt: 系统提示词
            user_message: 用户消息
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大输出 token 数
            
        Returns:
            模型响应文本
        """
        import asyncio
        
        start_time = time.time()
        
        try:
            ctx = self._new_context(method="invoke")
            client = self._coze_client(ctx=ctx)
            
            formatted_messages = self._convert_messages(
                system_prompt=system_prompt,
                user_message=user_message,
                messages=messages
            )
            
            logger.info(f"[LLM] 开始异步调用模型: {model}, 消息数: {len(formatted_messages)}")
            
            # coze SDK 的 invoke 是同步的，使用线程池包装
            response = await asyncio.to_thread(
                client.invoke,
                formatted_messages,
                model,
                temperature,
                max_tokens
            )
            
            # 或者使用流式调用获得更好的响应体验
            # 这里先用同步调用确保稳定性
            
            result = self._extract_content(response)
            logger.info(f"[LLM] 异步调用完成，耗时: {time.time() - start_time:.2f}秒, 输出长度: {len(result)}字符")
            
            return result
            
        except Exception as e:
            logger.error(f"[LLM] 异步调用失败: {e}, 耗时: {time.time() - start_time:.2f}秒")
            raise
    
    async def astream(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        异步流式调用 LLM
        
        Args:
            messages: 消息列表
            system_prompt: 系统提示词
            user_message: 用户消息
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大输出 token 数
            
        Yields:
            模型响应文本片段
        """
        ctx = self._new_context(method="invoke")
        client = self._coze_client(ctx=ctx)
        
        formatted_messages = self._convert_messages(
            system_prompt=system_prompt,
            user_message=user_message,
            messages=messages
        )
        
        try:
            for chunk in client.stream(
                messages=formatted_messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                if chunk.content:
                    content = chunk.content
                    if isinstance(content, str):
                        yield content
                    elif isinstance(content, list) and content:
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                yield item.get("text", "")
                    
        except Exception as e:
            logger.error(f"LLM 流式调用失败: {e}")
            raise


# 单例客户端
_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取默认 LLM 客户端"""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client
