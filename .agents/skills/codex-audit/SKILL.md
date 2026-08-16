---
name: codex-audit
description: |-
  用 Codex 审查当前分支、未提交改动或最近 commit，覆盖代码、论文、实验台账和 harness 规则。
  承接 .claude/commands/codex-audit.md 到 Codex skills。
argument-hint: "[审查范围或重点，如 working-tree / HEAD~1 / 术语一致性]"
user-invocable: true
context: inline
---

# Codex 审查

先采集：

```bash
git status --porcelain
git log --oneline -10
git diff --stat HEAD~1..HEAD
git diff --stat
```

审查范围：

1. 有未提交改动时，默认审 working tree。
2. 工作区干净时，默认审最近一次 commit。
3. 明确指定 base 时，按指定 base 审当前分支。

Codex 主入口内优先使用内置 review 能力：

```bash
codex review --help
codex exec review --help
```

输出要求：

1. findings 按 Critical / Major / Minor 分类。
2. 每条必须有文件位置、问题、判断依据和建议。
3. 论文和实验 claim 必须对照 `.pipeline/experiments/` 中对应的 decision log 与实验台账。
4. 不批量接受建议；需要修改时逐条处理。
