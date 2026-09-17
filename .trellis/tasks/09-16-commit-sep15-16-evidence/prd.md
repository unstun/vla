# Commit Sep 15-16 evidence: D.1b, HarnessVLN, MIP

## Goal

Commit the work left uncommitted after `6260fe2f` without putting large bytes into history. Same method as
`archive/2026-09/09-14-commit-backlog-evidence` (Dr Sun, 2026-09-16: "Yes, text only").

## Background (measured 2026-09-16)

- 124 status entries; 4,998 untracked files, 986 MB, plus three modified tracked files
  (`RESULT_PHASE_D.md`, the Isaac task `implement.md`, `.pipeline/literature/index.md`).
- 956 MB of it is `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/`. Each run package there carries its own
  copy of the materialized PCT runtime (native `.so` files plus pinned Python source) and, for five runs, point-cloud
  and journal dumps of 7-65 MB each.
- 37 new D.1b frames and depth arrays are already ignored by the existing Isaac block but are not in its manifest.
- Nested `.gitignore` files inside the HarnessVLN experiment (committed with it) already keep `pi/node_modules/`,
  `p2b_execution/{inputs,pct_runtime,builds/*/src}` local; their hashes are in `package-lock.json`,
  `input_manifest.json`, `pct_runtime_manifest.json` and each build's `overlay_manifest.json`.

## Decisions

- D1 (Dr Sun) Text only, as on 2026-09-15. Deferred and left untracked: `.playwright-cli/`, `output/`,
  `docs/research/papers/pdf/`.
- C1 (Dr Sun, 2026-09-16: approved) HarnessVLN text files over 5 MB stay local-only: 17 files, 617 MB (`clouds.jsonl`,
  `pilot_journal*.json`, `metrics.jsonl`). 13 of them are also in the verified local bundle
  `.pipeline/handoffs/2026-09-16_harnessvln_archive/evidence.tar.gz`.
- C2 Per-run `pct_runtime/` copies stay local-only (184 files, 81 MB).

## Requirements

- R1 Local-only files are covered by `.gitignore` rules scoped to one experiment root, with a comment block naming
  what is ignored, where the hash record is and how to regenerate it. No global extension rule.
- R2 Every local-only file has a line in its root's tracked `LOCAL_ONLY_BYTES.sha256`; existing lines are kept.
- R3 Commits follow `review/REVIEW_TABLE.md`; each stages exactly its `review/group_NN.txt` list
  (`GIT_LITERAL_PATHSPECS=1 git add --pathspec-from-file`).
- R4 Nothing is deleted, moved or rewritten; no evidence label changes.

## Acceptance Criteria

- [x] AC1 After the last commit, `git status --porcelain` lists only the deferred paths. Checked before commit 5: only group-5 paths and the deferred paths remained.
- [x] AC2 `shasum -a 256 -c` passes with 0 failures for every touched manifest; the ignored set in the touched roots
      equals the local-only set plus the nested-ignore and older-manifest sets named above. 3 manifests, 0 failures; the local-only list was identical before and after the new rules; every local-only
      path is ignored and no committed path is. The other ignored files in these roots (older Isaac run bytes under
      pre-existing rules, the nested-ignore sets) were not re-verified here.
- [x] AC3 No committed blob over 5 MB. Checked per commit.
- [x] AC4 `git check-ignore` does not ignore representative `.pdf`, `.png`, `.mp4`, `.jsonl` paths outside the
      scoped roots. `docs/x.pdf` and `.png`/`.mp4`/`clouds.jsonl`/`pct_runtime/*.so` probes in a new experiment root are not ignored.
- [x] AC5 `CLAUDE.md` is still exactly `@AGENTS.md\n`; changed JSON/YAML/Python parse. JSON 1,346, YAML 78 and Python 1,655 files parse; `setup/dsh_default_config.yaml` uses DeepSeek Harness's `!!js` tag and is syntax-valid only.
- [x] AC6 Credential scan of staged text is clean (done once on 2026-09-16 before approval: variable names only).
- [x] AC7 Dr Sun approved the review table (2026-09-16, with C1); each commit matches its list. Commits `8df243fc`, `c10f2976`, `e226be6f`, `ad9b157d`; each staged list equalled its group file.
- [x] AC8 Hot zone and journal record this commit and the 2026-09-16 decisions. Hot zone rewritten within budget (982/799/683 characters); journal session added.

Also verified: a 39,352-file SHA-256 snapshot taken before staging still matched after commit 4.

## Out of Scope

- Remote runs, the SCAN fix test and MIP episodes (separate work).
- Deleting the deferred paths or the ~1 GB of Codex checkpoint refs in `.git`.
