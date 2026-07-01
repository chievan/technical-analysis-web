"""RED: Test SSE analysis stream.

Expected behavior:
- GET /api/v1/analysis/start returns SSE event stream
- Stream contains thinking, tool_call, tool_result, report_chunk events
- Final event is "done" with analysis_id and skill_version
"""

import json


def _parse_sse(text: str):
    """Parse SSE text into list of event dicts."""
    events = []
    for line in text.strip().split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


def test_analysis_sse_emits_all_event_types(client):
    """Analysis SSE stream should emit all four event types plus done."""
    response = client.get("/api/v1/analysis/start", params={"symbol": "600519"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(response.text)
    types = [e["type"] for e in events]

    assert "thinking" in types
    assert "tool_call" in types
    assert "tool_result" in types
    assert "report_chunk" in types
    assert "done" in types


def test_analysis_sse_done_event_contains_ids(client):
    """The final done event should include analysis_id and skill_version."""
    response = client.get("/api/v1/analysis/start", params={"symbol": "600519"})
    events = _parse_sse(response.text)

    done = [e for e in events if e["type"] == "done"]
    assert len(done) == 1

    assert "analysis_id" in done[0]
    assert "skill_version" in done[0]
    assert len(done[0]["analysis_id"]) > 0
    assert done[0]["skill_version"].startswith("2026-07-01.")
