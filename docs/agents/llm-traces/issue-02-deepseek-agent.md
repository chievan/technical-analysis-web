# Issue 02: 真实 DeepSeek Agent 接入

**Sprint**: 2026-07-01
**Trace ID**: `issue-02-deepseek-agent`
**Related**: [PRD](../../prd/PRD.md), [ADR-0001](../../adr/0001-deepseek-agent-tool-calling.md), [ADR-0002](../../adr/0002-sse-streaming-for-agent-visualization.md), [Issue-01](./issue-01-tdd-sprint.md)

## 1. 本轮成果

本 sprint 完成 Slice 2 的全部 5 项 AC，将模拟 Agent 替换为真实 DeepSeek API 调用：

| 交付物                                                     | 状态 | 文件                                   |
| ---------------------------------------------------------- | ---- | -------------------------------------- |
| `agent_service.py` DeepSeek API 客户端，Flash/Pro 模型切换 | ✅   | `backend/agent/agent_service.py`       |
| SKILL.md 作为 system prompt                                | ✅   | `backend/skill/SKILL.md`               |
| Agent 推理内容通过 SSE 实时 streaming                      | ✅   | `backend/agent/agent_service.py`       |
| 模型切换在前端生效                                         | ✅   | `frontend/src/views/AnalysisView.vue`  |
| Agent 输出存入 analysis_steps 和 analysis_reports          | ✅   | `backend/services/analysis_service.py` |

### 1.1 架构总览

```
前端 (Vue 3)
  │  GET /api/v1/analysis/start?symbol=600519&model=deepseek-chat
  ▼
FastAPI → analysis_service.start_analysis()
  │
  ├─ 创建 Analysis 记录 (SQLite)
  ├─ async for event in agent_service.stream_analysis(symbol, model)
  │   │
  │   ├─ httpx POST https://api.deepseek.com/chat/completions
  │   │   ├─ headers: Authorization=Bearer {key}
  │   │   ├─ json: {model, messages: [system(SKILL.md), user], stream:true}
  │   │   └─ SSE stream → data: {"choices":[{"delta":{"content":"..."}}]}
  │   │
  │   ├─ thinking events → AnalysisStep 入库 + SSE → 前端 AgentStream
  │   ├─ report_chunk events (reasoner only) → SSE → 前端 AgentStream
  │   └─ report_complete → AnalysisReport 入库 + SSE done event
  │
  └─ SSE streaming → 前端 useSSE composable → AgentStream/ReportViewer
```

## 2. TDD 循环记录

### 第 1 轮：agent_service 单元测试

| 步骤  | 动作                                                                                                                                                                                                                                                               | 结果                                    |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| RED   | `test_agent_service.py` — 模型映射、system prompt 读取                                                                                                                                                                                                             | 通过（纯函数无需 mock）                 |
| GREEN | 无改动                                                                                                                                                                                                                                                             | 通过                                    |
| RED   | `test_returns_error_when_no_api_key`                                                                                                                                                                                                                               | 通过                                    |
| GREEN | 无改动                                                                                                                                                                                                                                                             | —                                       |
| RED   | `test_streams_thinking_events_for_chat` — mock httpx streaming                                                                                                                                                                                                     | **失败** — `AttributeError: __aenter__` |
| GREEN | 改用真实 async context manager 类（`MockClientCM`/`MockStreamCM`）替代 `AsyncMock` 链                                                                                                                                                                              | 通过                                    |
| Learn | httpx.AsyncClient 多层 async context manager（`async with client:` → `client.stream()` → `async with stream:` → `response.aiter_lines()`）在 `AsyncMock` 链下 `__aenter__` 行为不可预测。最佳 mock 策略是自定义 async context manager 类，每个只实现需要的协议方法 |

### 第 2 轮：analysis_service SSE 集成测试

| 步骤  | 动作                                                                                                                                   | 结果                                        |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| RED   | `test_analysis_sse.py` — 更新为 mock agent_stream 而非 mock 数据                                                                       | **失败** — 2 个 done event                  |
| GREEN | 添加 `report_saved` 防重旗，避免 `report_complete` 和 post-loop fallback 双重触发                                                      | 通过                                        |
| RED   | `test_analysis_sse_report_saved_to_db` — 断言 `综合评分` in report                                                                     | 失败 — mock 的 thinking 事件不含 "综合评分" |
| GREEN | 扩展 mock 的 thinking 事件包含评分内容                                                                                                 | 通过                                        |
| Learn | async generator 的 loop-exit 边界需显式追踪（`report_saved`、`error_occurred`），避免 post-loop fallback 与 loop-internal handler 重复 |

### 第 3 轮：agent_service 边界测试

| 步骤  | 动作                                                                                                         | 结果                                                                |
| ----- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------- |
| RED   | `test_handles_http_401_error`                                                                                | **失败** — `try/except` 未包裹外层 `async with httpx.AsyncClient()` |
| GREEN | 将 `try` 范围扩大到覆盖整个 client 生命周期                                                                  | 通过                                                                |
| RED   | `test_handles_connection_error`                                                                              | 通过                                                                |
| RED   | `test_calls_api_with_correct_url_and_model`                                                                  | **失败** — `aiter_lines` 用了同步 `iter([])`                        |
| GREEN | 改用 `async def _empty_lines(): return/yield` (async generator)                                              | 通过                                                                |
| Learn | `httpx.Response.aiter_lines()` 是 async generator method，mock 必须用 `async def` + `yield`，不能用 `lambda` |

