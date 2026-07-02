"""Tests for analysis deduplication (per-symbol per-date overwrite confirmation).

Behaviors:
- GET /api/v1/analysis/check returns report_exists=true when a completed
  analysis exists for the same (symbol, analysis_date) pair.
- GET /api/v1/analysis/check returns report_exists=false when no match.
- Starting analysis without force=true when a report already exists
  emits a report_exists SSE event instead of running a new analysis.
- Starting analysis with force=true re-runs and overwrites the old record.
- Different symbols on the same date do NOT conflict.
- Same symbol on different dates do NOT conflict.
- ta_engine.py generates K-line dates up to today (not capped at April 30).
"""

import json
import uuid
from datetime import datetime, date, timedelta

import pytest
from unittest.mock import patch

from backend.models import Analysis, AnalysisReport


def _create_completed_analysis(
    db_session,
    symbol="600519",
    analysis_date=None,
    conclusion="综合评分：+1（谨慎偏多）",
):
    import uuid as _uuid

    today = (analysis_date or date.today()).isoformat()
    a = Analysis(
        id=str(_uuid.uuid4()),
        symbol=symbol,
        symbol_name="",
        model="deepseek-chat",
        skill_version="2026-07-01.1",
        status="completed",
        conclusion=conclusion,
        analysis_date=today,
    )
    db_session.add(a)
    db_session.commit()

    r = AnalysisReport(
        id=str(_uuid.uuid4()),
        analysis_id=a.id,
        report_md=f"## Report for {symbol} on {today}\n\n{conclusion}",
    )
    db_session.add(r)
    db_session.commit()
    return a


# ─── check endpoint tests ───


def test_check_no_report_exists(client):
    """Check returns report_exists=false when no analysis exists."""
    resp = client.get("/api/v1/analysis/check", params={"symbol": "600519", "date": "2026-07-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_exists"] is False
    assert "analysis_id" not in data


def test_check_report_exists(client, db_session):
    """Check returns report_exists=true with existing analysis details."""
    a = _create_completed_analysis(db_session, analysis_date=date(2026, 7, 1))

    resp = client.get("/api/v1/analysis/check", params={"symbol": a.symbol, "date": "2026-07-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_exists"] is True
    assert data["analysis_id"] == a.id
    assert data["conclusion"] == a.conclusion


def test_check_defaults_to_today(client, db_session):
    """When no date param is given, check defaults to today's date."""
    today = date.today().isoformat()
    a = _create_completed_analysis(db_session, analysis_date=date.today())

    resp = client.get("/api/v1/analysis/check", params={"symbol": a.symbol})
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_exists"] is True
    assert data["analysis_id"] == a.id


def test_check_different_symbol_no_conflict(client, db_session):
    """Different symbol on same date should not conflict."""
    _create_completed_analysis(db_session, symbol="600519", analysis_date=date(2026, 7, 1))

    resp = client.get("/api/v1/analysis/check", params={"symbol": "000300", "date": "2026-07-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_exists"] is False


def test_check_different_date_no_conflict(client, db_session):
    """Same symbol on different date should not conflict."""
    _create_completed_analysis(db_session, symbol="600519", analysis_date=date(2026, 6, 30))

    resp = client.get("/api/v1/analysis/check", params={"symbol": "600519", "date": "2026-07-01"})
    assert resp.status_code == 200
    assert resp.json()["report_exists"] is False


# ─── start endpoint with force flag ───


@pytest.fixture
def auto_mock_agent():
    """Mock the agent to return deterministic SSE events."""
    with patch(
        "backend.services.analysis_service.stream_analysis",
    ) as mock:
        async def _stream(*_a, **_kw):
            yield {"type": "thinking", "content": "starting analysis..."}
            yield {"type": "report_complete", "content": "## Fresh Report\n\nDone."}
        mock.return_value = _stream()
        yield


async def _mock_agent_dedup_stream(symbol: str, model: str):
    """Mock agent with deterministic output for dedup testing."""
    yield {"type": "thinking", "content": f"Analyzing {symbol}..."}
    yield {"type": "report_complete", "content": "## Fresh Report\n\nOverwritten with force."}


@pytest.fixture
def mock_agent_dedup():
    with patch(
        "backend.services.analysis_service.stream_analysis",
        side_effect=_mock_agent_dedup_stream,
    ):
        yield


def _parse_sse(text: str):
    events = []
    for line in text.strip().split("\n"):
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


def test_start_without_force_returns_report_exists_event(client, db_session, mock_agent_dedup):
    """Starting analysis without force when report exists emits report_exists event in SSE."""
    from datetime import date
    a = _create_completed_analysis(db_session, analysis_date=date.today())

    resp = client.get("/api/v1/analysis/start", params={"symbol": a.symbol})
    assert resp.status_code == 200

    events = _parse_sse(resp.text)
    exists_events = [e for e in events if e["type"] == "report_exists"]
    assert len(exists_events) == 1
    assert exists_events[0]["analysis_id"] == a.id
    assert exists_events[0]["report_exists"] is True

    # Should NOT have run a new analysis
    new_report_events = [e for e in events if e["type"] == "report_complete"]
    assert len(new_report_events) == 0


def test_start_with_force_overwrites(client, db_session, mock_agent_dedup):
    """Starting analysis with force=true overwrites existing report."""
    from datetime import date
    old = _create_completed_analysis(
        db_session,
        analysis_date=date.today(),
        conclusion="Old conclusion",
    )

    resp = client.get(
        "/api/v1/analysis/start",
        params={"symbol": old.symbol, "force": "true"},
    )
    assert resp.status_code == 200

    events = _parse_sse(resp.text)
    thinking_events = [e for e in events if e["type"] == "thinking"]
    assert len(thinking_events) > 0

    # Old analysis should have been deleted
    from backend.models import Analysis
    remaining = db_session.query(Analysis).filter(Analysis.symbol == old.symbol).all()
    assert len(remaining) == 1

    # Old record should be replaced (new id)
    assert remaining[0].id != old.id


# ─── data recency test ───


def test_kline_data_ends_at_current_date():
    """ta_engine kline data should end at today's date, not April 30."""
    from backend.skill.scripts.ta_engine import run_engine

    result = run_engine("600519")
    klines = result["klines"]
    last_date = klines[-1]["date"]

    today = date.today()
    # Last kline date should be today or today - 1 (depending on weekends)
    assert last_date >= (today - timedelta(days=2)).isoformat(), (
        f"Expected kline date near {today.isoformat()}, got {last_date}"
    )
    assert last_date <= today.isoformat(), (
        f"Expected kline date <= {today.isoformat()}, got {last_date}"
    )
