# Pending Changes Review — 2026-10-22

Scope: the 50 tracked modifications present before this task. They were reviewed
without editing or staging them. Existing untracked research/spec/task files are
also preserved. No experiment claims were revalidated through a simulator run.

## Finding — P2: inline task startup regresses in a multi-platform checkout

Location: `.trellis/scripts/task.py:199-204`, in the new empty-context gate.
The gate checks seeded implement/check manifests without consulting the active
inline execution policy. `.claude/` or `.cursor/` causes `task.py create` to seed
those manifests, even when `codex.dispatch_mode: inline` is configured.
Consequently a normal `task.py start` fails in the VLA configuration, although
`.agents/skills/trellis-brainstorm/SKILL.md:170` says inline execution skips the
JSONL gate. A Codex-only fixture succeeds, isolating the multi-platform trigger.

Evidence: `research/runtime_results.json` records the actual refusal; the same
scenario passes using the pre-update scripts in `research/before_update_comparison.json`.
The explicit `--allow-empty-context` override works, as does populated context.
Recommendation: resolve the inline/platform policy before adopting this upgrade;
preserve the context requirement when actual subagent execution needs it. Until
then, intentionally inline work can use the existing explicit override. No
upstream template was patched in this review.

## Framework classification — 45 files

- 43 template-bearing files match their recorded template hashes.
- 44 of 45 files match a fresh local generation from the installed Trellis
  0.6.17 package, including the version file. All changed Python runtime files
  also match the installed package source bytes.
- The remaining file is the template-hash registry. It has the same 191 keys;
  four values reflect existing project-specific AGENTS/config/hook choices.
  This is expected project metadata, not an unexplained code fork.
- Changes cover task validation/rename/archive behavior, active-session handling,
  atomic writes, shared YAML parsing, bounded Git-lock retry, journal commit
  evidence and idempotent retries, and matching skills/commands across platforms.

Twelve isolated behavioral probes produced 11 passes and the one inline-start
failure above. Passed checks include create/curate/start/finish, invalid context,
archive collisions, no automatic staging/commit, rename references, and pending
and committed journal retry idempotency. Malformed-task archival intentionally
warns and preserves the original bytes; it is not treated as a silent repair.

Re-run the probes against the pending local update:

```bash
python3 .trellis/tasks/archive/2026-10/10-22-vla-branch-review/research/runtime_probes.py \
  --source . --output /private/tmp/vla-trellis-review.json
```

The script writes only its requested output and temporary fixture repositories.
It does not operate on real tasks or journals. See `research/path_review.json`
for per-file SHA-256 and template comparisons.

## Research and retention classification — five files

- `.gitignore`: ten exact v290 MP4 ignores, without broad extension rules.
  All ten local file sizes and SHA-256 values match `MEDIA_STORAGE.md`.
  That storage manifest remains untracked, so publishing the ignore alone
  would omit the recovery/provenance document required by the project contract.
- The experiment versions index adds 420 lines. All 45 new Markdown link targets
  exist locally; all 45 are untracked. Publishing only the index would create
  broken links on GitHub. The experiments and their acceptance claims remain
  outside this harness review's runtime scope.
- The backend spec index adds three links to untracked new specs. Those three
  files must be reviewed together with the index before a future publication.
- The callback-failure and shared-environment specs add experiment-derived
  contracts. They belong with their research evidence, not with a generic
  Trellis update. No semantic acceptance of those experiments is implied here.

The 85 existing untracked Trellis-area files include three new specs and 82
research task files. They were inventoried, not added, archived or uploaded.
Details: `research/reference_review.json`, `research/media_manifest_check.json`.

## Recommendation

Keep all 50 modifications pending. First correct or deliberately resolve the
one Trellis inline-start regression; then review a separate 45-file framework
commit. Package the five research/retention edits with their referenced evidence
only when Dr Sun authorizes that research publication. Do not include them in
the branch-alignment commit.

## Path-by-path disposition

| Path | Classification | Disposition |
|---|---|---|
| `.agents/skills/trellis-brainstorm/SKILL.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.agents/skills/trellis-continue/SKILL.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.agents/skills/trellis-meta/references/local-architecture/context-injection.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.agents/skills/trellis-meta/references/local-architecture/task-system.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.agents/skills/trellis-session-insight/SKILL.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.agents/skills/trellis-session-insight/references/cli-quick-reference.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.claude/commands/trellis/continue.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.claude/hooks/inject-subagent-context.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.claude/hooks/inject-workflow-state.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.claude/hooks/session-start.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.claude/skills/trellis-brainstorm/SKILL.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.claude/skills/trellis-meta/references/local-architecture/context-injection.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.claude/skills/trellis-meta/references/local-architecture/task-system.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.claude/skills/trellis-session-insight/SKILL.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.claude/skills/trellis-session-insight/references/cli-quick-reference.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.codex/hooks/inject-subagent-context.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.codex/hooks/inject-workflow-state.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.codex/hooks/session-start.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.cursor/commands/trellis-continue.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.cursor/hooks/inject-subagent-context.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.cursor/hooks/session-start.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.cursor/skills/trellis-brainstorm/SKILL.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.cursor/skills/trellis-meta/references/local-architecture/context-injection.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.cursor/skills/trellis-meta/references/local-architecture/task-system.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.cursor/skills/trellis-session-insight/SKILL.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.cursor/skills/trellis-session-insight/references/cli-quick-reference.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.gitignore` | Research / retention | Reviewed; unchanged and unstaged |
| `.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/README.md` | Research / retention | Reviewed; unchanged and unstaged |
| `.trellis/.template-hashes.json` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/.version` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/add_session.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/common/__init__.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/common/active_task.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/common/config.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/common/developer.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/common/git.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/common/io.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/common/paths.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/common/safe_commit.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/common/task_context.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/common/task_store.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/common/task_utils.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/common/tasks.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/common/trellis_config.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/common/workflow_phase.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/scripts/task.py` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
| `.trellis/spec/backend/index.md` | Research / retention | Reviewed; unchanged and unstaged |
| `.trellis/spec/backend/newton-callback-failure.md` | Research / retention | Reviewed; unchanged and unstaged |
| `.trellis/spec/backend/newton-shared-environment.md` | Research / retention | Reviewed; unchanged and unstaged |
| `.trellis/workflow.md` | Trellis 0.6.17 | Reviewed; unchanged and unstaged |
