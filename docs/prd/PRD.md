# PRD: Technical Analysis Web Application

**Version**: 1.0
**Status**: Draft
**Date**: 2026-06-30

## 1. 产品概述

基于已有的 `technical-analysis-pro` CLI skill，构建一个 Web 应用，通过同花顺 iFinD 获取数据，结合 DeepSeek Agent 调用 skill 生成技术分析报告和回测结果，并形成 skill 版本迭代的闭环体系。

### 核心价值

- 将 CLI 技能转化为可视化 Web 体验
- 通过 DeepSeek Agent 使 skill 的完整执行过程可观测
- 基于历史分析数据持续优化 skill 能力
- 交互式图表替代静态图片

## 2. 用户角色

**单人系统**（仅本人使用）

- 不需要登录、权限管理、多用户隔离
- 所有历史数据对当前用户可见

## 3. 技术栈

| 层级   | 技术                  | 备注                                                |
| ------ | --------------------- | --------------------------------------------------- |
| 前端   | Vue 3 + Vite          | 熟悉，开发效率高                                    |
| 图表   | ECharts               | 交互式 K 线、指标、信号标注                         |
| 后端   | FastAPI               | 熟悉，异步支持好                                    |
| 数据库 | SQLite                | 单人系统，零运维                                    |
| 数据源 | 同花顺 iFinD quantapi | 通过 Python 引擎获取                                |
| AI     | DeepSeek API          | DeepSeek V4 Flash / V4 Pro，可切换                  |
| Agent  | 原生 Tool Calling     | 不使用第三方 Agent 框架，FastAPI 直接管理 tool call |

## 4. 架构设计

### 4.1 系统架构

```
┌──────────────────────────────────────────────────────┐
│                    浏览器 (Vue 3)                      │
│  ┌──────────┐  ┌──────────────────────────────────┐  │
│  │ 主分析页面 │  │ 历史浏览页面                     │  │
│  │ - 标的输入  │  │ - 按标的/版本/时间筛选          │  │
│  │ - 模型选择  │  │ - 点击查看完整报告              │  │
│  │ - 会话流可视│  │ - 导出 HTML/MD                 │  │
│  │ - 完整报告  │  └──────────────────────────────────┘  │
│  │ - 交互图表  │                                        │
│  └──────────┘                                           │
└────────────────────────┬─────────────────────────────────┘
                         │ SSE / WebSocket streaming
                         ▼
┌──────────────────────────────────────────────────────┐
│                  FastAPI 后端                          │
│                                                       │
│  ┌─────────────┐  ┌──────────────────────────────┐   │
│  │ Agent 服务   │  │  Tool 执行器                  │   │
│  │ - 管理 Deep- │  │  - run_ta_engine(code)      │   │
│  │   Seek 会话  │  │  - run_backtester(code,par- │   │
│  │ - 处理 tool  │  │    ams)                      │   │
│  │   call 流    │  └──────────────────────────────┘   │
│  │ - streaming  │                                     │
│  └─────────────┘  ┌──────────────────────────────┐   │
│                    │  Skill 版本管理               │   │
│                    │  - 文件 hash 比对            │   │
│                    │  - 版本号生成               │   │
│                    │  - skill 同步脚本           │   │
│                    └──────────────────────────────┘   │
│                                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │  SQLite (via SQLAlchemy)                     │   │
│  │  analyses / analysis_steps / reports         │   │
│  │  backtest_results / skill_versions           │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│           DeepSeek API (Agent Mode)                   │
│  System Prompt: SKILL.md + 工具描述                   │
│  Agent 自主判断何时调用 Python 引擎                   │
│  完整思考过程通过 streaming 回传                     │
└──────────────────────────────────────────────────────┘
```

### 4.2 一次完整分析流程

