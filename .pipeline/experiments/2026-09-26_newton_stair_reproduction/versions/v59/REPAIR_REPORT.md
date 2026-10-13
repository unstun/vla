# v58–v59 repair validation

Stage: experiment + analysis, 2026-10-03. **The goal-search repair passes, but v59 timing remains defective across chained retries; overall 30 Hz and tail-elimination acceptance fails.**
Both requested 90-second recordings completed on gpu5070ti. v59 has a separate
cold-recovery stall at 81.03 s, including a 1.10 s measured pause; it is not promoted
over the retained v48 navigation reference.

[Updated frequency/latency/motion figure](analysis/v59_time_series.png),
[PDF](analysis/v59_time_series.pdf), and
[review video](../../../../../output/2026-09-27_lite3_versions/v59_realtime_trial01_review_v61.mp4).
The final v61 camera is display-only; its physical source remains v59.
[Video provenance and visual checks](../v61/REVIEW_VIDEO.json).

## Changes and preserved contracts

**v58**, parent v57, adds a live necessary endpoint-evidence certificate before
final-goal A*. Every possible exact/tolerance endpoint is considered. A possibly
observed reflected front/rear footprint-cell pair retains the original search;
remote all-unknown endpoints cannot pass the original collision query. There is
no cached safety verdict. The manager, FSM, controller, optimizer, final goal,
yaw, dynamics, physical-floor and stop rules are exact parent behavior.

**v59**, parent v58, preserves a checked sampled PVA's time origin through warm
and native fallback planning. The controller consumes elapsed time once on
receipt instead of resetting each delayed curve to zero. Existing command,
heading/final-yaw freeze, cancellation, emergency, goal and dynamics functions
remain exact parent bytes. Every original PVA and newest whole-curve occupancy/
stair-support gate still runs. No v49 solve budget or new stop reason is used.

Builds and all inherited component gates pass, plus 3,000 footprint-pair checks,
15 actual-controller timing checks, 10 delayed native-epoch checks per fixture,
and supplementary timestamp negatives. Source, installed binaries and physical
input gates passed before launch and source/install identities were rechecked
after recording. [Scope proof](scope_verification.json),
[contracts](tests/attempt01/result.json), [post-run verification](analysis/verification.json).

## Full recording-window performance

Successful Hz uses the entire navigation pacing wall interval, including
initial waiting, failures and pauses. Latency distributions below use completed
rounds in that same interval. These are separate closed-loop trajectories,
not paired causal speedup measurements.

| Recording | Successful Hz | Median ms | P95 ms | P99 ms | Max ms | Measured 3D path m |
|---|---:|---:|---:|---:|---:|---:|
| v57_realtime_trial01 | 25.65 | 2.28 | 56.37 | 75.03 | 660.97 | 46.20 |
| v57_realtime_trial02 | 25.76 | 2.41 | 60.69 | 76.87 | 290.15 | 46.62 |
| v58_realtime_trial02 | 27.53 | 2.04 | 12.83 | 74.49 | 659.53 | 55.19 |
| v59_realtime_trial01 | 26.43 | 1.95 | 13.09 | 140.47 | 1236.71 | 55.04 |

Both new recordings reach 89.9621887 native seconds from 90,000 nominal physics
steps, with zero dropped physics steps. Their paced navigation interval starts
at 11.0208235 s and lasts 78.9413652 native seconds; measured RTF is 0.96476/0.96444.
No logged emergency-state transition or invalid-current-spline event occurs.
Neither recording reaches the complete route's final goal within this bound.

Both include an initial 1.40 s navigation hold at 11.12–12.52 s. After that initial
hold, v58 has no measured pause exceeding 1 s; v59 has one at 81.287–82.386 s. The
older core pause field uses the first/last planner-log times and omits that
initial waiting interval. We preserve it separately and report the complete
navigation interval explicitly. Post-recording planner activity is excluded
from the final plotted latency/tracking samples.

## The diagnosed late slowdown is removed

The idle-host controlled v58 replay uses 20 original states, 80 alternating
calls and exact return/path comparison. Maximum goal-search time drops
**44.614381 → 0.259025 ms (99.4194%)**. All 12 formerly expanding states are
pruned by the necessary endpoint certificate. No GPU job or container was
active; source identity is unchanged. This is a component speedup, not a live
full-solve speedup. [Idle replay03](../v58/paired/idle_summary.json).

The original replay02 measured 45.128580 → 0.272144 ms while another host job
overlapped component work. Its load caveat and frozen result remain preserved
in the [original comparison](../v58/paired_summary.json).

For 85–90 s in the new recordings:

