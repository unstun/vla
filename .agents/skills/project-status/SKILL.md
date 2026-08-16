---
name: project-status
description: |-
  Lite3 VLA 项目状态摘要 + 路由。
  触发: Dr Sun 说 "看下进度/状态如何/接下来做什么/路由/规划/plan",
  或 AI 进入新会话需要先理清当前阶段 (规划 / 实验 / 写作) 时调用。
  区别于 superpowers `writing-plans` skill (那是写实施计划用), 本 skill 专注本项目状态简报 + 下一步路由。
argument-hint: "[可选: 你想优先关注的某个方面，如 '开源仓库调研' / '集成进度']"
user-invocable: true
context: inline
---

# Lite3 VLA 项目状态摘要 · 路由

> 镜像自 `.claude/commands/plan.md`，让 Cursor / Codex / 其他 CLI 也能加载本 SOP。
> 受众: 本项目主 session (任意 CLI) 调本 skill 启动一次"状态摘要 + 路由对话"。

> Claude Code 使用 AskUserQuestion；Cursor 使用 AskQuestion；Codex Default mode 没有问答工具时，用简短中文问题确认必要信息。

你是 Lite3 VLA 项目 Conductor。先全面读取项目状态，再和 Dr Sun
一起决定接下来做什么。

## 第一步: 定向检索 + 读取最新状态

> 查询“看进度 / 现在 / 上次 / 未关闭决策”时，必须先调
> `memory-retrieval` 做定向检索，再核对 git 与原始项目文件。

工作流:

1. **先 invoke `memory-retrieval` skill**, 传入查询意图:
   ```
   memory-retrieval args: "Lite3 VLA 当前阶段 / 基线选择 / 开源仓库调研 / 集成进展 / 未关闭决策"
   ```
2. **再按 memory-retrieval 返回的精选清单 Read 具体文件**——典型清单包括:
   ```
   bigmemory/热区/状态简报.md (subagent 已核对冷区是否更新)
   bigmemory/热区/未关闭决策.md
   bigmemory/热区/近期改动.md
   .pipeline/literature/index.md
   .pipeline/experiments/              # 按 subagent 提示读最近台账
   .pipeline/terminology/terminology.md
   ```
3. 如 memory-retrieval 报"热区已过期", 优先读它返回的冷区路径或 .pipeline/ 原始资料。

## 第二步: 生成状态摘要, 和 Dr Sun 对话

用问答工具展示项目当前状态:

> **Lite3 VLA · 当前状态**: [从状态简报提取]
>
> **最近进展**: [1-2 句话]
>
> **待解决**: [未关闭决策中的阻塞项, 如有]
>
> **建议下一步**: [你认为最合适的下一步]

选项 (根据实际情况动态生成):
- `按建议继续: [具体下一步]`
- `我有其他想法`
- `先看看详细的实验/文献状态`

## 第三步: 根据用户选择行动

- 选择继续: 建议使用对应 skill
  - 开源代码调研 → `inno-code-survey`
  - 文献调研 → `literature-survey`
  - 诊断 → `diagnose`
  - 评审 → `codex-review` 或 `dual-review`
- 选择调整: 进一步问诊了解想法
- 选择查看详情: 列出 `.pipeline/experiments/` 和 `.pipeline/literature/index.md` 的内容摘要

## 最后: 更新热区

如果对话中产生了 Dr Sun 明确确认的新方向决策或任务调整，更新
`bigmemory/热区/状态简报.md`。

## CLI 适配

| CLI | 调用方式 |
|---|---|
| Codex | `$project-status` 或自然语言触发本 skill |
| Cursor | invoke 本 skill (主 session 直接读 + 对话, 不外派) |
| Codex App | paste 任务包（project-status 语境；本 skill 是 SOP, Codex 内跑也能跟着做） |

**为什么不外派**: 本 skill 是"读状态 + 对话路由", 必须主 session 跑——只有主 session 能直接和 Dr Sun 对话 + 调 AskQuestion 工具。
