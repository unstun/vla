# v34 component results (scan65)

These are acceptance steps K1–K4 of `PLAN.md`, on `runtime/scan65_evidence_floor_v34`. All ran in this MacBook's
Docker VM with the pinned Humble image, and no physical episode had run when they were recorded. K5, the
independent review, is recorded separately.

## K1: materialization and build

- **Byte-exact materialization** (`materialize.py`, `changes.patch`, `check_build.py` → `check_build.json`):
  - **What changed:** 144 lines inserted, none removed, in three files:
    - the new header `evidence_floor_fill.h`: +115;
    - `grid_map.h`: +6;
    - `scan_reactive_grid_methods.inc`: +23.
  - **Removal check:** removing the insertions gives back scan64's bytes, file by file.
  - **Line endings:** `grid_map.h` mixes CRLF and LF (433 of 516 lines CRLF). Its first insertion follows a CRLF line
    and is CRLF; the other two follow LF lines.
  - **Patch check:** applying `changes.patch` to `parent_source/` (scan64's bytes) and to an empty file reproduces
    all three scan65 files byte for byte. Every other source file equals scan64's.
- **Build** (`repairs/2026-09-26_generic_occupancy/build_candidate.py`):
  - **Result:** built scan65 in the pinned image from scan64's colcon cache in 129 s. It passed, and the source
    identity was unchanged before and after. Evidence: `build_evidence_scan65_evidence_floor_v34/` and
    `candidate65_evidence_floor_v34_identity.json`.
  - **A first attempt did not start** (`attempt01_docker_daemon_down/`): Docker Desktop was not running, and no
    container ran.
- **What recompiled:** the same 7 translation units as v31's build: `grid_map.cpp`, `dyn_a_star.cpp`,
  `bspline_optimizer.cpp`, `measured_cloud_probe.cpp`, `scan_planner_node.cpp`, `scan_replan_fsm.cpp` and
  `planner_manager.cpp`.
- **Installed files that changed from scan64:**
  - `libplan_env.a`, `scan_planner_node` and `measured_cloud_probe`;
  - the headers `grid_map.h` and `scan_reactive_grid_methods.inc`, and the new `evidence_floor_fill.h`.

  `libbspline_opt.a`, `libpath_searching.a` and every shared library are byte-identical to scan64's.
- **Warnings:** 32 in both builds, the same multiset of file, line, column and message. None is new, and none names
  the new code.

## K2: the red/green fill contract (`fill_contract/`)

- **Setup:**
  - **Builds:** one source is compiled against scan64 (red, `red_v33/`, 104 s) and scan65 (green, `green_v34/`,
    126 s). All exit codes are 0.
  - **The rule's parameters:** tolerance 0.12 m, step 0.26 m, guard radius 0.35 m.
  - **The oracle:** `oracle.py` is an independent Python implementation of `PLAN.md`'s rule. `check.py` judges both
    builds against it (`contract_results.json`: passed).
- **Synthetic cases (16, `make_cases.py`).** Red returns every input unchanged. Green equals the oracle layer by
  layer, and each case's designed outcome holds on both the oracle's and the native output:

  | Case | Green |
  |---|---|
  | Band trimmed beside solid cells | all 195 trimmed floor cells added |
  | Isolated wrong-height cell | the floor added at that cell only; the wrong layer kept first |
  | Lower level at (15, 6) inside the guard | 1.56 m not added within 0.35 m (square to square) of it; 126 added elsewhere, plus the hole's own lower layer |
  | No surface at all at (15, 6) | the same rejection set; 126 added |
  | Only a higher surface at (15, 6) (solid) | nothing rejected for it; 194 added |
  | A surface 0.20 m below at (15, 6) | floor for the guard; nothing rejected |
  | A surface 0.27 m below at (15, 6) | a drop; the same rejections as a lower level |
  | Navigation layer 0.10 m from the evidence floor | nothing added at the floor |
  | Navigation layer 0.13 m away | the floor added beside it in every trimmed cell |
  | Two evidence layers 0.04 m apart | added once per cell |
  | Evidence origin offset by −0.07 m | each layer added in the navigation cell containing its evidence cell's centre |
  | Evidence absent, in another frame or resolution, empty, or non-finite | nothing added; output equals input |

- **Real map** (the pinned grounds):
  - **Green:** adds 17,214 layers and rejects 22,785 candidates near drops, exactly the oracle's set (cell and
    float64 height). Every navigation layer is kept. The navigation ground has 27,278 cells; the result has 28,378.
  - **Red:** adds nothing.
  - **By height:** 14,458 of the added layers are on the ground floor (0.1 m bin) and 1,205 on the upper floor
    (1.5–1.6 m).
  - **Scoring:** after v30's step score, the added layers are 14,915 Flat, 445 Stair and 1,854 Unknown; Unknown still
    blocks.
  - **Cost:** one full-map fill takes 63 ms, best of three.
- **Node** (`fill_order_contract`, real subscriptions, both builds). Two orders:
  - **navigation first:** navigation, evidence, malformed evidence, evidence again, navigation again, evidence with
    a hole east of the entry band, evidence again;
  - **evidence first:** evidence, then navigation.

  At every checkpoint (7 and 2), in both builds, the node's raw ground, its scored terrain and the decision's terrain
  equal the tree's own headers applied to the node's decoded inputs with the evidence then usable. Green's kept
  navigation ground equals the decoded navigation ground.
  - **Green adds:** none without usable evidence; 17,214 with the pinned evidence; 17,177 with the hole.
  - **The hole:** it removes 4 evidence floor points, one per cell in x −4.495 to −4.395, y −3.55 to −3.15. Those
    cells keep only the ground floor below and the upper floors, so 37 added layers within 0.35 m of them are rejected
    as beside a drop.
  - **Red:** never adds.

