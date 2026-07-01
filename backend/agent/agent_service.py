"""DeepSeek Agent — connects to DeepSeek API with SKILL.md as system prompt and tool calling.

Architecture (per ADR-0001):
- Native tool calling: FastAPI manages the conversation loop directly
- Each request streams text deltas for thinking/report
- When the model requests a tool call, the service executes it and feeds
  the result back into the conversation context
- The loop continues until the model produces the final report (stop)

Tool calling is only supported for deepseek-chat (deepseek-reasoner does
not support function calling per DeepSeek API documentation).
"""

import json
from typing import AsyncGenerator

import httpx

from backend.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, SKILL_DIR
from backend.agent.tool_definitions import TOOLS
from backend.tools.engine_runner import EXECUTOR_MAP

MODEL_MAP = {
    "deepseek-chat": "deepseek-chat",
    "deepseek-reasoner": "deepseek-reasoner",
}

# Only deepseek-chat supports tool/function calling
TOOL_CAPABLE_MODELS = {"deepseek-chat"}


def _get_system_prompt() -> str:
    """Read SKILL.md as the system prompt for the agent."""
    skill_path = SKILL_DIR / "SKILL.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return "You are a technical analysis expert."


def _get_model_name(model: str) -> str:
    """Map frontend model codes to DeepSeek API model names."""
    return MODEL_MAP.get(model, "deepseek-chat")


def _build_tool_calls(tool_calls_acc: dict[int, dict]) -> list[dict]:
    """Build complete tool_calls list from accumulated streaming deltas."""
    result = []
    for idx in sorted(tool_calls_acc.keys()):
        tc = tool_calls_acc[idx]
        result.append({
            "id": tc["id"],
            "type": "function",
            "function": {
                "name": tc["function"]["name"],
                "arguments": tc["function"]["arguments"],
            },
        })
    return result


async def _call_and_stream(
    client: httpx.AsyncClient,
    messages: list[dict],
    api_model: str,
    use_tools: bool,
) -> AsyncGenerator[dict, None]:
    """Make a single streaming API call to DeepSeek.

    Yields immediate events (thinking / report_chunk) for real-time display,
    plus a final turn_complete event with the accumulated result.

    Internal events yielded:
      {"type": "turn_complete", "content": str, "tool_calls": list, "finish_reason": str|None}
    """
    request_kwargs: dict = {
        "model": api_model,
        "messages": messages,
        "stream": True,
    }
    if use_tools:
        request_kwargs["tools"] = TOOLS

    async with client.stream(
        "POST",
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        json=request_kwargs,
    ) as response:
        response.raise_for_status()

        content = ""
        tool_calls_acc: dict[int, dict] = {}
        finish_reason: str | None = None

        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            data_str = line[6:].strip()
            if data_str == "[DONE]":
                break

            try:
                chunk = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            choices = chunk.get("choices", [])
            if not choices:
                continue
            delta = choices[0].get("delta", {})
            finish_reason = choices[0].get("finish_reason")

            # Reasoning content (deepseek-reasoner only)
            reasoning = delta.get("reasoning_content", "") or ""
            if reasoning:
                yield {"type": "thinking", "content": reasoning}

            # Regular text content
            content_delta = delta.get("content", "") or ""
            if content_delta:
                content += content_delta
                if api_model == "deepseek-reasoner":
                    yield {"type": "report_chunk", "content": content_delta}
                else:
                    yield {"type": "thinking", "content": content_delta}

            # Tool call deltas (accumulate by index across chunks)
            tool_call_deltas = delta.get("tool_calls", [])
            for tcd in tool_call_deltas:
                idx = tcd.get("index", 0)
                if idx not in tool_calls_acc:
                    tool_calls_acc[idx] = {
                        "id": tcd.get("id", ""),
                        "function": {"name": "", "arguments": ""},
                    }
                acc = tool_calls_acc[idx]

                if tcd.get("id"):
                    acc["id"] = tcd["id"]

                func = tcd.get("function", {})
                if func.get("name"):
                    acc["function"]["name"] += func["name"]
                if func.get("arguments"):
                    acc["function"]["arguments"] += func["arguments"]

        tool_calls = _build_tool_calls(tool_calls_acc) if tool_calls_acc else []
        yield {
            "type": "turn_complete",
            "content": content,
            "tool_calls": tool_calls,
            "finish_reason": finish_reason,
        }


