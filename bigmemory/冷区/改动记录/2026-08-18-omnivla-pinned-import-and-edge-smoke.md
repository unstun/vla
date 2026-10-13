---
origin: human_directed
reviewed: false
date: 2026-08-18
---

> [摘要] Pinned OmniVLA-edge ran on macOS CPU with recorded patches; the original 8B result here is manifest-only. This is historical, not current runtime state.


# OmniVLA Pinned Import And Edge Offline Smoke

## Decision

Dr Sun confirmed OmniVLA as the first low-cost VLA reproduction candidate on
2026-08-18, closing the survey gate opened by
`.pipeline/survey/2026-08-16_lite3_vla_open_source_reproduction_survey.md`
(section 7). Task `08-18-omnivla-offline-smoke` executed the minimal offline
reproduction: pinned source import, pinned checkpoint provenance, an isolated
environment, and the official edge inference entry point.

## Pinned Identities

- Repository: `https://github.com/NHirose/OmniVLA`, MIT
- Commit: `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68`
- Tree: `c2cdba2b3ca036684007fe4ab1c12ada73623cc5`
- Snapshot: `third_party/2026-08-18_omnivla_5182600/OmniVLA/`, 108 files, no
  nested `.git`, `SOURCE_MANIFEST.sha256` verified before and after all runs
- Edge checkpoint: `NHirose/omnivla-edge` @
  `b1361b7e24f101edea795a98b00a826b61a97394`, MIT, `omnivla-edge.pth`
  434,276,465 B, SHA-256
  `f93b056f124380899fce3e087a5c2b41ce4d8c07e211daad52b6ebf02e80d04d`,
  downloaded and verified against the Hugging Face LFS oid
- 8B checkpoint: `NHirose/omnivla-original` @
  `e36a84d4923c041149d441f93f3bdb7092bb5f07`, MIT, 26 files,
  15,998,670,997 B — manifest only, bytes not downloaded
- CLIP `ViT-B/32`: MIT, SHA-256 `40d365715913c9da98579312b702a82c18be219cc2a73407c4526f58eba950af`,
  relocated into `third_party/2026-08-18_omnivla_5182600/checkpoints/clip/`

Weight bytes stay local-only under one dated, path-specific `.gitignore` block
with tracked manifests, per `AGENTS.md` rule 9.

## Execution Contract

The pristine snapshot is never edited. Execution uses a git-ignored working copy
`.pipeline/experiments/2026-08-18_omnivla_offline_smoke/work/OmniVLA` rebuilt by
`scripts/make_workcopy.sh` as *pristine + `patches/0001..0005`*, and the rebuild
was verified byte-identical to the tree the runs used.

## Result

Eight successful runs of the official `python inference/run_omnivla_edge.py` on
the sample inputs shipped upstream, CPU float32, macOS arm64: shape `(8, 4)`,
all finite, heading components unit-norm, `(v, ω)` inside upstream's own clip
and limiter bounds, peak RSS 3.15-3.28 GiB, 0.26-0.32 s per forward pass.
Identical configurations produce bit-identical trajectories, so the sweep deltas
are attributable to the inputs.

Language sensitivity on this single sample image is present: replacing
`"blue trash bin"` with `"turn left and go to the door"` shifts the trajectory
endpoint 0.435 m and flips the commanded yaw rate sign. Commanded linear
velocity stayed pinned at the 0.3 m/s limiter ceiling for every language prompt,
including `"stop, do not move forward"` — this model in this configuration has
no stop behaviour, which a future Lite3 safety layer must not inherit.

Against the authors' shipped reference figure `inference/1_ex_omnivla_edge.jpg`
(their own rendering of the default configuration), the local figure matches
visually: mean absolute pixel difference 0.0208/255 over the whole image, all
1,559 differing pixels confined to the drawn trajectory curve, camera panels
pixel-identical.

## Evidence Labels

- OmniVLA source: `imported`
- `omnivla-edge`: `imported` and `reproduced`, with the caveat "macOS arm64,
  CPU, float32, no FlashAttention, patches 0001-0005 — not the official CUDA
  environment, and one sample forward pass, not an evaluation"
- `omnivla-original` (8B): `imported` at manifest level only; the probe stopped
  at the pre-declared 22 GB available-memory guard (17.27 GB measured), so the
  weights were not downloaded and no forward pass exists

Nothing is `integrated` or `validated`.

## Boundary

No training, no benchmark, no dataset download, no ROS, no simulator, no
`machine-dog` or `machine-dog-nav` access, no remote execution, no robot
actuation, and no Lite3 interface work. The `(v, ω)` values are numbers in JSON
files and were never sent anywhere.

## Affected Paths

- `third_party/2026-08-18_omnivla_5182600/`
- `.pipeline/experiments/2026-08-18_omnivla_offline_smoke/`
- `.pipeline/experiments/README.md`
- `.gitignore` (one dated block)

## Commit

Not committed by the executing sub-agent; review and commit belong to the
primary session.
