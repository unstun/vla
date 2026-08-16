# Harden migrated agent harness

## Goal

Turn the migrated Agent harness from a locally usable draft into a
project-consistent, fresh-clone-reproducible VLA baseline without importing any
`machine-dog-nav` implementation or experiment state.

## Requirements

- Remove source-project SCAN, Go2, V12, forest-runtime, and CAD/Fusion claims
  from active VLA specs and artifact policy.
- Keep backend/frontend conventions explicitly provisional until a clean VLA
  baseline is imported and inspected.
- Replace the legacy Medical AI body of `inno-code-survey` with a concise VLA
  and navigation upstream code-survey workflow using this repository's paths.
- Restore Vendor Skills from a tracked repository URL and exact commit pin.
- Preserve real project-owned Skills across Codex, Claude Code, and Cursor;
  never let Vendor synchronization replace them.
- Prevent Vendor setup guidance from modifying the single-line `CLAUDE.md`
  wrapper or writing to an unconfigured issue tracker.
- Keep large-artifact handling explicit and path-specific instead of globally
  ignoring research evidence by extension.
- Do not import source tasks, experiments, memory, implementation code, or
  uncommitted source changes.

## Acceptance Criteria

- [x] Active Trellis specs contain no unimported SCAN/Go2/V12/forest runtime
  contract, and spec indexes truthfully label deferred layers.
- [x] PDF, PNG/JPG, MP4, ZIP, and CAD files are not globally ignored; the
  repository documents a reviewed path-specific policy for large local bytes.
- [x] `inno-code-survey` contains no Medical AI/Dr. Claw paths and writes only
  to the declared VLA upstream/survey layout.
- [x] A fresh clone can run `./sync-skills.sh` and restore the exact Vendor
  commit recorded in a tracked lock file.
- [x] Codex, Claude Code, and Cursor link project-owned Skills without replacing
  platform-managed real directories.
- [x] The project-owned `setup-matt-pocock-skills` behavior preserves
  `CLAUDE.md` and blocks issue writes until a VLA remote is approved.
- [x] Config, shell, Python, Skill, Hook, Trellis, symlink, and fresh-clone smoke
  checks pass; no stale source path or credential-like material is introduced.
- [ ] The fix is committed and the target worktree is clean.

## Notes

- Independent review of root commit `a8439ec` reported four Major and one
  Minor finding. This task owns those findings plus the closely related Cursor
  discovery boundary.
- Formal VLA implementation, training, remote execution, and baseline import
  remain out of scope.
