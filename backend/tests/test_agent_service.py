"""Tests for DeepSeek Agent service.

Behaviors:
- Model name mapping (deepseek-chat, deepseek-reasoner, unknown → default)
- SKILL.md is read as system prompt
- Streaming HTTP response is parsed into thinking events
- deepseek-reasoner reasoning_content is streamed as thinking, content as report_chunk
- Error events on HTTP failures
- Error event when DEEPSEEK_API_KEY is empty
"""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from backend.agent.agent_service import _get_model_name, _get_system_prompt, stream_analysis


class TestModelMapping:
    def test_deepseek_chat(self):
        assert _get_model_name("deepseek-chat") == "deepseek-chat"

    def test_deepseek_reasoner(self):
        assert _get_model_name("deepseek-reasoner") == "deepseek-reasoner"

    def test_unknown_model_defaults_to_chat(self):
        assert _get_model_name("unknown-model") == "deepseek-chat"


class TestSystemPrompt:
    def test_reads_skill_md(self):
        prompt = _get_system_prompt()
        assert len(prompt) > 100
        assert "技术分析" in prompt or "technical analysis" in prompt.lower()

    def test_contains_framework(self):
        prompt = _get_system_prompt()
        assert "五维交叉验证" in prompt


class TestStreamAnalysis:
    """Tests for the stream_analysis async generator.

    Uses real async context manager classes instead of complex mock chains
    to avoid mocking issues with httpx.AsyncClient's async context manager pattern.
    """

    def _make_mock_response(self, lines: list[str]):
        """Create a mock response object with aiter_lines async generator."""

        async def _aiter_lines():
            for line in lines:
                yield line

        response = MagicMock(spec=httpx.Response)
        response.aiter_lines = _aiter_lines
        response.raise_for_status = MagicMock()
        return response

    def _make_mock_client(self, lines: list[str]):
        """Build a full httpx.AsyncClient mock chain.

        The chain: AsyncClient() → async with → client.stream() → async with → response.aiter_lines()
        """
        mock_response = self._make_mock_response(lines)

        class MockStreamCM:
            """Mocks the context manager returned by client.stream()."""

            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, *args, **kwargs):
                pass

        class MockClientCM:
            """Mocks the AsyncClient instance used via async with."""

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args, **kwargs):
                pass

            def stream(self, method, url, *, headers, json):
                return MockStreamCM()

        return MockClientCM()

    @pytest.mark.asyncio
    async def test_returns_error_when_no_api_key(self):
        with patch("backend.agent.agent_service.DEEPSEEK_API_KEY", ""):
            events = [e async for e in stream_analysis("600519", "deepseek-chat")]

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "not configured" in events[0]["content"]

    @pytest.mark.asyncio
    async def test_streams_thinking_events_for_chat(self):
        lines = [
            'data: {"id":"1","choices":[{"index":0,"delta":{"content":"正在"},"finish_reason":null}]}',
            'data: {"id":"1","choices":[{"index":0,"delta":{"content":"分析"},"finish_reason":null}]}',
            'data: {"id":"1","choices":[{"index":0,"delta":{"content":"中"},"finish_reason":null}]}',
            "data: [DONE]",
        ]
        mock_client = self._make_mock_client(lines)

        with patch("backend.agent.agent_service.DEEPSEEK_API_KEY", "test-key"), \
             patch("httpx.AsyncClient", return_value=mock_client):
            events = [e async for e in stream_analysis("600519", "deepseek-chat")]

        thinking_events = [e for e in events if e["type"] == "thinking"]
        assert len(thinking_events) == 3
        assert thinking_events[0]["content"] == "正在"
        assert thinking_events[1]["content"] == "分析"
        assert thinking_events[2]["content"] == "中"

        complete = [e for e in events if e["type"] == "report_complete"]
        assert len(complete) == 1
        assert complete[0]["content"] == "正在分析中"

    @pytest.mark.asyncio
    async def test_streams_reasoning_and_report_for_reasoner(self):
        lines = [
            'data: {"id":"1","choices":[{"index":0,"delta":{"reasoning_content":"思考中..."},"finish_reason":null}]}',
            'data: {"id":"1","choices":[{"index":0,"delta":{"content":"最终报告"},"finish_reason":null}]}',
            "data: [DONE]",
        ]
        mock_client = self._make_mock_client(lines)

        with patch("backend.agent.agent_service.DEEPSEEK_API_KEY", "test-key"), \
             patch("httpx.AsyncClient", return_value=mock_client):
            events = [e async for e in stream_analysis("600519", "deepseek-reasoner")]

        thinking = [e for e in events if e["type"] == "thinking"]
        assert len(thinking) == 1
        assert "思考中" in thinking[0]["content"]

        chunks = [e for e in events if e["type"] == "report_chunk"]
        assert len(chunks) == 1
        assert "最终报告" in chunks[0]["content"]

        complete = [e for e in events if e["type"] == "report_complete"]
        assert len(complete) == 1
        assert complete[0]["content"] == "最终报告"

    @pytest.mark.asyncio
    async def test_handles_http_401_error(self):
        mock_response = MagicMock(spec=httpx.Response, status_code=401)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=mock_response,
        )

        class MockStreamCM:
            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, *args, **kwargs):
                pass

        class MockClientCM:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args, **kwargs):
                pass

            def stream(self, method, url, *, headers, json):
                return MockStreamCM()

        mock_client = MockClientCM()

        with patch("backend.agent.agent_service.DEEPSEEK_API_KEY", "test-key"), \
             patch("httpx.AsyncClient", return_value=mock_client):
            events = [e async for e in stream_analysis("600519", "deepseek-chat")]

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "401" in events[0]["content"]

    @pytest.mark.asyncio
    async def test_handles_connection_error(self):
        class MockClientCM:
            async def __aenter__(self):
                raise httpx.RequestError("Connection refused")

            async def __aexit__(self, *args, **kwargs):
                pass

        mock_client = MockClientCM()

        with patch("backend.agent.agent_service.DEEPSEEK_API_KEY", "test-key"), \
             patch("httpx.AsyncClient", return_value=mock_client):
            events = [e async for e in stream_analysis("600519", "deepseek-chat")]

        assert len(events) == 1
        assert events[0]["type"] == "error"
        assert "Connection refused" in events[0]["content"]

    @pytest.mark.asyncio
    async def test_calls_api_with_correct_url_and_model(self):
        call_kwargs = {}

        async def _empty_lines():
            return
            yield

        class MockStreamCM:
            async def __aenter__(self):
                return MagicMock(
                    aiter_lines=_empty_lines,
                    raise_for_status=MagicMock(),
                )

            async def __aexit__(self, *args, **kwargs):
                pass

        class MockClientCM:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args, **kwargs):
                pass

            def stream(self, method, url, *, headers, json):
                call_kwargs.update({"method": method, "url": url, "json": json})
                return MockStreamCM()

        mock_client = MockClientCM()

        with patch("backend.agent.agent_service.DEEPSEEK_API_KEY", "test-key"), \
             patch("httpx.AsyncClient", return_value=mock_client):
            async for _ in stream_analysis("600519", "deepseek-chat"):
                pass

        assert "chat/completions" in call_kwargs.get("url", "")
        assert call_kwargs["json"]["model"] == "deepseek-chat"
        assert call_kwargs["json"]["stream"] is True
        assert len(call_kwargs["json"]["messages"]) == 2
        assert call_kwargs["json"]["messages"][0]["role"] == "system"
        assert call_kwargs["json"]["messages"][1]["role"] == "user"
