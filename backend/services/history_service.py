from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.models import Analysis, AnalysisStep, AnalysisReport


def get_analysis_history(
    db: Session,
    symbol: Optional[str] = None,
    skill_version: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
):
    q = db.query(Analysis)
    if symbol:
        q = q.filter(Analysis.symbol == symbol)
    if skill_version:
        q = q.filter(Analysis.skill_version == skill_version)
    return q.order_by(desc(Analysis.created_at)).offset(offset).limit(limit).all()


def get_analysis(db: Session, analysis_id: str):
    return db.query(Analysis).filter(Analysis.id == analysis_id).first()


def get_analysis_steps(db: Session, analysis_id: str):
    return (
        db.query(AnalysisStep)
        .filter(AnalysisStep.analysis_id == analysis_id)
        .order_by(AnalysisStep.id)
        .all()
    )


def get_analysis_report(db: Session, analysis_id: str):
    return (
        db.query(AnalysisReport)
        .filter(AnalysisReport.analysis_id == analysis_id)
        .first()
    )
