---
origin: ai+local
reviewed: false
date: 2026-10-15
stage: experiment + analysis
status: surveyed
runtime_changes: false
new_physical_runs: 0
---

# machine-dog zero-command handling compared with v206

## Recommendation

The strongest reference is the current Zig deployment **PD-first return after
walking**, not the older MuJoCo whole-body gate or its experimental per-leg
latch. The newer implementation already addresses the failure class observed
in v206: a quiet but unevenly loaded robot can begin a gradual return to PD
without first satisfying a 35–65% contact-force split.

Reuse the existing stillness check and gradual transfer mechanism as the first
candidate. There is no reason to start by inventing a new navigation recovery
or a contact-force planning framework. Its fixed pose, disturbance policy and
unbounded locomotion wait are separate choices, not an indivisible package to
copy into VLA.

## Inspected source identity

- Local reference: `/Users/sun/tongbu/study/phdproject/machine-dog`.
- Origin: `https://github.com/unstun/machine-dog.git`.
- Inspected HEAD: `3fcb41ffb03fd7dffaf092c712417fad51cd78b1`.
- The five inspected implementation/launcher files have no working-tree changes
  relative to HEAD. The wider repository is dirty and was left untouched.
- Source hashes and four independently extracted historical runtime traces:
  `../experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-15_v206_terminal_settle/results/machine_dog_reference.json`.
- This is a read-only comparison of a related local project. No source was
  imported, built or executed as a controller; no license/import decision was
  made. No robot or simulator was actuated.

## Three distinct implementations

| Path | What zero velocity does | Relevance |
|---|---|---|
| V12 Zig `controller.zig:530–594` | Keeps invoking the policy with zero velocity and sends its joint targets at RL gains | No automatic fixed-PD standing branch here; do not conflate quiet RL behavior with PD ownership |
| Old MuJoCo `run_v17a28_mujoco_wasd.py:1558–1706` | Waits for quiet motion, four loaded feet and 35–65% pair shares, then captures a hold target | Same lineage as the gate now blocking VLA |
| V21k-family Zig `stance_hold.zig:223–245` | Waits for body/joint stillness, then gradually transfers to a stand target; no foot-load or balance gate on return | Best existing candidate for the v206 failure class |

The current simulator launcher explicitly selects `v21k_pd_first_accepted_a10_p2`
for non-V12 sessions and `legacy_v12` for V12 (`docker/run_runner.sh:103–118`).
`v21k_runtime.zig:195–200` explicitly enables `pd_first` and sets its stand pose.
The Hold class's standalone default is false for old golden-replay compatibility;
that default must not be mistaken for the runtime configuration.

The lineage is bidirectional: the old MuJoCo logic informed VLA's Python hold;
the Zig file starts as a port of that VLA hold, then adds the PD-first branch.
Reading only the old MuJoCo implementation would miss those later changes.

## Exact current return behavior

After walking, command magnitude <=0.001 enters STAND_SETTLING. The robot remains
under RL until all of these conditions hold continuously for 0.25 s:

- fresh velocity observation (runtime age <=0.25 s);
- full three-dimensional linear speed <=0.15 m/s;
- full three-dimensional angular speed <=0.5 rad/s;
- body tilt <=0.15 rad (about 8.59 degrees);
- every joint's absolute speed <=1 rad/s.

Source: `stance_hold.zig:34–35,85–87,212–243` and
`v21k_runtime.zig:585–587`. Some older prose says "yaw rate"; actual code uses
the norm of all three angular components.

There is **no** 10 N per-foot threshold or 35–65% balance requirement in this
return branch. The initial takeover from the vendor controller still has a
separate balanced-support check (`v21k_runtime.zig:267` onward). Startup and
post-walk return must not be confused.

Once stillness is confirmed:

1. Start a two-second smoothstep blend of the RL and stand stiffness laws;
   stiffness moves from its applied value toward Kp60; Kd is 1 from entry.
2. Limit the stand target's offset from each currently measured joint angle to
   0.2 rad, recomputed each tick, including subsequent holding.
3. Enter FIXED_STAND after the transfer. A new velocity command rejoins RL over
   0.25 s.

Sources: `stance_hold.zig:90–93,183–195,314–326,332–353,378–415`.
This is a real target/gain blend; the old MuJoCo implementation's two-second
STAND_TRANSITION label instead directly outputs the held target at Kp60/Kd1
(`run_v17a28_mujoco_wasd.py:1757–1763,1792–1797`).

The A8 runtime selects the policy's default per-leg pose `(0,-0.65,1.30)`.
Initial zero-command takeover ramps from the torque-matched seed to that pose
over two seconds; later returns use the stillness-controlled blend and the
0.2-rad target cap. This pose belongs to that policy/runtime, not VLA's V12
contract `(0,-0.8,1.6)`.

