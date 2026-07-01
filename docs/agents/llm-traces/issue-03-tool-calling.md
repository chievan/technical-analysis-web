# Issue 03: Tool Calling 引擎集成

**Sprint**: 2026-07-01
**Trace ID**: `issue-03-tool-calling`
**Related**: [PRD](../../prd/PRD.md), [ADR-0001](../../adr/0001-deepseek-agent-tool-calling.md), [ADR-0002](../../adr/0002-sse-streaming-for-agent-visualization.md)

## 1. 本轮成果

本 sprint 完成 Slice 3（Tool Calling 引擎集成）的全部交付物：

| 交付物                                                     | 状态 | 文件                                       |
| ---------------------------------------------------------- | ---- | ------------------------------------------ |
| Tool definitions（OpenAI-compatible，供 DeepSeek API）     | ✅   | `backend/agent/tool_definitions.py`        |
| 引擎执行器（run_ta_engine / read_reference）               | ✅   | `backend/tools/engine_runner.py`           |
| 模拟 ta_engine.py（随机漫步 + 120 日技术指标）             | ✅   | `backend/skill/scripts/ta_engine.py`       |
| 流式 tool_call delta 累积 + 多轮 conversation loop         | ✅   | `backend/agent/agent_service.py`           |
| SSE tool_call/tool_result/chart_data 事件持久化            | ✅   | `backend/services/analysis_service.py`     |
| 前端 AgentStream 组件 tool_call/tool_result 中文展示       | ✅   | `frontend/src/components/AgentStream.vue`  |
| ReportViewer markdown 渲染（marked 库）                    | ✅   | `frontend/src/components/ReportViewer.vue` |
| 21 项 TDD 测试（tool defs / engine / agent / integration） | ✅   | `backend/tests/test_tool_calling.py`       |

## 2. 实现过程

按 TDD 规范分阶段实现，非横向切分。

### 阶段 1：Tool definitions + engine runner

| 步骤  | 动作                                                                  | 结果 |
| ----- | --------------------------------------------------------------------- | ---- |
| RED   | `test_tool_definitions` (5 tests) — 验证 tool 结构的 OpenAI 合规性    | 通过 |
| GREEN | 创建 `backend/agent/tool_definitions.py` — `TOOLS` + `get_tool_names` | 通过 |
| RED   | `test_run_ta_engine` (3 tests) — 验证引擎返回结构化数据和子进程调用   | 通过 |
| GREEN | 创建 `backend/tools/engine_runner.py` — subprocess + JSON 解析        | 通过 |
| RED   | `test_run_ta_engine_subprocess` — 直接验证子进程调用路径              | 通过 |
| GREEN | 创建 `backend/skill/scripts/ta_engine.py` — 随机漫步 + 技术指标       | 通过 |

### 阶段 2：Agent tool calling flow（核心）

| 步骤  | 动作                                                                                       | 结果                                               |
| ----- | ------------------------------------------------------------------------------------------ | -------------------------------------------------- |
| RED   | `test_direct_report_without_tool_calls` — 验证无 tool 调用时的正常流                       | 失败 — `TypeError` mock client 不支持 `async with` |
| GREEN | 修复 mock：改用 `AsyncMock` 替代 `MagicMock`，`__aenter__` 返回 `AsyncMock`                | 通过                                               |
| RED   | `test_tool_call_triggers_execution_and_continues` — 验证 tool_call → 执行 → 继续循环       | 失败 — call_count 索引偏移                         |
| GREEN | 修复 mock：`capture idx = call_count[0]` 先捕获再递增                                      | 通过                                               |
| RED   | `test_parallel_tool_calls` — 验证并行多工具调用                                            | 通过                                               |
| RED   | `test_without_api_key_returns_error` — 验证空 API Key 时返回 error 事件                    | 通过                                               |
| GREEN | 重构 `agent_service.py`：提取 `_call_and_stream()`，新增多轮循环、tool_call 累积、结果回填 | 通过                                               |

### 阶段 3：SSE 持久化 + 集成

| 步骤  | 动作                                                                                          | 结果                                 |
| ----- | --------------------------------------------------------------------------------------------- | ------------------------------------ |
| RED   | `test_analysis_sse_with_tool_events` — SSE 流中包含 tool_call/tool_result                     | 失败 — mock stream 不产生 chart_data |
| GREEN | `agent_service.py` 在 engine 执行后 emit `chart_data` 事件                                    | 通过                                 |
| RED   | `test_tool_events_saved_to_db` — tool_call/tool_result 写入 AnalysisStep                      | 失败 — 无 `chart_data` 事件          |
| GREEN | `analysis_service.py` 添加 `chart_data` accumulator + `_save_report` 接收                     | 通过                                 |
| RED   | `test_report_with_chart_data_from_engine` — report 包含 chart_data                            | 失败 — content double-count bug      |
| GREEN | 修复 `report_complete` handler：移除 `full_content += content` (内容已通过 thinking 事件累积) | 通过                                 |

### 阶段 4：前端展示

| 步骤  | 动作                                                                   | 结果 |
| ----- | ---------------------------------------------------------------------- | ---- |
| RED   | AgentStream 显示 tool_call/tool_result 时使用中文标签和样式区分        | 通过 |
| GREEN | `displayContent()` 函数 + CSS 样式（蓝边 tool_call、绿边 tool_result） | 通过 |
| GREEN | ReportViewer：`marked()` 渲染 markdown（h1/th/ul/ol/code/blockquote）  | 通过 |

