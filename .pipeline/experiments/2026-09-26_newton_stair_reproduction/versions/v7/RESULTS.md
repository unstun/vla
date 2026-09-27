# v7: 0.6 m/s planned cruise contract; full navigation still fails

Stage: experiment + analysis. Dr Sun requested a minimum of 0.6 m/s.

The native planned-cruise change is implemented and passes its bounded native
tests. Direct 0.6 m/s control also walks and returns to PD. Neither the new empty
route nor the complete Building trial establishes successful navigation. In
particular, the Building trial never enters an eligible cruise interval.

## Change and meaning

`manager.min_cruise_speed: 0.6` is selected in both v7 planner YAMLs. It means
minimum horizontal **planned cruise**, excluding boundary acceleration/braking,
stationary holds and short moves that have no cruise interval. It does not mean
every command or measured body sample is at least 0.6 m/s.

Three native files change relative to v6: the manager source/header and a small
curve-measurement header. The manager reuses SCAN's time reallocation/refinement
when a cruise is too slow, then retains all original PVA, dynamic and complete
collision gates. The controller and PD/RL/factory behavior remain unchanged.
Nominal maxima remain 1.0 m/s and 0.5 m/s² with their previous admission
tolerances. Nav2's travel/approach distinction was inspected as a pinned
reference; see [UPSTREAM.md](UPSTREAM.md).

The 205-file source/config snapshot is immutable in `manifest.json` and
`source/`. The parent/config difference is `changes.patch`. No code, weights,
occupied cells, support data, timing watchdogs or previous version was changed
after freezing.

## Native and component evidence

| Attempt | Outcome |
|---|---|
| `build_evidence_scan46_cruise_v7` | Full native build passed, 39.24 s, source hashes unchanged |
| `v7_cruise_contract01` | Native derivative checks passed: slow/normal travel, stop, disabled parity, invalid inputs and 15 original moving curves |
| `v7_parameter_contract01` | Actual node rejects minimum > maximum, negative minimum and nonpositive acceleration |
| `v7_frontier_regression01` | Original v6 short continuation passes twice with identical results; PVA, complete collision and all negative cases pass |
| `v7_flat_measured01` | Original recorded input interval completes; 3 moving curves and 3 accepted plans. This is not a live route |
| `v7_retime_probe01` | Actual native retiming raises the original `flat_3` cruise minimum from 0.598556 to 0.607834 m/s; duration 6.654634 -> 6.296695 s; original/final full curves clear, PVA and dynamic gates pass |
| `v7_speed_06_control01` | Two direct 0.6 m/s walks and three PD holds pass all 10 original control checks, in one continuous 30 s physics episode |

The retiming probe uses 94 original measured flat scans with their original
body/sensor poses, the original floor prior and the captured native curve. It
calls the actual manager and optimizer; compiler access-check suppression is
limited to the diagnostic caller. It does not run a replacement planner.

The direct control trial moves 4.3965 m in total. During each four-second walk,
discarding only its first second for the declared steady-speed statistic,
measured forward means are 0.56661 and 0.56552 m/s. Corresponding ranges are
0.51459-0.59590 and 0.51345-0.59595 m/s. It ends in `FIXED_STAND`. A 0.6 command
therefore does **not** establish a measured 0.6 m/s lower bound. This trial has
no planner or navigation goal.

## Physical navigation failures retained

`v7_empty_route01` stops before physics because the new native source manifest
was missing from the geometry-only registry. `registration_receipt.json`
records the subsequent exact-hash identity registration. This is a packaging
receipt; frozen code/config did not change.

`v7_empty_route02` reaches 14.88 physical seconds, then reports the pre-existing
`initial_heartbeat_missing` failure. It publishes no moving curve and no
nonzero command. The minimum-speed check is not reached. The original common
and route reviewers fail, as expected; 190 applied acknowledgments match and
the measured final stop passes. This is not an empty-route speed validation.

`v7_building_route01` reaches the original 90,000-step bound (89.962189 s):

- Three published moving curves, of horizontal lengths 0.56725, 0.23680 and
  0.16990 m. All have zero eligible cruise samples; none satisfies a tested
  0.6 m/s cruise condition.
- Net XY progress 0.41132 m, accumulated XYZ path 0.87797 m and remaining goal
  distance 4.70238 m. Command peak XY 0.36333 m/s; measured peak XY 0.44438 m/s.
- 3,939 positive acknowledgments, no byte/command mismatches, exact continuous
  float32 clock/step sequence, intact raw sensor files and verified copyback.
- Minimum body-up component 0.94302; final mode `STAND_SETTLING`, no final PD
  dwell, no arrival and no backend terminal result. The driver terminal file
  is absent; no replacement was fabricated to satisfy a reviewer.

The standard Building review consequently cannot complete. The separate
`bounded_speed_review.json` records only the evidence it can actually check.
The first full v6 moving curve had also been replaced by a hold after about
0.38 simulation seconds. Raising a cruise requirement has not repaired these
early stops or the short available path windows.

## Video

`output/2026-09-27_lite3_versions/v7_building_test.mp4` is an ordinary byte-exact
file, 1,419,746 bytes, 1280x720, 1,124 frames and 89.92 encoded seconds. It renders
the original saved states with zero physics steps. All frame hashes, source
times and the full video decode pass. Frames 210 and 1123 were inspected; the
final caption explicitly says not arrived, with `STAND_SETTLING` visible.

The original recorder has one 140-substep gap at the factory-to-policy sampling
boundary; all other frame gaps are 80 substeps. The failed first verification
assumed uniform spacing everywhere and is retained. The corrected verification
checks the exact original state times and this explicit boundary; it does not
change the video or physics record.

## Reproduction and next boundary

Use the fixed local ROS image recorded in every `request.json`. Per-attempt
commands and native `inside.sh` scripts are retained in `evidence/`, with raw
local paths and hashes in `RETAINED_RUN_FILES.json`. Rebuild the frozen native
source with the existing `build_candidate.py`; register its reviewed identity
receipt before geometry-only execution. Re-run the original physical command
with a new run ID, `--integration-version v7` and the selected v7 planner YAML.
Run `review_speed_runs.py` with the existing E1 Python environment for the
independent SciPy/recorded-state review.

This version validates the declared native minimum-cruise contract and the
separate direct-command control condition. Full navigation remains unvalidated;
v3 is still only one accepted empty 12 m trial. Next work is to minimize the
existing source of short/blocked reference windows and early stops, then rerun
with the 0.6 cruise requirement retained. A separate production repair is v8.
