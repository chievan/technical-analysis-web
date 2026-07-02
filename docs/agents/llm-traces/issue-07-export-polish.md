# Issue 07: 导出 + 完善

**Sprint**: 2026-07-01
**Trace ID**: `issue-07-export-polish`
**Related**: #7, [issue-06](./issue-06-backtest.md)

## 1. 本轮成果

收尾阶段：报告导出（HTML/Markdown）、Skill 版本历史页增强、SSE 容错补全。

| 交付物                                            | 状态 | 文件                                       |
| ------------------------------------------------- | ---- | ------------------------------------------ |
| AnalysisView 主分析页导出按钮 (MD/HTML)           | ✅   | `frontend/src/views/AnalysisView.vue`      |
| GET /api/v1/skill/versions/{version} 版本详情端点 | ✅   | `backend/main.py`                          |
| 版本列表返回 files_count                          | ✅   | `backend/main.py`                          |
| SkillVersionsView 可展开文件清单 (文件名+哈希)    | ✅   | `frontend/src/views/SkillVersionsView.vue` |
| SSE 僵死连接检测 (120s 无事件超时)                | ✅   | `frontend/src/composables/useSSE.ts`       |
| HistoryDetailView 加载错误状态 + 返回导航         | ✅   | `frontend/src/views/HistoryDetailView.vue` |
| 版本详情 API 测试 (4 tests)                       | ✅   | `backend/tests/test_skill_version.py`      |

## 2. 实现过程

### 报告导出

- `AnalysisView.vue` 新增导出按钮区域，复用已有的 `downloadReport()` composable
- 按钮在 `finalReport` 可用时显示，支持 "导出 Markdown" 和 "导出 HTML" 两种格式
- `downloadReport()` 内部调用 `fetchReport()` 获取完整内容，通过 Blob 触发浏览器下载

### Skill 版本历史增强

- 后端 `GET /api/v1/skill/versions` 列表增加 `files_count` 字段
- 新增 `GET /api/v1/skill/versions/{version}` 端点，返回完整文件列表（文件名 → SHA256 哈希）
- 前端 `SkillVersionsView.vue` 从纯列表升级为可展开卡片：
  - 每张卡片显示版本号、创建时间、文件数
  - 点击展开，异步加载文件清单（文件名 + 哈希值）
  - 展开了加框高亮、加载态、交替行色

### SSE 容错

- 新增僵死检测：120 秒内未收到任何 SSE 事件则判定为超时，断开连接并显示友好提示
- `resetStallTimer` 在 `onmessage` 每次收到事件时重置
- `clearStallTimer` 在 `onerror`、`disconnect` 时清理，避免悬挂定时器

### 错误处理

- `HistoryDetailView.vue` 原本的 `catch {}` 升级为 `catch (e)`，设置 `loadError` ref
- 模板新增 `v-else-if="loadError"` 分支，展示错误横幅 + "返回历史" 导航
- 样式沿用 AnalysisView 的 `error-banner` 模式（白底红框 + 对比色）

## 3. 关键决策

### 3.1 文件变更存储格式

- **方案**：沿用现有 `str(files_hash)` Python dict repr 格式（如 `"{'file.py': 'abc123'}"`），后端使用 `ast.literal_eval` 安全解析
- **理由**：不破坏已有数据向前兼容；`ast.literal_eval` 相比 `eval` 安全，只解析字面量
- **tradeoff**：存储格式不是标准 JSON，但现有 6 个版本都使用此格式，迁移成本高

### 3.2 版本详情数据加载方式

- **方案**：列表只返回 `files_count`（轻量），详情通过独立 API 按需加载（展开时调用）
- **理由**：文件清单可能较大（每个版本含 SKILL.md + 引用 + 脚本），预加载到列表中会使首屏变慢
- **影响**：展开时需要额外网络请求，但带来了毫秒级延迟可接受

### 3.3 SSE 超时策略

- **方案**：120 秒全局无事件超时（非单次请求超时，非心跳间隔）
- **理由**：DeepSeek API 响应时间不确定（可能长思考），单次超时会误伤正常分析；无事件超时只检测完全僵死的连接
- **tradeoff**：分析确实慢但仍有零星事件时不会触发；心跳检测更精确但增加了复杂度

## 4. Review 发现 & 修正

从 review 中发现并修复了以下问题：

| 问题                                               | 修复                                               |
| -------------------------------------------------- | -------------------------------------------------- |
| 版本列表 `ast.literal_eval` 缺少 try/except        | 抽取 `_safe_files_count` 函数，统一捕获 ValueError |
| SkillVersionsView 多余的 `computed` import + `idx` | 删除未使用的导入和变量                             |
| AnalysisView 导出区域多余 `v-if="finalReport"`     | 外部 section 已守卫，移除内部重复条件判断          |

## 5. 测试覆盖分析

全量：**73 tests**（+4 新增，+2 修正，无回归）

| 测试文件                | 数量 | 内容                                                      |
| ----------------------- | ---- | --------------------------------------------------------- |
| `test_skill_version.py` | 5    | 哈希返回、文件名包含、列表 files_count、详情返回文件、404 |
| 其他 (existing)         | 68   | 无回归                                                    |
