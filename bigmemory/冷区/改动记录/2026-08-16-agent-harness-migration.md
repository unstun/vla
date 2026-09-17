---
origin: human_directed
reviewed: false
date: 2026-08-16
---

> [摘要] 2026-08-16 从固定提交迁移 agent 配置与 Trellis 到独立 VLA 仓库，未导入导航实现或原项目实验状态；版本与数量为当日快照。
> 2026-09-16 达到 31 天归档阈值；以下历史原文完整保留。

# Agent Harness Migration

## Goal

Prepare `/Users/sun/vla` as an independent Lite3 VLA project while preserving
the reusable Agent setup normally used in `machine-dog-nav`.

## Sources

- Harness source: `/Users/sun/tongbu/study/phdproject/machine-dog-nav`
- Committed source tree: `f7efd89b04865c8dedf00a76b9812697c1558ca8`
- Trellis: `0.6.14`, matching the source project and local CLI
- Vendor skills: `mattpocock/skills` at
  `66f92b61f5b1434a1c7422f6fbd8efc5ee0c0214`

The source repository had unrelated uncommitted work. The migration used its
committed tree for settings and did not modify the source checkout.

## Migrated

- `AGENTS.md` and the `CLAUDE.md` wrapper
- Codex, Claude Code, and Cursor settings, hooks, commands, and Agent adapters
- 36 project-local Skills, 9 Codex custom Agents, and 20 Vendor Skills
- Trellis scripts, workflow, configuration, and reusable specs
- Skill synchronization, safety rules, issue-tracker conventions, research
  pipeline templates, memory layout, and upstream repository manifests

## Deliberately Excluded

- `machine-dog-nav` implementation code
- Source Trellis task and workspace history
- Source experiment, survey, literature, terminology, and hot/cold memory state
- Simulator outputs, models, datasets, CAD/media, and uncommitted source edits

## Verification

- All 301 selected source-tracked harness paths exist in the target.
- TOML, JSON, YAML, Python, and shell syntax checks passed.
- Trellis task validation, package-context loading, and update dry-run passed.
- Codex `0.142.3` loaded the VLA `AGENTS.md`, 36 project Skills, and 20 Vendor
  Skills; all project and Vendor symlinks resolved.
- Codex, Claude Code, and Cursor session hooks returned valid context; git,
  hot-zone, workflow-state, and reviewed-metadata hooks passed smoke checks.
- No credential-like material or stale hard-coded skill path to the source
  project was found.

## Known Boundaries

- Codex native Hook files are installed, but the current user configuration
  does not enable `features.hooks`; activation also requires one-time `/hooks`
  approval.
- The strict current `skill-creator` validator flags inherited cross-platform
  frontmatter keys in 21 legacy project Skills. Codex `0.142.3` nevertheless
  discovered all 36 project Skills. The migrated `fetch-arxiv-md` Skill, whose
  paths changed in this migration, passes the strict validator.
- Trellis `0.6.15` is available, but this migration intentionally retained
  `0.6.14` to match the source project. No framework upgrade was performed.
