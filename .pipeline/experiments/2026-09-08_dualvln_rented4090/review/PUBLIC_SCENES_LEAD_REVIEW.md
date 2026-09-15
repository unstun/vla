---
origin: ai+local_evidence+readonly_remote_verification
date: 2026-09-09
reviewer: Codex
status: corrections_required
runtime_verdict: accepted_for_custom_public_scene_functional_test
stage: experiment_and_analysis
---

# Public-scene execution review

**Accept the demonstrated runtime result.** The official InternNav evaluator
executed on the rented RTX 4090 and produced real navigation, learned STOPs,
metrics, and playable local videos. Reporting and derived-artifact sync need
corrections before final closeout. No new model execution was performed during
this review. This remains an official evaluator on custom public-scene tasks,
not R2R benchmark reproduction.

Paths below are relative to the experiment directory.

## Independently verified

- Five supervisor records show exit 0, no timeout, and **721.889 seconds** total
  wall time. Actual input records invoke `scripts/eval/eval.py` from the worktree.
- The frozen annotation SHA-256 is
  `49f1bff7e1623e312b303b4b938a2c821c015e8ebad001a66c01a0f72e597889`.
  All five runs record that identity. Both episode headers preserve its exact
  instruction, start position/rotation, and goal position.
- Recomputed official results from `progress.json` and checked raw JSONL traces:

  | Episode | Successful runs | Terminal error range | Recorded collisions |
  | --- | --- | --- | --- |
  | 1 | 3/5 | 1.050–4.057 m | 0 in all runs |
  | 2 | 2/5 | 2.154–5.911 m | 8–10 in all runs |

- All ten terminal steps have S2 action-sequence provenance and the last raw
  S2 text is exactly `STOP`. None terminated by fallback or step/time cap.
  All five episode-2 runs entered the goal radius; three later stopped outside
  it. These are observed coordinate-based outcomes, not a proven failure cause.
- All **92 recorded pixel-goal events** correspond to the
  `look_down_followup` S2 branch. The known v1 view-label bug does not change
  that conclusion because the separate S2 branch record is available.
- All **20 MP4s** decoded fully with ffmpeg without errors. ffprobe frame counts
  match the corresponding traced episode lengths. Inspected successful and
  unsuccessful v1 composite frames, including the actual navigation map.
- The current worktree differs from pristine in exactly three source files:
  the two known lazy-import shims and evaluator instrumentation/video output.
  Inspected the full evaluator patch; added evidence collection does not feed
  observations/actions back into the policy. The current evaluator hash matches
  v2–v5. v1 records a distinct hash; retain its trace-label qualification.
- The reported Habitat-Lab 0.2.4 / Habitat-Sim 0.3.3 combination is supported by
  actual completed runs for this path. This establishes scoped runtime success,
  not compatibility across all Habitat tasks.
- Both public scene navmeshes also match their upstream **Git blob SHA-1 OIDs**
  when recomputed with the Git blob header. Their verification need not remain
  limited to size checks merely because they are not LFS objects.

Machine-readable checks: `review/public_scenes_lead_checks.json`.

## Corrections

### P1 — Reconcile the manifest and derived-file versions

The current local manifest check is **352/354 matching**, with no missing files.
Only `public_scenes/scripts/summarise_runs.py` and
`public_scenes/setup/run_summary.json` disagree with the recorded manifest.
All manifest-listed raw run records and MP4s match.

A read-only remote follow-up establishes:

- `summarise_runs.py`: local and remote both hash to `de365c0b…`; the manifest
  still records `d595c624…`.
- `run_summary.json`: local hashes to `9b7401d0…`; remote and manifest still
  record `03c1bc12…`.

The JSON diff contains reporting corrections, including changing "most" failures
to "half" and marking the v1 pixel-goal view field as unreliable. No raw success
metric changes appear in the inspected diff. Preserve this lineage, sync the
intended derived version, and regenerate/reverify the manifest and local
verification report. The existing `354/354` statement is stale, not a verified
description of the current files.

### P2 — Narrow the reproducibility claim

The pinned sampler uses `randn_tensor(..., generator=None)` and the inspected
evaluator seeds NumPy, not Torch. The two episodes' initial S2 output prefixes
and first pixel-goal input-image hashes match across all five runs, while first
S1 trajectories differ. Uncontrolled Torch sampling is therefore a strong
explanation for early divergence.

This does not establish that the evaluator is intrinsically unreproducible,
that S2 is universally deterministic, or that a published aggregate result is
unreliable. Greedy decoding is not a general guarantee of bit-identical GPU
execution. A fixed-seed duplicate and recorded input/RNG identities are needed
to test repeatability. See the [PyTorch 2.6 reproducibility guidance](https://docs.pytorch.org/docs/2.6/notes/randomness.html).

Revise the result to: these five runs did not control Torch RNG and produced
different trajectories. A separately labelled seeded diagnostic changes the
experimental random initialization, not the model architecture or controller
algorithm; preserve the original default-setting results. Such a diagnostic is
a recommended next test, not a prerequisite for accepting these recorded runs.

### P2 — Describe the room exclusion as a study choice

`public_scenes/scripts/scene_feasibility.py` uses a sampled diameter greater than
**6 m** and a within-radius fraction below **0.5** as its local eligibility rule.
The execution package only required the chosen start to be more than 3 m from
the goal. The room's sampled 4.35 m maximum therefore does not prove that no
valid short task exists.

The 82.9% figure is a fraction of 400 sampled positions for one selected goal,
not a statement covering every possible goal or the exact floor area. Excluding
the room in favor of two longer castle routes is a reasonable recorded choice;
replace "cannot distinguish navigation from standing still" and "unusable" with
the actual sampling rule and motivation. Do not retroactively change these runs.

### P2 — Keep failure diagnosis and measurement scopes precise

Episode 2 entered the success radius and then stopped outside it in three runs.
This does not by itself distinguish delayed stopping from confusing similar
landmarks or ambiguity in the handwritten instruction. Compare goal previews
and terminal views before selecting a causal explanation.

The S2 timer starts after processor/input preparation and ends after token
decoding; `generate_latents` is outside it. S1 timing covers trajectory generation,
CPU materialization, and action conversion. Name those boundaries explicitly
rather than describing them as full end-to-end system latency.

### P3 — Scope evidence completeness and update task metadata

Saved goal-frame RGB, traces, and videos support this functional review. They do
not contain every lossless level-view/depth input or RNG state required for exact
model-input replay. Capture those inputs at inference calls in the next
repeatability diagnostic. A complete transfer of recorded files is distinct
from a complete replay record.

The task's `public_scenes_dispatch` is `executed`, but its generic
`execution_handoff` still says `prepared_not_dispatched`. Correct that stale
field and distinguish accepted runtime evidence from pending report/sync edits.

## Recommended next step

First reconcile the two derived files and revise the unsupported claims. Then
use a small, separately labelled same-seed duplicate on the existing frozen
cases to test repeatability before considering 20–30 repeats. Retain original
unseeded runs and both successful/unsuccessful videos. Investigate episode 2's
terminal landmark and collision behavior with matched inputs.

This review adds only its report and machine-readable checks. Original returns,
implementation, run records, and task metadata are preserved; nothing was staged
or committed.
