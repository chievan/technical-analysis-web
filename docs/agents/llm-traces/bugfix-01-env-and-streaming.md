# Bugfix 01: 环境配置 & SSE 流式输出修复

**Date**: 2026-07-01
**Trace ID**: `bugfix-01-env-and-streaming`
**Trigger**: 点击"开始分析"后出现 `DEEPSEEK_API_KEY not configured` 错误；修复后出现逐字换行渲染

## 1. 问题清单

| #   | 问题                                               | 影响                                | 根因                                                                                                         |
| --- | -------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| 1   | `DEEPSEEK_API_KEY not configured`                  | 分析无法启动                        | `config.py` 用 `os.getenv()` 但未调用 `load_dotenv()`，虽安装了 `python-dotenv` 但从未执行                   |
| 2   | `UNIQUE constraint failed: skill_versions.version` | 分析卡在"分析中..."，SSE 无任何输出 | `compute_version()` 每次分析都创建新版本记录，版本号 `.N` 按字符串排序（`.9` > `.10`），重复创建已存在的版本 |
| 3   | Agent 思考内容逐字渲染，每个字一行                 | 用户看到大量 `💭 思考` 标签刷屏     | DeepSeek API 逐字流式返回，前端将每个字符作为独立 SSE event 渲染                                             |

## 2. 修复详情

### 2.1 环境变量加载

**文件**: `backend/config.py`

- 新增 `from dotenv import load_dotenv`
- 调用 `load_dotenv(BASE_DIR / ".env")` 在读取环境变量前加载 `.env` 文件
- 同时创建 `.env.example` 作为配置模板

### 2.2 Skill 版本号冲突

**文件**: `backend/services/skill_version_service.py`

旧逻辑存在两个问题：

1. **每次创建新版本**: 即使 skill 文件未变，每次分析都 INSERT 一条新版本记录，数据库迅速膨胀
2. **字符串排序缺陷**: `ORDER BY version DESC` 按字符串排序，`.9` 被判定大于 `.10`，导致 `.10` 被反复尝试创建

修复方案：

- 新增 hash 匹配：先查询 `files_hash` 是否已有匹配记录，有则直接复用
- 修复版本号取最大值逻辑：查询当天所有版本记录，逐一比较数字后缀而非依赖 SQL 排序

### 2.3 SSE 逐字渲染

**文件**: `frontend/src/components/AgentStream.vue`

- 新增 `groupedEvents` computed 属性，合并连续的同类型 event（重点处理 `thinking` 类型）
- 连续的 thinking event 内容累加为一段完整文本，共享一个标签

## 3. 变更文件

| 文件                                        | 操作 | 说明                                   |
| ------------------------------------------- | ---- | -------------------------------------- |
| `backend/config.py`                         | 修改 | 新增 `load_dotenv()`                   |
| `.env.example`                              | 新增 | 环境变量模板                           |
| `backend/services/skill_version_service.py` | 修改 | 修复版本号冲突（hash 复用 + 数字排序） |
| `frontend/src/components/AgentStream.vue`   | 修改 | 合并连续 thinking 事件                 |
| `this file`                                 | 新增 | Bugfix 记录                            |

## 4. 验证

- 全量 73 个后端测试通过
- 手动 curl SSE 端点确认流式输出正常（`curl ...analysis/start?symbol=600519`）
- 前端热更新后确认 thinking 内容连续渲染

## 5. 后续预防

- 环境变量类问题：新增项目需一步到位加载 `.env`
- 版本号依赖字符串比较：未来可改为 `YYYY-MM-DD-NN` 格式（固定宽度）
- 流式渲染需前端做缓冲合并，不能假设每个 SSE event 是完整语义单元
