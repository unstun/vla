# v31 component results (second candidate, scan64)

These are the acceptance steps 1–4 of `PLAN.md`: build, red/green
input-refresh contract, saved states and native regression, all on
`runtime/scan64_input_refresh_v31`. No physical episode had run when they were
recorded.
- **The first candidate:** scan63 and its records are in `attempt01/`. The
  first independent review failed them (`independent_review_round1.json`),
  and Dr Sun kept the narrower design and asked for every finding to be fixed.
- **Step 5:** the independent re-review is recorded separately in
  `independent_review.json`.

## 1. Materialization and build

**Byte-exact materialization** (review finding B1)
- **What changed:** `materialize.py` inserted 134 lines into five files and
  removed none (`changes.patch`: 134 added, 0 removed).
  - `grid_map.h`: +6;
  - `grid_map.cpp`: +81;
  - `scan_replan_fsm.cpp`: +41;
  - `planner_manager.cpp`: +4;
  - `bspline_optimizer.cpp`: +2.
- **Line endings:** `grid_map.h`, `grid_map.cpp` and `bspline_optimizer.cpp`
  mix CRLF and LF lines. Their CR counts are kept: 433, 1060, and
  1158 → 1160, since the optimizer's two inserted lines follow a CRLF line.
  The other insertions follow LF lines.
