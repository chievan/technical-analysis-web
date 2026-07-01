"""Tool execution functions for the DeepSeek agent.

Each function corresponds to a tool in tool_definitions.py.
Called by agent_service.py when the model requests a tool execution.
"""

import json
import subprocess

from backend.config import SKILL_DIR


def run_ta_engine(code: str) -> dict:
    """Execute ta_engine.py as a subprocess and return parsed JSON output.

    The engine script lives at backend/skill/scripts/ta_engine.py and is a copy
    from the technical-analysis-pro skill repo. If absent, returns an error dict.
    """
    engine_path = SKILL_DIR / "scripts" / "ta_engine.py"
    if not engine_path.exists():
        return {"error": f"引擎脚本不存在: {engine_path}"}

    try:
        result = subprocess.run(
            ["python3", str(engine_path), code],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"引擎执行超时（标的: {code}）"}

    if result.returncode != 0:
        return {
            "error": f"引擎执行失败（返回码 {result.returncode}）: {result.stderr[:500]}"
        }

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"error": f"引擎输出解析失败: {str(e)}"}


def read_reference(file: str) -> str:
    """Read a reference document from the skill references directory."""
    ref_path = SKILL_DIR / "references" / file
    if not ref_path.exists():
        available = [p.name for p in (SKILL_DIR / "references").iterdir()] if (SKILL_DIR / "references").exists() else []
        hint = f"可用文档: {available}" if available else "暂无参考文档"
        return f"参考文档 '{file}' 不存在。{hint}"
    return ref_path.read_text(encoding="utf-8")


# Map tool names to execution functions
EXECUTOR_MAP = {
    "run_ta_engine": run_ta_engine,
    "read_reference": read_reference,
}
