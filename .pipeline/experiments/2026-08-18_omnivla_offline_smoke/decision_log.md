---
origin: human_directed
reviewed: false
status: draft
---

# Experiment Decision Log: 2026-08-18 OmniVLA offline smoke (edge, CPU)

Sections **Parent** through **Claim Boundary** were written before any model
process was started. **Results** is appended afterwards and the pre-run sections
are not edited once results are known.

## Parent

- Parent implementation or checkpoint: none in this repository. This is the
  first execution of any VLA code here; the prior state is `surveyed` only
  (`.pipeline/survey/2026-08-16_lite3_vla_open_source_reproduction_survey.md`).
- Upstream source: https://github.com/NHirose/OmniVLA, branch `main`,
  commit `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68`,
  tree `c2cdba2b3ca036684007fe4ab1c12ada73623cc5`, MIT.
  Local pinned snapshot: `third_party/2026-08-18_omnivla_5182600/OmniVLA/`.
- Checkpoints (Hugging Face, MIT, pinned revisions):
  - `NHirose/omnivla-edge` @ `b1361b7e24f101edea795a98b00a826b61a97394`
    (`omnivla-edge.pth`, 434,276,465 B, sha256
    `f93b056f124380899fce3e087a5c2b41ce4d8c07e211daad52b6ebf02e80d04d`,
    downloaded and hash-verified);
  - `NHirose/omnivla-original` @ `e36a84d4923c041149d441f93f3bdb7092bb5f07`
    (26 files, 15,998,670,997 B, manifest recorded from the HF API).
- Local repository HEAD at task start: `87a3b3e8c77374511cdfa5e41664fa23676467c2`
  (working tree carried one unrelated pre-existing change, ` M AGENTS.md`,
  which this task does not touch).

## Evidence And Motivation

- Observed evidence: the 2026-08-16 survey (section 7) selected OmniVLA as the
  first low-cost VLA reproduction candidate for Lite3 and specified a minimal
  offline smoke test. Its section 4.1 records upstream issues #28 (language
  prompt may not change the output), #27 (trajectory scale), #26 (velocity
  clipping order).
- Why a run is justified: Dr Sun confirmed OmniVLA on 2026-08-18, which closes
  the survey gate. Nothing beyond `surveyed` can be claimed until an original
  upstream command actually runs and produces recorded artifacts. The run is
  offline, involves no robot and no network-connected actuation, and is
  bounded in time and memory.

## Exact Scope

One recorded change group:

1. Pinned import of the upstream tree and checkpoint provenance (no execution).
2. `inference/run_omnivla_edge.py` executed unmodified in behaviour, from a
   working copy = pristine + `patches/*.patch`, on the sample inputs shipped in
   the repository (`inference/current_img.jpg`, `inference/goal_img.jpg`), with
   the upstream default modality (language prompt only, `lan_inst_prompt =
   "blue trash bin"`, modality_id 7).
3. A sensitivity sweep of at least three configurations varying only the
   language prompt and the goal modality flags that upstream itself exposes in
   the `__main__` block (README: "settings around line 425").
4. Optional, strictly guarded probe of the 8B `inference/run_omnivla.py`.

Not in scope: training, fine-tuning, benchmark evaluation, dataset download,
ROS, simulator, `machine-dog` / `machine-dog-nav`, Lite3 adapters, real-robot
actuation, remote execution.

## Expected Signals

Expected (edge, default modality):

- process exits 0 within the 1800 s wall-clock limit;
- `predicted_actions` has shape `(1, 8, 4)` — 8 waypoints of `[x, y, hx, hy]` —
  and every element is finite;
- the script writes `inference/1_ex_omnivla_edge.jpg` (> 10 KB);
- the PD controller output `(v, ω)` is finite and inside the script's own bounds
  after clipping: `v ∈ [0, 0.5]`, `ω ∈ [-1, 1]`, then the velocity limiter
  keeps `|v| ≤ 0.3` and `|ω| ≤ 0.3`;
- host RSS stays far below 32 GiB (the edge checkpoint is 434 MB).