- **Patch check:** applying `changes.patch` to copies of `parent_source/`
  (which equals v30's bytes) reproduces all five scan64 files byte for byte.
  Every other source file is identical to v30's.
- **Code-level difference from scan63:** after CR normalisation, it is
  exactly the fixes:
  - N1 drain order;
  - N2 take errors and plain-number stamps;
  - N3/N5 logging;
  - N6 FSM odometry;
  - N7 the `target_check` site.

  `planner_manager.cpp` is identical to scan63's, and
  `bspline_optimizer.cpp` differs only in its CR bytes.

**Build**
- **Build:** `repairs/2026-09-26_generic_occupancy/build_candidate.py` built
  scan64 in the pinned image from the scan62 colcon cache. It took 71 s,
  passed, and the source identity was unchanged before and after. Evidence:
  `build_evidence_scan64_input_refresh_v31/` and
  `candidate64_input_refresh_v31_identity.json`.
- **What recompiled:** the same 7 translation units as in v30:
  - `grid_map.cpp`, `dyn_a_star.cpp` and `bspline_optimizer.cpp`;
  - `measured_cloud_probe.cpp`;
  - `scan_planner_node.cpp`, `scan_replan_fsm.cpp` and `planner_manager.cpp`.
- **Installed files that changed from v30:** `libplan_env.a`,
  `libbspline_opt.a`, `scan_planner_node`, `measured_cloud_probe` and the
  installed `grid_map.h`. `libpath_searching.a` (A*) and every shared library
  are byte-identical to v30's.
- **Warnings:** all 32 are v30's (the same file and message multiset); none is
  new.

## 2. Red/green input-refresh contract (`input_refresh_contract/`)

**Setup**
- **Probe:** `make_refresh_probe.py` keeps the stop diagnosis's replay
  byte for byte and adds four standard-library includes before it.
- **Builds:** the same source was built against v30 (red) and scan64
  (green).
- **Cases:** red runs C1–C6 and C7spin; green also runs C7refresh. Each case
  is one process on each of the four frozen v30 stop states: 28 red and 32
  green processes, all exit 0 (1143 s and 1300 s, run side by side).
- **Pending inputs:** the run's own, unchanged from the first contract
  (`pending/pending_manifest.json`):
  - C2, C4, C5, C6 and C7: 3 scans with their sensor poses, plus 44–53 body
    poses;
  - C3: 24–28 body poses.
- **Which lines count:** only `input_refresh` lines between the call's begin
  and end markers.

**Judgement.** The first judgement failed one check in all four states,
"C1 green applies nothing". Its test ("no refresh line in the call") did not
fit v31's logging.
- Green C1's safety callback replans after its conflict, as red's does. Each
  of its three replan attempts passes `target_check`, which v31 logs on every
  call, here with all counts 0.
- The corrected test is "every line applied nothing", and C5 uses the same
  test.
- The first judgement is kept (`summary_first_judgement.json`,
  `analyze_first_judgement.py`), and `PLAN.md` records the correction.
- The corrected judgement passes (`summary.json`).

**Results**

| Case | Red (v30) | Green (v31, scan64) |
|---|---|---|
| C1 stale scan (0.36 s), nothing pending | all four stop: `Collision`, conflict at 0.000 s, whole route blocked | identical stop, re-check and map digest to red's in all four; three `target_check` lines per state, all applying nothing |
| C2 as C1, scans pending | all four stop as in C1 | all four keep their entry state with a `Clear` re-check. The processed scan is the newest pending one, age 0.360–0.365 → 0.060–0.065 s. Applied at `safety`: 3 sensor poses, 3 clouds, 5 body poses |
| C3 stale pose (0.15 s), poses pending | each re-check equals the diagnosis's stale-pose row at Δ = 0.15 s. The holds and `stairs_replan` stop on `InvalidCurve`; the corridor entry stays clear | all four clear in their entry state; body age 0.150 → 0.0001 s. Each re-check equals the diagnosis's fresh-pose row (recorded, not required) |
| C4 planning timer, scans pending | all four fail in their entry state with "Target is occupied and no collision-free point" | all four apply the inputs at `exec` and plan successfully (`EXEC_TRAJ`, `final_plan_success=1`), 319–369 ms |
| C5 executor path | map digest equals green's | map digest equals green's C2 in all four |
| C6 inputs arriving during a planning call | no refresh; final map digest equals red C5spin | refresh lines at all four inner sites; 10–15 messages applied there; plans successfully in all four; final map digest equals green C5spin |
| C7 split batches | C7spin digests: c1370c11ad52a675, 3ca6cdb96f7b0ef8, 5ef97cd5094c2a1f, e243117632ff68ba | C7refresh and C7spin: identical per-batch records and digests to red's |

**FSM odometry** (review finding N6)
- **Green:** in C2, C3 and C4, `odom_pos_` and the map's body pose both
  equal the newest pending body pose.
- **Red:** `odom_pos_` stays at the frozen body pose in C2 (re-stamped), up
  to 0.12 m from the newest pending one.

**C4 beside the diagnosis** (review finding B2)
- **The comparison:** the diagnosis's replan at Δ = 0 succeeded in
  `stairs_replan`, `stairs_hold` and `upper_corridor_hold`, and failed at the
  corridor entry. Green C4 plans successfully in all four.
- **Why the corridor entry differs:** not isolated.
  - **What differs:** green plans 0.30 s later, from the run's newer scans
    and a later point on the executing curve.
  - **The diagnosis's failure:** at Δ = 0 the first colliding sample was
    WrongHeight at a navigation cell 2.61 m ahead. That is ground geometry,
    not scan age. Green's final curve crosses the same stretch and is clear.
  - **Another possible cause:** A* wall-time variation.
- **What it is not:** green C4 does not reproduce the Δ = 0 result, and the
  contract does not compare with it.

**C6 in detail** (review finding N4)
- **What arrives when:** at the call, the first two scans and the body poses
  before the second are pending. A helper thread publishes the rest in 8–10
  batches, 25 ms apart.
- **What the inner sites applied:**
  - **The last scan** (pose and cloud) with 5 body poses, at `replan_start`:
    the second attempt's in `stairs_replan` and `stairs_hold`, and the first
    (and only) one in `upper_corridor_hold`.
  - **Body poses:** 3–5 at `target_check` in all four states, and 3, 3 and 8
    at `rebound_round` in `stairs_replan`, `stairs_hold` and the corridor
    entry.
- **Corridor entry:** its call ended after 216 ms, with 7 of 10 batches
  published. `final_check` applied the last scan's sensor pose, whose cloud
  was still to come. The executor then applied that cloud with that pose,
  and the final map equals the executor path's.
- **Setup artifact:** the frozen body pose is re-stamped at the check time,
  and the pending body poses applied after it are older. So in C6 the body
  age after `exec` is 0.160–0.165 s, and 0.115–0.145 s after the first
  `target_check`, until the helper's poses arrive. A live run delivers poses
  in stamp order.

**C7 in detail**
- **Batch 4:** its cloud, whose sensor pose arrives only in batch 5, is
  applied with the previous scan's pose on all three paths (red spin, green
  spin, green refresh). The per-batch sensor position after batch 4 equals
  the one after batches 2–3.
- **Final map:** C7's final map therefore differs from C5spin's in every
  state. v31 does not repair a cloud delivered before its own pose; nor does
  v30's executor.
- **Precision:** the per-batch records print at the stream's default 6
  significant digits, so their equality is coarse. The final FNV-1a digest
  is exact, and it is equal on all three paths.

**Other measurements**
- **Extra time:** 46–83 ms wall inside the safety callback (green C2 minus
  green C5spin, the same check on the same map).
  - **What it covers:** 3 scans with their 3 sensor poses and 5 body poses
    applied to the map, plus 5 FSM odometry messages.
  - **Where:** the pinned linux/amd64 image, with red and green running side
    by side on this Mac's Docker VM.
- **Queue depth:** at most 5 body poses were applied per site (`SensorDataQoS`
  keep-last-5).

