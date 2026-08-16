---
origin: human_directed
reviewed: false
date: 2026-08-16
---

# Agent Harness Hardening

## Task

Harden the migrated Agent Harness after an independent review of root commit
`a8439ec`, without importing any `machine-dog-nav` implementation or experiment
state.

## Why This Record Matters

The first migration was locally usable, but that did not prove that its active
specifications matched the new VLA project's actual state or that a fresh clone
could reconstruct the same Skill topology. Future Harness changes need this
boundary so local readiness is not mistaken for reproducibility or VLA
implementation evidence.

## Review Findings Resolved

- Removed active SCAN, Go2, V12, forest-runtime, CAD, and Fusion contracts that
  had been inherited without importing the corresponding implementation.
- Replaced repository-wide evidence-extension ignores with a path-specific
  policy. Local-only large bytes now require tracked provenance, SHA-256,
  storage location, and regeneration instructions.
- Rewrote `inno-code-survey` for Lite3 VLA and autonomous-navigation upstream
  survey/acquisition; removed its Medical AI and Dr. Claw resources.
- Added `vendor-skills.lock` with canonical repository
  `https://github.com/mattpocock/skills.git` pinned to
  `66f92b61f5b1434a1c7422f6fbd8efc5ee0c0214`.
- Reworked `sync-skills.sh` so a fresh clone restores that exact Vendor commit,
  preserves real platform directories, and exposes project-owned Skills to
  Codex, Claude Code, and Cursor.
- Added a project-owned `setup-matt-pocock-skills` override. It preserves the
  exact single-line `CLAUDE.md` wrapper and blocks issue-tracker writes until a
  VLA remote is approved.
- Made backend/frontend specifications explicitly provisional until a clean
  VLA baseline is selected, pinned, imported, and inspected.

The resulting discovery topology contains 37 real project-owned Skills and 19
effective Vendor links. The upstream promoted set contains 20 names; the
project-owned setup override intentionally wins the one name collision.

## Affected Paths

- `AGENTS.md`, `.gitignore`, `SKILLS.md`
- `vendor-skills.lock`, `sync-skills.sh`
- `.agents/skills/inno-code-survey/`
- `.agents/skills/setup-matt-pocock-skills/`
- `.trellis/spec/backend/`, `.trellis/spec/frontend/`
- `.trellis/spec/guides/`, `.trellis/spec/harness/`
- `.trellis/tasks/08-16-harden-migrated-agent-harness/`

## Verification

- Config, shell, Python, Skill, Hook, Trellis, and symlink checks passed.
- A temporary fresh clone restored the exact pinned Vendor commit and the
  Codex/Claude/Cursor project and Vendor links while preserving platform-owned
  real directories.
- Fresh-clone negative checks confirmed that a wrong Vendor origin and a dirty
  Vendor checkout fail closed before link regeneration.
- Representative PDF, image, video, archive, and CAD evidence paths are not
  globally ignored.
- Active VLA Skills and specifications no longer contain the reviewed legacy
  Medical AI, Dr. Claw, SCAN, Go2, V12, or forest-runtime contracts.

## Claim Boundary

This is Harness validation only. No navigation baseline was imported, and no
VLA implementation, simulator run, remote run, formal training, checkpoint, or
real-robot result was produced.

## Commit

`7b079f0f3258fe0328f4defcd0f79839e67ba089` (`fix: harden migrated
agent harness`).