**最终计数**: 21 tests, 21 pass, 0 failures.

## 3. 关键决策

### 3.1 Native tool calling (vs LangChain)

- **方案**：FastAPI 直接管理 conversation loop，不使用 LangChain
- **理由**：减少依赖，完全控制 SSE 事件流格式
- **Trade-off**：需要自行实现 tool_call delta 累积（DeepSeek 返回流式的 tool_calls，按 index 分片到达），但避免了 LangChain 的 callback 复杂度

### 3.2 Tool definitions 放在 agent 包而非 tools 包

- **结构**：`backend/agent/tool_definitions.py`（定义）和 `backend/tools/engine_runner.py`（执行）分离
- **理由**：tool definitions 是 agent API 契约的一部分（DeepSeek API 格式），engine_runner 是纯执行逻辑
- **影响**：`agent_service.py` 引入 `EXECUTOR_MAP` 做运行时绑定

### 3.3 并行 tool call 处理策略

- **方案**：串行执行并行工具调用（非并发）
- **理由**：当前工具无外部 I/O 竞争（引擎耗时 <100ms），串行简化结果顺序保证
- **影响**：如果后续引入网络 I/O 工具（如实时行情 API），需改为 asyncio.gather

### 3.4 chart_data 独立事件

- **设计**：`run_ta_engine` 执行后额外 emit `chart_data` 事件（区别于 tool_result 的 summary 文本）
- **理由**：前端图表渲染需要结构化 JSON（K 线、均线、MACD），与 tool_result 的文本摘要分离
- **影响**：`analysis_service.py` 需额外 accumulator 和 DB 写入路径

### 3.5 Mock 策略

- **方案**：自制 mock streaming client（`_make_streaming_client`），不 mock httpx 全量
- **理由**：测试需要多轮 turn 的流式响应控制，第三方 mock 库难以表达 `[turn1_lines, turn2_lines]` 的多轮交互
- **影响**：mock 代码 ~50 行，但测试可读性高

## 4. 修复的 Bug

| Bug                          | 症状                                                                                           | 根因                                                               | 修复                                |
| ---------------------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------- |
| AsyncMock 兼容性             | `TypeError: 'async with' received an object from __aenter__ that does not implement __await__` | `MagicMock` 的 `__aenter__` 返回普通对象                           | 改用 `AsyncMock`                    |
| Call count 索引偏移          | 多轮测试中取错 lines 集合                                                                      | `call_count[0]` 在 `stream()` 中后递增导致索引错位                 | 在增量前捕获 `idx = call_count[0]`  |
| 空 assistant 消息            | 旧 assert `len(messages) == 2` 失败变成 3                                                      | 新 loop 对空 turn 也 append assistant 消息                         | 加 `if content or tool_calls:` 守卫 |
| Content 重复计算             | 报告内容翻倍                                                                                   | `report_complete` handler 重复拼接已由 thinking 事件累积的 content | 移除重复拼接                        |
| chart_data 缺失              | 报告无图表数据                                                                                 | `_save_report` 未接收 chart_data 参数                              | 添加 chart_data 参数 + SSE 事件     |
| `_summarize_result` 类型错误 | `"error" in result` 对字符串做子串搜索                                                         | 函数签名声明 `dict` 但 `read_reference` 返回 `str`                 | 改为 `dict                          | str`+`isinstance` 守卫 |

## 5. 架构改进

### `_call_and_stream()` 提取

```
Before：stream_analysis() 直接调用 httpx，所有逻辑混合
After:
  _call_and_stream() — 单次 API 调用，处理 delta 累积，产生 turn_complete
  stream_analysis()  — 多轮循环，调用 _call_and_stream()，处理 tool 执行
```

分离后职责清晰：_call_and_stream 负责"与 API 的一次对话"，stream_analysis 负责"完整的多轮分析任务"。

### tool_call delta 累积算法

```python
tool_calls_acc: dict[int, dict] = {}
# 按 index 分片到达，需要跨 chunk 累积
for tcd in tool_call_deltas:
    idx = tcd.get("index", 0)
    if idx not in tool_calls_acc:
        tool_calls_acc[idx] = {"id": "", "function": {"name": "", "arguments": ""}}
    # 每个字段可能分多次 chunk 到达，需要 += 拼接
    if func.get("name"):      acc["function"]["name"] += func["name"]
    if func.get("arguments"): acc["function"]["arguments"] += func["arguments"]
```

## 6. 后续建议

- **tool_call 超时**：当前 engine runner 无超时保护，`subprocess.run(timeout=30)` 仅测试用了。应在 `EXECUTOR_MAP` 层加通用超时
- **Engine 重试**：如果 ta_engine.py 执行失败，当前直接返回 error。可考虑重试 1 次（随机漫步引擎偶尔受系统负载影响）
- **TypeScript 类型更新**：`SSEEventType` 缺少 `chart_data` 和 `report_complete` 类型（当前用 string 宽声明）。应补全
- **ReportViewer 错误状态**：报告内容为空时显示 "暂无分析结果"，而非空白页
- **deepseek-reasoner 退化路径**：当前 reasoner 无 tool calling 能力，但后续若 DeepSeek API 支持则需启用
