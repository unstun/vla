# v29 landing stall: diagnosis from saved inputs

Stage: experiment + analysis, 2026-09-28. This is diagnosis only: no version,
no threshold change and no physics. All replays use the pinned local Humble
image, the v29 native install (`runtime/scan61_sensor_column_v29`) and the
v29 planner YAML (identical to the run's `planner.yaml`, `ec120d81…`).

## Frozen states from `v29_historical_full01`

`prepare_inputs.py` is the start-thrash freezer with only the run, the clocks,
the executing spline and the recorded committed window changed. It uses the
original scans, paired poses, route and spline. The navigation and surface
ground match the live publishers (`97d2dfbd…`, `b68527dd…`).

| State | Clock | Scans | Body | Spline | Committed window |
|---|---|---|---|---|---|
| onset | 47.3606 s, the REPLAN whose frontier first became 8.6446 s | 363 | (-5.000, -0.682, 1.435), second flight | traj 47 | 6.810 s |
| landing | 80.9771 s, the REPLAN after "Local reference window complete (8.64/73.60s)" | 699 | (-4.988, -2.476, 1.715), upper landing | traj 63 | 8.645 s |

## Reproduction

The unchanged v29 regression `gen_probe` (`4c216c08…`) reproduces the live
stall in both states:
- the frontier is 8.6445784420 s, the live value;
- `continued=false`;
- the landing state prints the same A* pool error, the same throttled
  `reactive_collision_blocked … q=(-0.442,-4.258,1.861)` line and "Local target
  is in collision and no nearby free target was found".

`landing_probe` (`make_probe.py`, `probe_derivation.json`) is the same probe
plus a read-only breakdown. Its `result.json` equals the unchanged probe's in
both states. The breakdown re-walks the frontier exactly as
`adjustGlobalTargetIfOccupied` does: from the route end backwards on the
0.05 s grid, with the previous-to-current yaw. For each footprint circle it
repeats `reactiveOccupancy` and `reactiveFootprintSupportQuery` step by step
with the native members, then checks the result against the native
functions. There are 0 circle, 0 sample and 0 support mismatches over 196
circle rows per state. None of the 1,300 route samples beyond the frontier is
free.

## Mechanism

1. **The PCT walkway selection is narrow here.** The pinned navigation ground
   selects the landing and the corridor after it as a band 6–7 cells
   (0.6–0.7 m) wide.
   - PCT's own selection is what narrows it: the file has no cell above cost
     20. Only 7 walkway-height points fall in x −4.9…−4.4, y −3.7…−2.4, at cost
     15.8–16.7.
   - The edge column costs 13.4–16.7, against a median of 7.55 inside.
   - The surface evidence has the 1.422 m landing and 1.558 m floor out to
     x ≈ −4.45.
2. **SCAN scores the band's outer ring as Unknown.** The ETH-style step score
   (`eth_step_score_adaptation.h`) looks at the 3 × 3 neighbours of each layer.
   A neighbour cell that is present but has no layer within 0.26 m makes the
   layer Unknown.
   - Beyond the band, cells are present because they carry other floors'
     surfaces (0.058, 3.118, 4.533 and 6.07 m).
   - So the walkway's outermost ring of cells is Unknown support.
3. **The route runs on that ring.** From the frontier on, the PCT route follows
   x −5.000…−4.93, along the boundary x = −4.995 between the known interior
   (column 20) and the Unknown ring (column 21).
   - It then cuts the Unknown inside corner of the turn.
   - It follows the corridor's Unknown north edge row (y ≈ −4.2) to x ≈ −3.7.
   - The robot itself stops in column 21, so `start_occupied=1`.
   See `support_map/landing_support_map.png`.
4. **Every sample past the frontier fails.** In the 4.5 s of route after the
   frontier (90 samples), in the landing state:
   - **Support query fails, 52 samples (t 8.695–11.243 s):**
     - 43 fail on the sample's own cell (UnknownSupport, verdict 8);
     - 9 fail on a footprint circle whose nearest layer is not selected.
   - **Never-observed voxels, 38 samples (t 11.293–13.142 s):** log-odds
     −2.00243, in the corridor behind the corner. That is ordinary exploration.

   The onset state gives 51 support failures and 39 never-observed voxels,
   with the same first failures.
5. **Why the stall is permanent.** Support is a static prior. The frontier walk
   accepts only exact route samples, and observation cannot change support.
   The frontier therefore stayed at 8.6446 s from 47.36 s until the run ended.
   The robot walked up to it (the last committed window ended there) and
   replanned against it until `native_replan_exhausted`.

## Why the live log pointed elsewhere

- **No log line for support failures.** `reactiveOccupancy` returns 1 without
  logging when the support query fails.
- **The logged point is only the first in-map sample.** The throttled line
  always comes from the first in-map sample of the backward walk from the route
  end. That sample sits at the map's +x edge (x_max = −0.05 m), about 4.9 m
  from the robot, and is never-observed.
- **The A* error comes from an unrelated search.** "Ran out of pool" comes from
  `findGoalNeighborhoodPath` from the robot to the distant final goal. The goal
  is far enough away that the search's endpoints fall outside the A* pool.
  This search runs before the frontier walk on every replan and is not the
  blocker.

The v29 results' first reading ("the frontier stops at never-observed space
beyond a turn") was therefore wrong about the near blocker.

## Evidence for the support labels

- **Native-header map:** `support_map/support_map.cpp` runs the native
  header-only step score on the pinned navigation ground. It rebuilds the live
  27,278 terrain cells.
- **Match against native lines:** all 240 `[SUPPORT]` lines printed by the four
  native replays match on status, known flag and first-pass height
  (`validate_support_map.py`, `validation.json`).
- **Python copy:** a Python copy of the two passes reproduces all 86,775 native
  layer labels (`evidence_fallback_estimate.py`).

## Causal test: support oracle

`oracle_probe` (`make_oracle_probe.py`) makes one change, inside the probe
only. After the unchanged replay, it relabels the 39 Unknown walkway layers
(of 153; heights 1.35–1.65 m) in x −5.3…−3.5, y −4.5…−2.3 as Flat. Scans,
occupancy, route, window, thresholds, optimizer and native code are unchanged.

| State | Frontier | Continuation | Accepted XY prefix | Boundary / full-curve |
|---|---|---|---|---|
| landing, unchanged | 8.645 s | fails | — | — |
| landing, oracle | 11.043 s | accepted | 0.568 m | pass / pass |
| onset, unchanged | 8.645 s | fails | — | — |
| onset, oracle | 10.743 s | accepted | 1.401 m | pass / pass |

- **Negatives:** no-progress, out-of-map and stale-input rejection still hold.
- **Robot spot:** the robot's own spot is no longer occupied in the landing
  state.
- **What remains beyond the new frontier:** only never-observed voxels in the
  occluded corridor (66 landing / 72 onset) and the map boundary (24 / 18).

## Implication and open decision

The stall is a mismatch between the PCT reference route and SCAN's static
support model, not a sensor or waiver problem. v29's footprint waiver is not
involved. Candidate scopes for the next version, none implemented:

1. **Evidence-backed neighbour check in the step score.** A present neighbour
   without the walkway level counts as a possible drop only if the pinned
   surface evidence also lacks a surface near that level.
   - It never adds cells to the PCT selection.
   - An offline estimate (lead only) clears exactly the 39 landing-box layers
     but changes 7,873 layers map-wide (7,514 → Flat, 359 → Stair).
   - It would need a drop-edge red/green contract and the full regression.
2. **Lateral tolerance in the frontier walk.** When an exact route sample fails
   only on support, accept the nearest supported pose within one cell.
   - Support labels stay as they are.
   - The robot's current cell stays Unknown.
3. **Keep the route inside the selection.** The PCT route stays at least one
   cell inside the selection, and SCAN is unchanged. This changes the global
   route and needs a check that the narrow stair flights still admit a route.

Decision (2026-09-28): Dr Sun chose option 1 for v30 after reading this
diagnosis. The wall-clock freshness class remains separate.

## Attempts

`execute.py` (breakdown) and `oracle_execute.py` (oracle) each ran once, exit
0, in 375 s and 204 s wall time. There were no failed attempts.

## Boundary

- This is diagnosis and one probe-only counterfactual. It is not a fix, a
  version or a relaxed threshold.
- The oracle relabel is a question, not a proposal to mark cells supported.
- The frozen inputs and probe builds stay local-only (`LOCAL_ONLY_BYTES.json`).
- v29 stays frozen and unvalidated, and v3 remains the only accepted condition.
