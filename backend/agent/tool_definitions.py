"""Tool definitions for DeepSeek agent (OpenAI-compatible format)."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_ta_engine",
            "description": "运行技术分析引擎，获取标的的结构化技术指标数据，包括K线、均线、MACD、RSI、KDJ、BOLL、成交量等",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "标的代码，如 600519（A股）、000300（指数）、TL（期货）",
                    }
                },
                "required": ["code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_reference",
            "description": "阅读技术分析框架参考文档，获取五维交叉验证评分标准和分析方法论",
            "parameters": {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "description": "文档文件名，如 technical_analysis_framework.md 或 five_dimension_framework.md",
                    }
                },
                "required": ["file"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_backtester",
            "description": "运行回测系统，基于历史K线数据测试交易策略表现。返回回测结果含收益率、最大回撤、胜率等",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "标的代码，如 600519（A股）、000300（指数）、TL（期货）",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "回测开始日期，格式 YYYY-MM-DD",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "回测结束日期，格式 YYYY-MM-DD",
                    },
                    "initial_capital": {
                        "type": "number",
                        "description": "初始资金（元），默认 100000",
                    },
                    "strategy": {
                        "type": "string",
                        "description": "策略名称，可选: trend_following(趋势跟踪), mean_reversion(均值回归)",
                    },
                    "ma_short": {
                        "type": "integer",
                        "description": "短期均线周期，默认 5",
                    },
                    "ma_long": {
                        "type": "integer",
                        "description": "长期均线周期，默认 20",
                    },
                },
                "required": ["code"],
            },
        },
    },
]

TOOL_MAP = {t["function"]["name"]: t for t in TOOLS}


def get_tool_names() -> list[str]:
    return list(TOOL_MAP.keys())
