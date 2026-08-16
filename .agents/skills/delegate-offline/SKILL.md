---
name: delegate-offline
description: |-
  生成 Codex App/CLI 手动任务包。触发：需要外部 Codex 执行长任务、远端任务、跨模型审查或 Cursor 节省主会话上下文。
  承接 .claude/commands/delegate-offline.md 到 Codex skills。
argument-hint: "[要委派给外部 Codex 的任务]"
user-invocable: true
context: inline
---

# Codex 手动任务包

生成任务包时必须包含：

1. Source of Truth：本地 repo 是唯一代码真源。
2. Sync Gate：远端或外部 CLI 可临时诊断修改，但最终必须同步回本地同路径，并由本地 `git diff` 呈现。
3. 任务目标、允许修改范围、禁止修改范围。
4. 成功信号、失败信号、回传格式。
5. 必要命令和日志保存位置。

如果任务会跑远端代码，使用 `remote-experiment` 的实验模板和 `AGENTS.md` 中的 SSH alias；远端运维细节由 `research-training-observability` 维护，不在任务包中复制。

任务包只输出 Markdown 文本，不包裹成一整段 `codex exec` shell 语法。
