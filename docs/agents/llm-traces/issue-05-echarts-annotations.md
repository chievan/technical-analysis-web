# Issue 05: 交互图表支撑/阻力位标注

**Sprint**: 2026-07-01
**Trace ID**: `issue-05-echarts-annotations`
**Related**: [PRD](../../prd/PRD.md), #5, [issue-04](./issue-04-echarts-charts.md)

## 1. 本轮成果

本 sprint 在已有 ECharts K 线图表基础上，新增支撑位/阻力位标注功能：

| 交付物                                                | 状态 | 文件                                     |
| ----------------------------------------------------- | ---- | ---------------------------------------- |
| ChartData 类型新增 support_levels / resistance_levels | ✅   | `frontend/src/types/index.ts`            |
| KLineChart 支撑/阻力位 markLine 渲染                  | ✅   | `frontend/src/components/KLineChart.vue` |

## 2. 实现过程

### 数据来源

引擎 `ta_engine.py` 已输出 `support_levels` 和 `resistance_levels`（各 2 个值，基于最近 10/20 个周期的最高/最低价），只需在前端消费。

### KLineChart markLine

在 Candlestick series 中添加 `markLine`，动态遍历 `support_levels`/`resistance_levels` 数组：

- 支撑位：绿色虚线（`#26a69a`），标签 `支撑 {value}`
- 阻力位：红色虚线（`#ef5350`），标签 `阻力 {value}`
- `silent: true` 避免干扰鼠标交互
- `symbol: "none"` 隐藏端点标记

## 3. 关键决策

### 3.1 markLine vs markArea

- **方案**：markLine（水平虚线）
- **理由**：支撑/阻力是具体价位，不是区间；markLine 语义更准确
- **影响**：视觉简洁，与 RSI 超买超卖线风格一致

### 3.2 数据空安全

- ChartData 中 `support_levels`/`resistance_levels` 声明为可选（`?`）
- markLine data 通过 `|| []` 回退，引擎未输出时不渲染

## 4. 测试覆盖分析

无新增测试（纯前端 ECharts markLine 渲染，需浏览器环境）。
