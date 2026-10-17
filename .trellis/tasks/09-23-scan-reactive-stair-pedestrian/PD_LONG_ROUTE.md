# PD hold and unobstructed long-route Newton trial

Stage: experiment + analysis. Authorized by Dr Sun on 2026-09-27: connect the
existing PD/RL switching and show a long PCT + corrected SCAN execution without
obstacles. Local simulation only; the original Isaac A4 remains open.

## Change boundary

Newton currently stays under RL at zero command, although the existing
`isaac_runner/stance_hold.py` already implements the qualified switching path.
The old scene has an obstacle and the driver cancels at 27 simulation seconds.
Reuse the state machine without changing its gains, thresholds or transitions.
Use Newton's pinned public SensorContact API for measured foot support, preserve
the applied-action observation history, and record joint ownership explicitly.

Changes belong in the Newton motor adapter, flat scene, bounded episode/driver,
native graph map selection and recorded-state renderer. Add a dedicated long
route driver and a registered empty-floor PCT input; preserve old profiles.
Do not change the native PCT, SCAN42 v9, controller, occupancy or freshness limits.
Keep failed attempts and pre-edit source snapshots in the dated repair folder.

Factory homing/stand remains the previously recorded ideal-encoder simulation
condition. Run its existing algorithm before navigation, then transfer the
measured standing state to PD with a torque-matched seed. Do not reset pose,
velocity or policy history after initialization; no mechanical calibration claim.

## Prospective checks

1. Existing hold tests and original motor/golden-policy contracts pass.
2. A continuous stand/walk/stop/restart control trial records FIXED_STAND with
   Kp=60, Kd=1 and policy_owns_joints=false, plus REJOIN and RL with movement.
3. The requested unobstructed flat route is 12 m, beyond the 3.5 m local planning
   horizon. Native PCT computes it from the registered synthetic support prior.
   Only measured geometric LiDAR and body localization reach SCAN.
4. One continuous physical run, at most 150 simulation seconds and 1700 wall
   seconds, ending on original backend ARRIVED plus >=2 s PD FIXED_STAND.
   XY error <=0.25 m; no fall (up-z >=0.5), base height >=0.20 m after startup;
   full-rate force mapping and no contact-capacity overflow. Original homing
   in-place/calibration failures stay separate from this route's acceptance.
5. Record raw native route/curves, commands, forces, controller state, actual
   pose, clocks and source hashes. Render only from saved states and deliver a
   regular MP4 with visible robot, global route and local curve. Decode it and
   inspect beginning, travel and final-stop frames.

No formal training, remote server use, physical actuation, obstacle-avoidance
claim, old-result relabeling or unrelated refactor is included.

## Execution notes

- `pd_switch_control01` and `pd_switch_factory02` fail the fixed eight-second
  stop windows. Keep their force-balance waits and failures. No gate was relaxed.
- `pd_switch_factory03` uses measured fixed-hold dwell before restarting;
  three holds and two rejoins pass in one 43.927 s episode. The final settle plus
  transition lasts about 16.4 s, which is a real latency limitation.
- Existing hold tests: 53 pass. Original motor/history contracts: eight pass;
  nine pass after adding the read-only physics-observer dynamics regression.
- `empty_long_route01` produces PCT/SCAN motion but fails with `odom_stale`:
  observed body-pose gap 0.2957 s versus unchanged 0.25 s watchdog. The next
  trial publishes actual integrated body samples every five physics substeps;
  policy and LiDAR periods, original watchdogs and native planner are unchanged.
- `empty_long_route02` still fails odometry freshness; `empty_long_route03`
  separates captured-state sensing and evidence I/O but fails heartbeat freshness.
  Measured control intervals reach 0.563 s. Do not relax the 0.20/0.25 s gates.
- The explicit empty scene can reuse the original E1 native MuJoCo CPU solver
  inside Newton, instead of the MuJoCo-Warp CPU path required by exact actor
  mesh contacts. A native 1 s physics probe took 0.146 s wall time. Qualify
  `--physics-backend native` separately, with the original URDF, a friction-1
  ground plane, recorded floor ray mesh, original control gains and actual
  `mj_contactForce` foot support. Pace control to its 20 ms physical interval.
  Preserve the Warp default and all prior actor trials; this is an explicitly
  different empty-floor solver condition, not an equivalence claim.

## Bounded result, 2026-09-27

`empty_long_root_live08` passes all 17 declared route checks: native arrival,
12.0169 m actual navigation path, 0.19697 m final goal error and 2.080 s final
PD hold. Common interface checks also pass. The continuous 41.760 s episode
includes factory startup; the final replay is `empty_long_video10`, delivered
as `output/2026-09-27_lite3_pd_long_route/lite3_pct_scan_12m_pd.mp4`.

Condition: original native CPU solver, navigation pacing factor 0.5 and
`scan43_prefix_diagnostic_v2` (SCAN42 v9 plus observational logging/query calls).
Extra logging changes scheduling, so this is one validated instrumented trial,
not proof of fixed startup or default-build repeatability. Run06 and run07
initial-heartbeat failures remain. Original freshness/occupancy/PD gates were
not relaxed. The task remains in progress because the original Isaac A4 and
general obstacle qualification remain open. Full evidence and remaining leads:
`repairs/2026-09-27_pd_long_route/RESULTS.md` in the Newton stair experiment.
