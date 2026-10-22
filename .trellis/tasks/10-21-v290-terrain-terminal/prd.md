# v290 supported local search and terminal braking

## Goal
Complete the user-approved three-part continuation of the v289 diagnosis: terrain-following interior local search with exact endpoints, no implicit sloped-plane retreat near obstacles, and a controlled terminal slowdown that absorbs tracking/PD drift.

## Confirmed evidence
- Frozen v289 is the parent. Main seed calls AstarSearch(..., true); dyn_a_star.cpp:225 bypasses terrain support in this exact mode. Intermediate XY neighbors therefore use a chord plane when the upstream-plane parameter is enabled.
- ConvertToIndexAndAdjustStartEndPoints turns terrain_search_ off after failed endpoint projection. CM02 repair searches may therefore change representation while retreating. Both mechanisms are source facts; captured-input red/green is required for causal attribution.
- Candidate reactive refusals on the four unfinished routes are verdict7/voxel2 (inflated nonterrain contributions), not unobserved air. Retain those obstacles pending raw contribution audit.
- CD12 first source crossing is at114.7686s, applied forward0.4066m/s, RL. Worst source margin-0.0462213m is later in STAND_TRANSITION with zero command. A terminal yaw-only change is insufficient.

## Requirements
R1 Preserve exact requested start/end XYZ, checked terminal connector, full collision and dynamic gates. Terrain support selects only interior search heights in exact mode.
R2 Support-aware endpoint repair stays on support while retreating in XY; it must not switch the whole search to a chord plane. No terrain evidence retains the legacy representation. True obstacle, gap, unavailable/stale evidence remain refusals.
R3 Inspect retained raw contributions at captured failed queries; no broad obstacle waiver or source-solid mesh query in the local hot loop.
R4 Slow terminal approach using existing position gain and velocity/slew limits; account for speed reduction in spline phase. Preserve original0.25m XY/0.20m Z capture and measured PD completion. Do not reintroduce tiny-radius centering or hard publication vetoes.
R5 Keep radius0.35m, scan/deadline0.1s, cloud/body freshness, global reference ownership, factory control and route cohort unchanged. No route/coordinate/scene exceptions.

## Acceptance
- Native parent/candidate contrast: equal-end-height stairs in exact mode follow supported interior elevations while returned endpoints remain unchanged; blocked terminal connector remains blocked.
- Obstructed support-aware repair retains terrain mode, bounded adjustment and checked edges; unsupported/stale/observed-obstacle controls remain rejected.
- Actual ROS-clock tracking tests: terminal distance limits commands smoothly, coupled turn and phase remain consistent, original capture/hold/cancel tests pass.
- Captured-input comparison and raw-contributor provenance are returned locally. These are zero-physics checks and do not claim a repaired physical CD12 trajectory.
- Full offline53 and ten new physical attempts remain separate from component qualification; no v289 attempt is rerun or reclassified.

## Scope boundary
Only versioned local search/tracker behavior, necessary regression probes and execution/provenance adapters. No global geometry/radius/timing relaxation, new local hard veto, RL/PD retuning, cohort changes, unrelated harness edits, automatic commit or remote-only source.
