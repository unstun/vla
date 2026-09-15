# Commit Aug 18 to Sep 14 research evidence

## Goal

Get the uncommitted research record from Aug 18 to Sep 14 into git without putting multi-gigabyte media into the
history. Text evidence goes into commits Dr Sun can review. Large bytes stay on this Mac, each with a path-specific
ignore rule and a tracked SHA-256 record. Opened 2026-09-14 after the status review ("Review and commit").

## Background (measured 2026-09-14)

- Last commit `3635579`. 74 Phase A paths from the Isaac task are staged, 54 tracked files are modified, and
  34,036 files are untracked, about 4.1 GB in total.
- Untracked bytes by kind:
  - media, frame dumps, arrays, archives and scene files: 25,177 files, 3,641 MB;
  - upstream work copies and vendored source: 4,802 files, 144 MB;
  - text: 4,060 files, 355 MB, including 291 MB of `.jsonl` telemetry and traces.
- Existing tracked records already hold the SHA-256 of most bytes that would be ignored. Files with no record yet:
  - OmniVLA `vendor-src/transformers-openvla-oft`: 4,269 files, 75 MB;
  - DualVLN: 452 files, 88 MB (decoded frames, a micromamba tarball, some public-eval images);
  - smaller gaps: X-NavDP `media/suite01` (6 files, 8.8 MB), Isaac `analysis/` (13 images), TIC-VLA Orin runs (4),
    Active MVP v2 frames (7), OmniVLA receive-only `runtime/` (4), TIC-VLA DynaNav logs (2).
- Binary files hiding in the text class (7 files, 1.9 MB): one `.zip`, one `.wav`, three `.aiff` and two Habitat
  `.navmesh`.
- Fetched upstream source trees under `references/upstream/**/source/` are already ignored, nested `.git` directories
  included. The Lite3 sim bridge is the one intended exception.
- Credential scan of untracked and modified text found no real secret. The only hit is a dummy test token in
  vendored `transformers` source, which will be ignored.
- Rule: `.trellis/spec/harness/project-harness-contract.md:62` forbids repository-wide extension ignores for research
  evidence. Large local-only bytes need a reviewed path-specific rule and a tracked manifest (AGENTS.md, Engineering
  Rule 9).

## Decisions (Dr Sun, 2026-09-14)

- D1 Open a Trellis task and plan before staging anything.
- D2 Media policy **text only**. Track text, scripts, logs, manifests and `.jsonl` of any size. Keep videos, frame
  dumps, images, arrays, archives, scene and CAD files, work copies and vendored third-party source local-only.

## Requirements

- R1 Every local-only file is covered by a path-specific ignore rule, scoped to one experiment, task or survey
  directory, with no global extension rule. A comment block per root names the task, the storage location (this Mac
  path) and how to regenerate the bytes or why they cannot be.
- R2 Every local-only file has its SHA-256 and relative path in a tracked, unignored manifest under its own root,
  verifiable with `shasum -a 256 -c`. Per-root file counts and total sizes go in the `.gitignore` comment; per-file
  sizes are not recorded, because `shasum -c` format has no field for them (amended 2026-09-14 after review).
- R3 Commits are ordered by date and grouped by topic, so each can be reviewed alone (grouping in `design.md`). Each
  commit stages only its group's paths.
- R4 Before any commit, Dr Sun sees the per-commit review table: path count, bytes, top directories and the full path
  list saved in this task's directory. No commit happens without his approval.
- R5 Dr Sun's own uncommitted edits are committed as they are and named in the review table. Nothing gets reverted.
  Example: the one-line `AGENTS.md` "Project override: use English by default."
- R6 Nothing is deleted, moved, re-encoded or rewritten, and no evidence label changes. Only these are written:
  - new manifests and `.gitignore` rules;
  - this task's files;
  - the final memory sync (hot-zone status brief, recent changes, journal).
- R7 Commit messages use the repository's conventional style (`docs:`, `chore:`, `feat:`) with the attribution line.

## Acceptance Criteria

- [ ] AC1 After the last commit, `git status --porcelain` lists only the deferred paths named in Out of Scope.
- [x] AC2 For every root, each ignored untracked file appears in a tracked manifest, and `shasum -a 256 -c` passes
      with 0 failures.
- [x] AC3 No committed blob larger than 5 MB is media, an archive, an array or a work copy. Every committed file over
      5 MB is listed and is a text log or trace.
- [x] AC4 `git check-ignore` does not ignore representative `.pdf`, `.png`, `.mp4`, `.zip` and `.step` paths outside
      the scoped roots, so no global extension ignore has crept in.
- [x] AC5 `CLAUDE.md` is still exactly `@AGENTS.md\n`. Every changed JSON, YAML, TOML, Python and shell file parses.
- [x] AC6 A credential re-scan of the staged text is clean before each commit.
- [x] AC7 Dr Sun approved the review table before the first commit, and every commit matches its approved path list.
- [ ] AC8 The hot-zone status brief, recent changes and journal describe Isaac Phases B–D and this commit, and the
      Isaac task's E.2 item is ticked.

## Out of Scope

- Deleting or moving any bytes, including the playwright junk and anything on the rented 4090.
- Archiving or changing the status of other Trellis tasks.
- Any git remote, push or history rewrite.
- `.playwright-cli/` and `output/playwright/`: browser-tool logs from 2026-09-08 (0.3 MB). Left untracked and
  reported, not ignored.
- Re-checking the scientific claims inside the committed records.
