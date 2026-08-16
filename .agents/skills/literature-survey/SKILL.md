---
name: literature-survey
description: |-
  Lite3 VLA 与自主导航文献、开源仓库调研 SOP。触发：Dr Sun 说“调研/搜论文/survey/找相关工作/补文献/找开源仓库”。
argument-hint: "[调研方向、关键词、时间窗或输出要求]"
user-invocable: true
context: inline
---

# Lite3 VLA 与自主导航文献、开源仓库调研

先读取 `bigmemory/热区/状态简报.md`、`.pipeline/literature/index.md`、`.pipeline/terminology/terminology.md`。

执行前先给出搜索范围、关键词、目标数量和保存位置。需要确认时，Claude Code 使用 AskUserQuestion；Cursor 使用 AskQuestion；Codex Default mode 用简短中文问题。

执行原则：

1. 使用 `web-search` / `academic-researcher` / `paper-finder` / `biorxiv-database` 等合适 skill。
2. PDF 保存到 `docs/research/papers/<CitationKey>.pdf`。
3. 文献索引追加到 `.pipeline/literature/index.md`。
4. 综述输出写到 `.pipeline/survey/<topic>.md`，必须带 `origin` 和 `reviewed` frontmatter。
5. 开源仓库必须记录 URL、许可证、固定 commit、依赖和原作者运行说明。
6. 只检查代码写 `surveyed`；只有原始流程真实跑通才能写 `reproduced`。
7. 付费墙或工具无法访问时列出检索项，不编造 DOI、URL 或结果。
