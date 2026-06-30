# ADR-0002: SSE Streaming for Agent Visualization

**Status**: Accepted  
**Date**: 2026-06-30

## Context

前端需要实时展示 DeepSeek Agent 的完整执行过程（思考文本、tool call 状态、报告片段）。有两种实时通信方案：

1. **WebSocket** — 全双工通信，双向推送，需 ws:// 协议和额外的依赖
2. **SSE (Server-Sent Events)** — 单向服务器推送，基于 HTTP 协议，浏览器原生支持 EventSource API

## Decision

采用 **SSE** 作为实时通信协议。

## Rationale

- **单向通信已足够**：数据流只有 后端 → 前端 方向，前端不需要向已建立的流发送数据（新请求通过独立 HTTP API 发出）
- **浏览器原生支持**：`EventSource` API 无需额外库，自带自动重连
- **兼容 FastAPI SSE**：`sse-starlette` 库成熟稳定，与 FastAPI 异步机制配合良好
- **协议简单**：纯文本格式，调试方便，没有 WebSocket 的握手和帧解析开销
- **一个人用，无并发瓶颈**：SSE 的单连接限制（HTTP/1.1 下浏览器限制 6 个并发连接）不是问题

## Consequences

- 如果未来需要前端向后端主动推送数据（如"取消分析"），需要通过单独的 HTTP API 实现，不能复用 SSE 通道
- 如果在大并发场景下使用，需要考虑 HTTP/2 或迁移到 WebSocket