```
1. 用户在前端输入标代码 (如 "600519")，选择模型，点击"开始分析"
2. FastAPI 接收请求，执行 skill 版本检测（hash 比对 skill/ 目录）
3. FastAPI 建立 DeepSeek API 连接（SSE streaming）
│
4. DeepSeek Agent 开始按 SKILL.md 步骤执行：
│
   4a. Agent 解析标的 → 工具调用 run_ta_engine(code="600519")
   4b. FastAPI 执行 python3 ta_engine.py 600519 ... → 返回 JSON
   4c. Agent 阅读指标数据 → 分析趋势/动量/波动/量价/位置风险
   4d. Agent 阅读方法论参考 → 五维交叉验证
   4e. Agent 生成完整报告
│
5. 所有 Agent 思考过程 + tool call 步骤 streaming 回前端
6. 最终报告存入 SQLite
7. 前端渲染报告（Markdown → HTML）+ ECharts 交互图表
```

### 4.3 DeepSeek Agent 工具定义

```python
tools = [
    {
        "name": "run_ta_engine",
        "description": "运行技术分析引擎，获取标的的结构化技术指标数据",
        "parameters": {
            "code": "标的代码，如 600519, 000300, TL",
            "output_dir": "输出目录（可选）",
        }
    },
    {
        "name": "read_reference",
        "description": "阅读技术分析框架参考文档",
        "parameters": {
            "file": "文档文件名，如 technical_analysis_framework.md"
        }
    },
    {
        "name": "run_backtester",
        "description": "运行回测引擎",
        "parameters": {
            "code": "标的代码",
            "start_date": "回测起始日期",
            "end_date": "回测结束日期",
            "initial_capital": "初始资金（默认 1000000）",
            "strategy_params": "策略参数（JSON 字符串）",
        }
    }
]
```

### 4.4 Streaming 协议

后端通过 SSE (Server-Sent Events) 向前端推送实时流：

```json
// Agent 思考文本
{"type": "thinking", "content": "正在解析标的代码：600519..."}

// Tool call 开始
{"type": "tool_call", "tool": "run_ta_engine", "args": {"code": "600519"}, "status": "started"}

// Tool call 结果
{"type": "tool_result", "tool": "run_ta_engine", "status": "completed", "summary": "引擎完成，获取到 500 条日线数据"}

// 报告片段
{"type": "report_chunk", "content": "## 贵州茅台 技术分析报告"}

// 完成信号
{"type": "done", "analysis_id": "abc123", "skill_version": "2026-06-30.1"}
```

## 5. 功能需求

### 5.1 主分析页面

| 功能           | 描述                                                        | 优先级 |
| -------------- | ----------------------------------------------------------- | ------ |
| 标的输入       | 输入框，支持 A 股代码、指数代码、期货代码                   | P0     |
| 模型选择       | DeepSeek V4 Flash / V4 Pro 切换                             | P0     |
| 开始分析       | 触发完整技术分析流程                                        | P0     |
| 回测触发       | 独立按钮，触发回测流程，可配置参数                          | P1     |
| 实时会话流     | 实时显示 Agent 思考、tool call、报告生成过程                | P0     |
| 完整报告展示   | 最终报告的 Markdown → HTML 渲染                             | P0     |
| 交互式图表     | ECharts K 线 + 均线 + BOLL + 信号标注（缩放/悬停/切换周期） | P1     |
| 报告导出       | 导出为 HTML 或 Markdown 文件                                | P1     |
| 同标的历史分析 | 页面内切换查看该标的历史分析报告                            | P1     |

### 5.2 历史记录页面

| 功能     | 描述                                 | 优先级 |
| -------- | ------------------------------------ | ------ |
| 筛选     | 按标的代码、skill 版本、时间范围筛选 | P0     |
| 列表展示 | 分析时间、标的、结论摘要、skill 版本 | P0     |
| 详情查看 | 点击进入完整报告查看                 | P0     |
| 回测记录 | 同样的列表 + 筛选 + 详情查看         | P1     |
| 导出     | 单条或批量导出                       | P2     |

### 5.3 Skill 版本管理