## K3: the two frozen corridor-entry stands (`stand_replay/`)

- **The replay:** the corridor-entry audit's `corridor_probe`, rebuilt against scan65, on the audit's frozen states
  with the pinned grounds.
- **v32's state:** it is the audit's re-frozen one, at its live replan moment (audit review round 1, B2). The run on
  the first, 5 ms late state is kept in `attempt01_v32_late/`, and it gave the same outcome (a 5.84 s clear curve on
  the first attempt).

| Stand | scan64 (the audit's replay; reproduces the trial) | scan65 |
|---|---|---|
| v33 | 9 failed attempts: "inside an obstacle" at the start, then seed and optimizer failures | the first attempt plans; the committed 5.47 s curve to (−1.658, −4.144) passes the native full check (548 samples) |
| v32 | 9 failed attempts: curves rejected at cell (47, 41) | the first attempt plans; the committed 5.77 s curve to the same target passes (578 samples) |

- **Headings:** all start headings are free at both stands on scan65.
- **Cross-check:** the probe's breakdown matched the native functions, with 0 mismatches.
- **The fill's log lines:** each replay's six `evidence_floor_fill` lines include the used-evidence ones, with
  86,775 navigation layers, 17,214 added and 22,785 rejected.

## K4: saved states and native regression

Both suites are v31's, rebuilt against scan65. Each ran alone on the Docker VM (`alone_check.json`: 0 samples with
another container). Every output and normalised log is compared with scan64's recorded run.
- **`log_review.py`:** keeps v31's normalisation and also drops v34's `evidence_floor_fill` lines, recorded
  separately.
- **`difference_analysis.py`:** checks every query-CSV change against the fill. It also sorts the log differences by
  kind.

### Saved states (`runs/v34_saved_states01`, 498 s; `review.json`: component scope passed)

- **Exit codes:** all 9 probes and both breakdowns exit 0.
- **Every state still continues**, with the same frontier.
- **The seven walking-start states:**
  - `result.json` and `result_negatives.json` are identical to v31's.
  - Their query CSVs differ only in `front_support_count` and `rear_support_count` (957 of 1,474 rows). In every row
    each count grows by exactly the layers the fill added in that footprint cell.
- **Landing and onset (the v29 landing-stall states, on the upper landing)** accept longer continuations:
  - landing: 0.568 → 0.914 m;
  - onset: 1.401 → 1.833 m.

  Their local target moves into the corridor, from (−4.86, −3.65) and (−4.91, −3.46) to (−4.42, −4.14) and (−4.43,
  −4.13). 9 and 3 route samples at the corridor entry (x −5.0 to −4.2, y −4.3 to −3.5) turn from blocked to free,
  each with a footprint circle or body cell over a cell where the fill added the floor. The landing probe's breakdown
  outputs follow.
- **Logs:**
  - **`reactive_collision_blocked`:** the same lines except the terrain cell count (27,278 → 28,378).
  - **`near_sensor_verdict`:** the diagnostic prints the first queried voxels near the sensor, and only those that
    pass support. The printed set follows the query order. At landing and onset, v34 prints 3 and 2
    measured-obstacle verdicts at points east of the old band edge, which now reach the LiDAR check.
  - **Optimizer and A* lines:** they differ where support changed the candidate sets. Where a start state's A*
    recovered a connector, the connector and cost are the same.

### Native regression (`runs/v34_native_regression01`, 464 s; `review.json`: component scope passed)

- **Continuations:** all 11 are accepted with full gates and negatives. Their JSON outputs and negatives are
  identical to v31's, and the four repeats are identical.
- **Contracts:** the body-support contract (15 cases) and the ground contract pass.
- **Obstacle cases:** all 8 unmapped measured cases (empty, static human, box, thin wall, post, low box, occluded
  human, blocked corridor) and all 5 mapped cases give output identical to v31's.
- **Query CSVs:** all 11 differ only in the two support counts (32 of 103 rows; 957 of 1,474 for v26). Every row's
  change equals the fill's added layers.
- **Logs:**
  - **Most:** terrain cell counts, the extra ground-floor layer (0.058 m) in the probe's `[SUPPORT]` detail, and
    diagnostic sets.
  - **`original`:** the throttled first-blocked line names another query, now a measured obstacle.
  - **`v26`:** a fixed-heading start check at 145.7° reads free.
  - **`v18`:** two seed searches end on A*'s 0.2 s wall-time budget, and a later search recovers. The accepted
    continuation is identical.
  - **`v23_repeat`:** its first goal-neighbour search ends on the budget. That search already timed out in one of
    v31's two runs.
  - **`execution.log`:** build order only.

  The explanations are in `log_difference_explanations.json`.

## What K1–K4 show, and what they do not

- **Shown:**
  - The rule is implemented as specified: the oracle, the cases, the real map and both message orders agree.
  - It frees both frozen corridor-entry stands on the first attempt.
  - It changes no measured-obstacle verdict in the regression.
  - Its other effects on saved states are the added support itself: longer continuations at the landing and onset,
    support counts, and diagnostics.
- **Not shown:**
  - **Live behaviour.** A single physical trial is the next step.
  - **Drop handling in a run.** It is tested by the synthetic cases and the node's hole checkpoint only.
- **A* budget exposure:** the larger free search space makes some A* searches reach their 0.2 s wall-time budget,
  as in `v18` and `v23_repeat`. Whether a search does depends on machine speed. On gpu5070ti, SCAN's container runs
  natively rather than under emulation.
