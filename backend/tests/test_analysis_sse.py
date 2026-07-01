"""RED: Test SSE analysis stream with real DeepSeek agent integration.

Expected behavior:
- GET /api/v1/analysis/start returns SSE event stream
- Stream contains thinking and report_chunk events from agent
- Final event is "done" with analysis_id and skill_version
- Error events are handled gracefully
"""

import json
from unittest.mock import patch

import pytest


def _parse_sse(text: str):
    """Parse SSE text into list of event dicts."""
    events = []
    for line in text.strip().split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


async def _mock_agent_stream(symbol: str, model: str):
    """Mock agent_service.stream_analysis for testing."""
    yield {"type": "thinking", "content": "正在分析标的 600519..."}
    yield {"type": "thinking", "content": "均线系统呈多头排列。"}
    yield {"type": "thinking", "content": "MACD 金叉延续，RSI 中性偏强。"}
    yield {"type": "thinking", "content": "综合评分：+1（谨慎偏多），均线多头排列。"}
    yield {
        "type": "report_complete",
        "content": "## 报告\n\n综合评分：+1（谨慎偏多）",
    }


@pytest.fixture(autouse=True)
def mock_agent():
    """Mock the agent service for all SSE tests."""
    with patch(
        "backend.services.analysis_service.stream_analysis",
        side_effect=_mock_agent_stream,
    ):
        yield


def test_analysis_sse_emits_thinking_and_done(client):
    """Analysis SSE stream should emit thinking and done events."""
    response = client.get(
        "/api/v1/analysis/start", params={"symbol": "600519"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(response.text)
    types = [e["type"] for e in events]

    assert "thinking" in types
    assert "done" in types


def test_analysis_sse_done_event_contains_ids(client):
    """The final done event should include analysis_id and skill_version."""
    response = client.get(
        "/api/v1/analysis/start", params={"symbol": "600519"}
    )
    events = _parse_sse(response.text)

    done = [e for e in events if e["type"] == "done"]
    assert len(done) == 1

    assert "analysis_id" in done[0]
    assert "skill_version" in done[0]
    assert len(done[0]["analysis_id"]) > 0
    assert done[0]["skill_version"].startswith("2026-07-01.")


def test_analysis_sse_steps_saved_to_db(client, db_session):
    """Thinking events should be saved as AnalysisStep records."""
    from backend.models import AnalysisStep

    response = client.get(
        "/api/v1/analysis/start", params={"symbol": "600519"}
    )
    # Consume the stream
    _parse_sse(response.text)

    steps = db_session.query(AnalysisStep).all()
    assert len(steps) >= 4
    assert all(s.step_type == "thinking" for s in steps)


def test_analysis_sse_report_saved_to_db(client, db_session):
    """After SSE completes, the report should be saved in DB."""
    from backend.models import Analysis, AnalysisReport

    response = client.get(
        "/api/v1/analysis/start", params={"symbol": "600519"}
    )
    _parse_sse(response.text)

    analysis = db_session.query(Analysis).first()
    assert analysis.status == "completed"

    report = db_session.query(AnalysisReport).first()
    assert report is not None
    assert "综合评分" in report.report_md


def test_analysis_sse_passes_model_parameter(client):
    """The model parameter should be passed through to the agent service."""
    with patch(
        "backend.services.analysis_service.stream_analysis",
    ) as mock_stream:
        mock_stream.return_value.__aiter__.return_value = [
            {
                "type": "report_complete",
                "content": "## Test\n\nContent",
            }
        ]

        client.get(
            "/api/v1/analysis/start",
            params={"symbol": "600519", "model": "deepseek-reasoner"},
        )

        mock_stream.assert_called_once_with("600519", "deepseek-reasoner")
