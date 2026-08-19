# Journal - sun (Part 1)

> AI development session journal
> Started: 2026-08-16

---



## Session 1: Archive and audit Lite3 VLA survey

**Date**: 2026-08-16
**Task**: Archive and audit Lite3 VLA survey
**Branch**: `main`

### Summary

Archived the referenced survey conversation, verified both package hashes and archive safety, stored 24 paper PDFs as local-only artifacts with a tracked manifest, merged 24 paper and 21 repository records at surveyed status, rechecked the Top 5 from official sources, and preserved the no-import/no-runtime boundary.

### Git Commits

| Hash | Message |
|------|---------|
| `3f782c982e5758d2800e5b6addd1efbf3c0e83a5` | (see git log) |

### Status

[OK] **Completed**


## Session 2: Migrate VLA repository into phdproject

**Date**: 2026-08-18
**Task**: Migrate VLA repository into phdproject
**Branch**: `main`

### Summary

Moved the complete VLA repository to /Users/sun/tongbu/study/phdproject/vla without an old-path symlink; preserved Git, nested Vendor state, research evidence, and relative links; updated live path declarations and passed full harness validation.

### Git Commits

| Hash | Message |
|------|---------|
| `f5f9f8f` | (see git log) |

### Status

[OK] **Completed**


## Session 3: OmniVLA offline reproduction — pinned import and edge smoke

**Date**: 2026-08-18
**Task**: `08-18-omnivla-offline-smoke`
**Branch**: `main`

### Summary

Imported OmniVLA at pinned commit `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68` as a
byte-identical snapshot with a SHA-256 manifest, recorded checkpoint provenance for
`omnivla-edge` (downloaded, hash-verified) and `omnivla-original` (manifest only),
relocated the CLIP ViT-B/32 weights into the project, built an isolated conda env in
which all official pins installed exactly, and ran the official
`inference/run_omnivla_edge.py` eight times on CPU. Two upstream blockers were found
and fixed by patch against a working copy, never the snapshot: `pyproject.toml` is
invalid TOML (blocks `pip install -e .` on every platform) and `Tensor.get_device()`
returns `-1` on CPU. Outputs are shape `(8, 4)`, finite, deterministic across
identical configurations, and match the authors' shipped reference figure visually
(mean absolute pixel difference 0.0208/255, differences confined to the trajectory
curve). The 8B probe stopped at a pre-declared 22 GB memory guard.

### Evidence

- `.pipeline/experiments/2026-08-18_omnivla_offline_smoke/README.md`
- `.pipeline/experiments/2026-08-18_omnivla_offline_smoke/decision_log.md`
- `third_party/2026-08-18_omnivla_5182600/PROVENANCE.md`

### Labels

`imported` for the source and all checkpoint identities; `reproduced` for
OmniVLA-edge only, with the caveat "macOS arm64 / CPU / float32 / no FlashAttention /
patches 0001-0005, not the official CUDA environment"; `omnivla-original` remains
manifest-level `imported` with no forward pass. Nothing `integrated` or `validated`,
and no Lite3 claim.

### Next Gate

Dr Sun reviews the evidence bundle and patch series; a GPU host must be designated
before the official 8B reproduction, and the Lite3 input/action contract remains
undefined.

### Git Commits

| Hash | Message |
|------|---------|
| — | not committed by the executing sub-agent; review and commit belong to the primary session |

### Status

[OK] **Completed** (implementation and follow-ups; awaiting review)
