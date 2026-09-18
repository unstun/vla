# Design: Isaac runner stance hold

## 1. Boundaries

- **New module** `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/stance_hold.py`:
  - pure Python and NumPy (no Isaac, Torch or ROS import);
  - unit-tested locally;
  - its source text is inserted verbatim into the patched runner by the materializer, so the executed runner stays
    one hash-recorded file (the same approach as `EXTERNAL_HELPER_SOURCE`).
- **`materialize_runner_patch.py`:** new anchors for the CLI flags, setup, the per-step call, gain writes and
  record fields. The frozen source hash (`1490dc85…`) is unchanged. `runner_external_episode.patch` and
  `source_hashes.json` are regenerated and reviewed.
- **Launchers:** `qualify_stand_runner.py` and `run_two_goal_pilot.py` get `--stance-hold {off,auto}`, default
  `off` (`auto` since PRD D8, 2026-09-18; the runner patch default stays `off`), written to `run_request.json` and checked at `--execute` against the prepared package.
- **`make_walk_review.py`:** shows the mode when the metrics carry it; old runs render as before.
- **Not touched:** `machine-dog` (read-only reference `0_trials/2026-08-22/v17a28_mujoco_wasd/run_v17a28_mujoco_wasd.py`),
  the V12 snapshot, backend, SCAN/PCT, `review_two_goal.py`.

## 2. State machine (port of the MuJoCo `MotionFsm`, stand path only)

Constants (MuJoCo values, V12 base gains):

| Name | Value | Source |
|---|---|---|
| `BASE_KP`, `BASE_KD` | 20.0, 0.5 (per joint) | V12 `Lite3ActuatorCfg` |
| `HOLD_KP`, `HOLD_KD` | 60.0, 1.0 | MuJoCo qualified hold |
| `COMMAND_DEADBAND` | 1e-3 | MuJoCo `HOLD_COMMAND_DEADBAND` |
| `SETTLE_LINEAR_SPEED_MAX` | 0.15 m/s (norm of base linear velocity) | MuJoCo |
| `SETTLE_ANGULAR_SPEED_MAX` | 0.5 rad/s (norm of base angular velocity) | MuJoCo |
| `TILT_MAX_DEG` | 10 (angle between body z and world z) | MuJoCo |
| `ENTRY_FOOT_FORCE_N` | 10 per foot (FL, FR, HL, HR) | MuJoCo |
| `SETTLE_DWELL_S` | 0.25 | MuJoCo |
| `BALANCE_BAND` | [0.35, 0.65] for front, left and diagonal shares (FL+FR, FL+HL, FL+HR over the total) | MuJoCo |
| `TRANSITION_S` | 2.0 | MuJoCo |
| `REJOIN_S` | 0.25, smoothstep | MuJoCo |
| `HOLD_CONTACT_N` | 1.0 | MuJoCo |
| `DISTURBANCE_DWELL_S` | 0.25 | MuJoCo |
| `REENTRY_LOCKOUT_S` | 0.5 | MuJoCo |
| `SETTLE_TIMEOUT_S` | 10.0 (auto mode restarts the wait window; RL keeps control) | MuJoCo |
| `ENTRY_RAMP_S` | 0.5, smoothstep (start of STAND_TRANSITION) | Isaac only, PRD D4 (not in MuJoCo) |

Modes: `RL`, `STAND_SETTLING`, `STAND_TRANSITION`, `FIXED_STAND`, `REJOIN`.

- **RL → STAND_SETTLING:** auto mode, the command has been within the deadband (delay 0), and the re-entry lockout
  has expired.
- **STAND_SETTLING:**
  - A non-zero command returns to RL.
  - Otherwise each gate is checked: speed, angular speed, tilt, and all four feet ≥ 10 N. When all pass for
    0.25 s, the mean support shares over that window must lie in the band.
  - If they do, the state machine enters STAND_TRANSITION with the torque-matched seed
    `q_hold = q + (Kp_applied / HOLD_KP) * (target_applied - q)`.
  - A failing gate restarts the dwell and names the blocking gate in `reason`.
  - The policy keeps control throughout.
