# Issue 04: ECharts 交互图表 + 报告导出 + UI 完善

**Sprint**: 2026-07-01
**Trace ID**: `issue-04-echarts-charts`
**Related**: [PRD](../../prd/PRD.md), [ADR-0001](../../adr/0001-deepseek-agent-tool-calling.md)

## 1. 本轮成果

本 sprint 完成 Phase 2 的核心功能，将静态文本分析升级为交互式图表体验：

| 交付物                                              | 状态 | 文件                                       |
| --------------------------------------------------- | ---- | ------------------------------------------ |
| 引擎输出完整时间序列（klines + 指标序列）           | ✅   | `backend/skill/scripts/ta_engine.py`       |
| ECharts K 线图表（K线/MA/BOLL/成交量/MACD/RSI）     | ✅   | `frontend/src/components/KLineChart.vue`   |
| 分析页面集成交互图表                                | ✅   | `frontend/src/views/AnalysisView.vue`      |
| 历史详情页集成交互图表                              | ✅   | `frontend/src/views/HistoryDetailView.vue` |
| 同标历史分析切换                                    | ✅   | `frontend/src/views/AnalysisView.vue`      |
| 报告导出（Markdown / HTML）                         | ✅   | `frontend/src/composables/useAnalysis.ts`  |
| TypeScript 类型补全（chart_data / report_complete） | ✅   | `frontend/src/types/index.ts`              |
| AgentStream chart_data/report_complete 展示         | ✅   | `frontend/src/components/AgentStream.vue`  |
| ReportViewer 空状态文案统一                         | ✅   | `frontend/src/components/ReportViewer.vue` |
| 2 项 TDD 测试（engine 时间序列输出）                | ✅   | `backend/tests/test_tool_calling.py`       |

## 2. 实现过程

### 引擎扩展

| 步骤  | 动作                                                                                                                                           | 结果 |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ---- |
| RED   | `test_engine_returns_time_series_data` — 验证 klines 数组存在且结构正确                                                                        | 失败 |
| RED   | `test_engine_returns_indicator_series` — 验证 ma/macd/rsi/boll 序列存在                                                                        | 失败 |
| GREEN | 在 `ta_engine.py` 中新增 `klines` + `ma5_series`/`ma10_series`/`ma20_series`/`ma60_series` + `macd_series` + `rsi_series` + `bollinger_series` | 通过 |

### KLineChart 组件

- 使用原生 ECharts（无 vue-echarts 包装器），通过 `onMounted`/`watch`/`onUnmounted` 管理生命周期
- 四网格布局：主 K 线面板（55%）、成交量（12%）、MACD（9%）、RSI（9%）
- 主面板：Candlestick + BOLL（虚线上下轨） + MA5/10/20/60（不同颜色）
- 成交量按涨跌着色（红绿）
- MACD 含柱状图 + DIF/DEA 线
- RSI 含超买超卖标记线（70/30）
- `dataZoom` 支持拖拽缩放
- `legend` 默认隐藏 BOLL 线（减少视觉杂乱）

### 多网格 ECharts 设计

```
Grid 0 (55%): Candlestick + BOLL(upper/middle/lower) + MA5/10/20/60
Grid 1 (12%): Volume (bar chart, per-candle green/red)
Grid 2 ( 9%): MACD (histogram + DIF + DEA lines)
Grid 3 ( 9%): RSI (line + markLines at 70/30)
```

### SSE 集成

- `useSSE` composable 新增 `chartDataStr` ref，在 `onmessage` 中累积 `chart_data` 事件
- `chartDataStr` 变化时 AnalysisView 自动解析 JSON → 传递给 KLineChart
- 兜底策略：SSE 未收到 `chart_data` 时，从已保存的 report 中读取

### 同标历史分析

- 分析完成后自动查询 `fetchHistory({symbol})`，排除当前记录
- 在控制面板下方显示为日期芯片（chip），点击在新标签页打开
- 仅显示最近 5 条同标分析

### 报告导出

- `useAnalysis.downloadReport(id, format)` 通用方法
- 通过 `Blob` + `URL.createObjectURL` 触发浏览器下载
- HistoryDetailView 展示"导出 Markdown"、"导出 HTML" 按钮

## 3. 关键决策

### 3.1 ECharts vs vue-echarts

- **方案**：直接使用 ECharts（`import * as echarts`），无 vue-echarts 包装器
- **理由**：K 线图表生命周期简单（初始化 → setOption → resize），无需两层组件抽象
- **Trade-off**：需要在 `onUnmounted` 中手动 `dispose`，但减少了额外依赖

### 3.2 引擎输出时间序列 vs 前端计算指标

- **方案**：引擎直接输出完整时间序列（klines + 指标序列）
- **理由**：引擎已有完整的 K 线生成和指标计算逻辑（MA/MACD/RSI/BOLL），前端只需渲染
- **替代方案**：引擎只输出原始 klines，前端用 ECharts 计算指标（echarts 内置 MA 但不支持 MACD/RSI）
- **结论**：后端计算确保指标在引擎和图表间一致，避免前端重新实现算法

### 3.3 chart_data 双通道传递

- **SSE 通道**：run_ta_engine 执行后 emit `chart_data` 事件 → 前端 useSSE 累积
- **DB 通道**：报告存入 AnalysisReport.chart_data → HistoryDetailView 通过 API 读取
- **理由**：实时分析页通过 SSE 即时获取，历史详情页通过 DB 持久读取
- **影响**：`useSSE` 新增 `chartDataStr` 状态，`useAnalysis` 新增 `fetchChartData` 方法

### 3.4 Null 值处理

- **问题**：MA 序列前 N 个值为 `None`（不满周期），BOLL 序列同
- **方案**：引擎中 `_none_safe` 和 `_boll_safe` 将 None 转换为 0
- **影响**：ECharts 不会因 null/undefined 断线，但 0 值在图表左侧可见，需设置 `dataZoom` 起始偏移
- **折中**：当前 `start: 40`（120 条显示后 60 条），0 值被自动裁剪

## 4. 修复的 Bug

| Bug          | 症状                                   | 根因          | 修复                                           |
| ------------ | -------------------------------------- | ------------- | ---------------------------------------------- |
| npm 网络超时 | `npm install echarts` 报 network error | 代理/网络限制 | 加 `--registry=https://registry.npmmirror.com` |

## 5. 测试覆盖分析

### 5.1 最终计数

60 tests, 60 pass, 0 failures, 1.12s total.

### 5.2 新增覆盖

```
backend/skill/scripts/ta_engine.py → 2 new tests（时间序列字段验证）
  - test_engine_returns_time_series_data
  - test_engine_returns_indicator_series
```

### 5.3 未覆盖区域（已知缺口）

- **KLineChart 组件**：前端图表无自动化测试（ECharts 渲染需要 Canvas/浏览器，puppeteer/playwright 超出当前 scope）
- **图表 resize**：容器尺寸变化时 `chart.resize()` 有效但未验证
- **导出功能**：`downloadReport` 的下载流程在 jsdom 下无法测试（`URL.createObjectURL` 不支持）
- **chart_data 为空时**：HistoryDetailView 的 `fetchChartData` 返回 null 时正确降级但无测试