Expected (sweep): trajectories differ between semantically different prompts.
This is recorded as an observation, not as a pass/fail gate, because a null
result is exactly the condition upstream issue #28 describes and is itself
evidence worth keeping.

Failure signals:

- non-zero exit, uncaught exception, or exit 124 (timeout);
- NaN/Inf anywhere in the waypoints or in `(v, ω)`;
- wrong shape;
- no output image;
- checkpoint hash mismatch, or the pristine manifest failing to re-verify.

Stop conditions:

- environment build > 60 min; edge inference > 30 min per attempt and at most
  3 attempts; sweep > 30 min; 8B probe > 60 min total and at most 2 attempts;
  whole task ≈ 5 h. On reaching a limit: stop, record, report — do not retry
  in a loop.
- 8B probe additionally requires > 60 GB free disk before download and
  ≥ 22 GB available memory before load; never fp32.

## Execution

- Command (edge, default): from `work/OmniVLA`,
  `portable_timeout.pl 1800 /usr/bin/time -l <env>/bin/python inference/run_omnivla_edge.py`
  wrapped by `scripts/run_edge.sh`, which sets `OMNIVLA_RUN_DIR` and collects
  artifacts.
- Environment: conda env `omnivla`, python 3.10.20, torch 2.2.0, torchvision
  0.17.0, numpy 1.26.4, transformers 4.40.1 (openvla-oft fork). Device: CPU —
  upstream's own fallback when `torch.cuda.is_available()` is False. No
  FlashAttention (CUDA-only). Deviations: `env/DEVIATIONS.md`.
- Host: Apple M5, macOS 26.5.2, arm64, 32 GiB unified memory, no CUDA.
- Artifact directory: `.pipeline/experiments/2026-08-18_omnivla_offline_smoke/runs/<UTC>_<tag>/`
  containing `stdout.log`, `stderr.log`, `meta.json`, `outputs.json`, and the
  generated figure.
- Remote copy: none. Everything runs and stays on the local machine.

## Claim Boundary

What this run can establish, at most:

- `imported` for the OmniVLA source at the pinned commit and for the
  `omnivla-edge` checkpoint at its pinned revision (hash-verified);
- `reproduced` for **OmniVLA-edge only**, and only with the explicit caveat
  "macOS arm64, CPU, float32, no FlashAttention — not the official CUDA
  environment; run with the recorded patch series".

What it cannot establish:

- nothing here is `integrated` or `validated`;
- it says nothing about the 8B `omnivla-original` model unless that probe
  actually completes a forward pass and writes the declared artifacts; a
  download or a manifest is only `imported`;
- it says nothing about accuracy, benchmark performance, or the paper's
  reported results — a single sample forward pass is not an evaluation;
- it says nothing about Lite3: no camera calibration, no action interface, no
  navigation or locomotion integration, no robot command was produced or sent;
- a successful environment build, a successful download, or a zero exit code is
  not by itself reproduction evidence.

## Results

Appended 2026-08-19 after execution. The sections above were not edited.

### What ran

Seven successful runs of the official entry point
`python inference/run_omnivla_edge.py` plus one recorded failure, all on
CPU/float32, macOS arm64, from `work/OmniVLA` = pinned snapshot + patches
0001–0004. Every process was wrapped in a 1800 s wall-clock limit; none came
close (3–5 s each).

### Failure recorded before success (attempt 1 of 3)

`runs/20260819T061412Z_edge_default_lan_bluetrashbin_failed_get_device/`
— exit 1, 85 s (most of it the one-time CLIP ViT-B/32 download):

```
  File ".../inference/model_omnivla_edge.py", line 272, in forward
    src_key_padding_mask = torch.index_select(self.all_masks.to(device), 0, no_goal_mask)
RuntimeError: Device index must not be negative
```

Cause: `model_omnivla_edge.py` uses `Tensor.get_device()` (lines 49 and 241),
which returns `-1` for CPU tensors, and `.to(-1)` is invalid. This is a
CUDA-only assumption in upstream code, not an environment problem. Fixed by
`patches/0004-edge-cpu-device-get-device-minus-one.patch`
(`get_device()` → `.device`, identical behaviour on CUDA). Attempt 2 succeeded;
the third attempt was not needed.

