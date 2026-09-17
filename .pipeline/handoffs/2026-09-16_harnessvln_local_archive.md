---
origin: ai_only
reviewed: false
archive_status: knowledge_gate_passed_lead_verified
date: 2026-09-16
stage: experiment_and_analysis
---

# HarnessVLN Local Archive And Continuation



Archived at Dr Sun's request on 2026-09-16, 21:32 America/Los_Angeles
(2026-09-17 04:32 UTC). The scientific claims passed the archive knowledge gate after source-backed
context completion, and the lead verified linked evidence. Archival status
does not change any experiment's original verdict.

The local source of truth is `/Users/sun/tongbu/study/phdproject/vla`.
The current [Trellis task](../../.trellis/tasks/09-16-emos-harnessvln-reimplementation/task.json)
remains `in_progress`. No remote experiment or production repair was performed
as an archival side effect.

## Current conclusion

The offline Pi tool loop and native PCT/SCAN/Lite3 V12 Isaac service each have
bounded evidence. One continuous two-goal pilot completed cancellation,
confirmed stop, resubmission and both arrivals. Three later display probes
failed at resubmission, including the display-off condition. Reliable repeated
navigation has therefore not been established.

The captured SCAN rejection was reproduced in the actual native planner with
a fresh manager and an empty map. A one-line diagnostic candidate removes the
incorrect endpoint acceleration and passes the recorded fixture set. The
production source remains unchanged, and the candidate has not completed an
Isaac closed-loop test. This is the immediate continuation point.

All experiment-relative paths below use
[`../experiments/2026-09-16_pi_cortex_harnessvln/`](../experiments/2026-09-16_pi_cortex_harnessvln/)
as their base.

## Immutable experiment evidence

| Run or evidence | Recorded outcome | Local evidence |
| --- | --- | --- |
| `two_goal_20260916T162236Z_p2b_actual4` | One continuous episode passed 41 independent checks in 16.52 simulation seconds; 34/34 returned hashes matched. | [`P2B_RESULT.md`](../experiments/2026-09-16_pi_cortex_harnessvln/P2B_RESULT.md), [`actual4_lead_review/result.json`](../experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/qualification/actual4_lead_review/result.json), [`run package`](../experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/two_goal_runs/two_goal_20260916T162236Z_p2b_actual4/) |
| `pointcloud_20260916T171400Z_off` | Display off; 45 simulation seconds; A2 resubmission failed; 38/38 returned hashes matched. | [`run package`](../experiments/2026-09-16_pi_cortex_harnessvln/pointcloud_display/runs/pointcloud_20260916T171400Z_off/) |
| `pointcloud_20260916T172100Z_rviz` | Software RViz plus libx264; A2 resubmission failed; 46/46 returned hashes matched. | [`run package`](../experiments/2026-09-16_pi_cortex_harnessvln/pointcloud_display/runs/pointcloud_20260916T172100Z_rviz/) |
| `pointcloud_20260916T173400Z_rviz_gpu` | NVIDIA RViz plus NVENC display/recording passed; A2 resubmission failed; 47/47 returned hashes matched. | [`run package`](../experiments/2026-09-16_pi_cortex_harnessvln/pointcloud_display/runs/pointcloud_20260916T173400Z_rviz_gpu/) |
| `pointcloud_window_20260916T174100Z` | Exact run-specific RViz window selection and NVIDIA rendering passed; 10/10 returned hashes matched; no navigation episode. | [`qualification package`](../experiments/2026-09-16_pi_cortex_harnessvln/pointcloud_display/qualification/pointcloud_window_20260916T174100Z/) |
| `native_original_20260916T180500Z` | Original frozen planner failed the problematic resume fixture 3/3; the other three fixtures passed 9/9. | [`run package`](../experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/runs/native_original_20260916T180500Z/) |
| `native_true_end_20260916T180700Z` | Isolated candidate passed all four fixtures, three repeats each, 12/12. | [`run package`](../experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/runs/native_true_end_20260916T180700Z/) |

Both native diagnostic conditions matched 67 native source files, 380 installed
files and 15 diagnostic package files before execution, and each returned
16/16 matching artifact hashes. Existing run directories are immutable
snapshots. Any new source or condition requires a new run ID.

## SCAN diagnosis and candidate boundary

The observed chain was: cancellation reached `WAIT_TARGET`; the new PCT route
entered `GEN_NEW_TRAJ`; SCAN's refined candidates exceeded the unchanged
acceleration gate; no new spline reached the controller; and
`initial_heartbeat_missing` produced a protected fault stop. A later
generation-cancel rejection was a consequence of this chain.

Native replay reproduces the failure without Isaac, cancellation, a controller
or GPU load. The frozen implementation samples the polynomial before its end,
then supplies `evaluateAcc(t)` at the last sample as the terminal acceleration.
For the failed resume fixture, the true end is 1.73070084 seconds, but the last
sample is 1.6 seconds. Its acceleration is 1.77813133 m/s^2 instead of the true
endpoint's approximately zero. Refinement retains approximately
1.778376817 m/s^2, exceeding the unchanged 1.5 m/s^2 gate.

The isolated candidate is exactly this behavioral change:

```diff
- start_end_derivatives.push_back(gl_traj.evaluateAcc(t));
+ start_end_derivatives.push_back(gl_traj.evaluateAcc(time));
```