- **STAND_TRANSITION (2 s), then FIXED_STAND:** output `q_hold` with HOLD gains. Since PRD D4, the first 0.5 s
  is an entry gain ramp (see below).
- **FIXED_STAND disturbance:** linear or angular speed above the settle limit, tilt above 10°, or any foot at or
  below 1 N, lasting 0.25 s, returns to RL with a 0.5 s lockout.
- **STAND_TRANSITION or FIXED_STAND with a non-zero command → REJOIN:** blend from the last applied target and
  gains to the current policy target and base gains, `s = smoothstep(t / 0.25)`, then RL.
- **Non-finite input:** raise `StanceHoldError`. The runner treats it like its other adapter failures (status
  `NONFINITE`; no fallback).

**Entry gain ramp (PRD D4, added 2026-09-17 after C1).**

- **Why:** C1 passed AC3 but hopped at entry, with vertical speed +0.21 m/s and |yaw rate| 0.30 rad/s. The
  immediate Kp 20 → 60 step acts at once, but `Lite3Actuator` applies position targets 3 physics substeps late.
  The new gain therefore met the old target error.
- **Rule:**
  - At entry, the state machine stores `q0`, `T0`, `Kp0` and `Kd0`: the joint positions, applied target and
    applied gains.
  - For `u = smoothstep((t - t_entry) / ENTRY_RAMP_S)`, it outputs `Kp = Kp0 + (HOLD_KP - Kp0) u` and
    `Kd = Kd0 + (HOLD_KD - Kd0) u`.
  - The target is `q0 + (Kp0 / Kp) (T0 - q0)`, clipped to the joint limits.
- **Behaviour:**
  - The entry step (u = 0) repeats `T0` with `Kp0` / `Kd0`, so no gain is written.
  - The stiffness torque on `q0` stays `Kp0 (T0 - q0)` at every step.
  - At u = 1 the output is the torque-matched seed `q_hold` with the HOLD gains. FIXED_STAND and everything after
    it are unchanged.
- **Delay bound:** a delayed step applies `Kp_k` to `target_{k-1}`, which leaves a stiffness torque error of
  `Kp_k / Kp_{k-1} - 1`. At 20 ms steps that is at most 7.3 %; the immediate step gave 200 %.
- **Rejoin:** REJOIN during the ramp blends from the applied ramp values.
- **Records:**
  - Rows carry `stance_reason` `entry_gain_ramp`, then `entry_gain_ramp_complete`.
  - `status()["last_entry"]` records the ramp length, completion time, `q0` and `T0`.
  - The counters include `entry_ramps_complete`.
- **Scope:** this is an Isaac-specific departure; the MuJoCo design has no actuator delay. AC7 checks the result.

Interface:

```python
@dataclass
class HoldInput:
    now_s: float; command: np.ndarray  # (3,)
    joint_pos: np.ndarray; joint_vel: np.ndarray       # (12,), runner joint order
    policy_target: np.ndarray                          # q_default + 0.25 * policy_action
    applied_target: np.ndarray; applied_kp: np.ndarray; applied_kd: np.ndarray  # last step's output
    linear_speed: float; angular_speed: float; tilt_deg: float
    foot_forces: np.ndarray                            # (4,) FL, FR, HL, HR

@dataclass
class HoldOutput:
    target: np.ndarray; kp: np.ndarray; kd: np.ndarray
    policy_owns_joints: bool; mode: str; reason: str; progress: float

class StanceHold:
    def __init__(self, mode: str = "off"): ...         # "off" | "auto"
    def update(self, x: HoldInput) -> HoldOutput: ...
    def status(self) -> dict: ...                      # mode, reason, counters, entry/exit log
```

In `off` mode, `update()` returns `policy_target`, the base gains and `policy_owns_joints=True`, and keeps no state.

