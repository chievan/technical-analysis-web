import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database import init_db, get_db
from backend.models import BacktestResult
from backend.services.analysis_service import start_analysis
from backend.services.history_service import (
    get_analysis_history,
    get_analysis,
    get_analysis_steps,
    get_analysis_report,
)
from backend.services.skill_version_service import compute_skill_hash, compute_version
from backend.tools.engine_runner import run_backtester


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


# ────────────────────────────────
# Backtest endpoints
# ────────────────────────────────


def _generate_backtest_report_md(result: dict) -> str:
    """Generate a simple markdown summary from a backtest result dict."""
    strategy_names = {
        "trend_following": "趋势跟踪",
        "mean_reversion": "均值回归",
    }
    strat = result.get("parameters", {}).get("strategy", "trend_following")
    strat_name = strategy_names.get(strat, strat)

    lines = [
        f"# 回测报告：{result.get('symbol_name', result.get('symbol', '未知'))}（{result.get('symbol', '未知')}）",
        "",
        f"- **策略**: {strat_name}",
        f"- **初始资金**: ¥{result.get('initial_capital', 0):,.0f}",
        f"- **最终资金**: ¥{result.get('final_capital', 0):,.2f}",
        f"- **总收益率**: {result.get('total_return_pct', 0):+.2f}%",
        f"- **最大回撤**: {result.get('max_drawdown_pct', 0):.2f}%",
        f"- **胜率**: {result.get('win_rate', 0):.1f}%",
        f"- **总交易次数**: {result.get('total_trades', 0)}",
    ]

    params = result.get("parameters", {})
    if params.get("ma_short"):
        lines.append(f"- **短期均线**: MA{params['ma_short']}")
    if params.get("ma_long"):
        lines.append(f"- **长期均线**: MA{params['ma_long']}")

    trades = result.get("trades", [])
    if trades:
        lines.extend(["", "## 交易记录", ""])
        lines.append("| 日期 | 类型 | 价格 | 金额 | 原因 |")
        lines.append("|------|------|------|------|------|")
        for t in trades:
            lines.append(f"| {t['date']} | {t['type']} | {t['price']} | {t['value']} | {t.get('reason', '')} |")

    lines.append("")
    return "\n".join(lines)


@app.post("/api/v1/backtest/start")
def start_backtest_endpoint(
    symbol: str = Query(...),
    start_date: str = Query("", description="回测开始日期 YYYY-MM-DD"),
    end_date: str = Query("", description="回测结束日期 YYYY-MM-DD"),
    initial_capital: float = Query(100000),
    strategy: str = Query("trend_following"),
    ma_short: int = Query(5),
    ma_long: int = Query(20),
    db: Session = Depends(get_db),
):
    version = compute_version(db)

    result = run_backtester(
        code=symbol,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        strategy=strategy,
        ma_short=ma_short,
        ma_long=ma_long,
    )

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    report_md = _generate_backtest_report_md(result)

    bt = BacktestResult(
        id=str(uuid.uuid4()),
        symbol=symbol,
        skill_version=version,
        parameters=json.dumps(result.get("parameters", {}), ensure_ascii=False),
        results=json.dumps({
            "final_capital": result["final_capital"],
            "total_return_pct": result["total_return_pct"],
            "max_drawdown_pct": result["max_drawdown_pct"],
            "win_rate": result["win_rate"],
            "total_trades": result["total_trades"],
            "trades": result["trades"],
        }, ensure_ascii=False),
        report_md=report_md,
        chart_data=json.dumps({"equity_curve": result.get("equity_curve", [])}, ensure_ascii=False),
    )
    db.add(bt)
    db.commit()
    db.refresh(bt)

    return {
        "id": bt.id,
        "symbol": bt.symbol,
        "skill_version": bt.skill_version,
        "initial_capital": initial_capital,
        "final_capital": result["final_capital"],
        "total_return_pct": result["total_return_pct"],
        "max_drawdown_pct": result["max_drawdown_pct"],
        "win_rate": result["win_rate"],
        "total_trades": result["total_trades"],
        "trades": result["trades"],
        "equity_curve": result["equity_curve"],
        "parameters": result["parameters"],
        "report_md": report_md,
        "chart_data": {"equity_curve": result.get("equity_curve", [])},
        "created_at": bt.created_at.isoformat(),
    }


@app.get("/api/v1/backtest/history")
def get_backtest_history_endpoint(
    symbol: str = Query(None),
    date_from: str = Query(None, description="起始日期 YYYY-MM-DD"),
    date_to: str = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(20),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    from datetime import datetime

    q = db.query(BacktestResult)
    if symbol:
        q = q.filter(BacktestResult.symbol == symbol)
    if date_from:
        q = q.filter(BacktestResult.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        q = q.filter(BacktestResult.created_at <= datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59))
    records = q.order_by(BacktestResult.created_at.desc()).offset(offset).limit(limit).all()

    return [
        {
            "id": r.id,
            "symbol": r.symbol,
            "skill_version": r.skill_version,
            "total_trades": len(json.loads(r.results).get("trades", [])),
            "total_return_pct": json.loads(r.results).get("total_return_pct"),
            "max_drawdown_pct": json.loads(r.results).get("max_drawdown_pct"),
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@app.get("/api/v1/backtest/{backtest_id}")
def get_backtest_endpoint(backtest_id: str, db: Session = Depends(get_db)):
    bt = db.query(BacktestResult).filter(BacktestResult.id == backtest_id).first()
    if not bt:
        raise HTTPException(status_code=404, detail="Backtest not found")
    results = json.loads(bt.results)
    return {
        "id": bt.id,
        "symbol": bt.symbol,
        "skill_version": bt.skill_version,
        "parameters": json.loads(bt.parameters),
        "final_capital": results.get("final_capital"),
        "total_return_pct": results.get("total_return_pct"),
        "max_drawdown_pct": results.get("max_drawdown_pct"),
        "win_rate": results.get("win_rate"),
        "total_trades": results.get("total_trades"),
        "trades": results.get("trades", []),
        "equity_curve": json.loads(bt.chart_data).get("equity_curve", []),
        "report_md": bt.report_md,
        "chart_data": json.loads(bt.chart_data),
        "created_at": bt.created_at.isoformat(),
    }
