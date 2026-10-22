# v291 — terminal ownership and settling assistance

2026-10-22. Components, recorded replays and the complete strict53 offline gate passed. New physics attempts: **0**. Accepted v232/v233 unchanged. This candidate does not yet have a measured drift-reduction result.

## What changed

`TrackingNode` now owns terminal position correction, yaw and braking. `Controller` consumes that decision and still requires measured stopped/PD completion. It no longer substitutes its own early stop command. The existing 5 cm centering deadzone becomes the inner brake-entry band, with the existing half-yaw entry band (0.125 rad); the original 25 cm XY / 20 cm Z / 0.25 rad final acceptance stays intact. Once braking starts, the outer band retains it against gait sway. Full bounded proportional correction outside 5 cm avoids asymptotically tiny motion near the deadzone. This changes when braking starts, even though final acceptance is unchanged.

The opt-in v291 stance adapter adds assistance during zero-command `STAND_SETTLING`: a quiet leg with >=10 N measured foot force keeps its torque-matched target at the original RL gains (20 / 0.5). Uncaptured legs keep policy targets. Contact <=1 N releases that leg; excessive body speed/tilt releases assistance. A new motion command uses the existing 0.25 s rejoin. The actual mixed target feeds the next policy frame. Formal PD entry still requires every foot >=10 N for 0.25 s and the existing motion gates; the original gains, 2 s crossfade and disturbance exit remain.

The first PD crossfade retains the captured targets in its policy component instead of reintroducing stepping. The candidate is configured and qualified for `auto` / `xfade2s` via its Newton adapter. Foot mapping uses the authored 22 mm SHANK spheres; leg/joint ordering matches `lite3_reference/robots/lite3.py`: FL, FR, HL, HR, each HipX/HipY/Knee. The existing robot telemetry spreads `stance.row`, so the new per-foot mask is retained without changing the recorder.

## Evidence so far

| Check | Result | Evidence |
|---|---|---|
| Native build and component suite | All 14 packages passed, attempt02 | `results/native_components.json`, `native_manifest.json` |
| New stopping behavior | 12/12 | `results/python_components.json` |
| Actual Newton adapter with mocked arrays/contact API | 3/3 | `test_adapter.py`, same receipt |
| Inherited v216 regression | 14/14, candidate assistance disabled | `results/python_components.json` |
| D07/CD12 actual Controller/LocalMotion/TrackingNode replay | Both passed, 4,651 / 5,079 ticks | `results/controller_replay.json` |
| D07/CD12 stance replay | Both passed | `results/stance_replay.json` |
| Native geometry contract probe | Passed | `results/evaluators.json` |
| Strict53 planning plus independent source/raw-solid audit | Passed: 49/50 legal, 3/3 illegal rejection, median 1.421062432 s | `results/offline_gate.json`, `results/matrix_summary.json` |

Native tests retain the parent's `cpplint|uncrustify|xmllint` exclusions. The 37 collected XML results contain 273 testcase records across behavioral/lint checks; this is not 273 robot experiments. `cppcheck` and `lint_cmake` in the invoked suite passed. The first native build passed but tests failed: removing outer braking initially broke the already-at-goal/no-first-spline path, and one old expectation assumed the early-stop behavior. Attempt02 adds a stop-only tracker path for an already centered goal, prevents emergency-stop data from becoming arrival, and updates the intentional off-center expectation. The failure logs and receipts are retained; no failed test was discarded.

## What the same old inputs now produce

At CD12 115.108368 s, the recorded XY error is 6.9095 cm. The parent commands **0 cm/s** translation and reports braking. v291 commands **5.5276 cm/s** toward the goal, continues yaw correction, and does not report braking. This directly exercises the bug fixed by unified terminal ownership.

At D07 107.412598 s, both controllers command zero and neither reports goal braking. The emergency spline still dominates. This is expected: D07's first geometry failure occurred during the preceding turn; an emergency stop is not a false arrival.

| Recorded stance input | D07 | CD12 |
|---|---:|---:|
| Assisted settling samples | 582 | 186 |
| Parent target total variation before PD (rad, sum over 12 joints) | 42.2157 | 37.9400 |
| Candidate target total variation before PD | 35.6108 | 33.4404 |
| Reduction of target variation | 15.65% | 11.86% |
| Parent/candidate replayed PD entry (s) | 119.945709 / 119.945709 | 119.725830 / 119.725830 |

This replay uses fixed measured kinematics; it cannot change the old trajectory or shorten its support-wait time. The force observations belong to the recorded pre-step sensor update, with joint/body state from the preceding telemetry row. Parent replayed PD entry matches recorded transition within one 20 ms sample. Captured feet remain >1 N; every uncaptured target equals policy output. New commands may change future contacts and body motion in physics. The reported percentages are **joint-command variation, not centimeters of drift**.

## Reproduction and identity

User explicitly authorized ultra9 synchronization and component/53-case offline checks on 2026-10-22. Host workspace: `/home/ubuntu/sun/vla_v291_20261022`. Immutable parents: v290 navigation and hash-pinned v216 stance. The native overlay replaces only `scan_nav2_controller`; the other 13 native packages inherit v290. `native_manifest.json` records source, installed artifacts, evaluator binaries, fixtures and cohort. Runtime source was frozen before the scored53 run. This is not completion of the HTML freeze step: four held-out physical routes still need selection and the physical execution configuration needs recording.

Local Python: `python3 -m unittest discover -s .pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v291 -p 'test_*.py' -v` (15 new tests). Load `v216/test_return.py` with v291 on `sys.path` for the additional 14 default-off regressions.

Remote native: `python3 source/remote_checks.py attempt02`; evaluators: `python3 source/build_evaluators.py`; replay: worker Python `source/replay_controller.py` and `source/replay_stance.py` with `V291_PARENT_STANCE` pointing at the hash-pinned v216 module. Offline: `python3 source/offline.py freeze`, then `python3 source/offline.py matrix`. These are recorded one-time run IDs; scripts deliberately refuse to overwrite scored directories. Use the retained workspace to inspect this run, not to overwrite it.

## Complete strict53 result

One scored run: 53/53 cases completed, all execution and audit processes returned 0.
49/50 legal cases passed (CS01 remains rejected), all 3 illegal cases rejected.
47/49 admitted cases passed the first GPMP solve (95.92%). Global-planning median
was 1.421062432 s, P95 1.9044466 s, maximum 1.969067051 s. Initialization was
excluded and separately recorded. Each planning container had 2 CPUs / 6 GiB.
The original gate remains >=48/50 legal, 3/3 illegal, median <=1.5 s, first-solve
rate >=90%, all selected cases passed, and no accepted global/local negative
source/raw-solid margin. All 49 published legal routes received the unchanged
independent audit; all geometry checks passed. This is an offline planning gate,
not 49 successful robot traversals.

The parent v290 recorded 49/50 legal, 3/3 illegal and 1.361381101 s median.
All 53 per-case admit/reject/end-to-end/first-solve outcomes match the recorded parent; see `results/offline_integrity.json`. The new result does not claim a planning improvement; the changed control behavior
is established by components and recorded-controller comparison. The full local
receipts, case summaries and remote artifact hashes are under `results/`.

## What to do next

Select four unseen routes and finalize the fixed candidate-versus-v290 execution configuration before the planned 24 physical simulations. Measure zero-command-to-PD maximum displacement, PD takeover time, geometry during terminal turning, final steady duration, complete-route success and elapsed time. D07's pre-stop turning sweep remains an explicit target; these component results do not declare it solved.
