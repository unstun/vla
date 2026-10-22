# v287 complete offline and single-attempt physical report

离线：49/50 合法路线、3/3 非法对照，全局中位数 1.377 s。实跑：到达并完成 PD 6/10；到达且后续完整传感器记录几何通过 4/10；起立记录包络通过 10/10。原生进程故障 3 次。完整物理验收：未通过。

## Scope and immutable identities

The local VLA repository is the source of truth. v287 is a new329-file native composition from frozen v286; nine production files change. No scene, route or coordinate navigation branches were added. The hard source radius stays0.35m and the scanner period/deadline stays0.1s. Factory PD/policy, freshness/starvation limits, static global reference retention and tracker are unchanged.
The remote execution copy is /home/ubuntu/sun/vla_v287_20261020 on ultra9 (Core Ultra9 285K, RTX5070Ti). v286 raw data and earlier frozen versions remain preserved. No additional storage deletion was performed. Geometry and all53 zero-step captured inputs are reused byte-exact from v286 on the same host; every scored planner call and physical recording is new.

| Identity | SHA-256 |
|---|---|
| Local v287 source/cohort manifest | `1ac6d653894ef65138750fb779f0afdae528167f1408bd199466c934bf668a85` |
| Native installed/input/evaluator manifest | `1dacc549b8e3d51ccf3f3f9d6c6cbcebb851b14348acd5c4ccb5629cdc4a8fb0` |
| Physical execution manifest | `70a28fbdf7269447e580aa00d576e5aec2cbd5f47704dd2497d8544311aeace5` |

The offline/build container is pinned to ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343. Physical Nav2 uses the task-owned GDB image af529e408d9d130ba7b15a1eb2b78dc7b5408953a0de994ea05cccb43972fbec. The factory logical image, policy and original input identities remain unchanged. Release/O3 builds retain line symbols and frame pointers. Shared system settings and foreign jobs were not changed.

## Implemented changes and native evidence

- Removed exact-source rebound helpers and their L-BFGS calls. First-stage environmental scoring uses the existing precomputed ENV225 table; refinement still excludes environmental terms. Exact source geometry remains in global/static admission and independent audit.
- Replaced both capped penalties by max((target-margin)/target,0), and retained edge/solid derivatives below zero margin. Identical negative/zero/positive finite-difference checks fail4/8 on immutable v286 and pass8/8 on v287. Synthetic ENV queries take approximately0.2microseconds, with no added spatial searches; this is not a whole-planner latency claim.
- Removed the supported-air source collision call/cache. Normalization requires in-map, zero inflation and a complete passing support/layer/edge/freshness decision. Raw-unknown classification again precedes inflation/contributor classification. Actual native negative controls retain stale, inflated, unsupported, unassociated-height and out-of-map refusal.
- Added checked endpoint/neighbor pool access and safe empty AStar ownership initialization. Positive-tolerance terminal-border and out-of-pool tests exercise the actual search. The parent already checks all axes in Coord2Index; no old crash stack establishes an out-of-bounds cause. The new access guards are tested prevention, not proof of the old SIGSEGV cause.
- Completed aligned allocation declarations for missing Eigen owners/results. GridMap, SCANReplanFSM and BsplineOptimizer already had declarations, and the affected packages already use C++17. Alignment alone is not established as the old crash cause. All14 packages were rebuilt cleanly to avoid mixed class layouts.
- Native Nav2 children run under a signal-preserving GDB wrapper. Five zero-physics SIGSEGV/SIGBUS/SIGABRT/SIGILL/SIGFPE injections each return their signal exit status and retain all-thread, symbolized stacks. Python children enable faulthandler. Actual fault receipts/stacks are retained when present.

Qualification includes174 inherited native executions,18 repair checks,8 field checks,4 terrain directions,4 tracking clock cases,5 signal tests and50 legal-start checks. Development fixture-format and ROS-log-directory failures were preserved separately; they are not scored routes or physics attempts.

## Full 50+3 gate

All53 calls and independent geometry audits finished. Legal 49/50; illegal refusals 3/3. Admitted-route global median 1.376954s, all50-legal median 1.385928s; admitted p95 2.004709s, maximum 2.147577s. Gate passed. Initialization is excluded from the timed global call and is retained per case.
All50 legal starts pass: minimum extra edge margin0.1499999046m and source-solid margin0.1441991991m. No requests were resampled after results. Full case details and timing are in offline/matrix_summary.json and matrix_table.csv.

## Ten single physical attempts

Each route ran once after the complete offline gate. A failed prefix with clear sampled margins is not a completed geometric success. The table reports minimum margins over all recorded10Hz body poses, including terminal/tail poses; factory startup is audited separately below. Margins cap at+0.15m.

