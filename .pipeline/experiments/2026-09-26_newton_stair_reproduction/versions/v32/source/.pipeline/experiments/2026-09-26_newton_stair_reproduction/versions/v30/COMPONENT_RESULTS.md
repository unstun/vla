# v30 component results

These are the acceptance steps 1–6 of `PLAN.md`. No physical episode had run
when they were recorded. The first independent review failed on records,
regression scope and risk statements (no code defect). This file was
corrected after it, and the contract and both reviews were strengthened and
rerun (section 6).

## 1. Build

- **Build:** `repairs/2026-09-26_generic_occupancy/build_candidate.py`
  built `runtime/scan62_support_evidence_v30` in the pinned image from the
  scan61 colcon cache. It took 69 s, passed, and the source identity was
  unchanged before and after.
- **What recompiled:** the 7 translation units that include the two changed
  headers: `grid_map.cpp` (`plan_env`), `dyn_a_star.cpp` (`path_searching`),
  `bspline_optimizer.cpp` (`bspline_opt`), `measured_cloud_probe.cpp`
  (`geometry_probe`), and the planner node's `scan_planner_node.cpp`,
  `scan_replan_fsm.cpp` and `planner_manager.cpp`.
  - **Installed files that changed:** `libplan_env.a`, `scan_planner_node`,
    `measured_cloud_probe` and the two installed headers.
  - **Warnings:** all 32 are pre-existing and in unchanged files.
- **Evidence:** `repairs/2026-09-26_generic_occupancy/build_evidence_scan62_support_evidence_v30/`
  and `candidate62_support_evidence_v30_identity.json`.

## 2. Red/green support contract (`support_contract/`)

One source is compiled against v29 (red) and v30 (green) in the pinned image
(`run.py`, 58 s and 56 s). `check.py` compares every label and first-pass
height with `oracle.py`. All checks pass (`contract_results.json`).

- **Oracle:** `oracle.py` restates both rules in Python. It follows the C++
  structure closely, so it is a restatement, not an independent derivation.
  The independent reviewer's own implementation also reproduced both
  full-map dumps with 0 mismatches.
- **Pinned Building grounds:** the navigation ground is `ground_precise.f32`,
  and the surface evidence is `raw_ground.f32`. The trial publishes these
  exact bytes. The payloads, rebuilt with the publisher's own functions from
  the inputs `scripts/native_graph.py` passes, are byte-identical to both
  files (`runtime_input_identity.json`). So the green full-map labels are the
  labels the node computes in the trial.
  - **Match to the rules:** v29's labels equal the v29 rule on all 86,775
    layers, and v30's equal the v30 rule on all of them.
  - **What changed:** the rules differ on 7,873 layers, 7,513 going from
    Unknown to Flat and 360 to Stair. No other change occurs.
  - **Totals:** v29 has 7,873 Unknown, 72,232 Flat and 6,670 Stair layers.
    v30 has 79,745 Flat and 7,030 Stair, so no Unknown or Unsupported layer
    remains (see `PLAN.md`, risks added after the review).
  - **Landing box:** all 39 of its Unknown walkway layers (out of 153) become
    supported.
  - **Scored cells:** the set of scored cells is the navigation set in both
    trees.
  - **Label dumps:** both `map_labels.csv` files are local only. They are
    byte-identical to the first run's, and `label_dump_sha256.json` records
    their SHA-256 and label counts.
- **Synthetic cases (17):** each tree matches its own rule on every label,
  and the edge cell matches the plan's table.
  - **Changed by v30** (v29 all Unknown):
    - artifact edge → Flat;
    - evidence step up → Stair;
    - mixed step (+0.20 m evidence beside a −0.10 m navigation cell) →
      Unsupported;
    - sub-cell evidence origin offset → Flat;
    - an evidence origin offset of 0.07 m (0.7 cell), where only the evidence
      cell under the neighbour's centre has the level → Flat. Identity or
      corner lattice mapping reads a neighbouring evidence cell and fails;
    - a navigation neighbour with two equidistant layers (ambiguous) and
      evidence at the level → Flat.
  - **Unknown in both:** real drop, evidence absent there, ambiguous evidence,
    and evidence only beyond 0.26 m.
  - **Identical in both:** absent neighbours (now with evidence at another
    level, 1.62 m, so evidence wrongly used for absent neighbours would fail),
    navigation already has the level, and all five unusable-evidence forms
    (none, other frame, other resolution, empty, non-finite).
  - **Mutation check** (`mutation_check.py`, `mutation_results.json`): each
    wrong variant of the rule fails at least one case.
    - identity or corner lattice mapping: `offset_selects_centre_cell`;
    - evidence used for absent neighbours: `absent_neighbours`;
    - ambiguity ignored: both ambiguity cases;
    - skipping the neighbour instead of using the evidence height: both
      evidence-step cases.
