"""Tests for ORM model CRUD and relationships.

Behaviors:
- Create Analysis with symbol, model, skill_version, status
- Create AnalysisStep linked to an Analysis
- Create AnalysisReport linked to an Analysis
- Cascade delete removes steps and report when Analysis is deleted
- SkillVersion stores version hash and change_summary
- BacktestResult stores parameters and results
"""

import json
import uuid
from datetime import datetime

from backend.models import Analysis, AnalysisStep, AnalysisReport, BacktestResult, SkillVersion


def test_create_analysis(db_session):
    """Analysis can be created and queried."""
    a = Analysis(
        id=str(uuid.uuid4()),
        symbol="600519",
        symbol_name="贵州茅台",
        model="deepseek-chat",
        skill_version="2026-07-01.1",
        status="pending",
    )
    db_session.add(a)
    db_session.commit()

    saved = db_session.query(Analysis).first()
    assert saved.symbol == "600519"
    assert saved.symbol_name == "贵州茅台"
    assert saved.model == "deepseek-chat"
    assert saved.skill_version == "2026-07-01.1"
    assert saved.status == "pending"


def test_create_analysis_with_steps(db_session):
    """Analysis can have multiple steps."""
    aid = str(uuid.uuid4())
    a = Analysis(id=aid, symbol="600519", model="deepseek-chat", skill_version="2026-07-01.1")
    db_session.add(a)

    for i in range(3):
        s = AnalysisStep(analysis_id=aid, step_type="thinking", content=f"step {i}", extra="{}")
        db_session.add(s)
    db_session.commit()

    saved = db_session.query(Analysis).first()
    assert len(saved.steps) == 3


def test_create_analysis_with_report(db_session):
    """Analysis has a one-to-one relationship with AnalysisReport."""
    aid = str(uuid.uuid4())
    a = Analysis(id=aid, symbol="600519", model="deepseek-chat", skill_version="2026-07-01.1")
    db_session.add(a)

    r = AnalysisReport(
        id=str(uuid.uuid4()), analysis_id=aid,
        report_md="# Report",
        report_html="<h1>Report</h1>",
        chart_data=json.dumps({"type": "k_line"}),
        key_levels=json.dumps({"support": [1645]}),
        five_dimension=json.dumps({"trend": 1}),
    )
    db_session.add(r)
    db_session.commit()

    saved = db_session.query(Analysis).first()
    assert saved.report is not None
    assert saved.report.report_md == "# Report"
    assert json.loads(saved.report.chart_data) == {"type": "k_line"}


def test_cascade_delete_removes_steps_and_report(db_session):
    """Deleting an Analysis should cascade delete its steps and report."""
    aid = str(uuid.uuid4())
    a = Analysis(id=aid, symbol="600519", model="deepseek-chat", skill_version="2026-07-01.1")
    db_session.add(a)
    db_session.add(AnalysisStep(analysis_id=aid, step_type="thinking", content="x"))
    db_session.add(AnalysisReport(id=str(uuid.uuid4()), analysis_id=aid, report_md="x"))
    db_session.commit()

    db_session.delete(a)
    db_session.commit()

    assert db_session.query(AnalysisStep).count() == 0
    assert db_session.query(AnalysisReport).count() == 0


def test_skill_version_has_required_fields(db_session):
    """SkillVersion must have version, files_hash, and stores change_summary."""
    sv = SkillVersion(
        version="2026-07-01.1",
        files_hash=json.dumps({"SKILL.md": "a1b2c3d4e5f6"}),
        change_summary="Initial version",
    )
    db_session.add(sv)
    db_session.commit()

    saved = db_session.query(SkillVersion).first()
    assert saved.version == "2026-07-01.1"
    assert "SKILL.md" in saved.files_hash
    assert saved.change_summary == "Initial version"


def test_skill_version_version_is_unique_primary_key(db_session):
    """SkillVersion version is the primary key and should be unique."""
    sv1 = SkillVersion(version="2026-07-01.1", files_hash="{}")
    db_session.add(sv1)
    db_session.commit()

    import pytest
    from sqlalchemy.exc import IntegrityError

    sv2 = SkillVersion(version="2026-07-01.1", files_hash="{}")
    db_session.add(sv2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_backtest_result_full_roundtrip(db_session):
    """BacktestResult stores parameters and results JSON."""
    params = json.dumps({"initial_capital": 1000000, "strategy": "ma_cross"})
    results = json.dumps({"total_return": 0.15, "win_rate": 0.6, "max_drawdown": -0.05})

    bt = BacktestResult(
        id=str(uuid.uuid4()),
        symbol="600519",
        skill_version="2026-07-01.1",
        parameters=params,
        results=results,
        report_md="# Backtest Report",
        chart_data=json.dumps({"equity_curve": [1, 1.1, 1.05]}),
    )
    db_session.add(bt)
    db_session.commit()

    saved = db_session.query(BacktestResult).first()
    assert saved.symbol == "600519"
    assert json.loads(saved.parameters)["initial_capital"] == 1000000
    assert json.loads(saved.results)["win_rate"] == 0.6
    assert "# Backtest Report" in saved.report_md


def test_analysis_default_status_is_pending(db_session):
    """Analysis status should default to 'pending'."""
    a = Analysis(id=str(uuid.uuid4()), symbol="600519", model="deepseek-chat", skill_version="2026-07-01.1")
    db_session.add(a)
    db_session.commit()
    assert a.status == "pending"


def test_analysis_created_at_is_set(db_session):
    """Analysis created_at should be set on creation."""
    a = Analysis(id=str(uuid.uuid4()), symbol="600519", model="deepseek-chat", skill_version="2026-07-01.1")
    db_session.add(a)
    db_session.commit()
    assert a.created_at is not None
    assert isinstance(a.created_at, datetime)
