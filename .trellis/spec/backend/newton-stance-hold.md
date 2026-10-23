# Newton PD hold and long-route integration

## V12 command-range evidence correction (2026-10-23)

The model149999 handoff's saved `env.yaml:2100` enables
`dynamic_resample_commands`. In its hash-matched `commands.py`, the norm
cutoff at 0.2 m/s occurs only in the non-dynamic branch; the active dynamic
sampler uses remaining distance/time. Therefore this code does not establish
a fixed 0.2 m/s training floor. The zero-linear branch still retains yaw.
Source/config hashes and the dated correction are in
`.trellis/tasks/10-23-v12-terminal-turn-stop/research/evidence.md`.

The 34-recording Phase A audit confirms long low-speed terminal stalls, but
its longest pure-yaw interval is 1.559 s and its largest turn is 50.4 degrees.
These mixed terrain/transition observations do not set flat-ground execution
limits or a 180-degree drift allowance. The frozen definitions, 14 tests and
per-run/source-row measurements are in
`audits/2026-10-23_v12_command_range/` under the Newton experiment. No stance
contract, PD gate or accepted navigation baseline changed in this audit.

## v216 supported-transfer override (2026-10-15)

The approved v216 return retains v208 stillness/target/crossfade behavior but
requires every measured FL/FR/HL/HR force >=10 N throughout the 0.25 s entry
dwell. Do not restore front/left/diagonal balance-share constraints. During
STAND_TRANSITION, the existing linear/angular speed, tilt and >1 N contact
checks apply on every update with immediate RL output, including the completion
tick and simultaneous new command. Keep the 0.5 s reentry lockout. FIXED_STAND
retains its existing persistence; never describe that as immediate transition
protection. Forces are vector magnitudes, not vertical-only loads.

14 regression tests cover support loss, full dwell, all transition disturbances,
actual target/gain ownership and completion-boundary priority. v219 passed one
full route using v216. The stair transition stayed below 4.85 deg with all feet
loaded; a later FIXED_STAND disturbance lost hind support and returned to RL.
Report this recovered disturbance rather than claiming an uninterrupted stable
stair hold. Final PD remained continuously qualified for 4.338 s. See
`versions/v216/RESULTS.md` and `versions/v219/results/stair_pd_support.json` in the
2026-09-26 Newton experiment. All prior versions remain frozen.

## v291 candidate: assistance before formal PD (2026-10-22)

The opt-in v291 child may hold a quiet loaded leg during `STAND_SETTLING`
using a torque-matched target at unchanged RL gains. Foot order is FL/FR/HL/HR,
each containing HipX/HipY/Knee. Uncaptured legs retain policy output; captured
legs release at <=1 N contact, and excessive body motion releases assistance.
A new command reuses the existing rejoin; partial ownership must write actual
mixed targets into action history. Keep captured targets in the formal entry
crossfade's policy component. The v216 four-foot dwell, transition disturbance
exit and formal PD gains remain authoritative. Default-off behavior matches
v216. See `versions/v291/RESULTS.md` and its 12 stopping/3 adapter tests.

This is a component/offline candidate, not an accepted physical improvement.
Recorded-input reductions in target variation must not be reported as reduced
body drift. Do not apply this override to frozen v216 or adopted v232/v233.

## 1. Scope / Trigger

Explicit local Newton flat-scene PD/RL switching. The original Isaac stair gate
and physical factory calibration remain unvalidated. Preserve the default
policy-only mode and the legacy PD preparation profile.

## 2. Signatures

`Lite3Newton(..., stance_hold=False, startup_mode="policy")` optionally attaches
`newton_stance.NewtonStance`. `startup_mode="factory_pd"` requires stance hold
and refuses ordinary `step()` until the factory adapter finishes.