- **Node delivery order:** real GridMap subscriptions.
  - v30 scores exactly as v29 until evidence arrives. It then uses the
    evidence after navigation-then-evidence, after evidence-then-navigation
    (same label digest), after the evidence is restored and after the
    navigation ground is republished.
  - Malformed evidence falls back to the v29 labels.
  - **Real drop in the node:** republishing the evidence without its 8 points
    in the cell column beside the landing ring makes 10 walkway layers in the
    landing box Unknown again. That count equals the oracle's for the same
    removal. Restoring the evidence clears them.
  - The collision decision's copy always equals the node's labels.
  - v29 never uses the evidence: 39 Unknown landing-box layers at every
    checkpoint.
- **Scoring time** (one full-map scoring, best of 3, in the pinned
  linux/amd64 image on this Mac's Docker VM, not the robot's CPU): v30
  takes 71.8 ms with the evidence and 64.2 ms without it. v29 takes
  67.0–68.0 ms. The surface callback runs one such rescoring per evidence
  message.
- **Superseded:** `attempt01/` keeps the first passing run (15 cases, no node
  drop negative), unchanged.

## 3–4. Saved states (`runs/v30_saved_states01`)

The unchanged regression `gen_probe` was rebuilt against v30 (`plan_env` is
static). The read-only landing breakdown probe was rebuilt too. All nine
states continue, with boundary PVA, the full-curve gate and all negatives
(`review.json`, 450 s).

| State | v29 | v30 |
|---|---|---|
| seven walking-start states, 0.3517–0.3987 m | continue | `result.json`, negatives and queries byte-identical to v29 |
| landing, 80.98 s | frontier 8.645 s, fails | frontier 11.043 s, accepts 0.568 m |
| onset, 47.36 s | frontier 8.645 s, fails | frontier 10.743 s, accepts 1.401 m |

- **Match to the oracle:** the landing result, negatives and queries equal
  the diagnosis audit's probe-only oracle byte for byte. Onset equals it in
  every field except `start_occupied`: oracle 1, v30 0.
  - **Why `start_occupied` differs:** it is checked at the heading toward
    the chosen target. Oracle and v30 chose the same target, and the front
    footprint circle's centre falls in cell (21,74). Its 1.149 m layer lies
    outside the oracle's relabelled walkway band, so the oracle keeps it
    Unknown. v30 labels it Flat.
  - **Predicted values:** the support check alone predicts all three
    recorded values: baseline 0, oracle 1, v30 0
    (`difference_analysis/onset_start_support.json`).
- **Robot's own cell:** landing `start_occupied` goes from 1 (v29) to 0.
  Onset was already 0 in the v29 baseline.
- **Beyond the new frontiers:** the breakdown finds only never-observed voxels
  in the occluded corridor (66 landing / 72 onset) and the map boundary
  (24 / 18). It matches the native functions with 0 mismatches.
- **Byte-identical results, different planning.** In the seven start
  states, the recorded outputs match v29, but the planner path does not:
  - 6 of 7 states list more A* terminal candidates (for example 317 → 444).
  - **The planner's sequence:** it tries the full 3.85 s local window, then
    shorter reference prefixes: 1.925 s, then 0.9625 s in these states.
    Control goes from 1.925 s to 0.481 s.
  - **z_0p3600, z_0p3700 and z_0p3800:** v29 optimized a curve for the
    1.925 s prefix that the final gate rejected. In v30 that attempt fails
    inside the optimizer. Both versions then commit the identical 0.9625 s
    prefix.
  - **z_0p3650:** v30 adds one failed attempt on the full window, whose seed
    it now finds through newly supported cells. It then accepts a slightly
    different spline to the same 1.925 s prefix target (cost 0.510 → 0.564,
    412 → 410 samples).
  - The `[FIXED_START_YAW]` diagnostic at −1.994691 and 2.54264767 goes from
    1 to 0. The front circle centre cells (14,142) and (13,145) move from
    Unknown to Flat. Across these seven states and the regression's two `v26`
    runs, the support check alone predicts all 72 printed values
    (`difference_analysis/fixed_yaw_support.json`).
- **Review:** `review.py` now compares the recorded result, negatives and
  queries with v29 (start states) or the oracle (landing and onset), and
  every normalised start-state log with v29. The landing and onset breakdown
  CSVs are checked against the native functions instead.
  - **What it does not compare:** the landing and onset logs line by line,
    because this run's v29 reference has no such states.
  - **When it fails:** on any unexplained or stale entry in
    `difference_explanations.json`, and on an incomplete log comparison (no
    log compared, a missing v29 log, or an unexpected log without a v29
    counterpart).
  - **Result:** it passes with 8 compared logs and 8 explained differences,
    namely 7 probe logs and `onset.start_occupied`.

## 5. Native regression (`runs/v30_native_regression01`)

This is v29's suite, with identical probe source, inputs and commands, run
against v30 in 435 s.

