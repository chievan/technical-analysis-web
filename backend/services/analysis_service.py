import json
import uuid
from typing import AsyncGenerator

from sqlalchemy.orm import Session

from backend.models import Analysis, AnalysisStep, AnalysisReport
from backend.services.skill_version_service import compute_skill_hash, compute_version
from backend.agent.agent_service import stream_analysis


async def start_analysis(symbol: str, model: str, db: Session) -> AsyncGenerator[str, None]:
    skill_hash = compute_skill_hash()
    version = compute_version(db)

    analysis = Analysis(
        id=str(uuid.uuid4()),
        symbol=symbol,
        symbol_name="贵州茅台" if symbol == "600519" else symbol,
        model=model,
        skill_version=version,
        status="running",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    full_content = ""
    chart_data = {}
    error_occurred = False
    report_saved = False

    async for event in stream_analysis(symbol, model):
        event_type = event["type"]

        if event_type == "thinking":
            content = event["content"]
            full_content += content

            step = AnalysisStep(
                analysis_id=analysis.id,
                step_type="thinking",
                content=content,
                extra="{}",
            )
            db.add(step)
            db.commit()

            sse_event = json.dumps(
                {"type": "thinking", "content": content}, ensure_ascii=False
            )
            yield f"data: {sse_event}\n\n"

        elif event_type == "tool_call":
            content = event["content"]
            full_content += f"\n[工具调用: {content}]\n"

            step = AnalysisStep(
                analysis_id=analysis.id,
                step_type="tool_call",
                content=content,
                extra="{}",
            )
            db.add(step)
            db.commit()

            yield f"data: {json.dumps({'type': 'tool_call', 'content': content}, ensure_ascii=False)}\n\n"

        elif event_type == "tool_result":
            content = event["content"]
            full_content += f"\n[工具结果: {content}]\n"

            step = AnalysisStep(
                analysis_id=analysis.id,
                step_type="tool_result",
                content=content,
                extra="{}",
            )
            db.add(step)
            db.commit()

            yield f"data: {json.dumps({'type': 'tool_result', 'content': content}, ensure_ascii=False)}\n\n"

        elif event_type == "chart_data":
            try:
                chart_data = json.loads(event["content"])
            except (json.JSONDecodeError, KeyError):
                pass

        elif event_type == "report_chunk":
            content = event["content"]
            full_content += content

            yield f"data: {json.dumps({'type': 'report_chunk', 'content': content}, ensure_ascii=False)}\n\n"

        elif event_type == "report_complete":
            _save_report(db, analysis, full_content, chart_data)
            report_saved = True
            yield _done_event(analysis.id, version)

        elif event_type == "error":
            error_occurred = True
            analysis.status = "failed"
            analysis.conclusion = event["content"]
            db.commit()

            yield f"data: {json.dumps({'type': 'error', 'content': event['content']}, ensure_ascii=False)}\n\n"

    if not error_occurred and not report_saved and full_content:
        _save_report(db, analysis, full_content)
        yield _done_event(analysis.id, version)
    elif not error_occurred and not full_content:
        analysis.status = "failed"
        analysis.conclusion = "Agent returned empty response"
        db.commit()


def _save_report(db: Session, analysis: Analysis, content: str, chart_data: dict | None = None) -> None:
    """Save the full report (with optional chart data) and mark analysis as completed."""
    report = AnalysisReport(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        report_md=content,
        chart_data=json.dumps(chart_data, ensure_ascii=False) if chart_data else "{}",
    )
    db.add(report)
    analysis.status = "completed"
    analysis.conclusion = _extract_conclusion(content)
    db.commit()


def _done_event(analysis_id: str, version: str) -> str:
    return (
        f"data: {json.dumps({'type': 'done', 'analysis_id': analysis_id, 'skill_version': version}, ensure_ascii=False)}\n\n"
    )


def _extract_conclusion(text: str) -> str:
    """Extract a one-line conclusion from the full report."""
    for line in text.strip().split("\n"):
        stripped = line.strip()
        if "综合评分" in stripped or "综合结论" in stripped:
            return stripped
    for line in text.strip().split("\n"):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and len(stripped) > 10:
            return stripped[:120]
    return (text[:100] + "...") if text else ""
