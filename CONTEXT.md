# Context: Technical Analysis Web Application

> 技术分析 Web 应用项目的领域术语表。Web 应用基于 `technical-analysis-pro` CLI skill，通过 DeepSeek Agent 执行技术分析并可视化结果。

## Glossary

### 标的 (Symbol)

用户请求分析的交易品种。可以是 A 股代码（如 600519）、指数代码（如 000300）、国债期货代码（如 TL）、商品期货代码（如 FG）。引擎自动识别品种类型并映射到正确的数据源代码。

### 技术分析引擎 (TA Engine)

`ta_engine.py` — 完成所有确定性计算的 Python 程序。负责数据获取（iFinD / AKShare）、技术指标计算（MA、MACD、RSI、KDJ、BOLL、ATR）、K 线形态识别（TA-Lib，61 种）、五维交叉验证评分、异常扫描、关键价位识别。

### 回测引擎 (Backtester)

`ta_backtester.py` — 独立的回测工具，基于历史数据验证交易策略的表现。不属于核心分析流程，由用户主动触发。

### Skill

存放于 `backend/skill/` 目录下的一组文件，包含 `SKILL.md`（工作流定义）、`scripts/`（Python 引擎脚本）、`references/`（方法论参考文档）。DeepSeek Agent 被授予这些文件作为上下文来执行分析。

### Skill 版本

通过 `scripts/` 和 `references/` 下所有文件的 hash 值变化自动检测。版本号为 `YYYY-MM-DD.N` 格式，N 为当日递进序号。每次分析记录所用的 skill 版本。

### Agent

运行在 DeepSeek API 上的 LLM 实例，被赋予 SKILL.md 作为 system prompt 和一组 tool（`run_ta_engine`、`read_reference`、`run_backtester`）。Agent 自主决定调用时机和顺序，完整思考过程通过 SSE 流式回传。

### Tool Call

DeepSeek Agent 调用后端工具的行为。后端 FastAPI 收到 tool call 请求后执行对应的 Python 程序，将执行结果返回给 Agent 继续推理。

### Streaming

后端通过 Server-Sent Events (SSE) 将 Agent 的思考文本、tool call 状态、报告片段实时推送至前端的通信方式。前端逐行渲染出完整的 Agent 执行过程。

### 分析报告 (Analysis Report)

Agent 生成的完整技术分析报告，包含核心观点、行情概览、五维交叉验证、技术信号、关键价位、概率情景推演、风险提示。使用 Markdown 编写，前端渲染为 HTML，可导出。

### 回测报告 (Backtest Report)

回测执行后生成的报告，包含策略参数、收益率曲线、胜率、最大回撤等指标。独立于分析报告存储和展示。

### 五维交叉验证 (Five-Dimension Cross Validation)

引擎内置的评分系统，从趋势、动量、波动、量价、位置风险五个维度分别打分（-2 ~ +2），综合判断共识强度。具体逻辑详见 `references/five_dimension_framework.md`。

### 交互图表 (Interactive Chart)

基于 ECharts 渲染的交互式技术图表，包含 K 线、均线、布林带、成交量、信号标注等图层。数据来源于引擎输出的结构化 JSON，存储在 SQLite 中供前端渲染。区别于引擎生成的 matplotlib 静态图片。

### SKILL.md

定义 Agent 工作流程的核心文档。Agent 将其作为 system prompt 的一部分，按其中定义的 Step 1-8 逐步执行。包含标的解析规则、引擎调用方式、分析逻辑框架、报告模板等。

### 参考文档 (Reference)

`references/` 目录下的方法论文档，Agent 在分析过程中通过 `read_reference` 工具按需查阅。与 SKILL.md 的区别：SKILL.md 定义"做什么"，reference 定义"怎么做"。

### 历史记录 (History)

存储在 SQLite 中的所有分析记录和报告。支持按标的代码、skill 版本、时间范围筛选。目的是让用户能够纵向比较同一标的在不同时间点的结论变化，以及对比不同 skill 版本下的分析质量差异。

### SSE (Server-Sent Events)

后端向前端推送实时数据的标准协议。在项目中用于流式传输 Agent 的思考过程和工具调用状态，实现"可视化的 skill 执行过程"效果。
