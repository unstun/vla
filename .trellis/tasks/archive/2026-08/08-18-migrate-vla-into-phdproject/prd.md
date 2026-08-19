# Migrate VLA Repository Into phdproject

## Goal

Move the complete VLA research repository from `/Users/sun/vla` to
`/Users/sun/tongbu/study/phdproject/vla` so the project is physically located
with the other PhD projects, while preserving Git history, hidden harness
state, research evidence, nested upstream repositories, and skill discovery.

## Confirmed Facts

- The current repository is `/Users/sun/vla`, is approximately 645 MB, and its
  outer Git worktree was clean before this task was created.
- The destination parent `/Users/sun/tongbu/study/phdproject` exists and has
  approximately 178 GiB available.
- `/Users/sun/tongbu/study/phdproject/vla` does not currently exist.
- The repository contains hidden project state (`.git`, `.trellis`,
  `.pipeline`, `.agents`, `.claude`, `.codex`, `.cursor`), a nested
  `.skills-upstream/.git`, relative skill symlinks, and local research bytes.
- Current operational documents contain absolute `/Users/sun/vla` references.
- Historical conversation captures, archived task records, and checksum-bound
  staging evidence also contain the old path as historical data.

## Requirements

- Physically move the entire repository; do not leave `/Users/sun/vla` as the
  project source of truth and do not replace it with a compatibility symlink.
- Preserve the complete outer Git repository, nested `.skills-upstream`
  repository, ignored files, local PDFs, temporary survey evidence, and all
  relative symlinks.
- Change current operational path declarations and live documentation to
  `/Users/sun/tongbu/study/phdproject/vla`.
- Preserve immutable or provenance-sensitive historical captures and
  checksum-bound staging files byte-for-byte even when they mention the old
  path; document those references as historical rather than rewriting history.
- Do not download checkpoints, start OmniVLA inference, run training, launch
  Isaac Lab, or modify sibling projects during this task.
- Keep a rollback path until post-move validation succeeds.

## Acceptance Criteria

- [x] `/Users/sun/tongbu/study/phdproject/vla` exists as the complete repository.
- [x] `/Users/sun/vla` no longer exists and is not a symlink.
- [x] The outer repository retains branch `main`, HEAD, history, tracked files,
      ignored files, and the migration task.
- [x] The nested `.skills-upstream` repository is still recognized as a Git
      worktree.
- [x] Project-relative skill links resolve from the new root.
- [x] `CLAUDE.md` remains exactly the single-line `@AGENTS.md` wrapper.
- [x] Current operational source-of-truth declarations use the new absolute
      path; remaining old-path occurrences are limited to reviewed historical
      or checksum-bound evidence.
- [x] Trellis context and repository status commands run successfully from the
      new root.
- [x] No files are lost according to a pre/post migration inventory and size
      comparison.
- [x] The final report identifies the new path and instructs Dr Sun to reopen
      the Codex workspace there.

## Out Of Scope

- OmniVLA source import, checkpoint download, inference, training, simulation,
  or real-robot integration.
- Reorganizing sibling PhD repositories.
- Changing the contents of historical conversation captures or regenerating
  existing research evidence manifests.
