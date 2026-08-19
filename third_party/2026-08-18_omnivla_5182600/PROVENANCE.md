# Provenance: OmniVLA pinned source snapshot

Import date (local, UTC): 2026-08-19T05:57:23Z
Task: `.trellis/tasks/08-18-omnivla-offline-smoke`
Evidence label after this step: `imported` (source only; no run claim).

## Upstream identity

| Field | Value |
|---|---|
| Canonical repository | https://github.com/NHirose/OmniVLA |
| Default branch | `main` |
| Pinned commit | `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68` |
| Commit tree hash | `c2cdba2b3ca036684007fe4ab1c12ada73623cc5` |
| Commit date (author) | 2026-03-24 21:34:31 -0700 |
| Commit author | Noriaki Hirose |
| Commit subject | `Add publication` |
| License | MIT (`OmniVLA/LICENSE`; original copyright Moo Jin Kim, Chelsea Finn, Percy Liang 2025; modifications Noriaki Hirose, Catherine Glossop, Dhruv Shah, Sergey Levine 2025) |
| Paper | OmniVLA: An Omni-Modal Vision-Language-Action Model for Robot Navigation, https://arxiv.org/abs/2509.19480 |
| Project page | https://omnivla-nav.github.io/ |

The pinned commit is the one recorded by the 2026-08-16 survey
(`.pipeline/survey/2026-08-16_lite3_vla_open_source_reproduction_survey.md`,
sections 4.1 and 7.3, and
`.pipeline/survey/2026-08-16_lite3_vla_open_source_reproduction_survey/top5_code_evidence.tsv`).
It was re-verified on import: `git rev-parse HEAD` matched the SHA exactly and
`git status --short` was empty before export.

## Import method

Snapshot, not submodule, so the evidence is self-contained and every local
modification stays visible in the parent repository's `git diff`.

```bash
# scratch clone (session scratchpad, not durable storage)
git clone https://github.com/NHirose/OmniVLA.git OmniVLA-clone
cd OmniVLA-clone
git checkout 5182600cb4a9ee07684e17cdd2a6cbafc56b8a68
git rev-parse HEAD          # must equal the pinned SHA
git status --short          # must be empty
git rev-parse 'HEAD^{tree}' # c2cdba2b3ca036684007fe4ab1c12ada73623cc5

# byte-identical export without any .git directory
mkdir -p third_party/2026-08-18_omnivla_5182600/OmniVLA
git archive HEAD | tar -x -C third_party/2026-08-18_omnivla_5182600/OmniVLA

# manifest
cd third_party/2026-08-18_omnivla_5182600/OmniVLA
find . -type f | sort | xargs shasum -a 256 > ../SOURCE_MANIFEST.sha256
```

## Snapshot facts

| Field | Value |
|---|---|
| Local path | `third_party/2026-08-18_omnivla_5182600/OmniVLA/` |
| Nested `.git` | none (`git archive` export) |
| Tracked file count | 108 |
| On-disk size | 1.3M |
| Manifest | `third_party/2026-08-18_omnivla_5182600/SOURCE_MANIFEST.sha256` |
| Manifest SHA-256 | `66126da6cc9f0aafb7afb0381ed860a4652190c5a12b74c756c68782b76a24a0` |

Verify at any time:

```bash
cd third_party/2026-08-18_omnivla_5182600/OmniVLA
shasum -a 256 -c ../SOURCE_MANIFEST.sha256 | grep -v ': OK$'   # prints nothing
```

## Modification policy

This tree is **pristine and read-only**. No local edit is ever applied here.
Execution uses a working copy at
`.pipeline/experiments/2026-08-18_omnivla_offline_smoke/work/OmniVLA/`
(git-ignored) built as *pristine + `patches/*.patch`*; every patch is a tracked
unified diff with a recorded rationale.

## Checkpoints

Model weights are not part of this snapshot. Their pinned Hugging Face
revisions, sizes, and SHA-256 values are tracked in
`third_party/2026-08-18_omnivla_5182600/checkpoints/CHECKPOINT_MANIFEST.tsv`
with download instructions in `checkpoints/README.md`. The weight bytes
themselves are local-only under a path-specific `.gitignore` entry.

## Claim boundary

This document establishes `imported` only: a pinned upstream source snapshot
exists locally with verifiable hashes. It is not `reproduced`, `integrated`,
or `validated`, and it makes no statement about Lite3.
