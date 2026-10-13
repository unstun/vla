# v37 real-time physics candidate

Stage: experiment + analysis. Parent: frozen v36 component candidate (2026-09-30).
Status: device-selection component candidate; not yet executed or adopted.

Dr Sun approved the same-scene CPU/GPU comparison and subsequent native local
planning hotspot optimization on 2026-09-30. This version exposes only the
physics model device. Its two owned modules preserve the preceding CPU source
and add cpu/cuda:0 selection without changing the PD, policy, contacts, checks,
step sizes or navigation contract. Full episode launch remains on v36.

Owned changes: `physics/lite3_newton_v37.py` and `physics/robot_scene_v37.py`.
The BASE-path/import changes resolve the same pinned shared prerequisites from
the isolated version module. Copying these modules is deliberate: the shared
parent modules are part of frozen versions and cannot be refactored in place.
The benchmark harness belongs to the dated real-time audit, with each executed
driver preserved independently of this frozen device-selection implementation.

Dr Sun requested simulation time to match real time as closely as possible.
Target RTF is 1.0; preserve the 1 ms integration/joint-PD step, 20 ms policy
period, Building triangle contacts, imported robot/sensor geometry, source
weights and causal measured-state transport. Keep v36's selected wall-clock
global 1 Hz, local 30 Hz and controller 30 Hz plus final XYZ/yaw contract.

The 2026-09-30 audit of frozen CPU physics measured 2.000030 s solver time in
3.731837 s wall time: RTF 0.535937, before LiDAR/transport/navigation. Solver
steps averaged about 1.366 ms, and collision processing about 0.415 ms, per
1 ms physical step. Policy inference averaged 0.204 ms per 20 ms interval.
See `audits/2026-09-30_realtime_budget/`; this is a policy-zero physics-only
measurement, not a formal navigation run or exact factory/PD stand condition.

Installed Newton 1.6.0 supports the MuJoCo-Warp backend and Newton contact
solver on its model device. The selected existing model is explicitly CPU.
The next minimal candidate exposes model device selection and tests CUDA on
gpu5070ti without changing contact semantics or solver settings. Preserve
parent source bytes and exact patches before executing the changed variant.

Before full integration, use bounded CPU/CUDA component trials with one
continuous state each, original applied-force checks, finite/upright state,
input/source identity and actual solver timestamps. Record both cold setup
and warm stepping, RTF, actual policy/physics wall rates, contact capacity and
pose-read overhead. Device parity is numerical/behavioral, not assumed bitwise.
The same continuous condition contains 0.1 s zero-command warmup, 2.0 s measured
zero command and 2.0 s measured vx=0.2 m/s, with the same 200 Hz measured-pose
read cadence. Run the unchanged CPU parent, v37 CPU and v37 CUDA sequentially.
The parent/v37 CPU traces must match exactly. Report CUDA state/action drift
instead of declaring bit parity; require finite states, upright body (up z >=
0.5), force-mapping error <=1e-4 and the unchanged pre-integration capacity guard.
These are bounded component checks, not factory startup or navigation acceptance.
Each worker has a 600 s wall deadline, covering initialization/JIT as well as
the 4.1 s continuous simulation condition. Retain failures and all raw records.
If CUDA achieves spare compute capacity, a subsequent integer version will add
1:1 wall pacing using real solver elapsed time and log deadline misses; if it
remains slow, report that gap. Device selection and pacing are separate changes.
Do not fabricate a fast clock or discard physical steps to appear real time.

Full scene navigation with sensing/communication requires its own measured
end-to-end RTF and separately authorized long run. A physics-only speedup is
not whole-system or navigation acceptance. No training or hardware actuation.
