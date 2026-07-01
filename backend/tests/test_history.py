"""Tests for analysis history API.

Behaviors:
- GET /api/v1/analysis/history returns empty list when no analyses
- History filters by symbol
- History filters by skill_version
"""

from backend.models import Analysis


def _create_analysis(db_session, symbol="600519", skill_version="2026-07-01.1", model="deepseek-chat"):
    import uuid
    a = Analysis(
        id=str(uuid.uuid4()),
        symbol=symbol,
        symbol_name="",
        model=model,
        skill_version=skill_version,
        status="completed",
        conclusion="test conclusion",
    )
    db_session.add(a)
    db_session.commit()
    return a


def test_history_empty_when_no_data(client):
    """History should return empty list when no analyses exist."""
    response = client.get("/api/v1/analysis/history")
    assert response.status_code == 200
    assert response.json() == []


def test_history_returns_created_analyses(client, db_session):
    """History should return analyses after they are created."""
    _create_analysis(db_session)
    response = client.get("/api/v1/analysis/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "600519"


def test_history_filters_by_symbol(client, db_session):
    """History should filter by symbol query parameter."""
    _create_analysis(db_session, symbol="000300")
    _create_analysis(db_session, symbol="600519")
    _create_analysis(db_session, symbol="000300")

    response = client.get("/api/v1/analysis/history", params={"symbol": "000300"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(r["symbol"] == "000300" for r in data)


def test_history_filters_by_skill_version(client, db_session):
    """History should filter by skill_version."""
    _create_analysis(db_session, skill_version="2026-07-01.1")
    _create_analysis(db_session, skill_version="2026-07-01.2")

    response = client.get("/api/v1/analysis/history", params={"skill_version": "2026-07-01.1"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["skill_version"] == "2026-07-01.1"


def test_history_pagination(client, db_session):
    """History should support limit and offset."""
    for i in range(5):
        _create_analysis(db_session, symbol=f"00000{i}")
    response = client.get("/api/v1/analysis/history", params={"limit": 2, "offset": 0})
    assert len(response.json()) == 2
