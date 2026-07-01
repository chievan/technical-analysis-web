# Issue 06: 回测功能

**Sprint**: 2026-07-01
**Trace ID**: `issue-06-backtest`
**Related**: [PRD](../../prd/PRD.md), #6, [issue-05](./issue-05-echarts-annotations.md)

## 1. 本轮成果

独立的回测系统，用户可配置参数并触发回测，结果存入数据库并展示。

| 交付物                                              | 状态 | 文件                                                      |
| --------------------------------------------------- | ---- | --------------------------------------------------------- |
| `run_backtester` 工具定义                           | ✅   | `backend/agent/tool_definitions.py`                       |
| `run_backtester` 引擎 (MA crossover / RSI mean rev) | ✅   | `backend/tools/engine_runner.py`                          |
| Agent SSE `backtest_result` 事件                    | ✅   | `backend/agent/agent_service.py`                          |
| POST /api/v1/backtest/start + 回测报告生成          | ✅   | `backend/main.py`                                         |
| GET /api/v1/backtest/history（支持标的/日期筛选）   | ✅   | `backend/main.py`                                         |
| GET /api/v1/backtest/{id}                           | ✅   | `backend/main.py`                                         |
| BacktestForm.vue 参数配置表单（起止日期/资金/策略） | ✅   | `frontend/src/components/BacktestForm.vue`                |
| BacktestReport.vue 指标卡片 + 交易记录              | ✅   | `frontend/src/components/BacktestReport.vue`              |
| useBacktest.ts composable + 报告下载                | ✅   | `frontend/src/composables/useBacktest.ts`                 |
| BacktestHistoryView.vue 历史列表 + 筛选             | ✅   | `frontend/src/views/BacktestHistoryView.vue`              |
| BacktestDetailView.vue 详情页                       | ✅   | `frontend/src/views/BacktestDetailView.vue`               |
| 分析详情页显示同标历史回测                          | ✅   | `frontend/src/views/HistoryDetailView.vue`                |
| 主分析页"回测"按钮 + 表单弹窗                       | ✅   | `frontend/src/views/AnalysisView.vue`                     |
| 回测 API 测试 (10 tests)                            | ✅   | `backend/tests/test_backtest.py`                          |
| SSE 断线自动重连 (exponential backoff)              | ✅   | `frontend/src/composables/useSSE.ts`                      |
| SSE 错误状态传递 + 重试按钮                         | ✅   | `frontend/src/composables/useSSE.ts` / `AnalysisView.vue` |

## 2. 实现过程

### 后端

`run_backtester` 接收标的代码和策略参数，内部调用 `run_ta_engine` 获取 K 线数据，随后模拟交易逻辑：

- **趋势跟踪**：短期均线上穿长期均线时买入，下穿时卖出
- **均值回归**：RSI < 30 买入，RSI > 70 卖出

三个 REST 端点覆盖了回测的完整生命周期：提交 → 存储 → 查询列表 → 查看详情。

### 前端

三层组件结构：

- `BacktestForm.vue` — 模态弹窗，含起止日期、初始资金、策略、均线参数
- `BacktestReport.vue` — 指标卡片网格（收益率/最大回撤/胜率等）+ 参数展示 + 交易记录
- 两个视图页面：`BacktestHistoryView.vue`（列表）和 `BacktestDetailView.vue`（单条详情）

### SSE 增强

- `backtest_result` 事件类型，Agent 调用 `run_backtester` 时自动推送
- 断线自动重连：指数退避（1s → 2s → 4s → 8s → 16s），最多 5 次
- `onerror` 时标记 `connected = false`，重连失败显示友好提示
- `error` ref 在 AnalysisView 中展示为错误横幅 + 重试按钮

## 3. 关键决策

### 3.1 回测路径：直接 REST vs Agent 调用

- **方案**：用户触发时走直接 REST（`POST /api/v1/backtest/start`），Agent 在分析过程中可独立调用 `run_backtester` 工具
- **理由**：用户主动回测不应等待 Agent 会话启动；Agent 的回测工具作为补充场景（分析过程中 Agent 自行决定是否需要跑回测）
- **影响**：`run_backtester` 作为独立函数被 REST 端点和 Agent executor 双路复用

### 3.2 回测引擎位置

- **方案**：回测逻辑实现在 `tools/engine_runner.py` 中（不单独拆服务或脚本），复用 TA 引擎的数据获取能力
- **理由**：回测引擎不涉及外部子进程调用，纯 Python 计算，放在 executor 中结构最简洁
- **影响**：依赖 TA 引擎的数据输出，回测前自动调用 `run_ta_engine` 获取 K 线

### 3.3 参数传递方式

- **方案**：REST 端点使用 Query 参数（非 JSON body），Agent 工具定义使用 JSON arguments
- **理由**：DeepSeek tool calling 的 output 本身就是 JSON，直接映射到函数参数；REST Query params 与现有端点风格一致
- **tradeoff**：REST 最佳实践倾向 Body（尤其参数较多），但本项目 Query 参数模式已在多个端点使用

## 4. Review 发现 & 修正

从 review 中发现并修复了以下问题：

| 问题                             | 修复                                                       |
| -------------------------------- | ---------------------------------------------------------- |
| 缺少起止日期字段                 | 在 BacktestForm 和 POST 端点中新增 `start_date`/`end_date` |
| 回测历史缺少时间筛选             | 后端新增 `date_from`/`date_to` 查询参数，前端补充日期输入  |
| HistoryDetailView 使用 raw fetch | 替换为 composable 的 `fetchBacktest()`                     |

## 5. 测试覆盖分析

全量：**70 tests**（+2 新增）

| 测试文件           | 数量 | 内容                                                          |
| ------------------ | ---- | ------------------------------------------------------------- |
| `test_backtest.py` | 10   | 回测启动、自定义参数、日期过滤、历史筛选、分页、单条查询、404 |
| 其他 (existing)    | 60   | 无回归                                                        |
