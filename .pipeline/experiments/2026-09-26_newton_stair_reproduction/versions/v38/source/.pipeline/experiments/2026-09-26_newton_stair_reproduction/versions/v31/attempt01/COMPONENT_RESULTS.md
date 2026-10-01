> **Superseded record (first candidate, scan63).** Kept as written before the first independent review
> (`../independent_review_round1.json`). That review found wording errors here (N8): `all_path_edges_checked`
> also flips in the differing fixtures; "Ran out of pool" appears in green C4 too; the digest covers only
> `occupancy_buffer_inflate_cnt_` among the count buffers; C1 has no pending poses; `alone_check.txt` samples
> only the start and end of run `02`. The corridor-entry C4 success is not the diagnosis's result at delta 0 (B2).
> The current results are in `../COMPONENT_RESULTS.md`.

# v31 component results

These are the acceptance steps 1–4 of `PLAN.md`: build, red/green
input-refresh contract, saved states and native regression. No physical
episode had run when they were recorded. The independent review (step 5) is
recorded separately in `independent_review.json`.

The contract's first judgement failed on one red expectation that
`PLAN.md` had mis-transcribed from the stop diagnosis. The criterion was
corrected, and the first judgement is kept (§2).

## 1. Build

- **Build:** `repairs/2026-09-26_generic_occupancy/build_candidate.py`
  built `runtime/scan63_input_refresh_v31` in the pinned image from the
  scan62 colcon cache. It took 95 s, passed, and the source identity was
  unchanged before and after.
- **What recompiled:** the same 7 translation units as in v30, the ones that
  include `grid_map.h`:
  - `grid_map.cpp` (`plan_env`), `dyn_a_star.cpp` (`path_searching`) and
    `bspline_optimizer.cpp` (`bspline_opt`);
  - `measured_cloud_probe.cpp` (`geometry_probe`);
  - the planner node's `scan_planner_node.cpp`, `scan_replan_fsm.cpp` and
    `planner_manager.cpp`.
- **Installed files that changed:** `libplan_env.a`, `libbspline_opt.a`,
  `scan_planner_node`, `measured_cloud_probe` and the installed `grid_map.h`.
  Every shared library is byte-identical to v30.
- **Warnings:** all 32 are v30's. They have the same file and message
  multiset, and none is in v31's new lines.
- **Evidence:** `repairs/2026-09-26_generic_occupancy/build_evidence_scan63_input_refresh_v31/`
  and `candidate63_input_refresh_v31_identity.json`.

## 2. Red/green input-refresh contract (`input_refresh_contract/`)

**Setup**
- **Probe:** `refresh_probe.cpp` keeps the stop diagnosis's replay (v30's
  regression `gen_probe` input replay) byte for byte and appends the contract
  (`make_refresh_probe.py`, `refresh_probe_derivation.json`).
- **Builds:** one source, built against v30 (red) and v31 (green). The two
  runs took 838 s and 841 s.
- **Cases:** each of the four frozen v30 stop states runs five cases, one per
  process, against the real FSM callbacks.
- **Pending inputs:** these are the run's own scans and poses from the same
  interval (`pending/pending_manifest.json`). They are published but not spun,
  as during a long callback:
  - C2 and C4: 3 scans with their sensor poses, plus 44–53 body poses;
  - C3: the 24–28 body poses of those 0.15 s.

**Results** (all 40 processes exit 0; `summary.json`):

| Case | Red (v30) | Green (v31) |
|---|---|---|
| C1 stale scan (0.36 s), nothing pending | all four stop: `Collision`, conflict at 0.000 s, whole route blocked | identical stop and map digest; nothing applied |
| C2 as C1, scans pending | all four stop as in C1 | all four keep their entry state; re-check `Clear`; the processed scan is the newest pending one, age 0.360–0.365 → 0.060–0.065 s; applied at `safety` |
| C3 stale pose (0.15 s), poses pending | holds and `stairs_replan` stop on `InvalidCurve`; corridor entry clear. Each re-check equals the diagnosis's stale-pose row at Δ = 0.15 s | all four clear in their entry state; body age 0.150 → 0.000 s; each re-check equals the diagnosis's fresh-pose row |
| C4 planning timer, scans pending | all four fail in their entry state with "Target is occupied and no collision-free point"; three also print "Ran out of pool" | all four apply the inputs at `exec` and plan successfully (`EXEC_TRAJ`, `final_plan_success=1`) |
| C5 executor path | map digest equals green's C5 | map digest equals green's C2 in all four; nothing left to apply |

- **Equivalence (C5):** applying the pending messages through the refresh
  (green C2) and through the executor (green and red C5spin) gives the same
  FNV-1a digest in every state. The digest covers the occupancy, inflation
  and count buffers, the terrain and non-terrain hit sets, stamps, poses, map
  origin and bounds.
- **Queue depth:** only the newest 5 pending body poses were applied
  (`body_poses=5`), as `SensorDataQoS` keep-last-5 delivers to the executor
  too.
- **Extra time:** processing 3 scans and 8 poses inside the safety callback
  cost 37–69 ms wall (green C2 minus green C5spin, the same check on the same
  map). This is in the pinned linux/amd64 image on this Mac's Docker VM.
- **Artifact of the setup:** C1, C2, C4 and C5 re-stamp the frozen body pose
  at the check time. The pending body poses applied after it are up to
  0.2 ms older, so the body age after the refresh is 0.0002 s, not 0. The
  executor path applies the same order and gives the same digest.

**First judgement and correction**
- **What failed:** the first judgement (`summary_first_judgement.json`, from
  `analyze_first_judgement.py`) failed on one check,
  `stairs_replan: C3 red moving curve clear`.
