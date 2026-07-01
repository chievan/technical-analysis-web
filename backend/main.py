from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database import init_db, get_db
from backend.services.analysis_service import start_analysis
from backend.services.history_service import (
    get_analysis_history,
    get_analysis,
    get_analysis_steps,
    get_analysis_report,
)
from backend.services.skill_version_service import compute_skill_hash


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Technical Analysis API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/skill/version")
def get_skill_version():
    files_hash = compute_skill_hash()
    return {"files_hash": files_hash, "files_count": len(files_hash)}


@app.get("/api/v1/skill/versions")
def get_skill_versions(db: Session = Depends(get_db)):
    from backend.models import SkillVersion

    versions = db.query(SkillVersion).order_by(SkillVersion.created_at.desc()).limit(50).all()
    return [
        {"version": v.version, "change_summary": v.change_summary, "created_at": v.created_at.isoformat()}
        for v in versions
    ]


@app.get("/api/v1/analysis/start")
async def start_analysis_endpoint(
    symbol: str = Query(...),
    model: str = Query("deepseek-chat"),
    db: Session = Depends(get_db),
):
    return StreamingResponse(
        start_analysis(symbol, model, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/v1/analysis/history")
def get_analysis_history_endpoint(
    symbol: str = Query(None),
    skill_version: str = Query(None),
    limit: int = Query(20),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    records = get_analysis_history(db, symbol, skill_version, limit, offset)
    return [
        {
            "id": a.id,
            "symbol": a.symbol,
            "symbol_name": a.symbol_name,
            "model": a.model,
            "skill_version": a.skill_version,
            "status": a.status,
            "conclusion": a.conclusion,
            "created_at": a.created_at.isoformat(),
        }
        for a in records
    ]


@app.get("/api/v1/analysis/{analysis_id}")
def get_analysis_endpoint(analysis_id: str, db: Session = Depends(get_db)):
    a = get_analysis(db, analysis_id)
    if not a:
        raise HTTPException(404, "Analysis not found")
    return {
        "id": a.id,
        "symbol": a.symbol,
        "symbol_name": a.symbol_name,
        "model": a.model,
        "skill_version": a.skill_version,
        "status": a.status,
        "conclusion": a.conclusion,
        "created_at": a.created_at.isoformat(),
    }


@app.get("/api/v1/analysis/{analysis_id}/steps")
def get_analysis_steps_endpoint(analysis_id: str, db: Session = Depends(get_db)):
    steps = get_analysis_steps(db, analysis_id)
    return [
        {
            "id": s.id,
            "step_type": s.step_type,
            "content": s.content,
            "extra": s.extra,
            "created_at": s.created_at.isoformat(),
        }
        for s in steps
    ]


@app.get("/api/v1/analysis/{analysis_id}/report")
def get_analysis_report_endpoint(analysis_id: str, db: Session = Depends(get_db)):
    r = get_analysis_report(db, analysis_id)
    if not r:
        raise HTTPException(404, "Report not found")
    return {
        "id": r.id,
        "analysis_id": r.analysis_id,
        "report_md": r.report_md,
        "report_html": r.report_html,
        "chart_data": r.chart_data,
        "key_levels": r.key_levels,
        "five_dimension": r.five_dimension,
        "created_at": r.created_at.isoformat(),
    }
