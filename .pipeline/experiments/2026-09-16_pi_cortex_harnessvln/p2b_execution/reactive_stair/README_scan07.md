# scan_07: precomputed ETH-style step score on selected PCT ground cells

Status: **hash-gated local source candidate, Foxy-built and startup-smoked**. This is a
new copy of the successfully built `scan_06` source. `scan_04`, `scan_05`, and
`scan_06` remain unchanged.

## Exact source and attribution

- ETH upstream: [StepFilter.cpp at
  `14d24c059e1c43466aadf328280adf6394d78039`](https://github.com/leggedrobotics/traversability_estimation/blob/14d24c059e1c43466aadf328280adf6394d78039/traversability_estimation_filters/src/StepFilter.cpp).
  The pinned local primary file is
  `references/upstream/2026-09-23_eth_stepfilter_reference/StepFilter.cpp`,
  SHA-256 `cdcf18ef0b6396770ea779fd03683b757ddd78640bc4817205377713186920f2`.
- Original license: BSD-3-Clause-style text, Copyright (c) 2015 Peter
  Fankhauser. The full upstream `LICENSE` is preserved as
  `ETH_STEPFILTER_LICENSE.txt` beside the adaptation header in the candidate.
- Local code in `eth_step_score_adaptation.h` is an **adaptation** of ETH's
  two-pass method, not an imported ROS 1 `StepFilter` or a claim of bitwise
  equivalence.

ETH pass 1 computes the maximum minus minimum elevation in a circular
neighborhood. Pass 2 finds the largest local step, counts cells with a step
strictly greater than the critical height, and computes
`step = min(stepMax, nCritical / criticalCellNumber * stepMax)`. Its score is
`1 - step / critical` when the effective step is below critical, otherwise
zero. `ethSecondPassScore` implements this formula directly and has numeric
parity fixtures.

## Local PCT/V12 adaptation

The standalone PCT node publishes a 0.10 m selected-ground PointCloud2 with
possibly multiple elevations per XY cell. The filter scores the complete
snapshot **once on receipt**, before `GridMap` accepts terrain support; it
does not scan elevation columns during a live collision query.

- Both circular radii are 0.15 m, covering the 8 adjacent 0.10 m cells. The
  local V12 critical height is 0.26 m and critical-cell count is 4. These
  differ from ETH's robot config (`0.12 m`, `0.04 m`, `0.04 m`, 4) and are
  recorded in the candidate manifest.
- A neighbor contributes the unambiguous nearest elevation to the surface
  being scored. Missing or ambiguous neighbor cells make that surface
  `Unknown`. This keeps two separate elevations at one XY from contaminating
  each other's scores. Sparse PCT coverage can therefore cause a safe yield.
- In addition to ETH's score, a surface whose **own first-pass jump** is at
  least 0.26 m is `Unsupported`. This hard capability gate prevents an isolated
  tall rise from becoming allowed through ETH's soft critical-cell factor.
- Complete wide tread interiors have zero local jump and remain supported as
  `Flat`. Subcritical stair edges (at least 0.04 m) are supported as `Stair`.
  These labels describe local height shape, not a semantic staircase detector.
- Accepted support still cannot clear current tracked-person occupancy or an
  unclassified LiDAR return. `scan_06`'s separate provenance and shared
  collision query are retained. Box and wall returns outside the selected
  ground band remain nonterrain obstacles.

## Evidence and runtime blocker

The local C++ fixtures cover ETH formula values, flat terrain, a 0.18 m stair,
wide tread interior, a 0.50 m box, a thin high wall, missing cells, and two
elevation layers. The materializer checks the 72-file built `scan_06` source
identity, the exact ETH source hash, unchanged copied files, and changed-file
hashes. A synthetic microbenchmark measures the pure score and decision code;
it excludes ROS, SCAN buffers, raycasting, callbacks, and scheduler effects.

An offline check used the pinned `new_building.pickle` (SHA-256
`ab5499ff100fe233f6cfabb59ce7592290cddd042c92ead5e37e9e2b593d24da`)
and reproduced the PCT publisher's 86,775 selected cells. The adaptation kept
70,501 supported (64,543 Flat, 5,958 Stair edge), marked 14,282 Unsupported,
and 1,992 Unknown. Of 3,105 selected surfaces adjacent to a 4–26 cm
four-neighbor height change, 2,508 remained supported. The 597 rejected
step-like surfaces need route-level inspection; these aggregate counts do not
show whether the intended stair corridor stays open. The exact command and
counts are recorded in `actual_pct_step_score_diagnostic.json`.

The current integrated P2B pilot calls a PCT worker over a socket and **does
not launch** the standalone node that publishes `/pct_tomogram`. The lead's
separate CPU probe proved that standalone node can publish 86,775 selectable
cells from the pinned Building map, but it did not connect that topic to the
integrated run. A complete current-person track producer is also absent. Until
both inputs are wired and identified, `scan_07` will fail closed at runtime.
The `scan_07` Foxy build and a no-input ROS startup smoke passed; their local
evidence is in `builds/scan_07/` and the task review. There is no 50 ms
live-loop measurement or Isaac episode from this slice.

Run local checks from `p2b_execution`:

```sh
python3 reactive_stair/test_materialize_scan_07.py -v
g++ -std=c++17 -Wall -Wextra -Werror -pedantic \
  -I builds/scan_07/src/plan_env/include \
  reactive_stair/test_eth_step_score_adaptation.cpp \
  -o /private/tmp/test_eth_step_score_adaptation
/private/tmp/test_eth_step_score_adaptation
g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic \
  -I builds/scan_07/src/plan_env/include \
  reactive_stair/bench_scan07_decision.cpp -o /private/tmp/bench_scan07_decision
/private/tmp/bench_scan07_decision
g++ -std=c++17 -O2 -Wall -Wextra -Werror -pedantic \
  -I builds/scan_07/src/plan_env/include \
  reactive_stair/diagnose_actual_pct_step_score.cpp \
  -o /private/tmp/diagnose_actual_pct_step_score
python3 reactive_stair/emit_pct_selected_ground.py | /private/tmp/diagnose_actual_pct_step_score
```