## 3. Runner integration (patched `run_pct_scan_building.py`)

The per-step order today is: write the command, `wrapped.step(previous_actions)`, checks, `actions = policy(obs)`,
`previous_actions = actions`.

The new order is:
1. After `actions = policy(obs)`:
   - build `HoldInput` from `robot.data.joint_pos` / `joint_vel` (env 0), the command, `root_lin_vel_w` /
     `root_ang_vel_w` norms, tilt from `projected_gravity_b` (`acos(-g_z)`), and the foot forces from the existing
     `contact.data.net_forces_w[0, foot_ids]` norms;
   - `policy_target = default_joint_pos + 0.25 * actions[0]`, taken from the env's action term
     (`_offset` and `_scale`, read once and recorded, not assumed).
2. `out = hold.update(...)`.
3. If `out.policy_owns_joints`, then `previous_actions = actions`, which is exactly today's behaviour.
   Otherwise `previous_actions = (out.target - offset) / scale`.
   This is the applied-action feedback: `wrapped.step` turns it back into `out.target`, and the policy's
   `last_action` observation sees the applied action, as in the qualified MuJoCo contract.
4. Write gains for the next step: `robot.actuators[name].stiffness[:] = out.kp[joint_ids]` and the same for
   `damping`, for "Hip" and "Knee". Only when they changed; a write in `off` mode is a test failure.
   - `Lite3Actuator` is an explicit `DelayedPDActuator`, so its `compute()` reads these tensors every substep.
   - `TrialEvents` guards only root pose writes and resets, so gain writes are not a trial mutation.
   - Setup records the actuator class, the joint-id mapping and the initial gains. A preflight reads the gains
     back after the first write.
5. Record per step (additive `metrics.jsonl` fields):
   - `stance_mode`, `stance_reason`, `stance_progress`, `policy_owns_joints`;
   - `applied_kp_mean`, `applied_kd_mean`;
   - `applied_target_minus_policy_max_abs`;
   - `applied_torque_max_ratio`: `max |robot.data.applied_torque| / effort_limit`.
   The summary lists entries, exits and reasons, time in each mode, and `stance_hold` settings with the module's
   SHA-256.

The order of the first step and of resets is unchanged. The hold never writes pose, never resets, and does not
change the command path, so the 41 review checks read the same fields as before.

Recorded action values change while holding: `previous_actions` is the applied action. The review uses admitted
commands, not actions, so it is unaffected.

## 4. Qualification (implement.md step C, after Dr Sun approves the budget)

- **C1 stand A/B:** `qualify_stand_runner.py`, `stand_probe`, 60 s, `--stance-hold off` then `auto`, on the
  5070 Ti host. Metrics per AC3 are computed from `metrics.jsonl` by a new local analyzer.
- **C2 two-goal series:** `run_isaac_series.py`-style driver with `--stance-hold auto` and `scan_04`, 8 episodes
  (D12 split), review by `review_two_goal.py`, AC4/AC5 analysis, walk videos.
- **Budget estimate:** C1 about 2 × 3 min, C2 about 8 × 3 min; about 7 GB GPU; remote-only bulk as before.

## 5. Risks

- **The MuJoCo gains may not transfer.** The Isaac actuator has a 0-4 substep delay and a speed-derated torque
  clip, and V12 differs from V17. Kp 60 might oscillate or saturate. AC3 and AC5 would show it, and the fix is
  a separately reviewed gain change, never a threshold change.
- **V12's zero-command motion may rarely satisfy the balanced four-foot gate.** In MuJoCo, V17's weight shift
  delayed entry by up to about 6 s. AC3 bounds entry at 10 s. If entry is too slow, the per-leg latch is a
  documented follow-up and is not added now.
- **Episode timing.** The pilot resubmits after a 1 s still dwell, possibly while the state machine is still in
  STAND_SETTLING or STAND_TRANSITION. That is a covered path (cancel settle or REJOIN), and the report records it.
