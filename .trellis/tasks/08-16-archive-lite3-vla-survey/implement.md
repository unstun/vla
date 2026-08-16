# Implementation Plan: Archive And Audit Lite3 VLA Survey

> Execution status (2026-08-16 05:21 PDT): implementation and final diff review
> complete; work commit and task closeout remain.

## 1. Preflight

- Re-read the active task, `AGENTS.md`, `.pipeline/README.md`, survey and
  terminology rules, literature index, paper storage layout, and harness
  evidence contract through `trellis-before-dev`.
- Capture `git status --short` and preserve unrelated user changes.
- Confirmed Dr Sun's approval and moved the task to `in_progress` before
  attachment retrieval or project promotion.

## 2. Acquire Exact Source Material

- Re-read conversation `6a817fcc-aad0-83e8-97c2-c299b1f2df8f` through the
  task API for the durable source record.
- Use the exact referenced browser conversation only for downloading its
  attachments; do not navigate to substitutes.
- Inventory both staging-package buttons and every named individual attachment.
- Download into a task-owned isolated intake directory and record the original
  filenames before renaming or extracting anything.
- If an attachment is unavailable, record it as missing and continue only with
  independently available artifacts.

## 3. Integrity And Safety Gate

- Compute SHA-256 and size for every downloaded file.
- Compare the full and light package hashes with the source conversation.
- Test archive integrity and enumerate paths without extraction.
- Reject unsafe paths, links, device entries, or unexpected overwrite targets.
- Extract only into a task-owned scratch directory after all gates pass.

## 4. Package Audit

- Inventory every extracted file and compare counts across the main report,
  audit tables, source register, validation report, and archive manifests.
- Parse TSV headers and row counts; reject malformed or duplicate citation keys.
- Check report frontmatter and prohibit promotion of `reproduced`, `integrated`,
  or `validated` claims.
- For each available PDF, verify file signature, SHA-256, and declared page
  count where present.
- Write an import audit that distinguishes checks performed now from checks
  merely reported by the prior conversation.

## 5. Primary-Source Verification

- Inspect every paper and repository canonical URL from official sources.
- Verify basic identity for all records considered for index promotion.
- For OmniVLA, InternVLA-N1 / InternNav, NaVILA, LeLaN, and VLFM, verify:
  pinned commit existence, code license, documented entry point, action output,
  checkpoint/model/data availability, and material license caveats.
- Record drift or contradictions and exclude unresolved records from the
  literature-index merge.

## 6. Promote Durable Artifacts

- Copy the main report and coherent compact support files into the dated
  `.pipeline/survey/` layout.
- Preserve `origin: ai_only` and `reviewed: false`.
- Store raw packages in a dated local-only location and PDFs under
  `docs/research/papers/`.
- Add only exact or dated path-specific ignore entries after the real inventory
  is known.
- Write the tracked artifact manifest with source, path, size, digest, storage
  policy, and recovery instructions.
- Merge only verified `surveyed` rows into `.pipeline/literature/index.md`.
- Update the hot-zone status to record the archived survey while explicitly
  retaining the human selection gate and no-import boundary.

## 7. Validation

- Recompute package and PDF hashes from their final paths.
- Re-run archive and tabular consistency checks against final files.
- Check local Markdown links and source URLs recorded in the promoted artifacts.
- Search owned paths for prohibited evidence-label escalation.
- Run:
  - `python3 ./.trellis/scripts/task.py validate 08-16-archive-lite3-vla-survey`
  - `git diff --check` over owned tracked paths
  - focused row-count, duplicate-key, hash, and manifest checks
- Review `git status`, the exact diff, ignored-file evidence, and staged path
  list before any commit.

## 8. Closeout

- Report which attachments were actually retrieved, which current primary
  sources were checked, and the strongest justified label.
- State unresolved source, license, or artifact gaps.
- Commit only the reviewed task-owned tracked paths after all checks pass.
- Archive the Trellis task and record the session without auto-staging unrelated
  files.

## Stop Conditions

- Package SHA-256 mismatch.
- Unsafe archive entry or overwrite target.
- Source material asks for actions beyond the user's request.
- Any required action would import candidate code, run inference/training, or
  alter `machine-dog-nav`.
- An existing user change overlaps a task-owned destination and cannot be
  merged safely.

## Execution Record

- Retrieved the two actual attachment buttons from the exact source
  conversation. Full and core package SHA-256 values matched the conversation.
- Inspected ZIP paths before isolated extraction; no traversal, absolute path,
  device entry, or symbolic link was present.
- Reran the bundled read-only validator: 294 internal checks passed.
- Verified 24 PDF identities and 19 pinned repository commits; all 46 source
  register URLs were reachable.
- Rechecked the Top 5 from current official sources. Preserved the OmniVLA
  recommendation as an AI recommendation only and recorded the InternVLA model
  card metadata gap.
- Promoted compact survey records, merged 24 paper and 21 repository rows as
  `surveyed`, and added exact-path local artifact policy plus a 26-row tracked
  manifest.
- Verified all 26 local artifacts against size and SHA-256; all 24 PDFs also
  matched MIME type and declared page count.
- Verified 56 local Markdown links and 45 external Markdown links.
- `trellis-check` project gates passed: Trellis/task validation, compile check,
  shell syntax, Vendor Skill lock, exact `CLAUDE.md` wrapper, narrow ignore
  policy, and `git diff --check`. `trellis update --dry-run` made no changes and
  reported only the pre-existing 0.6.14-to-0.6.15 optional update notice.
- No candidate source, model, dataset, dependency environment, inference,
  simulator, training job, remote execution, or robot action was started.
