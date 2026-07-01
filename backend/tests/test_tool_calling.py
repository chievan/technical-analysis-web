"""Tests for tool calling (Slice 3).

Behaviors:
- Tool definitions have correct OpenAI-compatible structure
- Engine runner executes ta_engine.py and returns structured JSON
- Engine runner handles missing engine script gracefully
- read_reference returns appropriate message for missing files
- Agent service handles tool_call deltas in streaming response
- Agent service loops correctly for multi-turn conversations
- Full SSE integration: events include tool_call and tool_result types
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.agent.agent_service import (
    _call_and_stream,
    _summarize_result,
    stream_analysis,
)
from backend.agent.tool_definitions import TOOLS, get_tool_names
from backend.tools.engine_runner import run_ta_engine, read_reference


# ────────────────────────────────
# Tool definitions tests
# ────────────────────────────────


class TestToolDefinitions:
    def test_tools_is_list(self):
        assert isinstance(TOOLS, list)
        assert len(TOOLS) >= 2

    def test_each_tool_has_correct_structure(self):
        for tool in TOOLS:
            assert tool["type"] == "function"
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]
            assert tool["function"]["parameters"]["type"] == "object"
            assert "properties" in tool["function"]["parameters"]
            assert "required" in tool["function"]["parameters"]

    def test_run_ta_engine_tool_has_code_parameter(self):
        tool = next(t for t in TOOLS if t["function"]["name"] == "run_ta_engine")
        props = tool["function"]["parameters"]["properties"]
        assert "code" in props
        assert props["code"]["type"] == "string"
        assert "code" in tool["function"]["parameters"]["required"]

    def test_read_reference_tool_has_file_parameter(self):
        tool = next(t for t in TOOLS if t["function"]["name"] == "read_reference")
        props = tool["function"]["parameters"]["properties"]
        assert "file" in props
        assert "file" in tool["function"]["parameters"]["required"]

    def test_get_tool_names(self):
        names = get_tool_names()
        assert "run_ta_engine" in names
        assert "read_reference" in names


# ────────────────────────────────
# Engine runner tests
# ────────────────────────────────


class TestRunTaEngine:
    def test_engine_returns_structured_data(self):
        result = run_ta_engine("600519")
        assert "error" not in result, f"Engine error: {result.get('error')}"
        assert result["symbol"] == "600519"
        assert result["symbol_name"] == "贵州茅台"
        assert "latest" in result
        assert "moving_averages" in result
        assert "macd" in result
        assert "rsi" in result
        assert "bollinger" in result
        assert "support_levels" in result
        assert "resistance_levels" in result

    def test_engine_latest_price_is_float(self):
        result = run_ta_engine("600519")
        assert isinstance(result["latest"]["price"], (int, float))

    def test_engine_different_symbol(self):
        result = run_ta_engine("000300")
        assert result["symbol"] == "000300"
        assert result["symbol_name"] == "沪深300"
        assert result["data_points"] == 120

    def test_engine_executes_from_subprocess(self):
        """Verify the engine can be invoked as a subprocess (as in production)."""
        import subprocess

        proc = subprocess.run(
            ["python3", "backend/skill/scripts/ta_engine.py", "600519"],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0
        data = json.loads(proc.stdout)
        assert data["symbol"] == "600519"
        assert "latest" in data


class TestReadReference:
    def test_missing_file_returns_message(self):
        result = read_reference("non_existent.md")
        assert "不存在" in result

    def test_empty_dir_returns_hint(self):
        result = read_reference("anything.md")
        assert "暂无" in result or "不存在" in result


class TestSummarizeResult:
    def test_ta_engine_summary(self):
        result = run_ta_engine("600519")
        summary = _summarize_result("run_ta_engine", result)
        assert "贵州茅台" in summary
        assert "120" in summary

    def test_read_reference_summary(self):
        summary = _summarize_result("read_reference", "参考文档内容")
        assert "参考文档" in summary

    def test_error_result_summary(self):
        summary = _summarize_result("run_ta_engine", {"error": "脚本不存在"})
        assert "❌" in summary
        assert "脚本不存在" in summary


# ────────────────────────────────
# Agent service tool calling tests
# ────────────────────────────────


class TestAgentToolCalling:
    """Test the tool calling flow in agent service.

    Uses mock HTTP responses that simulate DeepSeek API streaming with tool calls.
    """

    def _make_streaming_client(self, lines_list: list[list[str]]):
        """Create a mock client that provides different responses across multiple stream() calls.

        lines_list: list of line sets, one per stream() call (per turn).
        """
        call_count = [0]

        class MockStreamCM:
            def __init__(self_, lines):
                self_._lines = lines

            async def __aenter__(self_):
                return self_

            async def __aexit__(self_, *args, **kwargs):
                pass

            async def aiter_lines(self_):
                for line in self_._lines:
                    yield line

        class MockClientCM:
            async def __aenter__(self_):
                return self_

            async def __aexit__(self_, *args, **kwargs):
                pass

            def stream(self_, method, url, *, headers, json):
                idx = call_count[0]
                call_count[0] += 1
                lines = lines_list[idx] if idx < len(lines_list) else []
                mock_response = MagicMock(spec=httpx.Response)
                mock_response.raise_for_status = MagicMock()
                mock_response.aiter_lines = MockStreamCM(lines).aiter_lines
                cm = AsyncMock()
                cm.__aenter__ = AsyncMock(return_value=mock_response)
                cm.__aexit__ = AsyncMock(return_value=None)
                return cm

        return MockClientCM()

    @pytest.mark.asyncio
    async def test_without_api_key_returns_error(self):
        with patch("backend.agent.agent_service.DEEPSEEK_API_KEY", ""):
            events = [e async for e in stream_analysis("600519", "deepseek-chat")]
        assert len(events) == 1
        assert events[0]["type"] == "error"

    @pytest.mark.asyncio
    async def test_direct_report_without_tool_calls(self):
        """When the model produces a report without tool calls, events should be
        thinking/report_complete."""
        lines = [
            'data: {"id":"1","choices":[{"index":0,"delta":{"content":"## 分析报告\\n\\n"},"finish_reason":null}]}',
            'data: {"id":"1","choices":[{"index":0,"delta":{"content":"综合评分：看多"},"finish_reason":null}]}',
            'data: {"id":"1","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]

        mock_client = self._make_streaming_client([lines])

        with patch("backend.agent.agent_service.DEEPSEEK_API_KEY", "test-key"), \
             patch("httpx.AsyncClient", return_value=mock_client):
            events = [e async for e in stream_analysis("600519", "deepseek-chat")]

        types = [e["type"] for e in events]
        assert "thinking" in types
        assert "report_complete" in types
        assert "tool_call" not in types

    @pytest.mark.asyncio
    async def test_tool_call_triggers_execution_and_continues(self):
        """When the model calls a tool, the agent should execute it and continue the loop."""
        # Turn 1: model thinks and calls run_ta_engine
        turn1_lines = [
            'data: {"id":"1","choices":[{"index":0,"delta":{"content":"让我先获取数据"},"finish_reason":null}]}',
            'data: {"id":"1","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call_abc","type":"function","function":{"name":"run_ta_engine","arguments":""}}]},"finish_reason":null}]}',
            'data: {"id":"1","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{\\"code\\":\\""}}]},"finish_reason":null}]}',
            'data: {"id":"1","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"600519\\"}"}}]},"finish_reason":null}]}',
            'data: {"id":"1","choices":[{"index":0,"delta":{},"finish_reason":"tool_calls"}]}',
            "data: [DONE]",
        ]
        # Turn 2: after tool result, model produces report
        turn2_lines = [
            'data: {"id":"2","choices":[{"index":0,"delta":{"content":"基于数据，均线多头排列"},"finish_reason":null}]}',
            'data: {"id":"2","choices":[{"index":0,"delta":{"content":"综合评分：看多"},"finish_reason":null}]}',
            'data: {"id":"2","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]

        mock_client = self._make_streaming_client([turn1_lines, turn2_lines])

        with patch("backend.agent.agent_service.DEEPSEEK_API_KEY", "test-key"), \
             patch("httpx.AsyncClient", return_value=mock_client):
            events = [e async for e in stream_analysis("600519", "deepseek-chat")]

        types = [e["type"] for e in events]

        # Should have thinking, tool_call, tool_result, and final report
        assert "thinking" in types
        assert "tool_call" in types
        assert "tool_result" in types
        assert "report_complete" in types

        # Verify tool_call event content
        tool_call_events = [e for e in events if e["type"] == "tool_call"]
        assert len(tool_call_events) == 1
        tc_data = json.loads(tool_call_events[0]["content"])
        assert tc_data["tool"] == "run_ta_engine"
        assert tc_data["args"]["code"] == "600519"

        # Verify tool_result event content
        tool_result_events = [e for e in events if e["type"] == "tool_result"]
        assert len(tool_result_events) >= 1
        tr_data = json.loads(tool_result_events[0]["content"])
        assert "tool" in tr_data
        assert "summary" in tr_data

        # Verify chart_data event emitted (from engine result)
        chart_data_events = [e for e in events if e["type"] == "chart_data"]
        assert len(chart_data_events) == 1
        cd = json.loads(chart_data_events[0]["content"])
        assert cd["symbol"] == "600519"
        assert "latest" in cd
        assert "moving_averages" in cd

        # Verify final report
        report_events = [e for e in events if e["type"] == "report_complete"]
        assert len(report_events) == 1
        assert "看多" in report_events[0]["content"]

    @pytest.mark.asyncio
    async def test_parallel_tool_calls(self):
        """Model can call multiple tools at once (parallel tool calling)."""
        lines = [
            'data: {"id":"1","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call_001","type":"function","function":{"name":"run_ta_engine","arguments":""}}]},"finish_reason":null}]}',
            'data: {"id":"1","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"{\\"code\\":\\"600519\\"}"}}]},"finish_reason":null}]}',
            'data: {"id":"1","choices":[{"index":0,"delta":{"tool_calls":[{"index":1,"id":"call_002","type":"function","function":{"name":"read_reference","arguments":""}}]},"finish_reason":null}]}',
            'data: {"id":"1","choices":[{"index":0,"delta":{"tool_calls":[{"index":1,"function":{"arguments":"{\\"file\\":\\"five_dimension_framework.md\\"}"}}]},"finish_reason":null}]}',
            'data: {"id":"1","choices":[{"index":0,"delta":{},"finish_reason":"tool_calls"}]}',
            "data: [DONE]",
        ]
        turn2_lines = [
            'data: {"id":"2","choices":[{"index":0,"delta":{"content":"完成分析"},"finish_reason":null}]}',
            'data: {"id":"2","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}',
            "data: [DONE]",
        ]

        mock_client = self._make_streaming_client([lines, turn2_lines])

        with patch("backend.agent.agent_service.DEEPSEEK_API_KEY", "test-key"), \
             patch("httpx.AsyncClient", return_value=mock_client):
            events = [e async for e in stream_analysis("600519", "deepseek-chat")]

        tool_call_events = [e for e in events if e["type"] == "tool_call"]
        tool_result_events = [e for e in events if e["type"] == "tool_result"]

        assert len(tool_call_events) == 2
        assert len(tool_result_events) == 2

        tools_called = [json.loads(e["content"])["tool"] for e in tool_call_events]
        assert "run_ta_engine" in tools_called
        assert "read_reference" in tools_called


def _parse_sse(text: str):
    """Parse SSE text into list of event dicts."""
    events = []
    for line in text.strip().split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


class TestAgentToolCallingIntegration:
    """Integration tests: full SSE flow through the API with tool calling."""

    @pytest.mark.asyncio
    async def _mock_tool_stream(self, symbol: str, model: str):
        """Async generator that simulates the full tool calling flow."""
        # Turn 1: thinking + tool call
        yield {"type": "thinking", "content": "让我获取技术指标数据..."}
        yield {
            "type": "tool_call",
            "content": json.dumps({"tool": "run_ta_engine", "args": {"code": symbol}}, ensure_ascii=False),
        }
        yield {
            "type": "tool_result",
            "content": json.dumps(
                {"tool": "run_ta_engine", "summary": f"引擎完成：{symbol}，共120条数据"},
                ensure_ascii=False,
            ),
        }
        # Emit chart data (as the real agent_service does after engine execution)
        yield {
            "type": "chart_data",
            "content": json.dumps({"symbol": symbol, "latest": {"price": 2050}}),
        }
        # Turn 2: final report — content streamed as thinking, report_complete signals end
        yield {"type": "thinking", "content": "基于指标数据进行分析..."}
        yield {"type": "thinking", "content": "## 分析报告\n\n综合评分：看多"}
        yield {"type": "report_complete"}

    def test_analysis_sse_with_tool_events(self, client, db_session):
        """SSE stream should include tool_call and tool_result events."""
        with patch(
            "backend.services.analysis_service.stream_analysis",
            side_effect=self._mock_tool_stream,
        ):
            response = client.get(
                "/api/v1/analysis/start", params={"symbol": "600519"}
            )
            assert response.status_code == 200

            events = _parse_sse(response.text)
            types = [e["type"] for e in events]

            assert "tool_call" in types
            assert "tool_result" in types
            assert "thinking" in types
            assert "done" in types

    def test_tool_events_saved_to_db(self, client, db_session):
        """Tool_call and tool_result events should be saved as AnalysisStep."""
        from backend.models import AnalysisStep

        with patch(
            "backend.services.analysis_service.stream_analysis",
            side_effect=self._mock_tool_stream,
        ):
            response = client.get(
                "/api/v1/analysis/start", params={"symbol": "600519"}
            )
            _parse_sse(response.text)

        tool_steps = (
            db_session.query(AnalysisStep)
            .filter(AnalysisStep.step_type.in_(["tool_call", "tool_result"]))
            .all()
        )
        assert len(tool_steps) >= 2

        step_types = [s.step_type for s in tool_steps]
        assert "tool_call" in step_types
        assert "tool_result" in step_types

    def test_report_with_chart_data_from_engine(self, client, db_session):
        """When engine returns structured data, it should be in the final report."""
        from backend.models import AnalysisReport

        with patch(
            "backend.services.analysis_service.stream_analysis",
            side_effect=self._mock_tool_stream,
        ):
            response = client.get(
                "/api/v1/analysis/start", params={"symbol": "600519"}
            )
            _parse_sse(response.text)

        report = db_session.query(AnalysisReport).first()
        assert report is not None
        assert "看多" in report.report_md

        # Should have chart_data saved from engine output
        assert report.chart_data is not None
        saved_chart = json.loads(report.chart_data)
        assert saved_chart.get("symbol") == "600519"
