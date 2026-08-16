# Project Harness Contract

## 1. Scope / Trigger

This contract applies when changing `AGENTS.md`, `.trellis/`, `.codex/`,
`.claude/`, `.cursor/`, `.agents/skills/`, `.pipeline/`, `bigmemory/`, or the
skill synchronization scripts.

The purpose is to preserve one auditable behavior model across supported AI
platforms without copying the `machine-dog-nav` baseline project's task,
experiment, or mutable memory history.

## 2. Signatures

### Trellis initialization

```bash
trellis init --cursor --claude --codex --user sun \
  --skip-existing --no-monorepo --yes --workflow native
```

### Task validation

```bash
python3 ./.trellis/scripts/task.py validate <task-name>
python3 ./.trellis/scripts/get_context.py --mode packages
```

### Vendor skill refresh

```bash
git -C .skills-upstream pull
./sync-skills.sh
```

### Hook payloads

- Prompt hooks consume a JSON object on stdin with `prompt`,
  `user_prompt`, or `message`.
- Codex hook entry points emit valid JSON on stdout when output is present.
- Git and hot-zone prompt hooks emit text only when their keyword group matches.

## 3. Contracts

- `AGENTS.md` is the behavior source of truth; `CLAUDE.md` remains
  `@AGENTS.md`.
- `.trellis/config.yaml` sets `session_auto_commit: false`.
- Trellis-generated platform files remain managed by Trellis.
- Project-owned skills are real tracked directories in `.agents/skills/`.
- Claude Code discovers project skills through tracked symlinks in
  `.claude/skills/`.
- Vendor skills are ignored symlinks into `.skills-upstream/`.
- `sync-skills.sh` must never replace a real project-owned skill directory.
- `.pipeline/` stores reviewed research and experiment state.
- `bigmemory/` stores current and durable project state.
- Automatic staging or committing is forbidden.
- The local repository is the VLA source of truth; `machine-dog-nav`, other
  upstream repositories, and remote copies are references or execution copies.

Runtime environment:

| Key | Required | Meaning |
|---|---|---|
| `TRELLIS_CONTEXT_ID` | Task commands outside a platform hook | Selects the per-session active-task pointer. |
| `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR` | Set by Claude settings | Keeps shell work in the project. |

## 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| `.skills-upstream` missing | `sync-skills.sh` exits with a clone instruction; tracked project skills remain intact. |
| Vendor and project skill names collide | Project-owned real directory wins; vendor link is skipped. |
| Hot-zone file missing or older than 24 hours | Hook prints a warning; it does not edit or commit. |
| AI edits `reviewed: true` trusted Markdown | Post-tool hook resets it to `reviewed: false`. |
| TOML, JSON, YAML, Python, or shell syntax invalid | Validation fails before staging. |
| Trellis CLI and project versions differ | Report the mismatch; do not silently update framework files. |
| Dirty unrelated path exists | Preserve it and exclude it from task staging. |

## 5. Good / Base / Bad Cases

- Good: add a project skill as a real `.agents/skills/<name>/` directory,
  expose it with a Claude symlink, validate both, and stage only owned paths.
- Base: refresh vendor links with `sync-skills.sh`; no tracked diff is expected
  unless the synchronization contract changed.
- Bad: copy all of `machine-dog-nav/.pipeline`, its Trellis tasks, or experiment
  memory into this project and present that history as VLA state.

## 6. Tests Required

```bash
trellis --version
cat .trellis/.version
python3 ./.trellis/scripts/task.py validate <task-name>
python3 ./.trellis/scripts/get_context.py --mode packages
python3 -m compileall -q .trellis/scripts .codex/hooks .claude/hooks .cursor/hooks .agents/skills
find .claude .codex .agents/skills -type f -name '*.sh' -print \
  | while read -r file; do bash -n "$file"; done
git diff --check -- . \
  ':(exclude).agents/skills/trellis-*' \
  ':(exclude).claude/skills/trellis-*' \
  ':(exclude).cursor/skills/trellis-*' \
  ':(exclude).trellis/workspace/**'
trellis update --dry-run
```

Assertion points:

- TOML, JSON, and YAML parse without error.
- Prompt hooks emit expected keyword-gated output.
- Codex hook output parses as JSON.
- Project skill links resolve to `SKILL.md`.
- No migrated skill contains a hard-coded `machine-dog-nav` project path.
- Staged paths exclude `docs/research/` unless that task explicitly owns it.
- Trellis-managed templates are kept byte-for-byte as installed even when an
  upstream Markdown template contains trailing-space formatting.

## 7. Wrong vs Correct

### Wrong

```text
Copy machine-dog-nav/.trellis, .pipeline, and bigmemory recursively.
Run an auto-backup hook that commits whatever is dirty.
```

This imports unrelated research truth and can commit user-owned files.

### Correct

```text
Initialize the same Trellis release in skip-existing mode.
Adapt reusable behavior.
Create fresh VLA pipeline and memory state.
Validate, stage an explicit path list, review, then commit.
```