- **Hidden state writes.** A gain write that leaks into the PhysX drive (implicit actuator) would double the PD.
  The preflight asserts the actuator class and that the PhysX drive stiffness stays 0.

## 6. Rollback

`--stance-hold off` is the runner default (and was the launcher default until PRD D8). A run with `off` uses today's
control path. The previous patch and its hashes stay
in git history; existing run packages are untouched.

## 7. Scripted walk, side camera and entry damping (PRD D5, added 2026-09-17)

- **Command script:** `isaac_runner/command_script.py` is pure Python, inserted verbatim like `stance_hold.py`.
  - The new runner case `scripted_walk` requires `--command-script`; every other case refuses it.
  - The script is piecewise constant in loop-top sim time, with a 1e-4 s slack for float32 times. It must lie
    within the runner's own `--max-*` limits and is refused, not clamped, when it does not.
  - The script replaces the TCP command where `stand_probe` zeroes it, before the unchanged admission norm
    check. Everything downstream therefore sees it: the `base_velocity` write, the post-step parity and
    observation checks, `admitted_command`, `current_command.json`, the hold and the finish dwell.
  - The TCP snapshot is still recorded as `raw_command`. Rows carry `script_segment`.
  - The script path is kept out of the execution configuration. Its SHA-256 is bound through the scope's
    `command_script_sha256`, which the runner checks before physics.
  - The duration cap is 60 s, like `stand_probe`.
- **D5 plan:** `command_scripts/walk_stop_start_stop_v1.json`. The launcher runs it with the native baseline
  limits (`speed_1p0`), a 26 s duration and the finish request at 20 s. The script is zero from 14.5 s, so the
  finish dwell (zero command plus 1 s still) can end.
  - The worker also accepts `DURATION_REACHED` for this case, because the RL-only baseline may never hold 1 s
    of stillness.
- **Camera:** `--camera-heading-mode initial` latches the first captured frame's body yaw for the heading and
  side vectors. `body` (the default) gives the same vectors as before, which a test checks byte for byte.
  - The `side` launcher preset is trail 0, lateral -1.25, height 0.20, look-ahead 0, look-down 0.12, stride 2
    and 25 fps.
- **Entry damping:** `StanceHold(entry_kd=...)`.
  - `ramp` is the D4 behaviour. `step1` uses Kd 1.0 from the entry step.
  - `step2p5` uses Kd 2.5 from the entry step, then a smoothstep from 0.5 s to exactly 1.0 at FIXED_STAND at
    2.0 s. The precedent is MuJoCo `BOOT_LANDING_KD` 2.5 over the 1 s boot grace (MJ:131-140, 1803).
  - Kp and the target keep the D4 ramp in every variant. On the entry step, the step variants write a Kd-only
    change, and REJOIN blends from the applied values.
  - `--stance-entry-kd` other than `ramp` is refused with `--stance-hold off`.
- **Analysis:** `analyze_stance_hold.py walk` evaluates AC8 a-d with the frozen `ac8_walk` thresholds and
  applies the D5 selection rule. Command phases come from the recorded `admitted_command`; each phase's
  command step time is the sim time of the row before its first row.
- **Anchors:** the anchor group `scripted_walk` is applied after the stance-hold group. With every default
  (`body`, `ramp`, no script), the previous control and camera paths are unchanged.
- **Open items:**
  - ~~`run_two_goal_pilot.py` does not pass `--stance-entry-kd` yet.~~ Closed by PRD D6 (section 8): the launcher
    has the flag, records it in `run_request.json` and refuses a mismatch at `--execute`. It does not yet check
    the returned runner summary's `stance_hold.entry_kd`, which `qualify_stand_runner.py` does; C2 should add
    that check.
  - The side camera is 1.25 m right of the base, next to corridor walls at 1.3-1.45 m.

## 8. Crossfade entry and landing grace (PRD D6, added 2026-09-17)

- **Variants.** `STANCE_ENTRY_KD_MODES` gains `xfade1s` and `xfade2s`, with blend time `T_x` of 1.0 s and 2.0 s.
  Any other value keeps its D4/D5 behaviour exactly.
