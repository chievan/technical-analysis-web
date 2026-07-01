# Issue 01: TDD Sprint — 项目骨架 + 模拟分析流

**Sprint**: 2026-07-01
**Trace ID**: `issue-01-tdd`
**Related**: [PRD](../../prd/PRD.md), [ADR-0001](../../adr/0001-deepseek-agent-tool-calling.md), [ADR-0002](../../adr/0002-sse-streaming-for-agent-visualization.md)

## 1. 本轮成果

本 sprint 完成 Slice 1（Phase 1 核心链路）的全部 6 项交付物：

| 交付物                                                                                   | 状态 | 文件                                        |
| ---------------------------------------------------------------------------------------- | ---- | ------------------------------------------- |
| FastAPI 后端骨架（main/database/models/schemas/config）                                  | ✅   | `backend/`                                  |
| Vue 3 + Vite 前端骨架（router/views/components/composables）                             | ✅   | `frontend/`                                 |
| 5 张数据库表（analyses/analysis_steps/analysis_reports/backtest_results/skill_versions） | ✅   | `backend/models.py`                         |
| SSE 模拟 Agent 分析流（thinking/tool_call/tool_result/report_chunk → done）              | ✅   | `backend/services/analysis_service.py`      |
| Skill 版本自动检测（文件 hash → YYYY-MM-DD.N）                                           | ✅   | `backend/services/skill_version_service.py` |
| sync-skill.sh 同步脚本                                                                   | ✅   | `scripts/sync-skill.sh`                     |

## 2. TDD 循环记录

按 TDD 规范（`/skills/tdd`）的垂直切片方式，分 5 轮 RED→GREEN 实现，而非横向切分。

### 第 1 轮：测试基础设施

| 步骤  | 动作                                                                                          | 结果                                                    |
| ----- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| RED   | 创建 `conftest.py` + `test_skill_version.py`                                                  | 失败 — `ResourceClosedError: This Connection is closed` |
| GREEN | 修复数据库连接 — 改用临时文件 SQLite 而非 `:memory:`                                          | 通过                                                    |
| Learn | `:memory:` SQLite 在不同连接不共享；`connection.begin()` + rollback 与 async streaming 不兼容 |

### 第 2 轮：SSE 分析流

| 步骤  | 动作                                                                | 结果                                               |
| ----- | ------------------------------------------------------------------- | -------------------------------------------------- |
| RED   | `test_analysis_sse.py` — content-type 断言 `== "text/event-stream"` | 失败 — 实际值为 `text/event-stream; charset=utf-8` |
| GREEN | 改为 `startswith("text/event-stream")`                              | 通过                                               |
| Learn | FastAPI 的 StreamingResponse 会自动追加 charset 参数                |

### 第 3 轮：Skill version API

| 步骤  | 动作                                                 | 结果                   |
| ----- | ---------------------------------------------------- | ---------------------- |
| RED   | `test_skill_version.py` — 验证 hash 格式和文件名映射 | 通过（现存实现已正确） |
| GREEN | 无代码修改，实现直接通过                             | 通过                   |

### 第 4 轮：History + Analysis CRUD

| 步骤  | 动作                                                              | 结果     |
| ----- | ----------------------------------------------------------------- | -------- |
| RED   | `test_history.py` (5 tests) + `test_analysis_detail.py` (5 tests) | 全部通过 |
| GREEN | 无代码修改                                                        | 通过     |

### 第 5 轮：ORM 模型

| 步骤  | 动作                                                   | 结果     |
| ----- | ------------------------------------------------------ | -------- |
| RED   | `test_models.py` (9 tests) — CRUD + 关系 + 级联 + 约束 | 全部通过 |
| GREEN | 无代码修改                                             | 通过     |

**最终计数**: 23 tests, 23 pass, 0 failures, 7.6s total (其中 SSE 模拟延迟占 ~7s).

## 3. 测试覆盖分析

### 3.1 覆盖率

```
backend/
├── main.py                          → 通过 TestClient 覆盖全部 6 个 endpoint
├── models.py                        → 5 张表全部有 CRUD 测试
├── services/
│   ├── analysis_service.py          → SSE 事件类型 + done event 验证
│   ├── history_service.py           → 空列表、filter、分页
│   └── skill_version_service.py     → hash 格式、文件映射
├── database.py                      → 通过 conftest 引擎隔离覆盖
└── config.py                        → 隐式覆盖（通过路径依赖）
```

### 3.2 边界覆盖

| 边界                 | 测试                                               | 结果 |
| -------------------- | -------------------------------------------------- | ---- |
| 分析不存在时返回 404 | `test_get_analysis_not_found`                      | ✅   |
| 报告不存在时返回 404 | `test_get_analysis_report_not_found`               | ✅   |
| 无数据时返回空列表   | `test_history_empty_when_no_data`                  | ✅   |
| 重复主键报错         | `test_skill_version_version_is_unique_primary_key` | ✅   |
| 级联删除             | `test_cascade_delete_removes_steps_and_report`     | ✅   |
| 空 symbol 请求 SSE   | 未覆盖（前端已做 `disabled` 防护）                 | ❌   |

### 3.3 未覆盖的区域（已知缺口）

- **SSE 错误路径**：如果 `compute_version` 或 `compute_skill_hash` 抛出异常，streaming 是否优雅降级？—— 当前实现未处理。
- **SSE 空 symbol**：`symbol=""` 会出现空字符串 analysis 记录（前端已禁用按钮，后端未做验证）。
- **SSE 断开重连**：前端 `EventSource` 自动重连行为未测试。
- **Performance**：SSE 模拟延迟 0.3s/step 是硬编码的，不适合性能测试。

## 4. 关键决策

### 4.1 测试数据库策略

- **初始方案**：`sqlite:///:memory:` 配合 `connection.begin()` + rollback 实现测试隔离
- **问题**：async streaming response 的数据库操作在独立协程中执行，绑定连接在 yield 后被关闭
- **终案**：临时文件 SQLite + `autouse` fixture `create_tables`/`drop_all`
- **Trade-off**：每个测试重建成表（~50ms），但避免了连接生命周期问题

### 4.2 Endpoint 路由顺序

- **问题**：`/api/v1/analysis/history` 被参数化路由 `/{analysis_id}` 捕获
- **解决**：将 history 路由声明在 `/{analysis_id}` 之前
- **FastAPI 行为**：路由按注册顺序匹配，非 RESTful 的静态前缀路由需提前注册

### 4.3 SQLAlchemy `metadata` 保留字

- **问题**：`AnalysisStep.metadata` 与 SQLAlchemy 的 `DeclarativeMeta.metadata` 冲突
- **解决**：重命名为 `extra`
- **影响**：DB schema 中该字段名为 `extra`，与 PRD 的 `metadata` 不同

## 5. 后续建议

- **添加 SSE 错误处理测试**：用 mock 让 `compute_version` 抛出异常，验证 streaming 返回 error 事件并标记分析为 failed
- **添加 symbol 验证**：后端应当拒绝空 symbol（返回 422），而非创建一条无效记录
- **补上 `sse-starlette`**：当前 SSE 直接使用 `StreamingResponse` + 手工 `data: {json}\n\n`，后续可改用 `sse-starlette` 的 `EventSourceResponse` 以获得更规范的 SSE 支持
- **重建 temp DB 清理**：`conftest.py` 中的 `_db_fd`/`_db_path` 在进程退出时未清理（当前用 `rm -f /tmp/*.test.db` 手动清理）