| Route | Goal + PD | Goal + full recorded geometry | Duration s | Measured path m | Support extra cm | Source extra cm | Raw extra cm | Max low-speed pause after motion s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A04 | 0 | 0 | 61.00 | 28.65 | 15.000 | 15.000 | 15.000 | 6.756 |
| G05 | 0 | 0 | 86.58 | 28.59 | 7.291 | 15.000 | 15.000 | 16.211 |
| CU06 | 0 | 0 | 68.63 | 31.55 | 15.000 | 15.000 | 15.000 | 8.395 |
| D07 | 1 | 0 | 125.70 | 82.76 | 8.455 | -1.635 | -1.312 | 6.017 |
| S04 | 1 | 1 | 30.53 | 4.71 | 15.000 | 13.069 | 13.131 | 5.237 |
| CD12 | 1 | 0 | 133.54 | 89.66 | 9.784 | -4.226 | -4.083 | 4.484 |
| CM02 | 0 | 0 | 17.92 | 0.08 | 15.000 | 15.000 | 15.000 | 0.000 |
| CM07 | 1 | 1 | 57.76 | 24.67 | 10.875 | 15.000 | 15.000 | 6.956 |
| CS03 | 1 | 1 | 30.14 | 4.80 | 15.000 | 5.712 | 5.736 | 5.697 |
| CE03 | 1 | 1 | 27.12 | 2.24 | 15.000 | 3.135 | 3.136 | 6.097 |

