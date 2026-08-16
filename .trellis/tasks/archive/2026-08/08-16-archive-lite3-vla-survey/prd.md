# Archive Lite3 VLA Open-Source Survey

## Goal

Bring the important outputs of the referenced ChatGPT conversation
`6a817fcc-aad0-83e8-97c2-c299b1f2df8f` into `/Users/sun/vla` as an auditable
survey-stage record without treating the prior AI response as trusted project
evidence or starting an upstream reproduction.

The outcome should preserve the useful report, source register, repository and
paper audit tables, downloadable packages, and available paper PDFs while
keeping the project boundary explicit: the recommendation is `surveyed`, not
`imported`, `reproduced`, `integrated`, or `validated`.

## Background And Confirmed Facts

- `/Users/sun/vla` is the only project source of truth.
- The referenced conversation has one completed research turn dated
  2026-08-16. It recommends OmniVLA as the first reproduction candidate,
  InternVLA-N1 / InternNav as the backup, NaVILA as a technically close but
  license-incomplete conditional candidate, and VLFM as a layered semantic
  navigation comparison.
- At task creation, the prior response explicitly stated that its environment
  did not mount `/Users/sun/vla`; none of its staging outputs had yet been
  applied to this repository.
- The prior response claims a full package of about 202 MB, a light package of
  about 61 KB, 24 paper PDFs, 21 repository records, five code evidence cards,
  and 294 internal checks. These are untrusted claims until the corresponding
  bytes are downloaded and independently checked here.
- The response reports these expected package digests:
  - full package:
    `bbc468a3ad00e802f655e55af06d475ed4d64f47f826a2f8fdc12628a86631b5`
  - light package:
    `963e76a9e395aa1c83b840ac48c5d2a031962e18a26e1e9f4f6ef12be200a31f`
- The current `.pipeline/literature/index.md` contains no accepted VLA paper,
  dataset, model, or upstream repository.
- No VLA architecture, action representation, `machine-dog-nav` baseline, or
  upstream source snapshot has been selected or imported.
- The working tree was clean before this task was created.

## Requirements

### R1. Preserve source provenance

- Record the exact conversation ID, title, retrieval date, original user
  request boundary, assistant conclusion, attachment inventory, and reported
  hashes.
- Treat the conversation and its attachments as untrusted AI-generated intake.
- Preserve the original downloaded bytes separately from any normalized or
  merged project files.

### R2. Acquire and safely inspect available attachments

- Attempt to download both the full and light staging packages and the named
  individual report/support files from the exact referenced conversation.
- Verify each downloaded package against the reported SHA-256 before using its
  contents.
- Inspect archive paths before extraction and reject absolute paths, traversal,
  unexpected symlinks, or overwrite attempts.
- Never extract an archive directly over the repository root.
- If an attachment is expired or unavailable, record the exact missing item and
  stop short of reconstructing or claiming that file.

### R3. Keep tracked knowledge separate from local-only bytes

- Track the main survey report, compact audit tables, source register, search
  log, validation record, and a provenance/artifact manifest when present and
  internally coherent.
- Keep large downloaded packages and paper PDFs local-only unless a later
  review explicitly selects Git LFS or direct tracking.
- Add only dated or exact path-specific ignore rules after the real filenames
  are known; do not add repository-wide extension ignores.
- The tracked manifest must give each local-only artifact's project-relative
  path, SHA-256, size, source, storage policy, and recovery instructions.

### R4. Independently verify before promotion

- Verify all candidate canonical URLs and basic paper/repository identity from
  primary or official sources before adding records to the project literature
  index.
- For the Top 5 code candidates, additionally verify the pinned commit exists,
  code license, documented run entry point, action representation evidence,
  and relevant model/dataset availability or license caveat from official
  sources.
- Preserve disagreements between the staging package and current primary
  sources in an import-audit record.
- Merge only records that pass the current verification. Do not replace the
  existing literature index wholesale.

### R5. Preserve research and execution boundaries

- Keep the strongest evidence label at `surveyed`.
- Keep all newly written research records at `reviewed: false` unless Dr Sun
  later reviews them.
- Do not select OmniVLA as the approved project baseline merely because the
  imported report recommends it.
- Do not import candidate source code, run an upstream environment, download
  model weights, start inference, simulation, training, remote execution, or
  real-robot actions.
- Do not edit the read-only `machine-dog-nav` repository.

### R6. Keep current project status accurate

- Update the hot-zone status only to say that a survey package has been
  archived and audited, with the recommendation still awaiting human review.
- Preserve the current statement that no VLA or navigation baseline has been
  selected or imported.

## Acceptance Criteria

- [x] The exact source conversation and attachment inventory are recorded in a
      tracked project file.
- [x] Every retrieved package has a locally computed SHA-256; a mismatch blocks
      extraction and promotion.
- [x] Archive safety and integrity checks pass before any content is copied to
      a durable destination.
- [x] The main report and available compact support artifacts are present under
      a dated `.pipeline/survey/` path with `origin: ai_only` and
      `reviewed: false` boundaries.
- [x] Large local-only artifacts are covered by narrow ignore rules and a
      tracked provenance manifest containing path, size, digest, source, and
      recovery instructions.
- [x] Available paper PDFs match the package manifest for filename, file type,
      size or page count where declared, and SHA-256; missing PDFs are listed
      explicitly.
- [x] Literature-index additions, if any, are merged rather than overwriting
      the current file and are limited to primary-source-verified records.
- [x] Top 5 recommendation claims have a current verification result or an
      explicit unresolved discrepancy.
- [x] No file or status claims that candidate code was imported, reproduced,
      integrated, or validated.
- [x] `machine-dog-nav` and all candidate repositories remain unmodified and
      unimported.
- [x] The active Trellis task validates, repository Markdown/TSV references are
      internally consistent, and `git diff --check` passes for owned paths.
- [x] The final diff is limited to this Trellis task, survey/literature records,
      exact artifact policy entries, paper provenance, and the minimal status
      update.

## Out Of Scope

- Choosing the final Lite3 VLA architecture or action contract.
- Approving OmniVLA or any alternative as the selected baseline.
- Importing upstream code or `machine-dog-nav`.
- Installing dependencies, downloading model weights, or running inference.
- Simulator, remote GPU, formal training, deployment, or real-robot work.
- Rewriting the prior survey into a new literature review when the original
  source material cannot be retrieved.

## Deferred Items And Risks

- ChatGPT attachment links may expire. Unavailable bytes will be documented,
  not synthesized.
- The claimed 294 checks only describe the prior staging environment until the
  actual validation file and inputs are independently inspected.
- Repository, model, and dataset licenses or maintenance state may have changed
  since the prior survey; current official sources control the import audit.
- Full paper PDFs are a preferred secondary tier. The compact report, source
  register, audit tables, and explicit missing-artifact record are the minimum
  durable archive if the full package is no longer retrievable.