- **Entry capture.** On the settle-confirmation step, the code keeps the existing capture unchanged: q0, T0, Kp0,
  Kd0 and the torque-matched seed `H = q0 + (Kp0/60)(T0 − q0)`. What differs is the output of the first
  STAND_TRANSITION step.
- **Output during STAND_TRANSITION.** With `e = t − t_entry` and `w = smoothstep(e / T_x)`:
  - `w == 0` (the entry step): target = `P(t)` (this step's policy target), Kp = Kp0, Kd = HOLD_KD.
  - `0 < w < 1`: Kp = `(1 − w)·Kp0 + w·HOLD_KP`; target = `((1 − w)·Kp0·P(t) + w·HOLD_KP·H) / Kp`; Kd = HOLD_KD.
    This is the torque sum of the two PD laws, `(1 − w)·Kp0·(P − q) + w·HOLD_KP·(H − q)`, written as one PD law.
    Kp > 0 because Kp0 ≥ 0, HOLD_KP > 0 and w > 0.
  - `e ≥ T_x` (compared with `STANCE_TIME_EPS`): exactly H, HOLD_KP and HOLD_KD.
  - Reason labels: `entry_crossfade`, then `entry_crossfade_complete`. The counter `entry_ramps_complete` and
    `last_entry.entry_ramp_complete_t_s` record when w reaches 1. `last_entry.entry_ramp_s` records T_x.
  - The target is clipped to the joint limits as in every other supervisor mode.
- **Rate check (our arithmetic).** The largest Kp change per 20 ms step is 40·1.5·0.02/T_x: 1.2 for `xfade1s` and
  0.6 for `xfade2s`, i.e. at most 6 % of Kp. The D4 ramp allowed 7.3 %.
- **Landing grace.** For the two new variants, automatic arming (RL → STAND_SETTLING) needs
  `now ≥ ENTRY_GRACE_S = 1.0`. The runner passes `now` as sim time since the episode start. Before that, the
  mode stays RL with reason `entry_grace`. The old variants arm as before.
- **Unchanged.**
  - The settle gate, FIXED_STAND, the disturbance exit and the lockout.
  - REJOIN: a new command during the crossfade rejoins from the applied target and gains, as today.
  - The applied-action feedback to the policy.
  - `--stance-hold off`.
- **Records.** `stance_hold_constants()` adds the crossfade rule, `T_x` per variant and `ENTRY_GRACE_S`, so
  `stance_hold_setup.json` and `summary.json` describe the executed variant.
- **Launchers.**
  - `qualify_stand_runner.py` accepts the new values.
  - `run_two_goal_pilot.py` adds `--stance-entry-kd`: default `ramp` (since PRD D8: `xfade1s` with the hold on,
    `ramp` with it off), other values refused with `--stance-hold off`, recorded
    in `run_request.json` and checked against the prepared package, as `--stance-hold` is.
- **Thresholds.** `stance_hold_thresholds.json` gets a descriptive amendment only: the `ac8_walk.run` text names
  the new variants, and an amendments entry records D6. It is re-frozen before the runs. No limit changes.
- **Analysis.**
  - `analyze_stance_hold.py walk --off <C1d hold-off run> --on <xfade1s run> --on <xfade2s run>`.
  - A row-by-row comparison with the hold-off run up to the first STAND_TRANSITION row is reported (max absolute
    difference of `base_xyz`, `yaw_rate_radps` and `joint_pos`). It has no threshold. The analyzer does not
    compute it; the C1g report produces it from the two `metrics.jsonl` files.
  - Predicted first entry (replay of the C1d hold-off rows through the new state machine, 2026-09-17): the settle
    gate passes at once at the end of the grace, so the entry is at 1.28 s and FIXED_STAND at 3.30 s, 0.70 s
    before the 4.0 s command step. The same replay reproduces the C1d `ramp` entry (0.40 s) as its control.
