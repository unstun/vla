# Local Research And GitHub Publishing

Dr Sun's 2026-10-22 instruction keeps 24 existing research commits off GitHub.
This hold remains active until Dr Sun explicitly releases it.

## Branches

| Branch | Purpose | Upstream |
|---|---|---|
| `local/research-unpublished` | The existing primary checkout, unpublished research history and pending experiments | None; local only |
| `main` | The published baseline | `origin/main` |
| `codex/*` based on `origin/main` | A selected, reviewable publishing task | Its corresponding origin branch when pushed |

The research branch was renamed from local main without checking out, resetting
or stashing files. Its research records and data remain in their original paths.
Repository-local `push.default=simple` and `push.autoSetupRemote=false` ensure a
plain push from that branch stops instead of creating a remote research branch.
These settings are a default, not a replacement for checking an explicit refspec.

## Completing A Task

Keep task-scoped automatic commits and pushes for publishable work. First check
the current branch and outgoing commit range. On the research branch, commit
only authorized task files locally; do not add an upstream or push its ancestry.

For publication, create a managed worktree or branch based on `origin/main` and
apply only the approved task's change. A temporary Git index can prepare the same
scoped tree without checking out the older research tree in the primary workspace.
Verify the selected paths, test the resulting published tree, and inspect its
ancestors before pushing. Preserve the local research history and all unrelated
dirty files. Never force-push or use `--all` to reconcile these branches.

Do not switch the primary research checkout to the published main merely to
make `git status` clean: those trees intentionally contain different research
history. Use a separate checkout for ordinary work on the published baseline.

## Current Review Boundary

The 50 pre-existing modifications were reviewed in `10-22-vla-branch-review`.
The subsequent authorized `10-22-vla-no-hooks` task finalizes the reviewed
Trellis update with its inline-start repair and removes all project hooks.
The five research/retention edits and their related untracked evidence remain
pending; this harness maintenance does not publish them.