### Signals observed against the pre-run expectations

| Pre-run expectation | Observed |
|---|---|
| exit 0 within 1800 s | yes — exit 0, 3–5 s wall per run |
| shape `(1, 8, 4)`, all finite | yes — `(8, 4)` per sample, all finite, in all 7 runs |
| output figure > 10 KB | yes — 117.8–120.6 KB `1_ex_omnivla_edge.jpg` per run |
| `v ∈ [0, 0.5]`, `ω ∈ [-1, 1]` after PD clip | yes |
| `|v| ≤ 0.3`, `|ω| ≤ 0.3` after the limiter | yes |
| RSS far below 32 GiB | yes — peak RSS 3.15–3.28 GiB |
| trajectories differ between different prompts | yes — see the table |

Additional check not required by the plan: heading components satisfy
`hx² + hy² = 1` to within 1e-3 in every run, consistent with the `F.normalize`
in `model_omnivla_edge.py`.

Control: the default configuration was run twice
(`..._edge_default_lan_bluetrashbin` and `..._edge_default_repeat_determinism`)
and the two trajectories are **bit-identical** (max abs difference exactly 0.0).
Inference on this path is deterministic, so every difference in the table below
is caused by the input change and not by run-to-run noise.

### Sweep

| run | modality | prompt | exit | wall s | peak RSS MiB | finite | shape | max abs Δ (all) | max abs Δ (x,y) | max abs Δ (heading) | endpoint shift m | v | ω | forward s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `default_lan_bluetrashbin` | 7 (language only) | `blue trash bin` | 0 | 5 | 3207.7 | True | (8, 4) | 0.0000 (baseline) | 0.0000 | 0.0000 | 0.0000 | 0.300000 | -0.121271 | 0.280 |
| `lan_turnleftdoor` | 7 (language only) | `turn left and go to the door` | 0 | 3 | 3254.8 | True | (8, 4) | 4.2927 | 4.2927 | 0.4179 | 0.4350 | 0.300000 | 0.128396 | 0.276 |
| `lan_stopdontmove` | 7 (language only) | `stop, do not move forward` | 0 | 4 | 3213.0 | True | (8, 4) | 1.9214 | 1.9214 | 0.1985 | 0.1997 | 0.300000 | -0.010896 | 0.317 |
| `goalimage_only` | 6 (image only) | `xxxx` | 0 | 4 | 3283.2 | True | (8, 4) | 4.6269 | 4.6269 | 0.8868 | 0.6150 | 0.262615 | 0.300000 | 0.261 |
| `pose_only` | 4 (pose only) | `xxxx` | 0 | 4 | 3239.8 | True | (8, 4) | 3.5357 | 3.5357 | 0.2413 | 0.3536 | 0.222376 | -0.300000 | 0.291 |
| `pose_and_lan` | 8 (language and pose) | `blue trash bin` | 0 | 4 | 3221.1 | True | (8, 4) | 1.9872 | 1.9872 | 0.2991 | 0.2111 | 0.186486 | -0.300000 | 0.267 |

Deltas are against the upstream-default run. `max abs Δ` is over the raw
normalized waypoints; "endpoint shift" is the distance between the 8th
waypoints after applying upstream's own `metric_waypoint_spacing = 0.1`.

Observation, stated neutrally: on this single sample image the language prompt
does change the output. Replacing `"blue trash bin"` with `"turn left and go to
the door"` moves the endpoint by 0.435 m and flips the commanded yaw rate from
-0.121 to +0.128 rad/s; `"stop, do not move forward"` gives an almost straight
path (ω = -0.011). This is one image and three prompts, so it does **not**
resolve upstream issue #28 in either direction — it only records that the
language pathway is not inert here. Note also that the commanded linear
velocity stays pinned at the 0.3 m/s limiter ceiling for all three language
prompts, including the "stop" prompt: the model has no stop behaviour in this
setup, which is exactly the kind of assumption a Lite3 safety layer must not
inherit.

Changing the goal modality changes the output more than changing the prompt
(image-only: 0.615 m endpoint shift; pose-only: 0.354 m), and both saturate the
angular limiter at ±0.3 rad/s.

