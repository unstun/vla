---
origin: ai_with_source_check
reviewed: false
date: 2026-09-17
method: read-only survey of machine-dog (A), machine-dog-nav (B) and vla (C); file:line references not all re-opened by the lead
---

# Where a V12 stance hold would go (code survey)

Roots:
- A = `/Users/sun/tongbu/study/phdproject/machine-dog`
- B = `/Users/sun/tongbu/study/phdproject/machine-dog-nav`
- C = `vla`
- D = `A/2_experiment/deployment/lite3_rl_deploy_v1a.1/src`
- R = `C/references/upstream/2026-09-16_lite3_isaac_harness_backend/source/machine-dog-nav/integration/lite3_sim_bridge/lite3_sim_bridge`
- S = `C/references/upstream/2026-09-11_lite3_v12_locomotion/source/v12_runtime/source/robot_lab/robot_lab`

**Bottom line:** neither the Isaac runner nor the real-robot program has a PD stance hold after RL. Both keep
running V12 on a zero command. The only working walk-to-stand transition is A's MuJoCo preview (V17 qualified; it
can load the V12 export).

## Real-robot deployment (A, read-only)

- **Program:** `lite3_rl_deploy_v1a.1` (Zig). It runs the ONNX `policy/model_149999/policy_stateless_h10.onnx`
  (450 inputs, 12 outputs).
- **Control settings:**
  - 50 Hz; Kp 20 / Kd 0.5; damping Kp 0 / Kd 2.5 for 3 s (`D/types.zig:147-162`).
  - Default joints (0, -0.8, 1.6); action scale 0.25.
- **State machine** (`D/types.zig:74-86`, `D/controller.zig:273-285`):
  - `runRl` (`:526-595`) has no zero-command branch. It leaves only to damping or hind-stand.
  - No PD hold exists after RL.
- **Hind-stand template:**
  - Cubic spline from the measured q and dq (`D/hind_transition.zig:15-67`), 2.8 s.
  - Gains Kp 90/200, Kd 2/4 (`D/hind_types.zig:54-70`).
  - Zero-command entry guard (`D/controller.zig:624-630`).
  - The policy history is re-initialised on return to walking (`:771-777`).
- **v0 (C++):** the RL state leaves only to damping; StandUp is reachable only from Idle (Kp 100 / Kd 2.5).
- **Vendor stack:** it never goes walk → stand. The route is RL → damping → idle → stand-up
  (`A/.trellis/tasks/08-24-mujoco-inference-standstill-control/research/handoff_mechanics_lite3_stack.md:20-60`).
  The official MotionSDK hold is Kp 80 / Kd 0.7 (`A/artifacts/2026-09-08_lite3_official_standing_audit/README.md:7-20`).

## Isaac runner (C)

- The frozen runners are in R and are byte-identical to `B/integration/lite3_sim_bridge/lite3_sim_bridge/`.
- **Command path in `R/run_pct_scan_building.py`:**
  - The command comes from the TCP snapshot (`:800-801`). `stand_probe` only zeroes it (`:802-804`).
  - The command is written to `base_velocity` (`:813-816`), then `wrapped.step(previous_actions)` runs (`:819`).
  - Then `policy(observation)` (`:932-933`) and `previous_actions = actions` (`:939`).
  - No stand, hold or damping mode exists.
- **Where the PD happens:** IsaacLab applies the PD inside the actuator (stiffness 20, damping 0.5). A hold target
  must therefore be sent as an action, `(q_hold - q_default) / 0.25`. Gains above 20 would need runtime actuator
  changes; none exist today.
- **Hook point:** between policy output and `previous_actions` (`:933-939`), as a new anchor in the recorded runner
  patch (`isaac_runner/materialize_runner_patch.py`). The trigger can reuse the patch's zero-command and stillness
  logic (`runner_external_episode.patch:366-381`).

## Existing FSM to port (A MuJoCo preview)

- File: `A/0_trials/2026-08-22/v17a28_mujoco_wasd/run_v17a28_mujoco_wasd.py`.
- **States:** RL → STAND_SETTLING → STAND_TRANSITION → FIXED_STAND → REJOIN (`:116-203`).
- **Settings:** Kp 60 / Kd 1; 10 N per-leg load gate; 0.35-0.65 load-balance band; 0.25 s rejoin.
- **Transitions:**
  - The hold target is matched to the currently applied torque (`:1701-1703`).
  - Disturbance exit (`:1709-1746`); smoothstep rejoin (`:1806-1813`).
  - It can load the V12 export (`:238-273`).
- **Design and evidence:** `A/.trellis/tasks/08-24-mujoco-inference-standstill-control/design.md:114-183`,
  `prd.md:79-118`.

## V12 training (S; matches `A/.../handoff/tracked_configs/env.yaml:2092-2138`)

- **Zero-command training:**
  - `zero_command_curriculum` 0 → 0.1 over iterations 0-1500.
  - `limit_ang_vel_at_zero_command_prob=0.2`.
  - Linear commands with norm ≤ 0.2 are set to 0.
  - Resampling every 5 s.
- **Rewards and disturbances:**
  - `stand_still` and `feet_contact_without_cmd` are defined but unused.
  - Posture penalties have no extra weight when standing.
  - Pushes every 4 s.
- **Existing measurement:** V12's own zero-command stand in Isaac has yaw rate −0.101 to +0.126 rad/s (std 0.039)
  and drifts 3.2 cm in 10 s (`A/artifacts/2026-07-18_v12_model149999_flat_standstill_diagnosis/README.md:51-73`).
  That is already close to the 0.15 rad/s check.

## Parameters

| | Deployment | Isaac (V12) |
|---|---|---|
| Kp / Kd | 20 / 0.5 | 20 / 0.5 (training randomised ×0.9-1.1) |
| Torque limit | 40 / 40 / 65 Nm declared | hip 24 / knee 36 Nm, speed-derated |
| Action scale / default pose | 0.25 / (0, -0.8, 1.6) | same |
| Control period | 20 ms clock; state about 1 kHz | 5 ms physics × 4; actuator delay 0-4 substeps |
| Damping | Kd 2.5 for 3 s | none in the runner |

Other references:
- Zero-command stillness practice survey: `A/.pipeline/survey/zero_command_stillness_practice_2026-08-23.md`.
- Earlier Dr Sun sign-off requirement for real-robot and safety-controller changes: `A/.trellis/tasks/08-24-mujoco-inference-standstill-control/prd.md:120-126`.