## 3. 设计与实现的坑

### 3.1 双重 done event

```
mock agent yields:
  thinking("正在分析...")
  thinking("均线系统多头排列...")
  report_complete("## 报告\n\n评分：+1")

analysis_service loop 内:
  report_complete → _save_report() + yield done_event + report_saved=True

loop 结束后:
  if not error_occurred and not report_saved and full_content:
                        ↑ report_saved=True，不触发 ✅
```

### 3.2 httpx mock 的 async context manager 陷阱

```
预期链:
  httpx.AsyncClient(timeout=120.0) → client
  client.stream("POST", url, headers=..., json=...) → stream_cm
  async with stream_cm → response
  response.aiter_lines() → async generator

AsyncMock 问题:
  AsyncMock().__aenter__ → 返回自身（而非指定对象）
  AsyncMock().stream() → 返回 coroutine（而非 context manager）

解决: 手写 3 个 context manager 类
  MockClientCM（async __aenter__/__aexit__ + stream method）
  MockStreamCM（async __aenter__/__aexit__）
  mock_response（aiter_lines = async generator function）
```

### 3.3 deepseek-chat vs deepseek-reasoner 的 delta 差异

```
deepseek-chat:
  delta: {"content": "正在分析..."}       ← 全部走 content

deepseek-reasoner:
  delta: {"reasoning_content": "思考中..."}  ← 推理过程
  delta: {"content": "最终报告"}            ← 最终输出

策略:
  content + reasoning_content 同时存在时，分别 yield
  deepseek-chat → thinking 事件（同时作为 steps 和 report 来源）
  deepseek-reasoner → thinking（reasoning）→ report_chunk（final answer）
```

## 4. Review 发现与修复

根据 `/review` 技能的双轴审核结果：

### Standards 轴

| 问题                                      | 严重度 | 修复                                        |
| ----------------------------------------- | ------ | ------------------------------------------- |
| `import uuid` 在函数体内                  | 违规   | 移至模块顶层                                |
| CSS `.step-error` 非 BEM 修饰符           | 违规   | 改为 `.step--error .step-content`           |
| 测试用 class 而非函数（vs Slice 1 惯例）  | 判断   | 保留（pytest 两者均支持，且有语义分组需求） |
| `_empty_lines()` 的 `return/yield` 死代码 | 判断   | 保留（Python 模式：定义空 async generator） |

### Spec 轴

| 问题                                                  | 判定     | 结论                                                    |
| ----------------------------------------------------- | -------- | ------------------------------------------------------- |
| deepseek-chat 内容在 AgentStream 和 ReportViewer 重复 | 设计意图 | 此 slice 无 tool calling，推理即报告，下 slice 自动解决 |
| streaming 逐字符存为 step 导致 steps 表膨胀           | 设计意图 | 保持原始粒度，后续可加聚合逻辑                          |

## 5. 测试覆盖分析

### 5.1 最终计数

37 tests, 37 pass, 0 failures, 0.52s total（mock httpx，无网络请求）。

### 5.2 新增覆盖

```
backend/agent/
  ├── agent_service.py          → 11 tests（模型映射/system prompt/streaming/error/API call）
  └── __init__.py               → implicit

backend/services/
  └── analysis_service.py       → SSE 集成 5 tests（事件类型/DB 持久化/model 传递）
```

### 5.3 边界覆盖

| 边界                                     | 测试                                                 | 结果      |
| ---------------------------------------- | ---------------------------------------------------- | --------- |
| DEEPSEEK_API_KEY 为空                    | `test_returns_error_when_no_api_key`                 | ✅        |
| API 返回 401                             | `test_handles_http_401_error`                        | ✅        |
| 连接被拒绝                               | `test_handles_connection_error`                      | ✅        |
| 不明模型名 → 默认 deepseek-chat          | `test_unknown_model_defaults_to_chat`                | ✅        |
| reasoner 的 reasoning_content → thinking | `test_streams_reasoning_and_report_for_reasoner`     | ✅        |
| model 参数穿透                           | `test_analysis_sse_passes_model_parameter`           | ✅        |
| Agent 输出持久化到 report                | `test_analysis_sse_report_saved_to_db`               | ✅        |
| Agent 无输出（空 response）              | `start_analysis` post-loop `not full_content` branch | ❌ 未覆盖 |

### 5.4 未覆盖的区域（已知缺口）

- **空 response**：如果 DeepSeek 返回空 stream（`full_content = ""`），analysis 标记为 failed，但无端到端测试
- **网络超时**：`httpx.AsyncClient(timeout=120.0)` 的超时行为未测试
- **错误恢复**：streaming 中途断连后，已保存的 steps 如何处理？当前写多少算多少
- **前端 error 事件 UI**：AgentStream 渲染了 error 样式，但 AnalysisView 未在 error 时禁用"开始分析"按钮

## 6. 后续建议

- **Slice 3 tool calling**：`agent_service.py` 预留了 `tool_call`/`tool_result` 事件类型和 `run_ta_engine`/`read_reference` 工具定义，整合后 deepseek-chat 的 thinking/report 自然分离
- **`.env.example`**：将 `DEEPSEEK_API_KEY` 的配置方式文档化
- **agent_service 重试**：DeepSeek API 偶发 502，建议加 `tenacity` 重试（仅限 `GET` 类场景，streaming 重试需谨慎）
- **前端连接状态**：SSE 断线时前端应显示 reconnecting 状态