### 8B `omnivla-original` probe: SKIPPED at a pre-declared guard

`runs/20260819T061936Z_original_probe_skipped/` records the executed guard
check:

```
[probe] G1 disk      free: 171 GB (need > 60)              -> pass
[probe] G2 memory    available: 17.2 GB (need >= 22)       -> STOP
```

Available memory was a stable 17.27 GB across repeated samples, below the 22 GB
guard written before the runs. The guard was not relaxed. Because the probe does
not run, the 14.90 GiB of weights were not downloaded either (the plan requires
the download only if the probe is attempted); their identity is recorded in
`CHECKPOINT_MANIFEST.tsv` from the Hugging Face API at the pinned revision.

Two further blockers were confirmed by direct execution, so a future GPU-host
task does not have to rediscover them:

- `inference/run_omnivla.py` line 502 calls `torch.cuda.set_device(device_id)`
  unconditionally. On a non-CUDA host this raises
  `ValueError: Expected a cuda device, but got: cpu`. A device patch is required
  before any CPU/MPS probe. It was **not** authored speculatively.
- line 439 uses `torch.autocast("cuda", dtype=torch.bfloat16)`, which on a
  non-CUDA host warns "User provided device_type of 'cuda', but CUDA is not
  available. Disabling" and silently computes in float32 — a numerics change
  that would have to be handled explicitly rather than ignored.
- FlashAttention is probably **not** a blocker for this checkpoint: the pinned
  `config.json` sets no `_attn_implementation`, so transformers would fall back
  to its default attention.

### Resulting labels

- OmniVLA source @ `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68`: **imported**.
- `NHirose/omnivla-edge` @ `b1361b7e…`: **imported** (hash-verified) and
  **reproduced**, with the caveat: macOS arm64, CPU, float32, no FlashAttention,
  patches 0001–0004 applied — not the official CUDA environment, and a single
  sample forward pass, not an evaluation.
- `NHirose/omnivla-original` @ `e36a84d4…`: **imported** at manifest level only
  (bytes not downloaded, no forward pass, no reproduction claim).
- Nothing is `integrated` or `validated`. No Lite3 claim of any kind.

### Post-review addenda (2026-08-19, after the primary AI's review)

Two follow-ups were requested and executed. Neither changes any pre-run section
above, and neither changes a model output.

**CLIP weights moved inside the project.** Upstream `clip.load()` had placed the
354 MB `ViT-B/32` text encoder in `~/.cache/clip`, outside the repository and
against `AGENTS.md` rule 8. It was copied (the user's cache left intact) to
`third_party/2026-08-18_omnivla_5182600/checkpoints/clip/ViT-B-32.pt`,
manifested (MIT, sha256 `40d3657159…` equal to the digest OpenAI embeds in the
download URL), git-ignored in the same dated block, and wired up through
`patches/0005-edge-clip-download-root-in-project.patch` +
`OMNIVLA_CLIP_ROOT`. Re-running the default configuration
(`runs/20260819T062802Z_edge_default_after_clip_relocation/`) gave **max abs
Δ = 0.0** against the original default run — bit-identical trajectory and
identical `(v, ω)` — with `stdout.log` recording the project path as the
resolved CLIP root.

**Comparison against the authors' shipped reference figure.** The pre-run
sections above did not anticipate this check; the pinned tree ships
`inference/1_ex_omnivla_edge.jpg`, the authors' own rendering of exactly the
default configuration. Whole image: mean abs pixel difference 0.0208/255,
0.0448 % of pixels differing by more than 16. Trajectory panel: 0.0415/255 and
0.0896 %. All 1,559 differing pixels lie on the drawn trajectory curve
(x 1984-2285, y 153-765); the camera panels are pixel-identical.

This upgrades the confidence in the edge reproduction from "well-formed output"
to "visually matches the authors' published result for this configuration", but
it does **not** upgrade the label: it is still a rendered-figure comparison, not
a numeric one, because upstream publishes no arrays. The `reproduced`
(non-official environment) label and every claim boundary above stand unchanged.
