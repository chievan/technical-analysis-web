"""Tests for analysis detail/steps/report queries.

Behaviors:
- GET /api/v1/analysis/{id} returns analysis for existing ID
- GET /api/v1/analysis/{id} returns 404 for non-existent ID
- GET /api/v1/analysis/{id}/steps returns step list
- GET /api/v1/analysis/{id}/report returns report content
- GET /api/v1/analysis/{id}/report returns 404 for no report
"""

import json

from backend.models import Analysis, AnalysisStep, AnalysisReport


def _create_full_analysis(db_session):
    import uuid
    aid = str(uuid.uuid4())
    a = Analysis(id=aid, symbol="600519", model="deepseek-chat", skill_version="2026-07-01.1", status="completed")
    db_session.add(a)

    step = AnalysisStep(analysis_id=aid, step_type="thinking", content="test step", extra="{}")
    db_session.add(step)

    report = AnalysisReport(
        id=str(uuid.uuid4()), analysis_id=aid, report_md="# Test Report",
        report_html="<h1>Test</h1>", chart_data="{}", key_levels="{}", five_dimension="{}",
    )
    db_session.add(report)
    db_session.commit()
    return aid


def _create_analysis_no_report(db_session):
    import uuid
    aid = str(uuid.uuid4())
    a = Analysis(id=aid, symbol="600519", model="deepseek-chat", skill_version="2026-07-01.1", status="running")
    db_session.add(a)
    db_session.commit()
    return aid


def test_get_analysis_exists(client, db_session):
    """GET /api/v1/analysis/{id} returns analysis for existing ID."""
    aid = _create_full_analysis(db_session)
    response = client.get(f"/api/v1/analysis/{aid}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == aid
    assert data["symbol"] == "600519"
    assert data["status"] == "completed"


def test_get_analysis_not_found(client):
    """GET /api/v1/analysis/{id} returns 404 for non-existent ID."""
    response = client.get("/api/v1/analysis/non-existent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis not found"


def test_get_analysis_steps(client, db_session):
    """GET /api/v1/analysis/{id}/steps returns step list."""
    aid = _create_full_analysis(db_session)
    response = client.get(f"/api/v1/analysis/{aid}/steps")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["step_type"] == "thinking"
    assert data[0]["content"] == "test step"


def test_get_analysis_report(client, db_session):
    """GET /api/v1/analysis/{id}/report returns report content."""
    aid = _create_full_analysis(db_session)
    response = client.get(f"/api/v1/analysis/{aid}/report")
    assert response.status_code == 200
    data = response.json()
    assert data["analysis_id"] == aid
    assert "# Test Report" in data["report_md"]
    assert data["report_html"] == "<h1>Test</h1>"


def test_get_analysis_report_not_found(client, db_session):
    """GET /api/v1/analysis/{id}/report returns 404 when no report."""
    aid = _create_analysis_no_report(db_session)
    response = client.get(f"/api/v1/analysis/{aid}/report")
    assert response.status_code == 404
    assert response.json()["detail"] == "Report not found"
