from datetime import datetime

from pydantic import BaseModel


class AnalysisResponse(BaseModel):
    id: str
    symbol: str
    symbol_name: str
    model: str
    skill_version: str
    status: str
    conclusion: str
    created_at: datetime


class AnalysisStepResponse(BaseModel):
    id: int
    analysis_id: str
    step_type: str
    content: str
    extra: str
    created_at: datetime


class AnalysisReportResponse(BaseModel):
    id: str
    analysis_id: str
    report_md: str
    report_html: str
    chart_data: str
    key_levels: str
    five_dimension: str
    created_at: datetime


class SkillVersionResponse(BaseModel):
    version: str
    files_hash: str
    change_summary: str
    created_at: datetime