async def stream_analysis(
    symbol: str,
    model: str,
) -> AsyncGenerator[dict, None]:
    """Stream analysis from DeepSeek API with tool calling loop.

    For deepseek-chat: sends tool definitions, manages a multi-turn conversation
    (think → tool_call → execute → think → report).
    For deepseek-reasoner: text-only streaming without tools (existing behavior).

    Yields user-facing event dicts:
      {"type": "thinking", "content": "..."}
      {"type": "tool_call", "content": JSON with "tool" and "args"}
      {"type": "tool_result", "content": JSON with "tool" and "summary"}
      {"type": "report_chunk", "content": "..."}  (reasoner only)
      {"type": "report_complete", "content": "..."}
      {"type": "error", "content": "..."}
    """
    if not DEEPSEEK_API_KEY:
        yield {"type": "error", "content": "DEEPSEEK_API_KEY not configured"}
        return

    api_model = _get_model_name(model)
    use_tools = api_model in TOOL_CAPABLE_MODELS
    system_prompt = _get_system_prompt()

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"请对标的 {symbol} 进行技术分析。"},
    ]

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            while True:
                turn_events: list[dict] = []
                async for event in _call_and_stream(client, messages, api_model, use_tools):
                    if event["type"] == "turn_complete":
                        turn_events.append(event)
                    else:
                        # Pass through thinking/report_chunk immediately
                        yield event

                if not turn_events:
                    break

                turn = turn_events[-1]
                content = turn.get("content", "")
                tool_calls = turn.get("tool_calls", [])
                finish_reason = turn.get("finish_reason")

                # Only persist assistant turns with actual content
                if content or tool_calls:
                    assistant_msg: dict = {"role": "assistant"}
                    if content:
                        assistant_msg["content"] = content
                    if tool_calls:
                        assistant_msg["tool_calls"] = tool_calls
                    messages.append(assistant_msg)

                if tool_calls:
                    # Execute each requested tool and yield results
                    for tc in tool_calls:
                        func_name = tc["function"]["name"]
                        try:
                            args = json.loads(tc["function"]["arguments"])
                        except (json.JSONDecodeError, TypeError):
                            args = {}

                        # Notify frontend a tool is being called
                        yield {
                            "type": "tool_call",
                            "content": json.dumps(
                                {"tool": func_name, "args": args}, ensure_ascii=False
                            ),
                        }

                        # Execute the tool
                        executor = EXECUTOR_MAP.get(func_name)
                        if executor:
                            try:
                                raw_result = executor(**args)
                            except Exception as e:
                                raw_result = {"error": f"工具执行异常: {str(e)}"}
                        else:
                            raw_result = {"error": f"未知工具: {func_name}"}

                        summary = _summarize_result(func_name, raw_result)

                        yield {
                            "type": "tool_result",
                            "content": json.dumps(
                                {"tool": func_name, "summary": summary}, ensure_ascii=False
                            ),
                        }

                        # Emit structured chart data for engine results
                        if func_name == "run_ta_engine" and isinstance(raw_result, dict) and "error" not in raw_result:
                            yield {
                                "type": "chart_data",
                                "content": json.dumps(raw_result, ensure_ascii=False),
                            }

                        # Emit structured backtest result
                        if func_name == "run_backtester" and isinstance(raw_result, dict) and "error" not in raw_result:
                            yield {
                                "type": "backtest_result",
                                "content": json.dumps(raw_result, ensure_ascii=False),
                            }

                        result_str = (
                            json.dumps(raw_result, ensure_ascii=False)
                            if isinstance(raw_result, dict)
                            else str(raw_result)
                        )
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result_str,
                        })

                    # Agent will process tool results and continue
                    continue

                elif finish_reason == "stop":
                    if content:
                        yield {"type": "report_complete", "content": content}
                    break

                else:
                    # Unexpected finish_reason (length, content_filter, etc.)
                    if content:
                        yield {"type": "report_complete", "content": content}
                    break

    except httpx.HTTPStatusError as e:
        yield {
            "type": "error",
            "content": f"DeepSeek API error (HTTP {e.response.status_code})",
        }
    except httpx.RequestError as e:
        yield {
            "type": "error",
            "content": f"DeepSeek API request failed: {str(e)}",
        }


def _summarize_result(func_name: str, result: dict | str) -> str:
    """Generate a concise human-readable summary of a tool result.

    Accepts dict (from run_ta_engine) or str (from read_reference).
    """
    if isinstance(result, str):
        if func_name == "read_reference":
            return f"已读取参考文档（{len(result)}字符）"
        return "执行完成"
    if "error" in result:
        return f"❌ {result['error']}"
    if func_name == "run_ta_engine":
        name = result.get("symbol_name", result.get("symbol", "未知"))
        points = result.get("data_points", 0)
        price = result.get("latest", {}).get("price", "?")
        alignment = result.get("moving_averages", {}).get("alignment", "")
        return f"引擎完成：{name}（最新价{price}），共{points}条数据，均线{alignment}"
    return "执行完成"
