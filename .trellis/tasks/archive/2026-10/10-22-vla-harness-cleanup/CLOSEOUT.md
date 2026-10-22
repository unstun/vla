# VLA Harness Cleanup — 2026-10-22

The approved cleanup is implemented and filesystem/runtime checks passed.
The cleanup was initially left uncommitted. Dr Sun subsequently authorized
automatic task-scoped commit and push; this follow-up adds that standing rule
and includes the cleanup in its reviewed commit. Unrelated working-tree changes
remain excluded. No research-state archival was performed.

## Delivered

- AGENTS.md reduced from 165 to 81 lines, including the follow-up commit rule.
  Removed the obsolete initialization
  snapshot, kept durable project contracts and the exact Trellis managed block.
- Active skills reduced from 52 to 21: 12 unchanged Trellis core skills and nine
  project skills. Claude and Cursor expose the same 21 names.
- Removed 12 redundant project skills, 19 vendor skill entries and their mirrors,
  six unused Codex agent definitions, obsolete custom hook scripts and unused
  paper-analysis helpers. Exact paths are in `changes.json`.
- Merged state synchronization into archive and upstream navigation survey into
  inno-code-survey. Removed nonexistent workflow dependencies and automatic
  subagent/second-CLI review from project skills.
- Synchronization is offline and project-only. Vendor provenance and its
  existing source checkout remain available but are no longer auto-discovered.
- Disabled routine prompt/session injection and automatic reviewed-flag mutation.
  Kept Trellis agent-context delivery and Cursor's task-session bridge.

## Verification

- 11 focused tests passed: offline fresh-checkout sync, repeat execution,
  real/custom overrides, stale links, source preservation, catalog and hooks.
- Nine project skills passed Skill Creator frontmatter validation.
- JSON/TOML/YAML, Python and Bash syntax checks passed; all registered hook
  targets and skill discovery links resolve.
- Trellis CLI and project both report 0.6.17. Task context validation passed.
- Existing Trellis templates, runtime, workflow, config and dirty changes were
  preserved. 169 unaffected harness/global configuration files matched their
  baseline SHA-256 fingerprints.
- All 538,427 protected file entries matched before/after metadata (mode, size,
  mtime and symlink target), with zero additions or removals. This covered
  .pipeline, bigmemory, docs/research, references, third_party, deploy and
  artifact_retention. Global configuration was not edited.
- The first test run identified one leftover dataset-discovery bytecode cache;
  it was removed and all checks then passed.

See `validation.json` for the compact results. No simulator, remote experiment,
research-index update or global MCP operation was part of this task.

## Review And Recovery

Follow-up authorization (2026-10-22): after an authorized development task passes
its checks, review and commit only that task's files, then push the current
branch without another confirmation. Keep Trellis `session_auto_commit: false`.
The configured destination is `https://github.com/unstun/vla.git`, branch `main`.
Git commit/push output and the remote branch identity establish delivery.

The initial staging attempt encountered an empty `.git/index.lock` dated
2026-10-20. With no lock holder or Git process found, the unchanged stale file
was moved to `/private/tmp/vla-harness-cleanup-20261022/stale-index-20261020.lock`;
the exact task-path staging then succeeded.

Starting HEAD: `5bc7780d5aaf753f6c8d822dd261519555c9c91f`.
Retired tracked files are recoverable selectively from that commit. Retired
vendor source identity remains in `vendor-skills.lock`. Preserve unrelated
working-tree changes during any rollback; do not reset the repository.

Open a new host session to refresh skills and hook registrations. The checks
above establish on-disk readiness, not a live reload of this existing chat.
