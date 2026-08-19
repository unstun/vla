# Implementation Plan

## 1. Pre-move Evidence

- [x] Record source and destination identity and confirm the destination is
      absent.
- [x] Record outer and nested Git HEAD/status.
- [x] Record repository size, file inventory, and symlink targets.
- [x] Classify old absolute-path references into live versus historical files.

## 2. Live Path Updates

- [x] Update live source-of-truth and harness documentation using `apply_patch`.
- [x] Update active task records to refer to the destination where appropriate.
- [x] Preserve historical and checksum-bound artifacts.
- [x] Review `git diff` before moving.

## 3. Physical Migration

- [x] Revalidate that the exact destination is absent.
- [x] Move the complete source directory to the exact destination.
- [x] Switch all subsequent commands to the destination working directory.

## 4. Validation

- [x] Confirm the destination exists and the old path is absent.
- [x] Compare post-move inventory and size with the pre-move evidence.
- [x] Validate outer Git HEAD/status and nested `.skills-upstream` Git state.
- [x] Validate all relative skill symlinks.
- [x] Validate `CLAUDE.md`, Trellis context, and harness discovery from the new
      root.
- [x] Audit remaining old-path occurrences and confirm each is historical or
      checksum-bound.

## 5. Finish

- [x] Run the Trellis quality check for the migration scope.
- [x] Record the path migration in current project state and session journal.
- [x] Commit the verified migration-document updates from the new root.
- [x] Tell Dr Sun to reopen the Codex workspace at
      `/Users/sun/tongbu/study/phdproject/vla`.

## Rollback Gate

If the destination is incomplete, Git metadata is unavailable, or internal
relative links fail because of the relocation, move the directory back to
`/Users/sun/vla` before further modification and report the failure without
claiming completion.
