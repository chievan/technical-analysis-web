import json
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy.orm import Session

from backend.models import Analysis, AnalysisStep, AnalysisReport
from backend.services.skill_version_service import compute_skill_hash, compute_version

SIMULATED_STEPS = [
    {
        "type": "thinking",
        "content": "正在解析标的代码：600519（贵州茅台），识别为 A 股标的。开始准备技术分析流程。",
    },
    {
        "type": "tool_call",
        "content": json.dumps({"tool": "run_ta_engine", "args": {"code": "600519"}, "status": "started"}),
    },
    {
        "type": "tool_result",
        "content": json.dumps({
            "tool": "run_ta_engine",
            "status": "completed",
            "summary": "引擎完成，获取到 500 条日线数据。计算指标：MA5/10/20/60、MACD、RSI、KDJ、BOLL、ATR。",
            "data_points": 500,
        }),
    },
    {
        "type": "thinking",
        "content": "引擎数据已返回。趋势指标：MA5>MA10>MA20，短期多头排列。MACD 金叉延续，红柱缩短，动量有所衰减。RSI(14)=58.2，中性偏强。KDJ 三线粘合，方向不明。",
    },
    {
        "type": "thinking",
        "content": "开始五维交叉验证评分：\n1. 趋势维度（+1）：均线多头排列，价格处于 MA60 上方\n2. 动量维度（0）：MACD 红柱缩短，RSI 中性\n3. 波动维度（-1）：ATR 处于 20 日高位，波动率偏高\n4. 量价维度（+1）：近期成交量温和放大\n5. 位置风险（0）：价格处于布林带上轨附近，存在回调风险\n综合评分：+1（谨慎偏多）",
    },
    {
        "type": "tool_call",
        "content": json.dumps({"tool": "read_reference", "args": {"file": "technical_analysis_framework.md"}, "status": "started"}),
    },
    {
        "type": "tool_result",
        "content": json.dumps({
            "tool": "read_reference",
            "status": "completed",
            "summary": "已读取技术分析框架参考文档。",
        }),
    },
    {
        "type": "thinking",
        "content": "结合五维评分和参考框架，开始撰写分析报告...",
    },
    {
        "type": "report_chunk",
        "content": "## 贵州茅台（600519）技术分析报告\n\n### 核心观点\n当前处于 **谨慎偏多** 格局，短期均线多头排列支撑上行，但波动率偏高和位置风险提示回调可能。",
    },
    {
        "type": "report_chunk",
        "content": "### 行情概览\n- 最新价格：1,688.00\n- 均线系统：MA5(1,672) < MA10(1,658) < MA20(1,641)，多头排列\n- MACD：DIF(12.5) > DEA(8.3)，金叉延续，红柱缩短\n- RSI(14)：58.2，中性偏强\n- KDJ：K(52.3) D(50.1) J(56.7)，三线粘合\n- BOLL：价格接近上轨(1,695)，中轨(1,645)\n- ATR：35.6，波动率偏高",
    },
    {
        "type": "report_chunk",
        "content": "### 五维交叉验证\n\n| 维度 | 评分 | 说明 |\n|------|------|------|\n| 趋势 | +1 | 均线多头排列，价格在 MA60 上方 |\n| 动量 | 0 | MACD 红柱缩短，RSI 中性 |\n| 波动 | -1 | ATR 处于 20 日高位 |\n| 量价 | +1 | 成交量温和放大 |\n| 位置风险 | 0 | 接近布林带上轨 |\n\n**综合评分：+1（谨慎偏多）**",
    },
    {
        "type": "report_chunk",
        "content": "### 关键价位\n- 支撑位：1,645（BOLL 中轨）、1,600（MA60）\n- 阻力位：1,695（BOLL 上轨）、1,720（前高）\n\n### 风险提示\n1. 波动率偏高，需警惕突发消息引发的急跌\n2. 价格接近布林带上轨，短期存在技术性回调需求\n3. 成交量虽有放大但不够显著，上攻动能待确认",
    },
]

FULL_REPORT_MD = """## 贵州茅台（600519）技术分析报告

### 核心观点
当前处于 **谨慎偏多** 格局，短期均线多头排列支撑上行，但波动率偏高和位置风险提示回调可能。

### 行情概览
- 最新价格：1,688.00
- 均线系统：MA5(1,672) < MA10(1,658) < MA20(1,641)，多头排列
- MACD：DIF(12.5) > DEA(8.3)，金叉延续，红柱缩短
- RSI(14)：58.2，中性偏强
- KDJ：K(52.3) D(50.1) J(56.7)，三线粘合
- BOLL：价格接近上轨(1,695)，中轨(1,645)
- ATR：35.6，波动率偏高

### 五维交叉验证

| 维度 | 评分 | 说明 |
|------|------|------|
| 趋势 | +1 | 均线多头排列，价格在 MA60 上方 |
| 动量 | 0 | MACD 红柱缩短，RSI 中性 |
| 波动 | -1 | ATR 处于 20 日高位 |
| 量价 | +1 | 成交量温和放大 |
| 位置风险 | 0 | 接近布林带上轨 |

**综合评分：+1（谨慎偏多）**

### 关键价位
- 支撑位：1,645（BOLL 中轨）、1,600（MA60）
- 阻力位：1,695（BOLL 上轨）、1,720（前高）

### 风险提示
1. 波动率偏高，需警惕突发消息引发的急跌
2. 价格接近布林带上轨，短期存在技术性回调需求
3. 成交量虽有放大但不够显著，上攻动能待确认
"""


async def start_analysis(symbol: str, model: str, db: Session) -> AsyncGenerator[str, None]:
    import uuid

    skill_hash = compute_skill_hash()
    version = compute_version(db)

    analysis = Analysis(
        id=str(uuid.uuid4()),
        symbol=symbol,
        symbol_name="贵州茅台" if symbol == "600519" else symbol,
        model=model,
        skill_version=version,
        status="running",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    for step_data in SIMULATED_STEPS:
        import asyncio

        await asyncio.sleep(0.3)

        step = AnalysisStep(
            analysis_id=analysis.id,
            step_type=step_data["type"],
            content=step_data["content"],
            extra="{}",
        )
        db.add(step)
        db.commit()

        sse_event = f"data: {json.dumps({'type': step_data['type'], 'content': step_data['content']}, ensure_ascii=False)}\n\n"
        yield sse_event

    report = AnalysisReport(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        report_md=FULL_REPORT_MD,
    )
    db.add(report)
    analysis.status = "completed"
    analysis.conclusion = "谨慎偏多 — 均线多头排列支撑上行，但波动率偏高注意回调风险"
    db.commit()

    yield f"data: {json.dumps({'type': 'done', 'analysis_id': analysis.id, 'skill_version': version}, ensure_ascii=False)}\n\n"
