"""
LLM 客户端工具

直接使用 OpenAI SDK 调用豆包大模型，绕过 langchain 版本兼容性问题
"""
import os
import json
import logging
from typing import List, Optional, Dict, Any, AsyncGenerator
from openai import OpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)

# 默认配置 - 使用正确的环境变量
DEFAULT_BASE_URL = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL", "https://integration.coze.cn/api/v3")
DEFAULT_API_KEY = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY", "")


def parse_sse_response(response_text: str) -> str:
    """解析 SSE 格式的响应，提取文本内容"""
    content_parts = []
    for line in response_text.strip().split('\n'):
        if line.startswith('data: '):
            try:
                data = json.loads(line[6:])
                if 'choices' in data and data['choices']:
                    delta = data['choices'][0].get('delta', {})
                    if 'content' in delta:
                        content_parts.append(delta['content'])
            except json.JSONDecodeError:
                continue
    return ''.join(content_parts)


class LLMClient:
    """LLM 客户端，使用 OpenAI SDK 直接调用豆包模型"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.base_url = base_url or DEFAULT_BASE_URL
        self.api_key = api_key or DEFAULT_API_KEY
        
        if not self.api_key:
            logger.warning("API Key 未配置，请设置 COZE_WORKLOAD_IDENTITY_API_KEY 环境变量")
    
    def _get_client(self) -> OpenAI:
        """获取同步客户端"""
        return OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def _get_async_client(self) -> AsyncOpenAI:
        """获取异步客户端"""
        return AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def _build_messages(
        self,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """构建消息列表"""
        if messages:
            return messages
        
        result = []
        if system_prompt:
            result.append({"role": "system", "content": system_prompt})
        if user_message:
            result.append({"role": "user", "content": user_message})
        
        return result
    
    def invoke(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        model: str = "doubao-seed-2-0-lite-260215",
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
        client = self._get_client()
        formatted_messages = self._build_messages(
            system_prompt=system_prompt,
            user_message=user_message,
            messages=messages
        )
        
        try:
            # 使用流式请求来兼容 SSE 响应格式
            stream = client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            
            # 收集流式响应
            content_parts = []
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content_parts.append(chunk.choices[0].delta.content)
            
            return ''.join(content_parts)
            
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            raise
    
    async def ainvoke(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        model: str = "doubao-seed-2-0-lite-260215",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> str:
        """
        异步调用 LLM
        
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
        client = self._get_async_client()
        formatted_messages = self._build_messages(
            system_prompt=system_prompt,
            user_message=user_message,
            messages=messages
        )
        
        try:
            # 使用流式请求来兼容 SSE 响应格式
            stream = await client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            
            # 收集流式响应
            content_parts = []
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content_parts.append(chunk.choices[0].delta.content)
            
            return ''.join(content_parts)
            
        except Exception as e:
            logger.error(f"LLM 异步调用失败: {e}")
            raise
    
    async def astream(
        self,
        messages: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        user_message: Optional[str] = None,
        model: str = "doubao-seed-2-0-lite-260215",
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
        client = self._get_async_client()
        formatted_messages = self._build_messages(
            system_prompt=system_prompt,
            user_message=user_message,
            messages=messages
        )
        
        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
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