Original global-reference geometry is retained on10/10 routes. Native process faults:3. Scanner jobs:5287; deadline failures:0. Per-case command, pure-yaw, settling, pauses, terminal pose and PD evidence is in physical_table.csv and physical_return/*/results/.

Actual navigation RTF ranges 0.849390–0.939968; dropped physics steps total 0. Target pacing stays1.0. Debugger startup/fatal stops can perturb wall timing; original recorded clocks are retained and no faster-than-recorded physical performance is claimed.

## Local latency and error counters

Stage timing comes from actual V50_PROFILE log records. Optimizer timing is reported separately from complete local rounds, which also include search, input refresh, seed preparation, refinement and final checking. A low median does not imply every round met50ms.

| Route | Whole-round median / p95 / max ms | Optimizer median / p95 / max ms | Optimizer reports >50ms |
|---|---:|---:|---:|
| A04 | 11.148 / 70.282 / 559.662 | 2.987 / 17.394 / 248.925 | 15 / 1132 |
| G05 | 6.489 / 22.407 / 513.039 | 2.374 / 16.338 / 203.680 | 10 / 1207 |
| CU06 | 10.074 / 78.207 / 558.494 | 2.581 / 18.202 / 301.955 | 24 / 1272 |
| D07 | 11.348 / 34.841 / 408.587 | 3.156 / 17.411 / 274.875 | 27 / 3367 |
| S04 | 14.357 / 27.284 / 111.635 | 4.794 / 12.688 / 88.612 | 2 / 297 |
| CD12 | 10.963 / 34.016 / 433.941 | 3.042 / 16.533 / 254.042 | 34 / 3489 |
| CM02 | 107.731 / 283.051 / 302.531 | 18.592 / 170.458 / 170.458 | 1 / 3 |
| CM07 | 10.391 / 29.255 / 262.706 | 3.179 / 16.527 / 99.868 | 7 / 1075 |
| CS03 | 11.053 / 31.482 / 195.380 | 3.864 / 16.829 / 166.986 | 3 / 246 |
| CE03 | 8.767 / 31.777 / 53.961 | 3.193 / 17.287 / 37.265 | 0 / 147 |

| Same literal log counter | v286 | v287 |
|---|---:|---:|
| pool_exhaustion | 0 | 0 |
| endpoint_adjustment_failed | 0 | 27 |
| astar_optimization_failed | 6 | 25 |
| inside_obstacle | 859 | 0 |
| lbfgs_minus1008 | 84 | 674 |
| no_executable_trajectory | 51 | 9 |

### Recorded solid-boundary witnesses

D07 first crosses at116.767456s while RL owns joints and the applied command is[0,0,1.0]; XY distance to the requested goal is0.125061m. Its worst source margin is-0.016354m. CD12 first crosses at126.162292s with[0,0,0.501875] and goal distance0.106848m; the worst-0.042260m occurs during STAND_TRANSITION with zero command. Full measured state/command witnesses are in boundary_state_audit.json.
At the worst D07 sample, the latest causal curve is0.040s old and its nearest spatial point is0.017837m from the body. That point has+0.076694m source margin at its planned tangent heading; measured body yaw differs by128.350degrees and its actual margin is negative. CD12 nearest-point distance is0.039597m, with+0.070176m planned-heading source margin and23.500degrees body-heading difference. The last curve there is1.399s old. These are geometry/command comparisons, not a reconstruction of scaled tracker phase or proof that an old curve is currently executable.
Both first crossings coincide with terminal pure yaw, which the inherited tracking_node.hpp:310-323 branch permits inside XY/Z tolerance. The corrected optimizer gradient therefore cannot by itself certify the actual final-turn/PD envelope. No scene-specific fix or publication veto was added to hide this result.


Actual native fatal signals and their fault-thread frames:

- A04: SIGSEGV; rip            0x730d2cfbd6ec      0x730d2cfbd6ec <GridMap::terrainCellLayers(reactive_stair::Cell2 const&)+428>; first source frame: #0  std::_Hashtable<unsigned long, std::pair<unsigned long const, GridMap::TerrainCellLayers>, std::allocator<std::pair<unsigned long const, GridMap::TerrainCellLayers> >, std::__detail::_Select1st, std::equal_to<unsigned long>, std::hash<unsigned long>, std::__detail::_Mod_range_hashing, std::__detail::_Default_ranged_hash, std::__detail::_Prime_rehash_policy, std::__detail::_Hashtable_traits<false, false, true> >::_M_find_before_node () at /usr/include/c++/9/bits/hashtable.h:1583.
- CU06: SIGSEGV; rip            0x766d19dba05c      0x766d19dba05c <GridMap::rawContributorOccupancy(Eigen::Matrix<int, 3, 1, 0, 3, 1> const&)+1020>; first source frame: #4  GridMap::rawContributorOccupancy () at /work/src/plan_env/include/plan_env/scan_reactive_grid_methods.inc:432.
- CM02: SIGABRT; rip            0x74dba000300b      0x74dba000300b <raise+203>; first source frame: #11 0x000074db7a5ac6f9 in AStar::AstarSearch () at /work/src/path_searching/src/dyn_a_star.cpp:490.
  Allocator evidence: ['[controller_server-3] double free or corruption (out)']

A04 faults in terrainCellLayers cache lookup, CU06 in rawContributorOccupancy cache lookup, and CM02 reports double-free/corruption during A-star queue-vector growth. These are observed fault sites; an earlier invalid write/free or concurrency error can corrupt those containers. The stacks do not establish Eigen alignment or the endpoint pool as the root cause. Point4 remains unvalidated. Frozen v287 was not modified or retried to hide these results.
The unmodified literal counters above remain directly comparable. Application-only counters excluding debugger dumps are separately retained for every case; inspect them if a debugger frame contains an error literal. PCT core keeps its inherited O2/C++14 configuration; the affected local libraries use C++17/O3 with line symbols and frame pointers.


Counters are retry-inclusive line mentions, not independent failures. First contexts and stage-specific line-search failures are preserved in failure_terminal_bill.json. The inside-obstacle string comes from a control-point collision walk and is not itself a measured-trunk collision. Inspect typed verdicts and actual geometry separately.

## Startup, geometry and video integrity

Factory startup uses1380 original video-state poses, separately from the later10Hz sensor stream. Maximum sampled PD XY drift is0.121814m. Startup sampled envelopes pass10/10. Nominal crouch-height WrongHeight is reported separately from support-gap/source-solid clearance. No states were interpolated to certify safety.
Source-solid, registered raw-point and support-gap audits operate on measured recorded poses. These are sampled body-envelope checks, not continuous-time or foot-contact certification. No change to the0.35m threshold is hidden by reporting precision.
Ten complete regular MP4 files reproduce original factory and navigation states at30fps, with causal original trajectory overlays. No physics was rerun for rendering. Every video passes full decode, source/state/overlay checks and local SHA verification. See delivered/README.md for all10 file links, sizes and hashes.

## Delivery and remaining acceptance boundary

Physical acceptance does not pass: 4/10 completed with a clear entire later recording and 10/10 startup envelopes were clear. This single fixed-cohort run does not establish statistical reliability. Remaining failures or timing outliers are preserved as results, not retried or relabeled.
The frozen geometry-start receipt retains a legacy migration field navigation_source_changed=false; that field describes no geometry/input edit and is not the source-change claim for v287. The source manifests and nine-file changes.patch explicitly record the production changes. Legacy all_recorded sensor windows begin after factory startup, which is audited in startup_return/.
Raw captures, snapshots and build bytes remain on ultra9; compact reports, provenance and all10 actual review videos are returned locally. Reproduce analysis/rendering from unchanged raw states using the locally versioned ultra9 adapters. Preserve all frozen parents and failed records.
