# Original factory algorithm: crouch, zero-return torque, stand

Stage: experiment + analysis, 2026-09-27. This is a local Newton test authorized
by Dr Sun. No physical robot command was sent.

## Result

The unchanged factory library drove a continuous 12,000-step Newton episode
from crouch through its zero-return torque phase, preparation and standing.
The robot stood at approximately 0.34 m. **Strict factory calibration and
in-place acceptance did not pass.**

| Observation | Actual result |
|---|---|
| Zero-return phase | 1.000991–6.501711 s |
| Zero flag | 5.401791–5.501784 s |
| Preparation | 7.500639–8.500805 s |
| Rising | 8.500805–9.501209 s |
| Standing phase | 9.501209–12.001220 s |
| Standing height, after 10 s | 0.33925–0.35117 m |
| Largest displacement from spawn | 0.12448 m, during rising |
| Largest displacement after 10 s | 0.11114 m; exceeds the 0.10 m criterion |
| Final displacement | 0.09881 m |
| Largest standing linear speed | 0.05433 m/s |
| Native applied torque disagreement | 4.77e-7 Nm or less |

The zero flag occurs even with frozen joints in the synthetic test. It is not
independent proof of successful mechanical calibration. The simulation uses
ideal absolute joint angles; the hardware caller's motor-turn correction is
not applied. Its HipY reference is -3.49 rad, whereas the original URDF limits
that joint to -2.67 rad. The measured zero-phase angle is about -2.67052 rad.
See `ALGORITHM_ABI.md` for the source addresses and exact boundary.

The initial clock check incorrectly compared accumulated native float32 time
against a double-precision step product. The original failed verdict is
preserved in `result.json`. The separate read-only `review.json` verifies every
native timestamp against float32 recurrence with exactly zero disagreement.
The episode was not rerun. This corrects a checker assumption, not the unmet
in-place or calibration requirements.

## Evidence

- Physics: `../2026-09-26_newton_stair_reproduction/runs/factory_zero_stand01/`.
  Full-rate inputs, raw library replies and actual states: `full_rate.npz`.
- Actual-state video: `../2026-09-26_newton_stair_reproduction/runs/factory_zero_stand_video01/`.
  151 frames at 12.5 fps, 1280×720, 12.08 s display duration; recorded physics
  ends at 12.00122 s. These are separate clocks.
- Delivery: `output/2026-09-27_lite3_factory_test/lite3_factory_zero_stand_test.mp4`.
- Raw library motor outputs match the commands recorded by the physics driver.
  Every displayed joint state matches the corresponding actual physics state.
  Selected crouch, zero-torque and standing frames were visually inspected.
- Original library/configuration/dependency/model hashes: 35 files verified.
- Eight motor/interface tests and eight existing PD-startup regression tests
  passed. One earlier test-fixture failure is retained; the new force test now
  owns a separate robot because Newton reset does not reset its clock.

## Reproduction and next gate

Use the existing local Python runtime at
`../2026-09-26_newton_macos_policy/runtime/.venv/bin/python`:

```text
probe_algorithm.py --steps 4501 --run NEW_SYNTHETIC_RUN
run_newton_factory.py --run NEW_PHYSICS_RUN
review_newton_factory.py EXISTING_PHYSICS_RUN
```

The container image is pinned in `factory_process.py`; no image pull is needed.
It has network `none`, no passed-through devices, a read-only root/snapshot,
dropped capabilities, a non-root user, 1 GiB memory and a bounded lifetime.
Only a thin caller is compiled; neither the factory executable nor its startup
script is executed. Existing navigation and policy startup defaults are unchanged.

Next establish a source-backed mechanical/encoder model, including the mismatch
between the working joint range and the homing reference, before altering model
limits. Then rerun the same trial and diagnose displacement against the current
0.10 m criterion. Do not present this video as a passed physical calibration or
navigation result.
