"""DeepSeek Agent — connects to DeepSeek API with SKILL.md as system prompt."""

import json
from typing import AsyncGenerator

import httpx

from backend.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, SKILL_DIR

MODEL_MAP = {
    "deepseek-chat": "deepseek-chat",
    "deepseek-reasoner": "deepseek-reasoner",
}


def _get_system_prompt() -> str:
    """Read SKILL.md as the system prompt for the agent."""
    skill_path = SKILL_DIR / "SKILL.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return "You are a technical analysis expert."


def _get_model_name(model: str) -> str:
    """Map frontend model codes to DeepSeek API model names."""
    return MODEL_MAP.get(model, "deepseek-chat")


async def stream_analysis(
    symbol: str,
    model: str,
) -> AsyncGenerator[dict, None]:
    """Stream analysis from DeepSeek API.

    Yields dicts with event data:
      {"type": "thinking", "content": "..."}
      {"type": "report_chunk", "content": "..."}  # only for deepseek-reasoner
      {"type": "error", "content": "..."}
    """
    if not DEEPSEEK_API_KEY:
        yield {"type": "error", "content": "DEEPSEEK_API_KEY not configured"}
        return

    api_model = _get_model_name(model)
    system_prompt = _get_system_prompt()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"请对标的 {symbol} 进行技术分析。"},
    ]

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
                json={
                    "model": api_model,
                    "messages": messages,
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()

                full_content = ""
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})

                        # deepseek-reasoner: reasoning trace
                        reasoning = delta.get("reasoning_content", "") or ""
                        if reasoning:
                            yield {"type": "thinking", "content": reasoning}

                        # Regular content (also used for deepseek-chat)
                        content = delta.get("content", "") or ""
                        if content:
                            full_content += content
                            if api_model == "deepseek-reasoner":
                                yield {"type": "report_chunk", "content": content}
                            else:
                                yield {"type": "thinking", "content": content}
                    except json.JSONDecodeError:
                        continue

                if full_content:
                    yield {"type": "report_complete", "content": full_content}

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
