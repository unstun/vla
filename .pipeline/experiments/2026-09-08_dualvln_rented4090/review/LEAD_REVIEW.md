---
origin: ai+local+remote_verification
date: 2026-09-09
status: corrections_required
reviewer: Codex
stage: experiment_and_analysis
---

# Lead review of the Opus return

**Verdict: corrections required.** Accept the recorded BF16 inference and the
existence of a functioning model-to-Habitat loop with two playable local videos.
Both navigation trials failed the declared stop-and-distance criterion. Reporting,
instrumentation, visualization, and local evidence return need corrections before
the execution package can be closed. This review did not rerun the model.

Paths below are relative to the experiment unless explicitly identified as
upstream. Preserve `OPUS_RETURN.md` and the historical run records as submitted.

## Accepted evidence

- `runs/inference_v5/probe_record.json`: 8,383,538,891 parameters counted as
  BF16; all checkpoint loading-error lists empty; actual outputs across 40
  released fixture frames. All 40 input hashes match the local fixture bytes.
  This is an open-loop inference result, with dummy depth and pose.
- Comparing the pristine InternNav snapshot with `work/InternNav` found exactly
  two changed files, both recorded lazy-import shims. The pristine source is
  pinned at `7a5c62400ac45b313d9b709c740b64191556a242`.
- Both 200-step simulation recordings terminate at `step_cap`, with no learned
  STOP. v2 travelled 6.6544 m, reached a minimum geodesic distance of 1.0751 m,
  and ended at 2.5458 m. These distances do not make the trial successful.
- Both local MP4s match the returned SHA-256 values and decode to 200 frames at
  4 fps. `review/v2_decoded_contact.jpg` was extracted from the local v2 MP4 and
  visually inspected. These are simulation videos, not fixture slideshows.
- A fresh read-only remote check verified all 864 observation PNGs and both
  MP4s against `setup/observation_manifest.json`: no missing files or mismatched
  hashes. See `review/remote_verification.json`. No episode observation PNGs
  have yet returned locally. The remote GPU snapshot showed 2,903 MiB in use;
  that snapshot alone is not proof of historical process continuity.

## Findings

### R1 — High: reported global peaks and component timings are not measured that way

`scripts/probe.py:179` and `scripts/sim_runner.py:234` reset the CUDA peak
counter every frame or outer step. The final `vram_peak` therefore describes the
last interval, not the whole run. The simulator records its per-step peak before
the extra look-down inference (`sim_runner.py:274` versus `:295`).

| Run | Reported final-interval allocated MiB | Maximum recorded outer/frame interval MiB |
| --- | ---: | ---: |
| inference_v5 | 16,190.977 | 17,060.821 |
| sim_episode_v1 | 16,102.560 | 16,753.999 |
| sim_episode_v2 | 17,054.109 | 16,753.999 |

The v2 final interval includes a look-down call after its outer-step sample.
Intermediate look-down peaks were not retained, so a precise global peak cannot
be recovered for either simulator run. `nvidia-smi` values are snapshots, not a
sampled device peak. Keep these scopes explicit; do not manufacture missing data.

The latency groups are end-to-end `agent.step` invocations with/without S2,
not isolated S2 and S1 timings. The fixture has 21 calls containing S2 and 23
trajectory-bearing calls, including four containing both. The episode tables
omit 1 and 9 additional look-down S2 calls: total S2 invocations are 51 and 52,
not 50 and 43. Successful pixel-goal branches also invoke S1 in that same call;
the code and records imply 2 and 17 S1 invocations, but those look-down trajectory
arrays were not saved. Label reconstructed counts separately from direct logs.

The claim that `expandable_segments` reduced reserved memory compares different
workloads, not a controlled allocator experiment. Retain the setting and observed
values; withdraw the causal claim.

### R2 — High: empty output can be misreported as learned STOP

`scripts/sim_runner.py:269` converts empty output into `STOP` with source
`empty`. The branch at `:288` then treats it as learned STOP. This could turn a
parsing/inference failure near the goal into false success. Neither existing
episode used this fallback, so the observed failures are unchanged.

Require explicit S2 STOP provenance. Distinguish empty output, S1 padding/replan,
and learned STOP; cover these cases with a small regression test. The historical
v2 record's `success: true` is distance-only. Preserve that original record and
provide a clearly identified corrected analysis instead of rewriting history.

### R3 — Medium: the videos do not display the actual pixel-goal views

`scripts/make_video.py:65` always selects the level-camera image and `:100`
only draws `output_pixel`. That field is null on every step in both episodes.
All 1/9 pixel goals live in `look_down_output_pixel`, tied to
`look_down_rgb_path`. Thus neither current video shows the claimed pixel-goal
markers. Draw them on their matching tilted view, using its recorded input gain,
as an inset or separate frame. Do not project those pixels onto the level image
without a camera transformation.

Also label cached text as the last S2 output, and distinguish the pre-action
image from the post-action geodesic value. Save corrected videos under new names
and decode/inspect representative look-down frames. No model rerun is needed.

### R4 — Medium: causal explanations exceed the available evidence

Lower average brightness than the released fixtures establishes an input
difference. It does not establish the model's training distribution, prove that
exposure caused the failure, or make a software RGB gain equivalent to physical
camera auto-exposure. The decoded video also contains large black/missing-render
regions and saturated areas; their cause has not been established.

v1 remains a failed system trial. v2 is one trial with an explicit brightness
transform. Their different behavior motivates a hypothesis, not a model-versus-
simulator attribution. All observed pixel goals occurring after look-down is a
branch-use observation, not an ablation proving camera tilt causally necessary.
Remove these stronger claims from the corrected return.

### R5 — Medium: the custom adapter does not match the official Habitat input loop

The pristine upstream file
`internnav/habitat_extensions/vln/habitat_vln_evaluator.py:349` collects a tilted
RGB/depth view each step, and `:450`/`:488` use tilted goal and current views for
S1. The custom runner queries the realworld agent with level RGB/depth at
`scripts/sim_runner.py:224`/`:244` between explicit look-down requests. Subsequent
S1 calls can therefore pair a cached tilted goal view with a level current view.
Document this camera/cadence difference before assigning navigation failures to
the model. The existing test is a custom integration trial, not evaluator parity.

v2's first look-down is step 78 and first forward action is step 80; steps 0–79
were not all rotations. The upstream `forward_action > MAX_STEPS` guard at
`:512` is inside the pixel/S1 branch and cannot explain the initial 78 steps
before the first pixel goal. Missing scene semantic annotations are likewise
not a demonstrated cause without tracing their use in the policy's inputs.

### R6 — High for closure: the unique-output sync gate remains open

The 864 PNGs total **101,913,541 bytes** and remain remote. The verified local
MP4s are lossy level-camera views and cannot replace raw RGB/depth or tilted
observations. Complete a resumable transfer and verify every manifest entry
locally. Audit other unique evidence cited in the return for the same gap.

The saved runner's success computation was edited after the historical runs.
Do not claim its current bytes are the exact executed source. For future runs,
retain immutable script/config hashes and a runnable source snapshot or patch.

## Disposition

Use `OPUS_CORRECTION_PACKAGE.md` for the bounded correction pass. Keep the task
at `review`; execution evidence is partially accepted, archival is incomplete,
and no navigation validation or paper benchmark reproduction is accepted.
Nothing was staged or committed by this review.
