# CPU/CUDA comparison and solver graph evidence

Date: 2026-09-30. Stage: experiment + analysis. Executed sequentially on
gpu5070ti (Ryzen 7 9700X, RTX 5070 Ti). Local repository is the source of truth.
Six completed worker cases and 78 returned files passed SHA-256/size checks.
No owned profiling workers remain running after interruption.

Each closed-loop case has one continuous state: 0.1 s zero-command warmup,
2 s zero command, then 2 s vx=0.2 m/s. Same original Building mesh, URDF,
policy, 1 ms PD/physics, 20 ms policy, capacity guard, applied-force/finiteness
checks and 200 Hz pose reads. Phase wall time is synchronized. Initialization
and kernel/graph setup are recorded separately from warm stepping.

| Case | Zero phase RTF | Forward phase RTF | Scope |
|---|---:|---:|---|
| Original CPU | 0.534409 | 0.522150 | Unchanged parent |
| v37 CPU | 0.538210 | 0.522741 | 200 trace rows exactly equal to original CPU |
| v37 CUDA eager | 0.509826 | 0.505602 | No speed gain from device selection alone |
| v38 CUDA solver graph | 1.587084 | 1.582411 | About three times the CPU warm-step speed |

v38 captures only the existing fixed-dt solver call in two buffer-direction
graphs. Collision generation, PD, pre-integration capacity rejection and
post-integration force/finiteness checks still execute on every physical step.
Actual graph launches: 4,099; one first real integration warms the solver.
Solver host counter equals actual robot steps. Force-mapping error is zero;
minimum forward body-up z is 0.976661. This is physics-only warm-step evidence,
excluding LiDAR, transport, navigation and factory/PD initialization. It is
not full-stack RTF 1, 30 Hz or navigation acceptance.

CUDA/CPU and eager/graph closed-loop traces are not equal. Static differences
are small, but forward joint/action differences are substantial. To isolate
policy feedback, two additional continuous cases replay the same 200 recorded
50 Hz target vectors through the unchanged 1 ms PD loop, without new policy
inference in measured phases. See TARGET_REPLAY_PLAN.md and raw case identities.
Their input targets are exactly equal. Maximum body-position difference is
0.000325229 m, maximum joint-position difference 0.007906556 rad (about 0.453 deg).
The predeclared 0.001 m / 0.001 rad diagnostic parity gate **fails on joints**.
Do not relax that gate or claim preserved numerical behavior from upright pose
and force checks alone. Details: target_replay_comparison.json.

Status: v37/v38 sources are frozen component snapshots (5,796 / 5,806 files),
but neither CUDA variant is adopted into the full episode. The existing
integration remains v36, with CPU physics. Further numerical verification and
whole-stack integration/pacing are outstanding. No training, hardware actuation,
new long navigation/video trial, commit or push occurred.