**What the contract does not cover**
- **States:** four frozen stop states, not the whole route. Sim time is frozen
  during each call.
- **Timing:** C6's mid-call arrivals depend on the call's wall time. The
  per-site pattern differs between states and would differ between runs.
- **Narrower checks than the table:**
  - **C1:** "nothing applied" rests on the refresh lines and the unchanged
    scan age. A body pose applied at `safety` with a fresh age would print no
    line. Green C1's map digest and re-check equal red's in all four states,
    which does cover it; the analyzer does not assert this equality.
  - **C4 and C6:** "no stale signature" is judged on two classes, a conflict
    stop at 0.000 s and a whole-route block. None of the other classes
    appears in any green C4 or C6 call: `remaining_spline_invalid`,
    `final_spline_rejected`, "inside an obstacle" and a blocked terminal
    point (round-2 review NB1).

## 3. Saved states (`runs/v31_saved_states02`)

- **What ran:** v30's unchanged regression `gen_probe` and landing breakdown
  probe, rebuilt against scan64, on the seven frozen v28 walking-start states
  and the frozen v29 landing and onset states. It took 449 s.
- **Alone:** no other container ran on the Docker VM. `alone_check.json` has
  90 samples at 5 s intervals, none with another container.
- **Outcome:** all nine continue, as in v30. The seven start states accept
  0.56–1.97 m; landing accepts 0.568 m (frontier 11.043 s) and onset 1.401 m
  (frontier 10.743 s).
- **Identity:** all 48 result, negatives, query and breakdown files are
  byte-identical to `runs/v30_saved_states01`.
- **Logs:** 11 of the 12 compared logs are identical after v30's
  normalisation, once `input_refresh` lines that applied nothing and carry no
  negative age are removed. After the round-2 review (NB4) both runs'
  `log_review.py` keep negative-age lines; rerunning both reviews changed
  nothing.
  - **The one difference:** `z_0p3700/probe.log` has one failed seed A*
    search that ends by a different path in wall time. v30 and scan63 crossed
    the 0.2 s budget during terminal recovery; scan64 finished recovery at
    0.196 s without a connector. Both return `SEARCH_ERR`, and the later lines
    are identical (`log_difference_explanations.json`).
  - **Refresh lines:** 163 `input_refresh` lines in 11 logs (the four inner
    sites), none applying anything
    (`log_differences_vs_v30_input_refresh.json`).
- **Review:** `review.json` passes.

## 4. Native regression (`runs/v31_native_regression03`)

This is v30's complete suite (identical probe source, inputs and commands), on
scan64. It took 436 s, with no other container on the Docker VM
(`alone_check.json`: 87 samples at 5 s intervals, none with another
container).

- **Outputs:** all 11 continuations are accepted with full gates and
  negatives, and the repeats are identical. The body-support and ground
  contracts pass.
- **Identity:** every output file equals v30's:
  - all 11 continuation outputs, query CSVs and negatives;
  - all 5 mapped and 8 unmapped fixture outputs.

  This time no A* budget flip changed an output.
- **Logs:** 25 of the 27 compared logs are identical after normalisation.
  - **`execution.log`:** only the make progress percentages of two compile
    lines differ. The set of compiled objects is identical.
  - **`v18.log`:** one line fewer. The same six failed 267-node searches
    occur, with the same three terminal-recovery budget failures. One of
    them took at most 0.1 s, so `dyn_a_star.cpp` printed no elapsed time for
    it (it prints only above 0.1 s). The v30 build does the same in the
    paired timing control (`v30_rep5` printed 5 of 6).
- **Refresh lines:** 129 `input_refresh` lines, none applying anything.
- **Review:** `review.py` passes with both differences explained
  (`log_difference_explanations.json`).

**Timing control** (`runs/v31_regression_timing_control01`, run on scan63)
- **Setup:** the four timing-sensitive fixtures ran with the v30 and scan63
  regression probes in alternating containers, five repetitions each, alone on
  the VM.
- **Results:** scan63 reproduced v30's outputs in all 25 fixture runs. The v30
  build flipped `unmapped_low_box` in one repetition. The medians of the
  failed `v18` searches were 0.105 s (v30) and 0.104 s (scan63).
- **Why it still applies:** `dyn_a_star.cpp` and `libpath_searching.a` are
  byte-identical in v30, scan63 and scan64.

**Freeze and limits:** `freeze.py` requires both reviews and the timing
control. The A* wall-time budget is unchanged, so live planning outcomes can
still vary from run to run, in v30 as in v31.

## Status

Steps 1–4 pass their component scope on scan64. No physical episode has run,
and nothing here is a navigation result. v3 remains the last accepted
condition.
