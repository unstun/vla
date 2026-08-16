---
name: memory-retrieval
version: 5.0.0-codex
description: |-
  按需记忆检索。AI 判断需要项目历史上下文时主动调用，不自动触发。
  调用时将具体查询意图作为 args 传入，读取 bigmemory/ 与 .pipeline/ 的相关状态；Codex 子代理仅作为可选加速。
argument-hint: "[具体查询意图 — 针对当前问题的定向 query]"
user-invocable: true
---

# memory-retrieval

由 AGENTS.md 的项目状态与证据规则指引。AI 判断需要项目历史上下文时
**主动调用**，不做会话开头的无条件触发。

## 执行方式

Codex 主会话按以下顺序执行。

### 1. 本地检索（默认）

始终先读取热区三份文件：

```text
bigmemory/热区/状态简报.md
bigmemory/热区/未关闭决策.md
bigmemory/热区/近期改动.md
```

如果当前工具栏已经提供 Auggie MCP，先用它在 `bigmemory/` 与 `.pipeline/` 中按查询意图做语义检索。当前 Codex App 入口通常是 `mcp__auggie.codebase_retrieval`；MCP server 名为 `auggie`；`codebase-retrieval` 仅作为能力名或 Claude/Cursor 旧写法出现。实际入口以当前工具栏和 `codex mcp get auggie` 为准。

Auggie MCP 不可用、报错或返回内容不足时，从查询意图中抽取 2-6 个关键词，然后在冷区、`.pipeline/` 和 Trellis 任务记录中检索：

```bash
rg -n --smart-case "<关键词>" bigmemory/冷区 .pipeline .trellis/tasks \
  --glob '*.md' --glob '*.yaml' --glob '*.yml' --glob '*.json'
```

只打开与查询意图最相关的文件或片段。询问“目前/上次/进度/做到哪里”时，额外查看：

```bash
git status --short
git log --oneline -5
find .trellis/tasks -maxdepth 2 -name task.json -print
```

### 2. 子代理（可选）

只有当前工具栏已经提供子代理接口，且工具规则允许委派时，才使用子代理。Codex 环境禁止使用 Claude 专用的 `Agent({...})` 写法。

Codex 子代理调用形状：

```json
{
  "agent_type": "memory-retriever",
  "fork_context": false,
  "message": "查询意图: $ARGUMENTS\n项目目录: /Users/sun/vla\n要求: 只读检索 bigmemory/ 和 .pipeline/；返回 <= 800 字；列出来源文件。"
}
```

Claude Code 子代理调用形状：

```text
Agent({
  description: "Memory retrieval for session",
  subagent_type: "memory-retriever",
  prompt: "查询意图: $ARGUMENTS\n项目路径: /Users/sun/vla"
})
```

Codex 调用子代理时不要设置 `model`、`reasoning_effort` 或 `service_tier`。如果子代理报错、超时或输出为空，立刻改用本地检索；不要用不同模型名反复重试。

## 何时调用

当 AI 发现自己需要以下信息时主动调用,query 须针对具体问题:
- 之前的实验决策或配置
- pipeline 知识库中的调研结论
- 未关闭的研究决策
- Dr Sun 明确要求回忆/检索时

## 意图提取示例

| 当前需要 | 传给 agent 的查询意图 |
|---|---|
| 继续上游仓库调研 | "仓库候选、许可证、固定 commit、未完成核验" |
| 继续集成 | "最近集成进展、接口版本、运行证据、阻塞项" |
| 调研背景 | "待读文献、开源仓库、近期调研" |

## 置信度标注

引用 `.pipeline/survey/`、`.pipeline/experiments/` 或 `bigmemory/冷区/调研记录/` 时，先看文件开头 frontmatter：

```yaml
origin: ...
reviewed: ...
```

没有 frontmatter 时，按 `origin: ai_only, reviewed: false` 处理。低置信度记录只能作为线索，不能作为事实依据。

## 输出格式

总字数 <= 800，使用中文，保留来源文件：

```markdown
## 项目记忆上下文

> 检索方式: 本地检索 | Codex 子代理 | Claude Code 子代理 | 子代理失败后本地检索

### 当前状态
[从热区和任务状态提取当前活跃事项]

### 相关记录
[仅列与查询意图相关的记录；涉及置信度时标注 origin/reviewed]

### 未关闭事项
[只列与当前查询有关的未关闭事项]

### 来源文件
- [文件目录]
```

## 约束

- 纯只读，不修改任何文件
- 返回结果 <= 800 字
- 未找到相关记录时，明确写“未找到相关记忆”，禁止编造
