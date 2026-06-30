# ADR-0001: DeepSeek Agent with Native Tool Calling

**Status**: Accepted  
**Date**: 2026-06-30

## Context

Web 应用需要调用 DeepSeek API 来执行 `technical-analysis-pro` skill 的完整分析流程。这里有两种做法：

1. **使用 Agent 框架**（LangChain / CrewAI / Semantic Kernel）— 框架负责管理 tool call、上下文、memory
2. **原生 Tool Calling** — 直接调用 DeepSeek API 的 tool calling 能力，FastAPI 自行管理 tool 执行和会话状态

## Decision

采用方案 2：**原生 Tool Calling**，FastAPI 直接管理 DeepSeek 会话。

## Rationale

- **单人系统，无复杂 Agent 需求**：不需要多 Agent 协作、记忆持久化、RAG 等框架提供的复杂功能
- **streaming 控制精准**：原生 API 的 SSE streaming 可以直接透传到前端，框架往往会封装或延迟 streaming
- **简化部署和依赖**：减少一个大型依赖和其兼容性问题
- **Skill 流程固定**：SKILL.md 已经定义了线性步骤，不需要框架的动态规划能力
- **日后可升级**：当项目规模增长、需要多 Agent 协作时，再引入 LangChain 也是将原生 tool call 迁移到框架，没有技术债

## Consequences

- 需要自行管理 tool call 的上下文（每次 tool call 后将结果注入消息历史）
- 需要自行处理 API 错误重试和超时
- 未来如果需要复杂 Agent 编排，需要重构 Agent 层
