# Project Harness Contract

## 1. Scope / Trigger

Applies to project instructions, skills, discovery synchronization, platform
configuration and Trellis maintenance. Preserve unrelated dirty files and
research evidence; a harness change does not authorize research-state edits.

## 2. Instruction And Execution Model

- `AGENTS.md` owns project behavior; `CLAUDE.md` is exactly `@AGENTS.md\n`.
- Keep the 12 installed Trellis core skills, runtime, specs and templates.
- Project execution defaults to the main session. Subagents require Dr Sun's
  explicit request; `.trellis/config.yaml` keeps `codex.dispatch_mode: inline`.
- `session_auto_commit: false` remains set. Do not automatically stage or
  commit during startup, task archival or journal recording.
- At completion of an authorized development task, the main session reviews
  the exact task-owned staged diff, file list and sizes, commits the verified
  changes, and pushes the current branch to its configured remote without
  asking again. Exclude unrelated edits and heavy artifacts; verify the remote
  branch contains the resulting commit. This is the agent's completion duty,
  not a blanket Trellis auto-commit hook.
- Routine prompt/session injection and automatic review-flag mutation are
  disabled. Load context through Trellis skills. Reset reviewed flags manually
  when an authorized edit changes a reviewed research document.
- Retain agent-context hooks for requested delegation and Cursor's shell
  session bridge. Native session identity or an explicit, stable per-session
  `TRELLIS_CONTEXT_ID` is needed for task activation outside a bridge.
- Framework updates must preserve these project choices. Do not rewrite
  Trellis-managed files or their hash registry merely to silence update diffs.

## 3. Skill Discovery

The active catalog is documented in `SKILLS.md`: 12 Trellis core plus nine
project skills. Canonical project skills are real `.agents/skills/` directories.
Claude/Cursor mirrors are links unless a real installed directory owns the name.

`sync-skills.sh` is offline and project-only. It must:

- mirror canonical project skills without replacing real platform directories;
- preserve unrelated/custom links, including deliberate name overrides;
- remove only generated links into `../../.skills-upstream/` and dangling
  generated project links into `../../.agents/skills/`;
- work with no vendor checkout or lock present and produce the same discovery
  layout on repeat execution;
- never fetch, check out or reactivate vendor skills.

`vendor-skills.lock` and any existing ignored vendor checkout retain historical
provenance only. Global skills, plugins and MCP configuration are outside scope.

## 4. Research Boundaries

The local repository is the VLA source of truth. Siblings and upstream trees
are references; remotes are execution copies. `.pipeline/` and `bigmemory/`
retain their research roles. No bulk cleanup, relocation or history rewriting
is implied by skill maintenance.

Research bytes require scoped ignores and tracked hashes/storage/recovery
information. Preserve the existing per-directory `LOCAL_ONLY_BYTES.sha256`
convention; do not add repository-wide evidence-extension ignores.

## 5. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Vendor checkout absent or dirty | Sync still works without inspecting or modifying it. |
| Generated vendor link exists | Remove the link, never the target checkout. |
| Removed project skill leaves a generated link | Remove the dangling discovery link. |
| Real platform directory or custom link exists | Preserve it. |
| Retained skill or hook target is missing | Fail validation and repair the owned path. |
| Trellis CLI/project versions differ | Report it; do not upgrade as a side effect. |
| Unrelated dirty path exists | Preserve its content and exclude it from staging. |

## 6. Tests Required

```bash
python3 -m unittest discover -s tools/harness -p 'test_*.py'
bash -n sync-skills.sh
./sync-skills.sh
python3 .trellis/scripts/task.py validate <task-path>
python3 .trellis/scripts/get_context.py --mode packages
trellis --version
cat .trellis/.version
```

Parse changed JSON/TOML and retained skill frontmatter; check every discovery
link and registered hook target. Compile applicable Python in a temporary cache
and check shell syntax. Review the task-owned diff with `git diff --check`.
Compare pre-edit fingerprints for existing dirty files and protected paths.
A successful filesystem check does not prove an already-open host refreshed
its skill catalog; use a new session for discovery after cleanup.