`run_local_episode.py --scene flat_empty_long --geometry-obstacles --stance-hold
--startup-mode factory_pd --backend-executor single --applied-transport zmq
--goal-wall-budget 1500` selects the 12 m empty-floor condition. Use the unchanged
qualified SCAN42 v9 build and `geometry_smac_approach_flat.yaml` explicitly.
The scene allows 150 physical seconds / 1700 worker wall seconds. Its supervisor
maximum is 1800 seconds; the original E1 supervisor still defaults to 600.

`--physics-backend native` explicitly selects the original E1 native MuJoCo CPU
path for the empty long scene only. The default remains `warp`. Its ground plane
has friction 1; the finite floor mesh remains visible/ray-testable but has no
collision flag. Record the solver condition instead of claiming equivalence
with the exact actor-mesh Warp trials. Native CPU time uses float64 recurrence;
Warp CPU time uses float32 recurrence.

`--real-time-factor 0.5` paces native empty-scene navigation at half physical
real time without changing simulation dt or sensor/control periods. Record this
explicitly. This pacing is not a replacement for the unchanged freshness gates.

## 3. Contracts

- Import the original pure NumPy `isaac_runner/stance_hold.py` by exact SHA-256
  `9a97879a5d5ed2f7c9c3e327c1193b1c42cf079eaaf073a855afad53a7dbc306`.
  Retain auto/xfade1s, gains 60/1, all support/motion/dwell gates and transitions.
- Use pinned Newton 1.6.0 `SensorContact` and `SolverMuJoCo.update_contacts`.
  Keep its force observation buffer separate from collision/scoring contacts.
  Resolve each collapsed foot as the unique 22 mm sphere on FL/FR/HL/HR SHANK;
  never infer this order from unnamed shape indices.
- Native CPU support uses `mujoco.mj_contactForce`, following the read-only
  local MuJoCo runner's `_foot_contact_forces` sum-of-contact-magnitudes rule.
  Map native geometries through Newton's `mjc_geom_to_newton_shape` to the same
  four unique foot spheres. Exclude shank geometry despite fixed-joint collapse.
  The empty-scene contact observer records every substep; obstacle contact is
  inapplicable because this explicit profile contains no obstacle.
- Infer the policy at 50 Hz, then apply the existing state machine's target and
  gains. During RL ownership retain raw policy action feedback; while PD/blend
  owns joints use `(applied_target - Q0)/0.25`, as the existing Isaac port does.
- Factory initialization uses the previously audited local algorithm, ideal
  absolute encoders, existing zero/stand requests and 1 ms motor loop. Require
  measured upright standing and four-foot support continuously for 0.5 s.
  Transfer the loaded state into the existing hold with
  `target = q + (factory_force + HOLD_KD * qd) / HOLD_KP` after effort limiting.
  Reject a seed outside original joint limits. No physical-state reset.
- Factory force records, handoff force equality, pose and time remain local.
  The factory zero flag is not a mechanical calibration completion test.
- Applied snapshots add `stance_mode` and `policy_owns_joints` under `control`.
  A zero command alone does not establish PD ownership or readiness.
- Long-route body localization is published from the optional read-only
  `physics_observer` after every five completed 1 ms substeps. Policy remains
  50 Hz and LiDAR remains 10 Hz in simulation time. Every body sample has its
  actual solver time and physical-step sequence; never repeatedly restamp a
  cached pose. Keep the original 0.25 s wall-clock odometry watchdog.
- Native backend terminal status is lowercase `arrived`/`failed`; the driver
  finish-request protocol uses uppercase `FINISHED`/`FAILED`. These are different
  fields, not interchangeable spellings.
- The long driver waits for initial measured PD hold, sends one ground goal,
  then requires native arrival, <=0.25 m XY error and >=2 s final PD hold.
  PCT computes the global route from its registered synthetic floor prior;
  SCAN uses actual geometric LiDAR and body localization. No obstacle truth.
- Render the original recorded joint/body states. Global route and local curves
  come from native messages. Display grid/overview/camera never enter sensing.
