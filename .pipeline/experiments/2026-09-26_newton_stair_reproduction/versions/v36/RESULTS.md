# v36 component candidate: Nav2 timing and goal alignment

Date: 2026-09-30. Stage: experiment + analysis. Parent: frozen v35.
Status: **frozen_component_candidate**; 5,787 source/evidence files.
No v36 physical navigation or video trial was executed.

Dr Sun selected global planning at 1 Hz, local planning/navigation control at
30 Hz, XY goal tolerance 0.25 m and yaw tolerance 0.25 rad. Default final yaw
comes from the initial global path's last distinct horizontal segment. The
Lite3 additions remain Z tolerance 0.20 m and measured stopped dwell.
The 50 Hz simulation policy and 1000 Hz simulation physics/joint-PD remain
unchanged. Selected navigation rates use monotonic wall time; trajectory
progress uses simulation time.

## Direct evidence

All native builds and executable components ran on gpu5070ti, using the pinned
ROS image. This repository is the source of truth. Returned native installation
516 files, build records, and 185 files from nine component attempts were SHA-256
verified. Original replay inputs comprise 1,556 files, 76,786,237 bytes.

| Evidence | Actual result | Boundary |
|---|---|---|
| Final native build | Eight packages; 24.5978 s; source unchanged | Build, not navigation |
| Actual controller publications | 29.9993 wall Hz; maximum observed gap 34.2436 ms | Short component fixture, not sustained full stack |
| Nominal local scheduling | About 29.9 wall attempts/s through the real FSM timer | Invalid odometry rejects before geometry; not local solver throughput |
| Actual native PCT refresh | 1.000280884 wall Hz across five calls | Dedicated backend thread; observation sink instead of ROS/physical integration |
| Recorded v32 native local plan | Success; 87.804795 ms | **Over 33.333 ms budget** |
| Recorded v33 native local plan | Success; 120.263012 ms | **Over 33.333 ms budget** |
| Native behavior checks | 34 passed | Goal XYZ/yaw, emergency priority, stale curve/cancel, scheduler and invalid period cases |
| Backend regressions | 15 passed | Request immutability, refresh owner/preemption/cancel, goal identity, fresh XYZ/yaw and post-stop checks |
| Actual launch guard mutation test | Four checks passed on gpu5070ti | Changed binary, rehashed live manifest, and alternate build rejected |
| Independent Spec / Standards review | Both passed for exact candidate identity | Component review; acceptance limits retained |

Primary final records are `tests/attempt09/{result.json,probe.log,
backend_tests.log,global_native_result.json}` and each recorded state's
`probe.log`, `result.json`, `verify_old.json`, `convert_new.json`.
`manifest.json` preserves both local overruns and leaves
`local_planning_30hz_validated`, `navigation_contract_fully_validated` and
`navigation_validated` false. Two synchronous solver calls are never queued
to fake the achieved frequency; late periods are skipped.

## Source and safety boundary

Five native files changed. The planner-manager and AStar implementations remain
byte-identical to v35. `changes.patch`, `changes.json` and `parent_source/`
preserve the exact changes and old bytes. The backend and launch entries are
version-owned overlays; shared frozen runtime and every v35 source byte passed
the parent check. No policy, robot, physical step or collision geometry changed.

Emergency stop has an explicit wire marker and wins over final-yaw control.
An older pre-stop curve cannot resume movement. The exact requested goal pose
is separate from the grid-snapped path endpoint and fixed across same-command
global refreshes. Immutable request inputs and full command identity prevent
concurrent conflicting replays from changing the active goal. Actual pose is
rechecked after stopped dwell before arrival.

The wire schema changed. Old recorded CDR was verified against its original JSON
with the unchanged v35 generated types. New CDR uses the v36 schema and preserves
every original field; added goal/emergency flags are false for the historical
fixtures. Original sensor/pose/cloud bytes are unchanged. Conversion receipts
and both serialized hashes are returned. ROS field construction mutates nested
lists; the final converter keeps a deep copy for strict original-field equality.

The selected wall scheduler is independent of ROS pauses/rewinds. The optional
ROS scheduling basis has rollback fixtures. Complete command/trajectory recovery
after ROS rewind is not validated by those fixtures.

## Preserved unsuccessful attempts

All nine attempts remain available. Initial attempts exposed a test path-parent
error, absent remote recorded inputs, a clock-basis fixture transition error,
an overly narrow drift-command assertion, missing ROS Python paths for native
PCT, old/new CDR schema incompatibility, and the nested-list conversion issue.
The initial tested sources are retained under `history/initial_component_source/`.
Attempts 07 and 08 passed native/backend/global components but failed strict wire
conversion checks. Attempt 09 passed the complete component/replay procedure;
its local deadline measurements nevertheless failed the selected 30 Hz budget.
Attempts 03-09 include confirmed-not-running cleanup receipts. Attempts 01-02
used the container's automatic removal but have no separate cleanup receipt.

## Real-time and navigation acceptance

The separate CPU physics diagnostic under
`../../audits/2026-09-30_realtime_budget/` measured 2.000030 simulated seconds in
3.731837 real seconds, RTF **0.535937**. It excludes sensing, transport and
navigation and uses zero policy commands, not exact factory/PD stand. It is not
a v36 physical trial and does not establish whole-system real-time behavior.

Upstream mechanisms were surveyed in
`.pipeline/survey/2026-09-30_realtime_clock_upstream_survey.md`: shared `/clock`
and actual RTF/pacing are separate. A timing parameter cannot accelerate a slow
solver. Both physics capacity and local planning cost need measured improvement.
v37 is only a proposed CUDA physics evaluation; no v37 code/run exists.

Latest physical trial remains failed v35 `v35_historical_full01`; last accepted
navigation condition remains one **v3 empty 12 m floor** trial. No complete
Building arrival, full-stack 30 Hz, RTF 1, training or hardware actuation is
claimed. No commit or push. A new long navigation/video run needs its own
reviewed frozen candidate and explicit authorization.
