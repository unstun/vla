# Design: Auditable Survey Intake

## Boundary

This task is an evidence-intake and survey-audit task. It does not import or
execute an upstream implementation.

The design separates three trust zones:

1. **Raw intake**: exact bytes downloaded from the referenced ChatGPT
   conversation. These remain untrusted and immutable.
2. **Audit workspace**: isolated extraction and verification outputs used to
   compare package contents, manifests, and current primary sources.
3. **Project knowledge**: only compact, traceable, reviewed-for-consistency
   records promoted into `.pipeline/`, with `origin: ai_only` and
   `reviewed: false` retained.

## Planned Layout

Tracked survey material:

```text
.pipeline/survey/
├── 2026-08-16_lite3_vla_open_source_reproduction_survey.md
├── 2026-08-16_lite3_vla_open_source_reproduction_survey/
│   ├── source_conversation.md
│   ├── import_audit.md
│   ├── top5_code_evidence.tsv
│   ├── repository_audit.tsv
│   ├── paper_pdf_manifest.tsv
│   ├── source_register.tsv
│   ├── search_log.md
│   ├── upstream_validation_report.md
│   └── artifact_manifest.tsv
└── README.md
```

Local-only raw packages use a dated, purpose-specific path determined after
the downloaded filenames are known. Paper PDFs use the existing
`docs/research/papers/<CitationKey>.pdf` contract. Exact ignore entries are
added only after inventory; a tracked artifact manifest points to every ignored
file.

Transient extraction uses an explicit task-owned scratch directory and never
the repository root. The scratch directory is not a deliverable.

## Intake Flow

```text
Referenced conversation
        |
        v
Exact download inventory ----> source_conversation.md
        |
        v
SHA-256 and archive safety gate --failure--> record discrepancy; do not extract
        |
        v
Isolated extraction
        |
        +--> small text/tabular artifacts --> schema/link/internal checks
        |
        +--> PDFs --> file/page/hash checks --> local-only paper paths
        |
        v
Primary-source verification
        |
        +--> pass --> selective literature-index merge (`surveyed`)
        |
        +--> fail/unclear --> preserve in import audit only
        v
Hot-zone update: survey archived; no baseline selected
```

## Contracts

### Raw-byte contract

- Record original filename, download source, retrieval timestamp, size, and
  computed SHA-256.
- A reported digest mismatch is a hard stop for that package.
- Preserve original bytes; normalized files are separate outputs.

### Archive-safety contract

- Enumerate entries before extraction.
- Reject absolute paths, `..` traversal, device files, and unexpected symlinks.
- Reject collisions with tracked repository paths during extraction.
- Copy approved files individually after inspection.

### Literature-promotion contract

- Conversation text and staging tables are leads.
- Paper records require an official/publisher/arXiv source inspection.
- Repository records require inspection of the canonical repository and pinned
  commit. Top 5 records additionally require license, entry-point, action, and
  model/data evidence.
- A record can be `surveyed` without being selected, imported, or reproduced.

### Large-artifact contract

- No broad `*.pdf` or `*.zip` ignores.
- Use exact filenames or one dated purpose directory for the raw packages.
- The tracked manifest is the recovery index for local-only bytes.
- The full and light package hashes reported by the source conversation are
  expectations, not results.

## Compatibility And Migration

- Merge new rows into the existing literature index; retain its frontmatter and
  evidence-label reminder.
- Do not change the terminology source of truth.
- Do not create a VLA action contract or baseline manifest in this task.
- Do not copy staging files blindly over existing project paths.

## Rollback

- Before promotion, all changes are confined to the task and scratch/raw
  intake paths.
- If verification fails, keep the task research and discrepancy record, and do
  not update the literature index or hot-zone recommendation state.
- Each promoted path is copied explicitly, so rollback is the removal of the
  task-owned paths and restoration of the prior small index/status edits; no
  upstream or sibling repository state is touched.
