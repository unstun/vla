# Local Newton navigation versions

Dr Sun designated the delivered empty-floor system as v3 on 2026-09-27 and requested one version per change. These version numbers describe this local simulation integration, separately from native SCAN candidate/build numbers.

| Version | One change | Evidence status |
|---|---|---|
| v3 | Registered current empty 12 m PD/RL baseline | One bounded trial validated; not generally stable |
| v4 | Connect the same control chain to complete archived Building geometry (5 m stair goal) | Factory/PD pass; navigation fails before motion. See [result](v4/RESULTS.md) |
| v5 | Restore explicitly selected height optimization | Frozen failure repaired; Building starts moving but continuation fails; new empty-floor trial also fails. See [result](v5/RESULTS.md) |
| v6 | Admit map-resolution-sized local continuations through shared native guards | Captured 17.4 cm continuation passes and executes; full Building remains unsuccessful. See [result](v6/RESULTS.md) |
| v7 | Require 0.6 m/s minimum planned cruise, retaining acceleration/braking and stop exceptions | Native retiming and direct 0.6 command tests pass; full navigation remains unsuccessful. See [result](v7/RESULTS.md) |
| v8 | Skip absent terrain neighbors without clearing unknown query cells | Sparse support test passes; native continuation remains blocked |
| v9 | Restore historical positive Z inflation to 0.10 m | Rejected: continuation passes but low box is missed; no physical run |
| v10 | Separate raw ground evidence from traversability scores | All eight measured obstacle cases pass; continuation still blocked by heading mismatch |
| v11 | Report native replan exhaustion to the current P2B owner | Native notification, receiver and existing stop-flow tests pass |
| v12 | Use the planned segment heading consistently for reference target checks | Captured continuation passes twice; physical run aborts with confirmed container OOM |
| v13 | Remove discarded legacy seed initialization | Repeated native calls pass; physical OOM no longer reproduced; stair route still fails |
| v14 | Match replies only from the requested consumer | Recorded failure/hold order and existing stop-flow tests pass |
| v15 | Classify measured risers bounded by mapped neighboring treads | Native continuation and all eight obstacle cases pass; physical route advances 1.06 m then stops |
| v16 | Retry optimization failures with the existing fixed-height mode | Rejected at compilation; source retained |
| v17 | Correct the height-mode accessor placement | Old native continuations and bounded recovery pass; physical route advances 1.84 m then fails odometry freshness |
| v18 | Retain a fresh converged clock estimate when an individual sample is rejected | Clock regression passes; physical route advances 1.984 m then native replan exhaustion |
| v19 | Preserve original float32 heights for the same selected ground cells | Precision and four native continuation replays pass; physical route advances 2.159 m and stops |
| v20 | Keep the Building replay camera inside the stair corridor | Full v19 video visually checked and decoded; no navigation change |
| v21 | Separate broader floor-band evidence from selected-tread riser classification | ROS contracts and five continuations pass; eight unmapped cases unchanged; physical route advances 2.558 m then native replan exhaustion |
| v22 | Densify the same static Building surface evidence with pinned Trimesh sampling | Loader and actual ROS payload pass; density alone still fails the v21 stopped-state continuation |
| v23 | Apply the existing complete floor/riser rule to the explicit qualified classification source | Seven continuations and eight unmapped regressions pass; physical route stops after 1.208m and reaches its 90s bound |
| v24 | Separate body-reference height from footprint terrain-layer support | Nine continuations and eight unmapped regressions pass; physical5m stair arrival recorded, final PD hold incomplete |
| v25 | Restore the explicit historical complete-floor route using existing automatic PCT layers | Direct PCT preflight passes; live loader drops null and forces wrong layer1; physical run fails odom_stale |

| v26 | Preserve explicit automatic PCT layer through config loading | Loader and actual TCP/native chain pass; live correct route, but no-progress/diagnostic abort at110.73s |

| v27 | Reuse OMPL verified direct connection to simplify an already valid native seed | Eleven continuations pass; geometry outputs unchanged; live13.24s native segfault; no full-route acceptance |

| v28 | Restore scan_27 finite paired rebound constraints lost in the scan_04 optimizer restore | Crash isolated (seed 269, empty `back()`); red/green 10/13 -> 13/13, 96 seed replays and full regression pass; live run has no crash but fails `odom_stale` at 15.56 s after a 0.344 s control stall; no route progress |

| v29 | Known-footprint waiver tested at the queried point, up to the Mid-360 origin (+0.10854 m, pinned URDF) | Red/green waiver contract passes; all 7 saved walking-start states plan (v28 failed the stopped one); full regression outputs identical except 3 explained query-CSV rows; independent re-review passed; live run leaves the start (23 replans, not 806), climbs 1.31 m of stairs over a 9.77 m path, then `native_replan_exhausted` at 88.3 s on the upper landing; no arrival |

| v30 | Step score: a present navigation neighbour without the walkway level is a possible drop only if the pinned surface evidence also lacks a surface near that level | Red/green support contract (17 cases, node real-drop negative, mutation check) passes; frozen landing/onset states plan past 8.645 s; start states and full regression explained; independent review passed on the third round; live run crosses the upper landing (frontier to 15.64 s), 13.44 m path, stops 4.15 m short in the upper corridor on invalid-curve holds at 57.5 s, then `odom_stale` (0.264 s wall gap) at 69.35 s; no arrival |

Current integration candidate: **v30**. Last accepted navigation condition: **v3, empty
12 m floor only**. Videos are ordinary files under
`output/2026-09-27_lite3_versions/`: `v3_empty_12m.mp4` and
`v4_building_test.mp4`, `v5_building_test.mp4`, `v5_empty_test.mp4`, and
`v6_building_test.mp4`, `v7_building_test.mp4`, and `v15_building_test.mp4`.
A failed new version never replaces the older outcome.

Before editing a new logical behavior or configuration, create the next integer version and state its scope. Preserve a hash-verified source snapshot and exact difference from the parent before running it. Keep immutable run IDs under runs/ and associate every attempt, including failures, with its version. Keep results separately from the frozen source manifest. A new version does not mean a successful version. Record the last validated condition explicitly. Do not put a release tag on unrelated dirty repository changes. Earlier v1/v2 are not reconstructed or relabeled. No automatic pre-edit commit is performed.

Archived at user request on 2026-09-28 at v27 ([handoff](../../../handoffs/2026-09-28_newton_v27_archive/README.md)). Resumed the same day for v28 at Dr Sun's request; see [v28 results](v28/RESULTS.md). v29 follows Dr Sun's 2026-09-28 choice after the [start-thrash diagnosis](../audits/2026-09-28_v28_start_thrash/RESULT.md); see [v29 plan](v29/PLAN.md), [component results](v29/COMPONENT_RESULTS.md) and [physical results](v29/RESULTS.md). The v29 landing stall is diagnosed in the [landing-stall audit](../audits/2026-09-28_v29_landing_stall/RESULT.md). v30 follows Dr Sun's 2026-09-28 choice of option 1 after that diagnosis; see [v30 plan](v30/PLAN.md), [component results](v30/COMPONENT_RESULTS.md) and [physical results](v30/RESULTS.md).