## Existing physical evidence inspected

The main session read original runtime JSONL and simulator JSONL for four cases,
not just the decision-log summary. `inspect_upstream_records.py` preserves the
extraction and hashes. Times below refer to the historical simulation; the stop
command starts at 48 s.

| Historical case | Recorded result |
|---|---|
| A5 forced takeover, frozen M1.2 input | Forced transfer at 50.002 s while still moving; damping follows around 50.637 s; final roll 59.949 degrees and torso height 0.1734 m |
| A7 stillness-only return, frozen M2 | Starts transfer at 49.282 s, FIXED_STAND at 51.302 s; final torso 0.3346 m and four measured foot loads about 30/30/35/35 N |
| A8 fixed-pose return, frozen M2 | Starts at 50.882 s, FIXED_STAND at 52.902 s; final torso 0.3301 m and loads about 26/26/39/39 N |
| A8 frozen M1.2, never quiet | Remains STAND_SETTLING/waiting_for_linear_speed through the end; does not force takeover |

The M2 runtime's inferred hind-left load is negative at transfer entry. The
simulator's measured foot loads are nonnegative and finish loaded. These are
different channels: estimated robot loads are not equivalent to the direct
Newton contact forces used in VLA.

The retained A7 readout also reports clean returns with simulated LiDAR and
full-map inputs (FIXED_STAND about 3.3 and 3.2 s after stopping). These are
different perception inputs on the same physical flat-ground stop protocol,
not a demonstration on three terrain classes.

The trial history explicitly withdrew fixed-delay forced takeover after it
failed both without and with the target-offset cap. Adding a cap did not make
an actively staggering robot catch itself: a fixed-stance controller does not
take a recovery step.

Primary evidence root:
`machine-dog/artifacts/2026-10-06_v21k_m10000_lite3_deploy/tracked_logs/`:

- `newton_forced_return_5070ti_20261007/runs/m12/{runtime_logs,sim}/`
- `newton_no_time_limit_5070ti_20261007/runs/m2/{runtime_logs,sim}/`
- `newton_fixed_pose_5070ti_20261013/a8/runs/{m2,m12}/{runtime_logs,sim}/`
- `newton_no_time_limit_5070ti_20261007/newton_return_readout.txt`

Design history:
`.pipeline/experiments/2026-10-06/DEPLOY_V21k_M10000_decision_log.md:350–451,557–640,650–764`.
The A8/A10 changes are simulator-qualified in those records, not a claim of
equivalent deployment on the physical robot.

## Older alternative that should not be adopted

Read-only exploration of the original MuJoCo matrix confirms that experimental
per-leg latching is disabled by default and had worse results than its baseline:
36/36 baseline, 23/36 latch, 27/36 latch plus balance, 31/36 with an additional
two-second entry delay. A recorded failure reaches FIXED_STAND with large tilt.
The status enum alone is not proof of a physically stable hold.

Sources: `.trellis/tasks/08-24-mujoco-inference-standstill-control/research/restand_latency_diagnosis/stop_option_matrix/sweep{1,2,3}_matrix.json`
and `leg_latch__backward__2.2.json.gz`. These are V17.29/MuJoCo flat-ground
records, not V12/Newton stair-navigation qualification.

## Application to VLA without scene-specific tuning

The next candidate should reuse the **post-walk return mechanism**: measured
stillness including joint motion, a short dwell, and gradual bounded PD
transfer. This is more concrete and smaller than introducing a new support
planner. It addresses v206's gate dependency without touching PCT, SCAN,
global refresh, tracking strategy or Nav2 retries.

Keep these choices separate:

- Do not transplant the V21k pose into V12. Stand-target selection must respect
  the actual robot/policy and current support configuration. Equal joint targets
  for every leg are not demonstrated as appropriate across slopes and steps.
  A support-preserving torque-matched hold and a commanded nominal stand are
  different behaviors and should not be silently substituted.
- Do not translate the locomotion branch's indefinite wait into unlimited
  navigation waiting. Preserve the current terminal deadline and physical
  completion check while evaluating the locomotion change.
- Do not copy PD-first's "report disturbance but retain PD" policy as part of
  this fix. That is a separate control-mode behavior.
- Preserve measured-stop/hold validation: an enum changing to FIXED_STAND is
  insufficient. No coordinates, floor IDs, named scenarios or after-the-fact
  71%-specific force threshold belongs in the decision.

This survey supports selecting a reference implementation. It does not yet
prove that its stand target or takeover motion works on v206's recorded
physical state. No production port or new experimental version was created.