| 功能         | 描述                                           | 优先级 |
| ------------ | ---------------------------------------------- | ------ |
| 自动版本检测 | 每次分析前 hash 比对 skill 目录文件            | P0     |
| 版本记录     | 版本号、日期、文件 hash 列表、变更摘要         | P0     |
| 同步脚本     | `sync-skill.sh` 从源目录同步 skill 到应用 repo | P1     |
| 版本历史查看 | 在界面中查看 skill 版本变更历史                | P2     |

## 6. 数据模型

### 6.1 表结构

```sql
-- 分析主记录
CREATE TABLE analyses (
    id            TEXT PRIMARY KEY,       -- UUID
    symbol        TEXT NOT NULL,           -- 标的代码
    symbol_name   TEXT,                    -- 标的名称（引擎解析后填充）
    model         TEXT NOT NULL,           -- DeepSeek 模型名
    skill_version TEXT NOT NULL,           -- 使用的 skill 版本号
    status        TEXT DEFAULT 'pending',  -- pending/running/completed/failed
    conclusion    TEXT,                    -- 核心结论摘要
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Agent 执行步骤日志
CREATE TABLE analysis_steps (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id   TEXT NOT NULL REFERENCES analyses(id),
    step_type     TEXT NOT NULL,           -- thinking/tool_call/tool_result/report_chunk
    content       TEXT NOT NULL,           -- 步骤内容
    metadata      TEXT,                    -- JSON 格式的额外信息（tool 名称、参数等）
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 完整报告
CREATE TABLE analysis_reports (
    id            TEXT PRIMARY KEY,
    analysis_id   TEXT NOT NULL REFERENCES analyses(id),
    report_md     TEXT NOT NULL,           -- Markdown 报告全文
    report_html   TEXT,                    -- 渲染后的 HTML
    chart_data    TEXT,                    -- JSON 格式的图表数据（K线、指标等）
    key_levels    TEXT,                    -- 关键价位 JSON
    five_dimension TEXT,                   -- 五维评分 JSON
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 回测结果
CREATE TABLE backtest_results (
    id            TEXT PRIMARY KEY,
    symbol        TEXT NOT NULL,
    skill_version TEXT NOT NULL,
    parameters    TEXT NOT NULL,           -- JSON 回测参数
    results       TEXT NOT NULL,           -- JSON 回测结果（收益率、胜率、曲线等）
    report_md     TEXT,                    -- 回测报告
    chart_data    TEXT,                    -- 图表数据
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Skill 版本记录
CREATE TABLE skill_versions (
    version       TEXT PRIMARY KEY,        -- 如 "2026-06-30.1"
    files_hash    TEXT NOT NULL,           -- 所有文件的 hash 映射 JSON
    change_summary TEXT,                   -- 变更摘要（手动填写或自动生成）
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 7. 项目目录结构

```
technical-analysis-web/
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── main.ts
│   │   ├── router/
│   │   │   └── index.ts
│   │   ├── views/
│   │   │   ├── AnalysisView.vue       # 主分析页面
│   │   │   └── HistoryView.vue         # 历史记录页面
│   │   ├── components/
│   │   │   ├── AgentStream.vue         # 实时会话流组件
│   │   │   ├── ReportViewer.vue        # 报告渲染组件
│   │   │   ├── KLineChart.vue          # ECharts K 线图表
│   │   │   ├── BacktestForm.vue        # 回测参数配置
│   │   │   └── HistoryFilter.vue       # 筛选控件
│   │   ├── composables/
│   │   │   ├── useAnalysis.ts          # 分析流程管理
│   │   │   └── useSSE.ts               # SSE 连接管理
│   │   └── types/
│   │       └── index.ts
│   ├── index.html
│   └── vite.config.ts
│
├── backend/
│   ├── main.py                         # FastAPI 入口
│   ├── config.py                       # 配置管理
│   ├── database.py                     # 数据库连接 + ORM
│   ├── models.py                       # SQLAlchemy 模型
│   ├── schemas.py                      # Pydantic schemas
│   │
│   ├── agent/
│   │   ├── agent_service.py            # DeepSeek Agent 管理
│   │   └── tool_definitions.py         # 工具定义
│   │
│   ├── tools/
│   │   ├── engine_runner.py            # 调用 ta_engine.py
│   │   └── backtest_runner.py          # 调用 ta_backtester.py
│   │
│   ├── services/
│   │   ├── analysis_service.py         # 分析业务流程
│   │   ├── history_service.py          # 历史记录查询
│   │   └── skill_version_service.py    # 版本管理
│   │
│   ├── skill/                          # → 从源 skill 同步的副本
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   ├── ta_engine.py
│   │   │   └── ta_backtester.py
│   │   └── references/
│   │       ├── technical_analysis_framework.md
│   │       └── five_dimension_framework.md
│   │
│   ├── requirements.txt
│   └── .env
│
├── scripts/
│   └── sync-skill.sh                   # skill 同步脚本
│
└── README.md
```

## 8. 路由设计

| 路径           | 页面                                   | 说明                                      |
| -------------- | -------------------------------------- | ----------------------------------------- |
| `/`            | 主分析页                               | 标的输入 + 模型选择 + 实时会话 + 报告展示 |
| `/history`     | 历史记录                               | 按标的/版本/时间筛选，点击查看详情        |
| `/history/:id` | 报告详情                               | 查看单条完整报告                          |
| `/backtest`    | 回测页面（可合并到主分析页的独立 tab） | 回测配置 + 结果展示                       |

API 接口：

| 方法 | 路径                          | 说明                      |
| ---- | ----------------------------- | ------------------------- |
| POST | `/api/v1/analysis/start`      | 开始分析，返回 SSE stream |
| GET  | `/api/v1/analysis/:id`        | 获取单条分析记录          |
| GET  | `/api/v1/analysis/:id/report` | 获取完整报告              |
| GET  | `/api/v1/analysis/:id/steps`  | 获取执行步骤              |
| GET  | `/api/v1/analysis/history`    | 历史列表（支持筛选）      |
| POST | `/api/v1/backtest/start`      | 开始回测，返回 SSE stream |
| GET  | `/api/v1/backtest/:id`        | 获取回测结果              |
| GET  | `/api/v1/backtest/history`    | 回测历史列表              |
| GET  | `/api/v1/skill/version`       | 获取当前 skill 版本信息   |
| GET  | `/api/v1/skill/versions`      | 获取所有历史版本          |

## 9. 开发优先级

### Phase 1 — 核心链路（P0）

- 项目脚手架（Vue 3 + FastAPI + SQLite）
- Skill 副本同步 + 版本自动检测
- DeepSeek Agent 完整分析流程（tool call + streaming）
- 主分析页面：输入 + 实时会话流 + 报告渲染
- SQLite 数据存储

### Phase 2 — 增强功能（P1）

- ECharts 交互图表（K 线 + 均线 + 信号标注）
- 历史记录页面（筛选 + 详情查看）
- 回测（独立触发 + 参数配置 + 结果存储）
- 报告导出 HTML / MD
- 同标的历史分析切换

### Phase 3 — 完善（P2）

- Skill 版本历史查看
- 批量导出
- SSE 重连、错误恢复
- 引擎结果缓存

## 10. 非功能需求

- **响应速度**：Agent 思考过程 Streaming 到前端，用户无需等待完整完成才看到内容
- **错误处理**：DeepSeek API 调用失败、引擎执行失败、工具调用超时，均有前端提示
- **数据持久性**：所有分析记录和报告保存在 SQLite，支持随时回溯
- **可扩展性**：Agent 工具定义与 FastAPI 松耦合，后续可加入更多工具
- **版本追溯**：每次分析记录 skill 版本，可回看"v1.1 版本下对茅台的判断"
