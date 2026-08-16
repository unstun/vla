# Implementation Plan

1. Audit active specs, ignore rules, legacy Skill resources, and current Skill
   link topology.
2. Replace stale specs and correct bootstrap/task-state claims.
3. Rewrite `inno-code-survey`; add the safe setup override.
4. Add the Vendor lock and make synchronization deterministic across Codex,
   Claude Code, and Cursor.
5. Update Harness documentation, migration records, and hot-zone state.
6. Run syntax, Skill, Hook, Trellis, symlink, artifact-policy, staged-diff, and
   temporary fresh-clone checks.
7. Commit the verified fix, archive this task, and confirm a clean worktree.

## Rollback

Before commit, use targeted patches to revert only task-owned paths. Do not
reset or checkout the repository wholesale. If Vendor restoration fails, keep
the lock and script changes uncommitted and leave the existing ignored Vendor
checkout untouched for diagnosis.

## Verification Results

- Trellis task/context validation and `trellis update --dry-run` passed on
  project/CLI version `0.6.14`; no framework upgrade was applied.
- Python, Shell, JSON, TOML, YAML, Hook, wrapper, symlink, artifact-ignore, and
  staged-diff checks passed.
- Strict Skill validation passed for the rewritten `inno-code-survey` and the
  new project-owned `setup-matt-pocock-skills` override.
- A temporary clone with no Vendor checkout restored commit
  `66f92b61f5b1434a1c7422f6fbd8efc5ee0c0214`, rebuilt all three discovery
  layouts without tracked drift, preserved real Trellis directories, and
  rejected both a wrong origin and a dirty Vendor index.
- The first fresh-clone attempt exposed a `--no-checkout` false-positive in the
  dirty-worktree guard. `sync-skills.sh` now materializes a clean worktree
  before applying that guard, and the regression test passes.
