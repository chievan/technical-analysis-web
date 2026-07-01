import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship

from backend.database import Base


def _uuid():
    return str(uuid.uuid4())


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String, primary_key=True, default=_uuid)
    symbol = Column(String, nullable=False)
    symbol_name = Column(String, default="")
    model = Column(String, nullable=False)
    skill_version = Column(String, nullable=False)
    status = Column(String, default="pending")
    conclusion = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    steps = relationship("AnalysisStep", back_populates="analysis", cascade="all, delete-orphan")
    report = relationship("AnalysisReport", back_populates="analysis", uselist=False, cascade="all, delete-orphan")


class AnalysisStep(Base):
    __tablename__ = "analysis_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=False)
    step_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    extra = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", back_populates="steps")


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id = Column(String, primary_key=True, default=_uuid)
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=False)
    report_md = Column(Text, nullable=False)
    report_html = Column(Text, default="")
    chart_data = Column(Text, default="{}")
    key_levels = Column(Text, default="{}")
    five_dimension = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", back_populates="report")


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(String, primary_key=True, default=_uuid)
    symbol = Column(String, nullable=False)
    skill_version = Column(String, nullable=False)
    parameters = Column(Text, nullable=False)
    results = Column(Text, nullable=False)
    report_md = Column(Text, default="")
    chart_data = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)


class SkillVersion(Base):
    __tablename__ = "skill_versions"

    version = Column(String, primary_key=True)
    files_hash = Column(Text, nullable=False)
    change_summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