- Empty long-route sensing uses one standard `ThreadPoolExecutor` worker with
  a private captured `State.body_q`, pose and original sensor timestamp. The
  existing `GeometricLidar.scan(..., captured_state=...)` refits only its private
  sensor BVH. There is at most one scan in flight; a missed next sensor period
  fails explicitly. A separate single worker serializes evidence in order, with
  a 256-job backlog limit and checked futures. The ZMQ path keeps the original
  snapshot in its acknowledged log and Linux tmpfs instead of redundantly
  rewriting the Mac shared-file mirror. The legacy synchronous profile remains.

## 4. Validation & Error Matrix

| Condition | Outcome |
|---|---|
| Existing hold source hash changes | Refuse adapter import |
| Missing/ambiguous foot sphere | Refuse support mapping |
| No measured factory standing gate by 14 s | Stop before navigation |
| Invalid target or out-of-range handoff seed | Refuse PD transfer |
| Unbalanced support after zero command | Remain under RL settling; preserve delay |
| Native route failure, stale geometry or total deadline | Cancel and record failure |
| Backend arrival without final PD dwell | Keep observing within declared bound |

## 5. Good / Base / Bad Cases

Good: `pd_switch_factory03` records three actual fixed holds and two completed
rejoins in one 43.927 s physical episode. Its final RL-to-PD settling takes about
16.4 s. Base: unchanged policy-only operation passes the eight motor/interface
tests. Bad: call an eight-second zero-command interval a completed hold even
though force balance has kept the state machine in STAND_SETTLING.

The first long trial, `empty_long_route01`, stopped after about 1.9 m because
one received body-pose gap was 0.2957 s, exceeding the original 0.25 s watchdog.
Publishing only after an entire control interval is insufficient under slow
CPU execution. The substep observer must be tested for identical dynamics and
strictly advancing actual state before rerunning; `pd_long_motor_contracts03`
passes all nine tests including this regression. This diagnosis does not by
itself prove a complete long route.

## 6. Required Tests

Run the existing 53 pure hold tests and E1 motor/golden-policy contracts. Check
actual contact force ordering, applied action history, PD gains/ownership,
rejoins, force continuity, continuous solver time using the selected backend's
float32/float64 recurrence, final pose and stop.
Retain timed-out or too-short stop observations as failures, including
`pd_switch_control01` and `pd_switch_factory02`; never replace them with a later
successful outcome. Full navigation has its own prospective acceptance in
`PD_LONG_ROUTE.md` and read-only `review_long_route.py`.

`pd_switch_native04` passes the same three-hold/two-rejoin checks in one 42 s
physical episode (24.077 s total process wall time including factory startup).
`captured_lidar01` proves exact original point/world arrays when a captured state
is processed in a worker after physics has advanced; later live rays differ.
These component results do not establish 12 m route completion. The first native
long launch, `empty_long_route04`, stops before simulation on the unchanged
10 GiB free-space preflight. Never delete unique evidence or lower a storage
guard to make an almost-full disk appear qualified.

`empty_long_root_live08` subsequently passes all 17 prospective route checks:
12.0169 m actual path, 0.19697 m final error, 12 native moving curves and 2.080 s
final PD hold. This is one instrumented native CPU trial paced at factor 0.5.
`scan43_prefix_diagnostic_v2` adds logging/queries to SCAN42 v9 without changing
planner limits; it is not the default build. Earlier native startup failures
remain unresolved, and diagnostic overhead may change scheduling. Do not infer
repeatable startup or obstacle avoidance from this accepted empty route.

## 7. Wrong vs Correct

Wrong: use the raw background policy output as history while PD owns the joints,
sum contact candidates as forces, or stop a long trial at the old 27 s limit.

Correct: preserve controller ownership at the action/history seam, read actual
solver forces, and use native arrival plus measured final PD dwell.
