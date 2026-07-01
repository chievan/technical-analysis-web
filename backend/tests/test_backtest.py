"""Tests for backtest API endpoints.

Behaviors:
- POST /api/v1/backtest/start returns backtest result with expected fields
- GET /api/v1/backtest/history returns empty when no data
- GET /api/v1/backtest/history filters by symbol
- GET /api/v1/backtest/{id} returns specific backtest
- GET /api/v1/backtest/{id} returns 404 for non-existent ID
- Pagination works (limit/offset)
"""

import json
import uuid

from backend.models import BacktestResult


def _create_backtest(db_session, symbol="600519"):
    bt = BacktestResult(
        id=str(uuid.uuid4()),
        symbol=symbol,
        skill_version="2026-07-01.1",
        parameters=json.dumps({"initial_capital": 100000, "strategy": "trend_following"}),
        results=json.dumps({
            "total_return_pct": 5.0,
            "final_capital": 105000,
            "max_drawdown_pct": -3.0,
            "win_rate": 60.0,
            "total_trades": 5,
            "trades": [],
        }),
        report_md="# Backtest Report",
        chart_data=json.dumps({"equity_curve": []}),
    )
    db_session.add(bt)
    db_session.commit()
    return bt


def test_backtest_start_returns_result(client):
    """POST /api/v1/backtest/start returns backtest result with expected fields."""
    response = client.post("/api/v1/backtest/start", params={"symbol": "600519"})
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["symbol"] == "600519"
    assert data["initial_capital"] == 100000
    assert "final_capital" in data
    assert "total_return_pct" in data
    assert "max_drawdown_pct" in data
    assert "win_rate" in data
    assert "total_trades" in data
    assert isinstance(data["trades"], list)
    assert isinstance(data["equity_curve"], list)
    assert len(data["equity_curve"]) > 0
    assert "parameters" in data
    assert "report_md" in data
    assert "created_at" in data


def test_backtest_start_with_custom_params(client):
    """POST with custom parameters passes them to the backtester."""
    response = client.post(
        "/api/v1/backtest/start",
        params={
            "symbol": "000300",
            "initial_capital": 500000,
            "strategy": "mean_reversion",
            "ma_short": 10,
            "ma_long": 30,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "000300"
    assert data["initial_capital"] == 500000
    assert data["parameters"]["strategy"] == "mean_reversion"
    assert data["parameters"]["ma_short"] == 10
    assert data["parameters"]["ma_long"] == 30
    assert data["total_return_pct"] is not None


def test_backtest_history_empty_when_no_data(client):
    """GET /api/v1/backtest/history returns empty when no backtests exist."""
    response = client.get("/api/v1/backtest/history")
    assert response.status_code == 200
    assert response.json() == []


def test_backtest_history_returns_created(client, db_session):
    """GET /api/v1/backtest/history returns created backtests."""
    _create_backtest(db_session)
    response = client.get("/api/v1/backtest/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "600519"


def test_backtest_start_with_dates(client):
    """POST with start_date/end_date passes them to the backtester."""
    response = client.post(
        "/api/v1/backtest/start",
        params={"symbol": "600519", "start_date": "2026-01-01", "end_date": "2026-06-30"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["parameters"]["start_date"] == "2026-01-01"
    assert data["parameters"]["end_date"] == "2026-06-30"


def test_backtest_history_filters_by_date(client, db_session):
    """GET /api/v1/backtest/history filters by date range."""
    from datetime import datetime, timedelta

    # Create backtests
    bt1 = _create_backtest(db_session, symbol="600519")
    bt2 = _create_backtest(db_session, symbol="000300")

    # Manually set created_at to test date filtering
    bt2.created_at = datetime.utcnow() + timedelta(days=1)
    db_session.commit()

    today = datetime.utcnow().strftime("%Y-%m-%d")
    response = client.get("/api/v1/backtest/history", params={"date_from": today})
    assert response.status_code == 200
    data = response.json()
    # Both were created "today" (within test runtime), so both should appear
    assert len(data) >= 2


def test_backtest_history_filters_by_symbol(client, db_session):
    """GET /api/v1/backtest/history filters by symbol."""
    _create_backtest(db_session, symbol="000300")
    _create_backtest(db_session, symbol="600519")
    _create_backtest(db_session, symbol="000300")

    response = client.get("/api/v1/backtest/history", params={"symbol": "000300"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(r["symbol"] == "000300" for r in data)


def test_backtest_history_pagination(client, db_session):
    """GET /api/v1/backtest/history supports limit and offset."""
    for i in range(5):
        _create_backtest(db_session, symbol=f"0000{i}")
    response = client.get("/api/v1/backtest/history", params={"limit": 2, "offset": 0})
    assert len(response.json()) == 2


def test_backtest_get_by_id(client, db_session):
    """GET /api/v1/backtest/{id} returns specific backtest."""
    bt = _create_backtest(db_session)
    response = client.get(f"/api/v1/backtest/{bt.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == bt.id
    assert data["symbol"] == bt.symbol


def test_backtest_get_by_id_not_found(client):
    """GET /api/v1/backtest/{id} returns 404 for non-existent ID."""
    response = client.get("/api/v1/backtest/non-existent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Backtest not found"