| Measurement | v58 | v59 |
|---|---:|---:|
| Median complete round | 2.848 ms | 1.679 ms |
| Median goal-search scope | 0.007194 ms | 0.007509 ms |
| Maximum goal-search scope | 0.020629 ms | 0.020128 ms |
| Median signed along-track error (plan minus body) | +0.010 m | +0.064 m |
| Median raw translation-command speed | 0.869 m/s | 0.792 m/s |
| Largest matched common-time position step | 53.738 mm | 0.168 mm |

The original v57 trial02 audit measured about 0.97 m robot lead and 0.086 m/s median
translation command in its 85–90 s segment. The new runs travel further and occupy
different positions at those times, so this physical comparison is descriptive.
The controller/native delayed-input tests separately establish the timing fix.

For 141 matched v59 handovers in 85–90 s, sample-to-origin rebasing is zero. The
largest common-publication-time position difference is 0.168 mm, compared with
53.738 mm in 138 matched v58 transitions. This is not a claim that later optimized
PVA is mathematically identical: the largest matched velocity/acceleration
differences are retained in the handover JSON. Unmatched, clock-shifted or frozen
cases are counted/excluded. Controller receipt/pause state is not reconstructed
from the observer. Body errors use interpolation of 10 Hz sensor poses.

## Why 30 Hz still fails

At 81.027 s, v59 rejects the warm guess with `target_connector`. The proposed
extension cannot pass the unchanged segment collision/support check. The
existing fallback then performs eight rebound attempts; repeated A* searches
inside collision rebound fail in both ordinary and fixed-height modes. The
round eventually succeeds at 82.286 s after 1,236.709 ms, when the previous trajectory
has run out and the robot has paused.

Its inclusive profile contains 850.462 ms in the optimizer, 268.449 ms in seed
construction and 276.240 ms in input processing (13 cloud callbacks, 260.896 ms).
These scopes overlap and must not be summed as exclusive costs. At 79.333 s,
another 961.405 ms round contains seven rebound attempts and 882.529 ms in the
optimizer, again including repeated failed A* searches. The old curve has expired by final recovery, causing the manager to select completion time (`sampled=0`). The subsequent audit proves that its initial PVA is still the original sample, so this is an erroneous timestamp reset, not a fresh state restart.

The last curve observed before the 81.027 s round is trajectory 1934. Its origin
is 80.987122 s and its nominal expiry is **81.440673 s**. Recovery publishes at
**82.286407 s**, about 0.846 s after that expiry, consistent with the observed
deceleration and hold. This uses the observer's curve and nominal lifetime;
internal controller pause bookkeeping is not reconstructed.
[Recorded curve-expiry evidence](analysis/v59_realtime_trial01_curve_reserve.json).

v58 also encounters `target_connector` at 81.687 s and takes 659.526 ms across ten
rebound attempts. Thus the remaining costly chain exists before the v59 timing
change. The different live inputs/trajectories do not establish why one trial's
maximum is larger. [v58 line-addressed evidence](analysis/v58_realtime_trial02_tail_evidence.json),
[v59 line-addressed evidence](analysis/v59_realtime_trial01_tail_evidence.json).

A further repair needs to address candidate connector failure and repeated
cold recovery while preserving a usable trajectory, fresh validation and
actual spatial/expiry extension. It must distinguish a rejected new target
connector from validity of the accepted remaining curve. The unchanged safety
rejection must not be suppressed, and v49 hard abort/stop mechanics remain
excluded. No additional navigation repair is silently folded into these frozen
versions.

## Artifacts and acceptance

Raw captures, NPZ/JSONL, build trees and complete frame arrays remain on
gpu5070ti. Forty-two compact physical/plot/preview records (1,726,398 bytes) were
returned and SHA-verified; one usable review MP4 is the only heavy return.
The original camera's ceiling occlusion and v60's cropped framing are preserved
as failed visual attempts; v61 is display-only and replays the same v59 states.

The goal-search component and direct timing tests pass their declared checks. Chained retry timing does not: the 2026-10-03 audit detects a 1.259308 s rebasing of unchanged initial PVA.
**Sustained 30 Hz, full tail elimination, v59 uninterrupted physical progress and
full-route arrival do not pass.** Preserve all versions and results; the main
performance/continuity task remains open for review.


## Post-delivery correction: chained retries

The [2026-10-03 native diagnosis](../../audits/2026-10-03_v59_cold_recovery/REPORT.md) finds an incomplete v59 timing repair. Seven retry seeds retain the initial PVA sampled at81.027099609s, but the final curve uses82.286407471s as its origin after the old curve expires. The earlier statement that this was an ordinary fresh restart was incorrect. Normal single-success handovers and component checks do not cover this path.

The same audit reproduces a valid remaining curve, a correctly rejected footprint turn near the drop guard, and three identical failed obstacle-repair searches per optimizer attempt. No production repair or safety relaxation was made. The original report is retained in the audit history.
