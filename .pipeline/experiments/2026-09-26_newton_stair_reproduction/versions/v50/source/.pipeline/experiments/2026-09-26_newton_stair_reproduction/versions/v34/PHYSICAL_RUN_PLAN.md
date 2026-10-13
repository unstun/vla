# v34 live run: pre-registration

Written before the freeze and before any v34 physics. `PLAN.md` states the change, the checks and the claim
boundary. This file fixes how the single trial is executed and analysed. `HOST_NOTE_gpu5070ti.md` applies v33's
host rules to it.

## The run

- **Run:** `v34_historical_full01` on gpu5070ti (Dr Sun, 2026-09-29: "gpu5070ti, as for v33").
  - **The runner:** `hosts/2026-09-29_gpu5070ti/v34_trial_run.sh`. It is derived from v33's reviewed runner by
    substitution only (`make_v34_files.py`, `make_v34_files.json`: 15 changed lines, all version-bearing).
  - **The launch:** through `scripts/run_bounded.py --run-id v34_historical_full01 --deadline 1800`, around
    `scripts/run_local_episode.py`.
- **Flags:** exactly `v33_historical_full01`'s, except:
  - `--native-build runtime/scan65_evidence_floor_v34`;
  - `--planner-config versions/v34/building_planner.yaml`, a byte-identical copy of v33's;
  - `--integration-version v34`.
- **Gates before physics** (the launcher, unchanged):
  - v34's manifest;
  - the records of `setup/runtime_sources.json`;
  - the native build's source and install manifests and its build result;
  - the reviewed-candidate identity of its source manifest (`repairs/2026-09-26_generic_occupancy/
    candidate65_evidence_floor_v34_identity.json`);
  - the scene inputs.

  `hosts/2026-09-29_gpu5070ti/checks/p1_gates_v34.py` runs the same gates on the execution copy before the trial.
- **The sync** (after the freeze):
  - **What is copied:** every file named in the generated v34 manifest, at its project-relative path, plus the
    complete `runtime/scan65_evidence_floor_v34` directory and the manifest itself. This includes the version's
    non-build files, the candidate identity, the corridor audit, both K4 runs, the derived runner and gate check,
    and `make_v34_files.py/json`. The duplicate `versions/v34/source/` snapshot and excluded contract CMake build
    trees are not needed by the execution copy.
  - **The check:** every file in v34's manifest must have the same SHA-256 on both hosts before P1.
- **Simulation only:** no robot and no training.

## What is recorded

- **Acceptance:** the unchanged Building review for the historical profile, and the local review.
- **Navigation, v34's subject:**
  - **The corridor entry:** does the robot pass it without a stand? That means turning into the corridor past
    (−4.9, −3.4) to (−4.9, −3.6), where v32 and v33 stood. Where it stops, if it stops.
  - **Progress:** the farthest route pose reached (index into the 631-pose route), the sim time at which the body
    first passes x = −4.0 on the upper floor, and whether the corridor's east-end corner (route poses 200–207) is
    reached.
  - **SCAN's signatures:**
    - v31's `trial_signatures.py`: "inside an obstacle", "First three control points", final-check rejections,
      seed failures, replan cycles, the replan limit;
    - the cells of final-check rejections (`versions/v32/corridor_entry_curves.py`'s method);
    - A* wall-budget hits ("0.2 second time limit exceeded"), compared with v33's trial. This risk was found in K4.
  - **The fill at SCAN's start-up:**
    - **Expected:** the `evidence_floor_fill` line with `evidence_used=1` reports 86,775 navigation layers, 17,214
      added and 22,785 rejected (the contract's real-map result).
    - **Otherwise:** any other count is recorded as a deviation and investigated before other conclusions.
- **Watched, unchanged from v33** (its simulation-time gate stays in the stack):
  - `odom_stale`, `heartbeat_stale`, `initial_heartbeat_missing` and `applied_evidence_stale`;
  - the pose gaps over 0.25 s with v33's exposure rule, as a count and not a criterion;
  - clock-sync rejections, TTL windows and reconnects; the bridge's stall counters.
- **Videos:** the standard view and the heading-follow view, as for v33.

## Expected, not criteria

- **The corridor entry:** the robot passes it without a stand. Both blockers were removed at the two frozen stands
  (K3).
- **Possible later stops:**
  - **The corridor's east-end corner and further corners:** the route's support windows narrow there beside
    drops, which the guard keeps (`audits/2026-09-29_corridor_entry/RESULT.md`, §7).
  - **A* budget hits** in larger free areas.
- **How the run can end:** arrival at the goal, the 600 s physics bound, the 1500 s goal wall budget, the 1800 s
  deadline, SCAN's replan limit, or one of the gate's faults.

## Infrastructure failures

`HOST_NOTE_gpu5070ti.md`'s rule, which is v33's:
- **A failure before the first physics step** is not an outcome. It is recorded, and the trial runs under the next
  run ID (`v34_historical_full02` onward).
- **After physics starts,** the run is the outcome, whatever ends it.

## How the analysis writes its outputs

As for v33:
- **Where outputs go:** every post-trial tool runs from a scratch copy, or with its output path redirected. It writes
  run-named outputs under `runs/v34_historical_full01/` or `versions/v34/analysis/`, never over a pinned or committed
  file.
- **Fixed-name writers:** `ttl_windows.py`, `analyze_runs.py` and `corridor_entry_curves.py` are redirected.
- **After the analysis,** v34's manifest is re-verified against disk, and 0 mismatches are expected.

## Stop rule

- **One run,** not repeated for a better outcome.
- **An unexpected end** (a fill count deviation, a stand, a gate fault) is investigated from the saved records
  before anything else changes.