The failed-resume fixture's refined sampled maximum acceleration becomes
0.590244562 m/s^2. No safety limit, heartbeat deadline, controller setting or
fixture command was relaxed. The earlier successful resume uses a stopping
position about 5 cm away, yielding a sampled terminal acceleration of
1.47762351 m/s^2, just below the gate. Its success does not disprove the defect.

Read [`scan_replan_diagnosis/RESULT.md`](../experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/RESULT.md),
[`comparison.json`](../experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/comparison.json)
and [`independent_review.json`](../experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/independent_review.json).
The comparison passes nine checks. Attribution is limited to the frozen
implementation used here; unmodified official upstream code was not verified.

The fixtures derive from recorded PCT-request poses plus a frozen body-height
offset. They are not exact captures of all live native arguments or occupancy.
All repeats use seed zero. The candidate's problematic fixture still ends about
3.5 cm from the route endpoint. Production adoption must cover endpoint
geometry, nonempty-map collision checks, random initialization, later replans
and the full continuous Isaac episode. The production materializer and
`p2b_execution/builds/scan_03/` remain unchanged.

To recheck the returned diagnostic evidence locally, run from the VLA root:

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/analyze_native.py
```

This analyzes existing artifacts; it does not launch a new remote experiment.
The diagnostic `native_worker.py` and `container_cases.py` retain the actual
build/replay commands and 20-second per-case ceiling. Source regeneration is
in `instrument_manager.py`.

## GPU display preference and measured limit

Dr Sun requested greater GPU use. The display wrapper now defaults to actual
NVIDIA rendering and `h264_nvenc`; renderer logs, encoder session evidence and
decoded video confirm hardware use. Preserve this preference for future
display runs, and verify the actual renderer rather than only an environment
variable. Latest-only raw clouds use BEST_EFFORT depth 1 and zero decay.

The GPU display showed approximately 2,843 points per frame at 9-10 FPS.
Relative to display off, physics wall time increased from 56.839 to
58.422 seconds for 45 simulation seconds, or 2.786%; sampled active total-GPU
memory peak increased from 7,082 to 7,445 MiB, or 363 MiB. Telemetry drops were
zero. This includes recording overhead and a protected stationary tail after
navigation failed. One condition per profile establishes neither dense-map
capacity nor long-duration performance; high GPU saturation is not claimed.

Evidence: [`pointcloud_display/RESULT.md`](../experiments/2026-09-16_pi_cortex_harnessvln/pointcloud_display/RESULT.md),
[`gpu_comparison.json`](../experiments/2026-09-16_pi_cortex_harnessvln/pointcloud_display/gpu_comparison.json),
[`preview_provenance.json`](../experiments/2026-09-16_pi_cortex_harnessvln/pointcloud_display/preview_provenance.json)
and the actual [`58-second video`](../experiments/2026-09-16_pi_cortex_harnessvln/pointcloud_display/pointcloud_gpu.mp4).
The comparison's overall verdict remains false because full navigation failed;
its display/recording/provenance checks passed.
[`final_cleanup.json`](../experiments/2026-09-16_pi_cortex_harnessvln/pointcloud_display/final_cleanup.json)
records owned-process/container exit, free navigation ports and zero remaining
encoder sessions at the end of that experiment, not a new live host check.

## Resume work

1. Review the isolated correction and endpoint-fit residual before applying it
   to a new local materialized SCAN build. Preserve `scan_03` and all historical
   run packages. Keep the 1.5 m/s^2 gate and existing deadlines unchanged.
2. Qualify endpoint geometry, collision behavior and later replans, then run a
   new bounded continuous Isaac cancel/stop/resubmit/A/B trial under the
   existing acceptance criteria. Record the new source identity, package hash
   gate, raw events, controller/physics evidence, video and verified returns.
   A native fixture pass alone is insufficient to mark this repair integrated.
3. After the native service is sufficiently reliable, connect the actual Pi
   loop and Cortex/EMOS-compatible tool adapter to it. Visual grounding, graph
   memory, calibrated RGB-D/localization, real SLAM and language-driven
   navigation remain open. The existing Pi fixture loop is separate evidence.
4. Keep receive-only localization and eventual physical deployment separate;
   this archive authorizes neither real-robot actuation nor a formal long run.

The selected bridge pin is `848b4aecd01237805e0564c88d3ba09146fd2353`.
Sibling `machine-dog-nav` and `machine-dog` remain read-only references. Remote
workspaces are execution copies: final source and all acceptance evidence must
return to the same local VLA paths. No HarnessVLN paper-score reproduction or
deployment-readiness claim follows from the recorded tests.

## Other retained work

Earlier MIP evidence remains in
[`2026-09-16_mip_5070ti/REAL_EPISODE_RESULT.md`](../experiments/2026-09-16_mip_5070ti/REAL_EPISODE_RESULT.md).
InternVLA, camera work and other experiment entries remain in the
[experiment index](../experiments/README.md). The pre-archive hot zone was
preserved byte-for-byte in
[`bigmemory/冷区/改动记录/2026-09-16_2129_pre-harnessvln-hot-zone/`](../../bigmemory/冷区/改动记录/2026-09-16_2129_pre-harnessvln-hot-zone/).
These earlier tasks and decisions were not silently closed by this archive.

Archive package inventory, validation and local-backup details: [archive report](2026-09-16_harnessvln_archive_report.md).