- **Continuations:** all 11 are accepted with full gates and negatives.
- **Repeats:** identical.
- **Contracts:** the body-support and ground contracts pass.
- **Unchanged outputs:** all 8 unmapped and 5 mapped fixture outputs, all
  negatives, and every other continuation and query CSV are byte-identical to
  v29.
- **Output differences: only `v26` and its repeat**
  (`difference_explanations.json`):
  - **What changed:** the accepted prefix grows from 1.848 m to 3.662 m.
    - v29's optimizer rejected the full 3.675 s target: "First three control
      points are in obstacles" at the start.
    - Reference-prefix halving then accepted 1.8375 s.
    - In v30 the full target optimizes and passes the unchanged full-curve gate
      (652 samples).
  - **Why:** the start sits beside the ground-floor walkway's edge column at
    the stair foot. There, 24 walkway-level layers within 0.6 m move from
    Unknown to Flat or Stair, including the cell under the first control
    point.
  - **Query CSV:** only the `rejected_target` row's `t` (the accepted target
    time) differs. All 1,473 route-sample rows are identical.
- **Log differences:** 27 logs are compared, and 8 normalised logs differ
  from v29. All 8 are recorded (`log_differences_vs_v29.json`) and explained
  (`log_difference_explanations.json`).
  - **When `review.py` fails:** on any unexplained or stale entry, whether
    for an output or a log, and on an incomplete log comparison (no log
    compared, or a log present in only one run).
  - **Build output:** `execution.log` differs only in parallel-build output
    order.
  - **Diagnostic subsets:** `expired`, `original`, `v26` and `v26_repeat`
    print a different subset of the capped near-sensor diagnostic. No point
    printed by both runs changes (`difference_analysis/near_sensor_sets.json`).
  - **`v18`:** more A* terminal candidates, plus a failure-only timing
    warning. Each of the six failed rebound searches now takes 0.107–0.109 s.
    The committed curve is unchanged.
  - **`v23` and its repeat:** a different A* seed. v30's full-target curve
    now optimizes and is stopped only by the unchanged final full-curve gate
    (Collision at t = 4.955 s). The same prefix is committed.
  - **`v23_repeat` wall time:** one goal-neighbourhood search there depends
    on the 0.2 s wall-time budget.
  - **`v26`:** the optimizer path behind the explained output change. The
    fixed-yaw diagnostic changes as in the saved states.
- **Non-issue:** `request.json` mounts `runs/v17_native_regression01/probe_build`
  read-only, but `inside.sh` never uses it. All probes are rebuilt from
  `probe_source` against v30.

## 6. Independent review

- **First verdict (failed):** `runs/v30_native_regression01/independent_review.json`.
  It found no code defect. It failed on:
  - two wrong claims in this file (onset equal to the oracle; the robot's own
    cell in both states);
  - unrecorded log differences;
  - missing risk statements.
- **Fixes:**
  - the corrections above;
  - the log comparisons and explanations for both runs;
  - stricter `review.py` scripts;
  - two new synthetic cases, a stronger absent-neighbour case and the
    mutation check;
  - the node-level real-drop negative and the scoring time;
  - the label-dump hash record;
  - the risks added to `PLAN.md`.
- **Second verdict (failed, text only):** all five first-round blocking
  items were resolved and verified.
  - **New blocking item:** the rewritten saved-state explanations called the
    1.925 s reference-prefix attempts "full-target" attempts, and two
    sentences overstated the log comparison.
  - **Fixes:** both are corrected. Both `review.py` scripts now also fail on
    an empty or partial log comparison; with the v29 logs deleted from a
    scratch copy, both fail. The regression review also rejects stale
    output explanations.
- **Third verdict: passed**, all 8 checks, with nothing blocking.
  - **Scope:** this is the pre-freeze component review, not validation.
  - **Text applied afterwards:** its four non-blocking wording points were
    applied afterwards, as text only. They cover the z_0p3700 timeout placed
    in the full-window stage, control's prefix sequence, "start-state" in
    `PLAN.md`, and what the saved-state review compares.

## Claim boundary

- **What these steps show:** v30 scores support by the specified rule and is
  wired to its input in both delivery orders. The frozen landing and onset
  states now plan past the old frontier. Every difference in the regression
  outputs and logs, and in the saved-state outputs and start-state logs, is
  recorded and explained. The landing and onset logs are not compared line
  by line.
- **What is not yet known:** whether the robot passes the upper landing and
  reaches the goal.
  - On the pinned Building, v30 leaves no Unknown or Unsupported layer, so
    the trial cannot exercise drop handling.
  - The residual risks are in `PLAN.md`, and v3 remains the last accepted
    condition.
- **Local-only bytes:** the contract, probe and regression CMake build trees
  and the four 4 MB full-map label dumps (two current, two in `attempt01/`)
  stay local and are git-ignored by path. `support_contract/label_dump_sha256.json`
  records the dumps' hashes now. `versions/v30/LOCAL_ONLY_BYTES.json`,
  written after the trial, lists every local-only entry.
