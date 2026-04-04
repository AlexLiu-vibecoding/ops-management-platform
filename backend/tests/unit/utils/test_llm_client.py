"""
LLM 客户端测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio


class TestLLMClient:
    """LLM 客户端测试"""

    @pytest.fixture
    def client(self):
        """创建 LLM 客户端实例"""
        with patch('coze_coding_dev_sdk.LLMClient'), \
             patch('coze_coding_utils.runtime_ctx.context.new_context'):
            from app.utils.llm_client import LLMClient
            return LLMClient()

    def test_init_success(self):
        """测试初始化成功"""
        with patch('coze_coding_dev_sdk.LLMClient') as mock_client, \
             patch('coze_coding_utils.runtime_ctx.context.new_context') as mock_context:
            from app.utils.llm_client import LLMClient

            client = LLMClient()
            assert client._coze_client == mock_client
            assert client._new_context == mock_context

    def test_init_import_error(self):
        """测试导入失败"""
        with patch('builtins.__import__', side_effect=ImportError("No module")):
            with pytest.raises(ImportError):
                from app.utils.llm_client import LLMClient
                LLMClient()

    def test_convert_messages_with_system_and_user(self, client):
        """测试转换系统提示词和用户消息"""
        with patch('langchain_core.messages.SystemMessage') as mock_sys, \
             patch('langchain_core.messages.HumanMessage') as mock_human:

            mock_sys.return_value = "system_msg"
            mock_human.return_value = "human_msg"

            result = client._convert_messages(
                system_prompt="You are a helpful assistant",
                user_message="Hello"
            )

            assert len(result) == 2
            mock_sys.assert_called_once_with(content="You are a helpful assistant")
            mock_human.assert_called_once_with(content="Hello")

    def test_convert_messages_with_messages_list(self, client):
        """测试转换消息列表"""
        with patch('langchain_core.messages.SystemMessage') as mock_sys, \
             patch('langchain_core.messages.HumanMessage') as mock_human:

            mock_sys.return_value = "system_msg"
            mock_human.return_value = "human_msg"

            messages = [
                {"role": "system", "content": "System prompt"},
                {"role": "user", "content": "User message"}
            ]

            result = client._convert_messages(messages=messages)

            assert len(result) == 2
            mock_sys.assert_called_once_with(content="System prompt")
            mock_human.assert_called_once_with(content="User message")

    def test_convert_messages_empty(self, client):
        """测试转换空消息"""
        result = client._convert_messages()
        assert result == []

    def test_extract_content_string(self, client):
        """测试提取字符串内容"""
        mock_response = Mock()
        mock_response.content = "Hello, world!"
        result = client._extract_content(mock_response)
        assert result == "Hello, world!"

    def test_extract_content_list_of_strings(self, client):
        """测试提取字符串列表"""
        mock_response = Mock()
        mock_response.content = ["Hello", "world", "!"]
        result = client._extract_content(mock_response)
        assert result == "Hello world !"

    def test_extract_content_list_of_dicts(self, client):
        """测试提取字典列表"""
        mock_response = Mock()
        mock_response.content = [
            {"type": "text", "text": "Hello"},
            {"type": "other", "data": "ignore"},
            {"type": "text", "text": "world"}
        ]
        result = client._extract_content(mock_response)
        assert result == "Hello world"

    def test_extract_content_fallback(self, client):
        """测试内容提取的回退逻辑"""
        mock_response = Mock()
        mock_response.content = 123
        result = client._extract_content(mock_response)
        assert result == "123"

    def test_invoke_missing_model(self, client):
        """测试缺少 model 参数"""
        with pytest.raises(ValueError, match="model 参数为必传项"):
            client.invoke(user_message="Hello")

    def test_invoke_success(self, client):
        """测试同步调用成功"""
        mock_ctx = Mock()
        mock_coze_client = Mock()
        mock_response = Mock()
        mock_response.content = "AI response"

        client._new_context.return_value = mock_ctx
        client._coze_client.return_value = mock_coze_client
        mock_coze_client.invoke.return_value = mock_response

        result = client.invoke(
            model="test-model",
            user_message="Hello",
            temperature=0.5,
            max_tokens=1000
        )

        assert result == "AI response"
        client._new_context.assert_called_once_with(method="invoke")
        client._coze_client.assert_called_once_with(ctx=mock_ctx)

    def test_ainvoke_missing_model(self, client):
        """测试异步调用缺少 model 参数"""
        async def test():
            with pytest.raises(ValueError, match="model 参数为必传项"):
                await client.ainvoke(user_message="Hello")

        asyncio.run(test())

    def test_ainvoke_success(self, client):
        """测试异步调用成功"""
        mock_ctx = Mock()
        mock_coze_client = Mock()
        mock_response = Mock()
        mock_response.content = "Async response"

        client._new_context.return_value = mock_ctx
        client._coze_client.return_value = mock_coze_client
        mock_coze_client.invoke.return_value = mock_response

        async def test():
            result = await client.ainvoke(
                model="test-model",
                user_message="Hello async"
            )
            return result

        result = asyncio.run(test())
        assert result == "Async response"

    def test_astream_missing_model(self, client):
        """测试流式调用缺少 model 参数"""
        async def test():
            with pytest.raises(ValueError, match="model 参数为必传项"):
                async for chunk in client.astream(user_message="Hello"):
                    pass

        asyncio.run(test())

    def test_astream_success_string(self, client):
        """测试流式调用成功（字符串）"""
        mock_ctx = Mock()
        mock_coze_client = Mock()

        client._new_context.return_value = mock_ctx
        client._coze_client.return_value = mock_coze_client

        # 模拟流式响应
        chunks = [
            Mock(content="Hello"),
            Mock(content=" "),
            Mock(content="world"),
            Mock(content="!"),
        ]
        mock_coze_client.stream.return_value = chunks

        async def test():
            result = ""
            async for chunk in client.astream(model="test-model", user_message="Hello"):
                result += chunk
            return result

        result = asyncio.run(test())
        assert result == "Hello world!"

    def test_astream_success_list(self, client):
        """测试流式调用成功（列表）"""
        mock_ctx = Mock()
        mock_coze_client = Mock()

        client._new_context.return_value = mock_ctx
        client._coze_client.return_value = mock_coze_client

        # 模拟流式响应（列表格式）
        chunks = [
            Mock(content=[{"type": "text", "text": "Hello"}]),
            Mock(content=[{"type": "text", "text": "world"}]),
        ]
        mock_coze_client.stream.return_value = chunks

        async def test():
            result = ""
            async for chunk in client.astream(model="test-model", user_message="Hello"):
                result += chunk
            return result

        result = asyncio.run(test())
        assert result == "Helloworld"


class TestGetLLMClient:
    """获取默认客户端测试"""

    def test_get_client_singleton(self):
        """测试获取单例客户端"""
        with patch('app.utils.llm_client._default_client', None):
            with patch('app.utils.llm_client.LLMClient') as mock_llm:
                mock_instance = Mock()
                mock_llm.return_value = mock_instance

                from app.utils.llm_client import get_llm_client

                client1 = get_llm_client()
                client2 = get_llm_client()

                assert client1 == client2
                mock_llm.assert_called_once()

    def test_get_client_cached(self):
        """测试获取缓存的客户端"""
        mock_cached_client = Mock()

        with patch('app.utils.llm_client._default_client', mock_cached_client):
            from app.utils.llm_client import get_llm_client

            client = get_llm_client()
            assert client == mock_cached_client