- **Why the expectation was wrong:** `PLAN.md` had expected red to stay clear
  on both moving curves. The stop diagnosis, committed in b3a172e5 before
  this contract ran, records the opposite for one of them:
  - `RESULT.md` §2: with a pose older than 0.1 s, a curve that ends at rest
    fails as `InvalidCurve` in its last ~0.1 s.
  - Its `stairs_replan/result.json` row at Δ = 0.15 s: `InvalidCurve` at
    3.9526026171 s, 146 samples.
  - Red reproduced exactly that time and sample count.
- **What changed:** `analyze.py` now requires two things of red C3, in all
  four states:
  - its re-check equals the diagnosis's stale-pose row (status, time, samples
    and `raw_t`);
  - it stops on `InvalidCurve` exactly when that row is `InvalidCurve`.

  The correction also added the red C4 whole-route-block test, which the
  contract described but did not test. The green criteria and every case
  output are unchanged (the per-case rows of both judgements are identical).
  `PLAN.md` records the correction under its table.
- **Also recorded:** green C3 equals the diagnosis's fresh-pose row in all
  four states. This is recorded, not required.

**What the contract does not cover**
- **Inner refresh sites:** every pending message is published before the
  call, so only the first site of each callback (`safety` or `exec`) applies
  anything. `route_walk`, `replan_start`, `rebound_round` and `final_check`
  run with empty queues here. Messages arriving during a callback are
  exercised only in a live run.
- **States:** these are four frozen stop states, not the whole route.

## 3. Saved states (`runs/v31_saved_states01`)

- **What ran:** v30's unchanged regression `gen_probe` and landing breakdown
  probe, rebuilt against v31 (`plan_env` is static). They replayed the seven
  frozen v28 walking-start states and the frozen v29 landing and onset
  states. It took 473 s, and the run overlapped the green contract on the
  same Docker VM.
- **Outcome:** all nine continue, as in v30. The seven start states accept
  0.56–1.97 m. Landing accepts 0.568 m (frontier 11.043 s) and onset 1.401 m
  (frontier 10.743 s).
- **Identity:** every result, negatives, query and breakdown file is
  byte-identical to `runs/v30_saved_states01`. All 12 compared logs are
  identical after v30's normalisation. The review passes with no difference
  to explain (`review.json`).
- **Expected:** these replays deliver every input through the executor before
  planning, so nothing is pending. They contain no `input_refresh` line.

## 4. Native regression (`runs/v31_native_regression01`, `02` and the timing control)

This is v30's suite, with identical probe source, inputs and commands, run
against v31. `01` (450 s) overlapped the green and red contract runs on the
same Docker VM. `02` (435 s) reran it alone, with no other container running
from start to end (`alone_check.txt`). A first try of `02` used ROS domain 233,
which Fast DDS rejects; it stopped at start-up and is kept in
`runs/v31_native_regression02_attempt01_domain233/` with a note.

- **Continuations:** in both runs all 11 are accepted with full gates and
  negatives.
- **Repeats:** identical.
- **Contracts:** the body-support and ground contracts pass.
- **Identical to v30:** every continuation and query CSV and all negatives,
  in both runs. So are all 5 mapped and 8 unmapped fixture outputs, except
  one fixture per run:

| Run | Output that differs | Logs that differ |
|---|---|---|
| `01`, under load | `unmapped_low_box` | `unmapped_low_box.log`, `v18.log` |
| `02`, alone | `mapped_low_box` | `mapped_low_box.log`, `v18.log`, `v23_repeat.log`, `execution.log` (build order) |

- **What the differences are:** each differing fixture output is one A*
  search that exceeded its 0.2 s wall-time budget: `search_status` 0 → 2 and
  an empty path, every other field identical.
  - **In `01`:** the same v31 build gives v30's `unmapped_low_box` output
    in `02`.
  - **In `02`:** it gives v30's `mapped_low_box` output in `01`.
  - **Logs:** they differ only in A* elapsed times and budget failures, and in
    the planner path those failures take before the same committed result.
    `01`'s `v18` skips one repeated full-target attempt whose curve v30's
    final gate rejected; the committed prefix is identical.
- **Timing control** (`runs/v31_regression_timing_control01`):
  - **Setup:** the four timing-sensitive fixtures (`v18`, `v23` and its
    repeat, both low-box fixtures) ran with the v30 and v31 regression probes
    in alternating containers, five repetitions each, alone on the VM.
  - **Outputs:** the v31 build gives v30's output in all 25 fixture runs. The
    v30 build gives `search_status` 2 with an empty path for
    `unmapped_low_box` in one of its five repetitions, the same flip `01`
    showed.
  - **Speed:** `v18`'s failed rebound searches (267 nodes each) have a median
    of 0.105 s with v30 and 0.104 s with v31. Per repetition the v31 − v30
    median difference is +0.003, −0.001, +0.0015, −0.0055 and +0.001 s.
  - **Budget failures:** 26 with each build across the five fixtures. By
    fixture, v30 has 15, 5, 5, 0 and 1, and v31 has 16, 5, 5, 0 and 0.
  - `dyn_a_star.cpp` is byte-identical in v30 and v31. It times the whole
    search on `steady_clock`.
- **Conclusion:** these differences come from the A* wall-time budget on a
  shared machine, not from v31. v31 does not slow A* measurably.
- **Review:** both `review.py` runs pass with every difference explained
  (`difference_explanations.json`, `log_difference_explanations.json`), 27
  logs compared and no stale entry. `freeze.py` requires both.
- **Implication for the trial:** the same budget makes live planning
  outcomes vary from run to run, in v30 as in v31.

## Status

Steps 1–4 pass their component scope. No physical episode has run, and
nothing here is a navigation result. v3 remains the last accepted condition.
