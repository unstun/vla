# v33 component results (before the freeze), revised after independent review rounds 1 to 4

- **Round 1** (`independent_review_round1.json`) failed with two blocking findings and eight non-blocking ones.
  `REVIEW_RESPONSE_round1.md` answers each. The round-1 candidate's files, as reviewed, are kept in `round1/`
  (README there). This record replaces the round-1 text, whose provenance and K5 statements were wrong (below).
- **Round 2** (`independent_review_round2.json`) passed with ten non-blocking findings.
  `REVIEW_RESPONSE_round2.md` answers each. Their fixes change no runtime byte.
- **Round 3** (`independent_review_round3.json`), the first confirmation round, passed with six non-blocking
  findings. `REVIEW_RESPONSE_round3.md` answers each. Two change the pre-registered analysis and two fix check
  scripts, so round 4 confirms them.
- **Round 4** (`independent_review_round4.json`), the second confirmation round, passed with two non-blocking
  findings, both wording only. They were applied after it and are listed, with the old and new text, in
  `independent_review.json`: the K4 count (10 of 12, below), and the freeze boundary, the monitor's delay and the
  report when no gap qualifies.

The change, as `materialize.py` made it from the v32-verified parents and `changes.patch` records it:

| File | Lines added | Change |
|---|---|---|
| `runtime_sources/backend_adapter/backend_adapter/contracts.py` | 14 | `GateConfig.odom_time_base` (`wall` or `simulation`, default `wall`) and `odom_wall_backstop_s` (default 2.0; at least `odom_stale_s` under the simulation base only); `MeasuredState.stamp_s` (optional, finite) |
| `runtime_sources/backend_adapter/backend_adapter/control_gate.py` | 24 | optional `sim_clock`; `measurement_stale()` holds the freshness rule; `_blocking_reason` calls it in place of the old expression |
| `runtime_sources/backend_ros/p2b_backend_ros/node.py` | 32 | simulation base only: `/clock` subscription (the bridge's QoS), `sim_now()`, stamps into `MeasuredState`, the route-start check, four status fields |
| `scripts/native_graph.py` | 4 | the simulator's backend config sets the simulation base and the 2.0 s backstop |
| `setup/runtime_sources.json` | 4 | the three runtime files' rows: new `sha256` and `bytes`, `archived_sha256`, `local_modification` |

**Provenance, corrected (B1).** The round-1 text said the three runtime files "had not changed since their import"
and "none had been in a version manifest before". Both were wrong for `node.py`.
- **`node.py`:** it is in every version manifest since v11. v11 and v14 changed it, and each updated its row in
  `setup/runtime_sources.json`.
- **`contracts.py` and `control_gate.py`:** they had not changed since import, and they are not in v32's
  manifest. The import record pins them, and it is in v32's manifest.
- **The missed update:** `scripts/run_local_episode.py` re-hashes every record before physics. Round 1 did not
  update the record, so the planned trial would have been refused with "Archived runtime source changed".
- **The fix:** the record is now a changed file, as in v11, v14 and v26.

**Code changes after round 1:**
- **N3:** the backstop-versus-limit rule now applies under the simulation base only.
- **B2:** three comments now name the stalled pose path besides a stopped simulator: the `GateConfig` field
  comment, the `measurement_stale` docstring and the `native_graph.py` comment.
- **Unchanged:** the rule itself and `node.py`, which has the same bytes as in round 1 (`c94c9010…`).

## K1 and K2 (`check_change.py` → `check_change.json`): passed

- **K1, byte-exact:**
  - **Source files:** for each of the four, the recorded edits rebuild it from its preimage, and reversing them
    restores the preimage.
  - **The record:** `materialize.update_record` applied to the v32 record gives the current one, and restoring
    the three rows gives the v32 bytes.
  - **Hashes:** they match `prepared.json`.
  - **Everything else:** the other 2,970 files of v32's manifest are unchanged.
- **K2, scope:**
  - **Source files:** every one compiles. The changed definitions are exactly those `PLAN.md` lists, and all
    other module statements are identical.
  - **The record:** only the three rows change, only in `sha256`, `bytes`, `archived_sha256` and
    `local_modification`. Their hashes and sizes are the current files', and `archived_sha256` is the import
    hash (node.py's from before v11, unchanged). The format and the row order are unchanged.
- **Round 1 (recorded):** the first K2 run failed because my allow-list named the two dataclasses but not their
  `__post_init__` methods. The list was corrected; no code changed.
- **Round 2 (N10):** the record check crashed, instead of failing, on a changed row without `archived_sha256`.
  It now records a failure. In scratch, three mutants were detected without a crash: a note added to a foreign
  row, a dropped `archived_sha256` and a dropped row. `check_change.json` was unchanged by the fix.
- **Round 3 (N4):** an added or a renamed row still crashed. It now fails, and both mutants were detected in
  scratch along with the earlier three. `check_change.json` was unchanged again.

## K1b, the trial's record check (`record_check.py` → `record_check.json`): passed

- **The launch check:** `run_local_episode.py`'s three pre-physics lines, executed from the script's own text,
  pass on the v33 bytes. So does `review_local_episode.py`'s `source_identity` comparison: 36 inputs and 99
  records, no mismatch.
- **Negative control:** v32's record against the v33 files finds exactly `contracts.py`, `control_gate.py` and
  `node.py`. That is the round-1 state that would have been refused.

## K3, the gate contract (`gate_contract.py`): passed on the Mac (Python 3.12.13) and in the pinned image (3.10.12)

`gate_contract_mac.json` and `gate_contract_container.json` give identical case results.

| Case | Red (v32) | Green (v33) |
|---|---|---|
| C1 wall equivalence | — | 20,000 sequences × 200 events: identical outputs and state after every event |
| C2 host stall | `odom_stale` at 0.26 s | open throughout 1.5 s |
| C3 lost poses | — | `odom_stale` at 0.26 s of simulation age; age probe 0.24 s fresh, 0.26 s stale |
| C4 stopped simulator | — | fresh at 1.99 s of wall time, `odom_stale` at 2.01 s |
| C5 fail closed | — | no clock, a clock not yet reported, or a pose without stamp: `odom_stale` |
| C6 clock 5 ms behind the pose | — | fresh |
| C7 configuration | `odom_stale_s` 2.5 accepted | default `wall`/2.0; unknown base, negative backstop and NaN stamp rejected; under the simulation base a backstop below `odom_stale_s` (also `odom_stale_s` 2.5 with the default) rejected and one equal to it accepted; under the wall base `odom_stale_s` 2.5 and a backstop of 0.2 s accepted (N3); `native_graph.py`'s gate section gives `simulation`/2.0 |
| C8 check order | `heartbeat_stale` | `heartbeat_stale` under both bases |

- **C1 reached the pose rule both ways:** 7,824 evaluations ended in `odom_stale`, 1,686 in `ok` and 1,150 in
  `measured_map_mismatch`, a check that follows the pose rule. The reviewer also checked that mutants of the
  wall branch are detected (round 1, verified list).
- **A command error this round:** the first container run could not see the project. In zsh, `"$P:$P:ro"`
  applied the `:r` modifier, so the mount target became `…/vlao`. The corrected command uses `${P}`; the check
  itself did not change.

## K4, counterfactual replay (`replay_gate.py` → `replay_gate.json`): passed

The replay covers all 48 surveyed runs, with 380,795 recorded pose receipts.

- **Wall base (v32 rule):** 84 stale episodes in 16 runs. An end counts as reproduced when a replay episode lies in
  the pose gap its stop flow followed. They reproduce 10 of the 12 recorded `odom_stale` ends: v17, v25, v28, v30,
  v31, v32, `diag_v31_clock03/04`, `diag_v32_clock01` and `empty_long_route01` (`evidence/k4_end_match.py`, added
  after round 4).
  - **The two missed:** both gaps exceeded 0.25 s by only milliseconds, no replay evaluation point fell inside the
    stale window, and the backend's own watchdog caught them.
    - `v5_building_route01`, the 17th run with a gap over 0.25 s: its only such gap, 0.2604 s, left a 10.4 ms
      window.
    - `empty_long_route02`: its first gap, 0.2532 s, left a 3.2 ms window. The replay's one episode in that run
      lies in its second gap (0.339 s), which began about 3.9 s after the stop flow, so it is not the recorded end.
  - **Corrections:** earlier versions of this record, and of `PLAN.md`, said every recorded end was reproduced.
    I found `v5_building_route01`'s miss while checking round 3's N1 and wrote 11 of 12. That count matched runs,
    not gaps: `empty_long_route02` has a replay episode, but in the wrong gap. Round 4 (N1) found it.
  - **What it affects:** the wall-base validation, not the simulation base's result, whose ages stayed at or
    below 0.08 s.
- **Simulation base:** 0 stale evaluations in every run under all three clock models. M3, the burst after a gap,
  was added after round 1. M2 and M3 are approximations, and `PLAN.md` gives the direct measurement.
- **Synthetic loss:** dropping 0.30 s of simulation time of poses, while `/clock` keeps following the record,
  trips the simulation base in all 48 runs.
- **Against round 1:** every round-1 field of every run is unchanged.

## Evidence added after round 1 (`evidence/clock_lead_survey.py` → `clock_lead_survey.json`)

- **B2's recorded bound:** 128 pose gaps over 0.25 s, in 17 of 48 runs. Simulated time advanced at most
  0.0352 s between consecutive poses, and at most 0.08 s counting the poses delivered within 50 ms after the gap
  (`v12_building_route01`).
- **N1's direct measurement:** the in-container observer's `/clock` minus the backend's newest pose stamp was
  at most 0.08 s over 1,890,389 samples (`v12_building_route01`), and at most 0.0403 s elsewhere.
- **N5's heartbeat figures:** backend-side stalls of at least 0.2 s inside a pose gap were found in
  `v12_building_route01` and `empty_long_route03`. They are measured as the observer's gated-command gaps
  (0.439 s and 0.231 s) while raw commands kept flowing (0.026 s and 0.154 s). In the historical_full trials,
  the gated-command gaps inside pose gaps were at most 0.0495 s (v25).
- **Agreement with the reviewer:** these reproduce round 1's scratch figures. The reviewer counted 1,708,086
  observer samples where this script counts 1,890,389 (the selection rule was not given); the maxima agree.
- **Added after round 2** (N4, N1), from the worker's per-step applied reports (`applied_sent.jsonl`):
  - **Physics advance during pose gaps,** measured apart from the pose path: at most 0.06 s in the 122 of 128
    gaps with those reports (`pd_startup_human_live_v1`).
  - **The stopped-simulator margin:** in every step whose step-end pose reached the backend, the pose arrived
    after the step's applied-report stamp. The margin was at least 15.6 ms over 119,056 steps in 46 runs (median
    58.0 ms), and at least 45.0 ms in `v32_historical_full01`. So when stepping stops, the applied-evidence check
    goes stale before the pose backstop.
  - **My first pairing was wrong:** it took the newest pose stamped within each step's 0.02 s. It gave minima down
    to −18.3 ms, because where a step's end pose had been superseded in the bridge, float32 spacing (19.989 ms)
    let it pick the previous step's pose. Pairing with the step-end pose itself reproduces the reviewer's 45.0 ms
    (n = 12,692) exactly.

## K5, ROS smoke (`ros_smoke.py` via `run_ros_smoke.sh`): passed on the trial path

**Criterion:** the `trial` variant, which runs the trial's loader and `build_runtime` on a single-threaded
executor. The variant and the criterion were added after review round 1, and they are not pre-registered
(`PLAN.md`, K5).

| Check | `trial` attempt 03 (final harness) |
|---|---|
| 1 streaming | simulation base; loaded gate `simulation`/2.0/0.25; simulation age 0.0 s; route start fresh |
| 2 host stall (1.06 s of wall time, streams frozen) | the wall rule would be stale; route start fresh; gate open, block reason `ok`; longest command gap 0.027 s |
| 3 lost poses (`/clock` +0.30 s) | route start `body_pose_stale`; gate closed `odom_stale` |
| 4 stopped simulator | fresh and open at 1.9 s; `body_pose_stale` and `odom_stale` at 2.1 s |
| 5 backward `/clock` | ignored, counted once |

**Every attempt, in order:**

| Attempt | Harness | Result |
|---|---|---|
| Round 1, attempt 1 | first | did not start: ROS domain 233 is above the maximum of 232 (changed to 219) |
| Round 1, attempt 2 | first | failed checks 3 and 4 on the harness: a wall-bounded stream advanced only 0.23 s of simulated time under emulation, and without SCAN commands the node's watchdog closed the gate with `initial_heartbeat_missing` |
| Round 1, attempt 3 | revised (command stream, the node's decisions, streams bounded by simulated time) | passed; its outputs are `round1/ros_smoke.json` and `round1/ros_smoke_stdout.log` |
| `multi` 01, first invocation | round 2, before the check-4 fix | a 0-byte log and no JSON, cause not determined (Docker Desktop had just started); kept as `ros_smoke_multi_attempt01_first_invocation_stdout.log`, and the attempt number was reused |
| `multi` 01 | same | passed |
| `trial` 01 | same | failed check 4: the harness re-admitted the owner while check 3's pose was still 0.30 s stale, and the gate rightly closed at once. Fixed by streaming fresh poses before the new admission |
| `trial` 02 | check-4 fix | passed |
| `multi` 02 | check-4 fix | failed checks 2 and 3: the gate closed with `heartbeat_stale`. Route start was fresh in check 2 and `body_pose_stale` in check 3, as designed |
| `multi` 03 | plus diagnostics (no criterion changed) | failed check 4 on `heartbeat_stale`; the harness's own command receipts had gaps of 0.566 s (check 3) and 0.644 s (check 4) |
| `trial` 03 | final | passed; command receipt gaps at most 0.027 s |

- **Round 1's outputs:** attempts 1 and 2 wrote the same fixed-name files as attempt 3, which overwrote them.
  Their results above come from the session record.
- **Round 1's K5 text was wrong.** It said `PLAN.md` K5 "was revised to match before the passing run". The
  session record shows the revision was written after attempt 3 passed.
- **Why `multi` fails is not established (round 2, N6):** under emulation, its command receipts had gaps past
  the unchanged 0.20 s heartbeat. GIL contention among the harness's threads is a hypothesis; the publisher node
  has no callbacks for the executor to serve. The trial's backend has its own executor in its own process, and
  the recorded historical_full trials had gated-command gaps of at most 0.05 s.
- **Harness records (round 2, N6):**
  - `k5_harness/` keeps the harness of each round-2 attempt: `ros_smoke_round2_attempt01.py` (the first
    invocation, `multi` 01 and `trial` 01), `_attempt02.py` and `_attempt03.py`, with the unchanged
    `run_ros_smoke_round2_attempts01-03.sh`.
  - Attempts 01 and 02 were rebuilt by reversing the recorded edits, each found exactly once; replaying them
    forward gives the attempt-03 file byte for byte. The attempt-02 harness writes check 4's `gate_events`, as
    the attempt-02 JSONs show, and the attempt-01 harness does not.
  - **The old guard:** `run_ros_smoke.sh` did not stop a run whose log existed, because `set -e` ignores a
    failed test inside an `&&` list. No log was overwritten.
  - **The new script:** it exits explicitly and copies the harness it runs into `k5_harness/`, checking it
    unchanged afterwards. A scratch test refused an existing log and left it intact.
  - **Round 3, N3:** the check was skipped when a run failed, because `set -e` ended the script first. It now
    captures the run's status, always checks the harness, and exits with that status. A scratch test with a
    failing stub run passed an unchanged harness through and detected a changed one.
  - **After attempt 03,** only `ros_smoke.py`'s docstring changed (round 2, N1: in `trial`, check 4 models a
    stalled pose path, because the applied-evidence file is kept fresh).

## Pinned at the freeze (round 2, N9)

The seven files of `config_archived/` (13,628 bytes) were in no manifest or record, and git does not track them.
- **What the trial loads:** three of them: `bridge.yaml`, `controller.yaml` and `p2b_backend_ros.two_goal.json`.
  `planner.yaml` is not used, because the trial passes `--planner-config` (corrected after round 3, N5).
- **Pinned now:** `freeze.py` adds all seven to v33's manifest, so the trial's version gate checks them before
  physics.
- **Provenance:** the reviewer found them byte-identical to the archived run's configuration they were copied
  from.

## Next

- The freeze: `freeze.py` writes `manifest.json` after this record.
- The live run, `v33_historical_full01` (`PHYSICAL_RUN_PLAN.md`).
