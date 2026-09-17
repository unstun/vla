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
  `off`, written to `run_request.json` and checked at `--execute` against the prepared package.
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
- **STAND_TRANSITION (2 s), then FIXED_STAND:** output `q_hold` with HOLD gains.
- **FIXED_STAND disturbance:** linear or angular speed above the settle limit, tilt above 10°, or any foot at or
  below 1 N, lasting 0.25 s, returns to RL with a 0.5 s lockout.
- **STAND_TRANSITION or FIXED_STAND with a non-zero command → REJOIN:** blend from the last applied target and
  gains to the current policy target and base gains, `s = smoothstep(t / 0.25)`, then RL.
- **Non-finite input:** raise `StanceHoldError`. The runner treats it like its other adapter failures (status
  `NONFINITE`; no fallback).

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

`--stance-hold off` is the default. A run with `off` uses today's control path. The previous patch and its hashes stay
in git history; existing run packages are untouched.
