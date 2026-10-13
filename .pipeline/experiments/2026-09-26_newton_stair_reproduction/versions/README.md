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

| v31 | SCAN takes pending pose and scan messages at safe points on its single-threaded executor and applies them in stamp order through the unchanged callbacks (Dr Sun kept this narrower means of option 1; bounded planning later); the FSM refreshes its own odometry at its timers | Second candidate (scan64, byte-exact; the first, scan63, failed round-1 review and is kept in `attempt01/`); red/green refresh contract incl. mid-call and split-batch cases passes after one recorded analyzer correction; saved states and full regression outputs identical to v30; round-2 independent review passed; live run climbs both stair flights with no stale-input stop (v30 had 8 in the same 29.9 s) and ends on `odom_stale` (0.288 s wall pause, 3 clock-observation reconnects) at about 27.7 s, 7.12 m short, before the upper landing; no arrival |

| v32 | The Mac Newton worker collects and then freezes its heap (`gc.collect()`, `gc.freeze()`) before the control loop and after every 50th control step, so no automatic full cyclic collection holds the GIL (Dr Sun: fix the clock fault, after the [wall-clock chain diagnosis](../audits/2026-09-29_wall_clock_chain/RESULT.md)) | K1 byte-exact (three insertions in `scripts/newton_episode.py`), K2 AST scope, K3 three-schedule replay (no in-loop collection over 20 ms; 0 frozen garbage against 146,504 for freeze-only; identical states) and K4 independent review (passed in round 4, confirmed in round 5) pass. Instrumented run L1 is inconclusive by its exposure rule (2,818 of 7,100 steps), with no automatic full collection or process-wide hold, and ends on `odom_stale` from a 254.5 ms bridge hold. Trial L2 climbs both flights, stands at the corridor entry's wrong-height cell from 39.3 s and ends on `odom_stale` at 284.4 s (a 320 ms worker stall under host load); no arrival |
| v33 | In the simulator only, the backend's odom gate judges pose freshness by simulation time against `/clock` (0.25 s), with a 2.0 s wall-time backstop; the real robot's wall-time gate is unchanged (Dr Sun, 2026-09-29) | K1–K5 pass; independent review passed in round 2 and was confirmed in rounds 3 and 4 (K4 reproduces 10 of 12 recorded `odom_stale` ends). The trial ran on gpu5070ti ([port](../hosts/2026-09-29_gpu5070ti/PORT.md), validated P1–P6, five review rounds): it climbs both flights, stands at the corridor entry from 32.6 s and ends at 459.7 s when SCAN's replan limit runs out (`native_replan_exhausted`, 1,000 failures). No pose gap exceeded 0.25 s (longest 69.7 ms), so it says nothing about stall tolerance; no arrival, no fall. See [results](v33/RESULTS.md) |

| v34 | SCAN augments its copy of navigation ground with surface-evidence floors missing within 0.12 m, guarded against drops within 0.35 m | K1–K5 passed; 3,548-file freeze and remote gates passed. The single gpu5070ti trial crosses the former entry at 36.08 s, reaches the east-end corner and ends its 600 s nominal observation without arrival (600.52 s recorded physics; 5.88 m XY goal error). Original driver-final record is absent, so the unchanged formal reviewers emit no verdict. Full heading and standard videos decoded and verified. See [results](v34/RESULTS.md). |

| v35 | Nominal local replanning uses configurable 2 Hz scheduling, replacing displacement triggering; nominal initial/retry attempts are limited, safety replanning stays immediate | Build, native-FSM contract, independent reviews, 3,752-file freeze and remote gates pass. Single gpu5070ti trial ends at 561.51 s on native_replan_exhausted at the east-end corner, 5.95 m from goal. Median nominal interval 0.50354 s; no zero-command stop >=0.3 s before 54.26 s, but corner pulses and long stand remain. Verified 100 s preview and full heading video delivered; no arrival. See [results](v35/RESULTS.md). |

| v36 | Nav2 timing/goal contract: selected global 1 Hz, local/controller 30 Hz, exact final XYZ/yaw and fixed initial-route heading | 5,787-file component freeze; controller 29.9993 wall Hz and actual PCT 1.00028 wall Hz in bounded components. Native/backend/safety and two independent reviews pass. Recorded local plans succeed in 87.8/120.3 ms, exceeding 33.3 ms; whole-system 30 Hz and navigation remain unvalidated. No physical trial or new video. See [results](v36/RESULTS.md). |

Artifact pipeline: [v51](v51/RESULTS.md), display/storage only, renderer parent v46. Streaming MP4 and managed post-run retention are the default for new work. Removed62,371 verified PNG intermediates, compressed152 closed logs and archived10,260 raw members from three failed/diagnostic runs. Native/navigation source is unchanged. See [usage and restoration](v51/README.md).

Current runnable experimental reference: **v48**. Latest measured native development version on gpu5070ti: **v59**, through frozen v58/v57 and earlier repairs with v49 excluded. v58/v59 completed one 90-second recording each: successful planning **27.53/26.43 Hz**, maximum solve **659.526/1236.709 ms**, measured paths **55.19/55.04 m**. The endpoint-search and direct timing checks pass, but v59 has a **1.099 s late pause** and an unresolved **chained-retry timestamp reset**. See the [native diagnosis](../audits/2026-10-03_v59_cold_recovery/REPORT.md). Sustained 30 Hz, full tail elimination and full-route arrival fail. **v60/v61 are display-only**, using the exact v59 recording. See [repair report, plot and final video](v59/REPAIR_REPORT.md). Last complete-route trial remains v35.

[v52 results](v52/RESULTS.md): scoped terrain-cell lookups preserve original collision/support, goal/yaw/PVA and stop rules. Builds and safety gates pass (35 native, 64 cache, both warm fixtures and backend checks); idle-host paired max improves 473.514→422.981 ms (10.67%) with exact outcome/geometry. Live trial02 records 11.54 Hz attempts, 10.19 Hz successful plans, median 2.04 ms, max 711.404 ms, 23.19 m path and 46.57 s late pause; raw controller remains 29.9998 Hz. Zero >=1,000 ms rounds in this recording does not establish general tail elimination. No emergency transitions or invalid-current-curve events; full route and continuity/30 Hz gates still fail. All 795 original bulk members are verified and archived on gpu5070ti; 17 compact returns match hashes. [Time series](v52/analysis/v52_time_series.png), [idle replay](v52/analysis/idle_paired_latency.png). v49 remains excluded from ancestry.

[43-second corner diagnosis](../audits/2026-10-02_v52_corner_43s/REPORT.md): unchanged-native replay traces the 42.353 s route-refresh loss of warm eligibility/window, later footprint support-map rejection, freshness-sensitive recovery checks and downstream curve-end stop; no new navigation version or 30 Hz acceptance claim.

[v50 results](v50/RESULTS.md): a conservative necessary-condition precheck removes futile final-goal-neighborhood search before warm initialization; no v49 deadline or stop change. Build and all component safety tests pass; 18 paired replay rounds preserve exact geometry and reduce the combined maximum from107.481 to4.827ms. Live v50 maxima are1829.626 and858.031ms, with42.58/44.18s pauses and about23.7m path. Whole-window successful planning is10.39/10.47Hz; tail, continuity and30Hz acceptance fail. Unchanged v48 control also reaches the corridor corner and stalls late (max1017.612ms,24.82m). Preserve all runs and the v50 trial02 transfer-overlap caveat. [Time series](v50/analysis/v48_v50_time_series.png), [acceptance](v50/acceptance.json). v49 remains frozen and excluded from ancestry.

[v49](v49/RESULTS.md) adds a shared 20 ms compute /25 ms total cooperative budget. Native/component tests pass. Trial02 records **3.825 Hz** attempts, **2.883 Hz** new plans and **37.998 ms** maximum latency: no >=100 ms spikes, but three >33.333 ms rounds. A new timeout reason is ignored by the unchanged backend gate handler, causing 80 stop commands and repeated restarts; the stop contract fails. Only 1.432 m XY progress and no arrival. [Updated plots](v49/analysis/time_series/v48_v49_planning_time_series.png). Frozen failure evidence is preserved; the repair proposal is superseded by v50's direct v48 ancestry.

[v48](v48/RESULTS.md) adds owned, current remaining-curve warm initialization with original graph fallback and unchanged final gates. Native checks and paired warm-only ~3 ms solves pass. The qualified run has 1,207 warm-only accepts, median **3.092 ms**, P95 **126.496 ms**, P99 **207.175 ms**, local **15.859 Hz**, controller **30.001 Hz** and global **0.99997 Hz**. Common-case latency improves, but tail and 30 Hz targets do not pass. All 909 original artifacts are verified locally.

[v47](v47/RESULTS.md) implements feasible-window reuse. The qualified gpu5070ti run measures local **16.232 Hz**, controller **30.001 Hz**, global **0.99987 Hz** and RTF **0.94494**. First seed-search failures fall from 73.69% to 0.22%, but the local target remains unmet. The robot travels 22.73 m with no measured pause over one second; the 90 s recording ends without arrival. Trial01 is excluded because its backend dependency was missing; trial02 restores the exact already-frozen parent dependency. Source/configuration hashes and 909 qualified raw artifacts are verified locally.
Performance components: [v37](v37/RESULTS.md) freezes device selection (CPU trace
exact; naive CUDA slightly slower). [v38](v38/RESULTS.md) freezes solver graph
replay and measures physics-only RTF1.58, about3x CPU, but its fixed-target joint
numerical gate fails; CUDA is not adopted. [v39](v39/RESULTS.md) is frozen/built/tested: recorded plans 17.6/22.8 ms with exact geometry, but complete v42 local loop achieved only 9.06 Hz. [v40](v40/RESULTS.md) CPU graph replay matches all 200 original CPU trace rows exactly, physics-only RTF1.58. v41 integrates these components; [v42](v42/RESULTS.md) first physical recording failed timing gates. v43 is display-only 30 FPS actual-state replay. [v44](v44/RESULTS.md) extends the scoped cache across nested planning attempts and preserves empty-drain reuse; 48 cache and 34 native checks passed, recorded plans 11.8/12.8 ms. v45 adopts v44 and records navigation from the initialized physical state with a 6-CPU native quota. Actual local16.86Hz/RTF0.9400 remain below targets; raw controller29.96Hz and global1.00Hz were measured. Global refresh returned pct_no_route and original stop/copyback completed. [v46](v46/PLAN.md) replays the actual wall timeline without accelerating pauses.
Last accepted navigation condition: **v3, empty
12 m floor only**. Videos are ordinary files under
`output/2026-09-27_lite3_versions/`: `v3_empty_12m.mp4` and
`v4_building_test.mp4`, `v5_building_test.mp4`, `v5_empty_test.mp4`, and
`v6_building_test.mp4`, `v7_building_test.mp4`, and `v15_building_test.mp4`.
A failed new version never replaces the older outcome.

Before editing a new logical behavior or configuration, create the next integer version and state its scope. Preserve a hash-verified source snapshot and exact difference from the parent before running it. Keep immutable run IDs under runs/ and associate every attempt, including failures, with its version. Keep results separately from the frozen source manifest. A new version does not mean a successful version. Record the last validated condition explicitly. Do not put a release tag on unrelated dirty repository changes. Earlier v1/v2 are not reconstructed or relabeled. No automatic pre-edit commit is performed.

Archived at user request on 2026-09-28 at v27 ([handoff](../../../handoffs/2026-09-28_newton_v27_archive/README.md)). Resumed the same day for v28 at Dr Sun's request; see [v28 results](v28/RESULTS.md). v29 follows Dr Sun's 2026-09-28 choice after the [start-thrash diagnosis](../audits/2026-09-28_v28_start_thrash/RESULT.md); see [v29 plan](v29/PLAN.md), [component results](v29/COMPONENT_RESULTS.md) and [physical results](v29/RESULTS.md). The v29 landing stall is diagnosed in the [landing-stall audit](../audits/2026-09-28_v29_landing_stall/RESULT.md). v30 follows Dr Sun's 2026-09-28 choice of option 1 after that diagnosis; see [v30 plan](v30/PLAN.md), [component results](v30/COMPONENT_RESULTS.md) and [physical results](v30/RESULTS.md). v31 follows Dr Sun's 2026-09-28 choice of option 1 after the [stop diagnosis](../audits/2026-09-28_v30_stop_classes/RESULT.md), with the narrower means he kept after the first independent review; see [v31 plan](v31/PLAN.md), [component results](v31/COMPONENT_RESULTS.md) and [physical results](v31/RESULTS.md). v32 follows Dr Sun's 2026-09-29 decision to fix the clock fault, after the [wall-clock chain diagnosis](../audits/2026-09-29_wall_clock_chain/RESULT.md); see [v32 plan](v32/PLAN.md) and [live-run results](v32/RESULTS.md). v33 follows Dr Sun's 2026-09-29 decision to judge pose freshness by simulation time in the simulator; its trial ran on gpu5070ti by his decision ([port](../hosts/2026-09-29_gpu5070ti/PORT.md), [host note](v33/HOST_NOTE_gpu5070ti.md)); see [v33 plan](v33/PLAN.md), [component results](v33/COMPONENT_RESULTS.md) and [live-run results](v33/RESULTS.md). Heading-follow videos (display camera only, `scripts/render_heading_view.py`) exist for v30, v31, v32 and v33.

### v57 review-video storage record

Path-specific local-only video: `output/2026-09-27_lite3_versions/v57_realtime_trial02_review.mp4` (8773409 bytes).
SHA-256: `d96b73a44c36bd6c9be4b1a3d844a1d158eb045632c20d061702d7fc48d9fb5b`. Durable copy: `gpu5070ti:/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runs/v57_review_trial02_attempt03/newton_stair_recorded.mp4`.
Regenerate on gpu5070ti from the experiment directory with the worker Python:
`XDG_DATA_HOME=/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime/render_env /home/sun/vla_exec/envs/newton_worker/bin/python scripts/run_managed.py --run-id NEW_UNIQUE_REVIEW_ID --deadline 900 -- /home/sun/vla_exec/envs/newton_worker/bin/python versions/v57/render_review.py --source-run v57_realtime_trial02`.
The original font and exact pinned renderer dependencies are recorded in
[v57 video provenance](v57/REVIEW_VIDEO.json); raw states remain remote. This
record is in the already-tracked version index as well as the separate JSON.

[v58 results](v58/RESULTS.md): current endpoint evidence reduces idle-host paired goal-search maximum from 44.614 to 0.259 ms with exact outcomes. [v59 results](v59/RESULTS.md): shared sample/receipt time passes actual-controller and delayed native PVA checks. Builds and safety contracts pass. Both physical recordings are complete; the earlier resource-preflight failure is preserved. Overall performance and continuity acceptance remain open; v48 stays the reference.

### v59 review-video storage record

Superseded failed-view video (local copy removed after remote identity and final-replacement verification): `output/2026-09-27_lite3_versions/v59_realtime_trial01_review.mp4` (9579823 bytes). SHA-256: `95728a89d929c806b6e06e34bfdc369f70966494e6083bfa3dfd3ae2cdf5643a`. Durable copy: `gpu5070ti:/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runs/v59_review_trial01/newton_stair_recorded.mp4`. Full decode verified:1280x720,2449frames,30FPS,81.633333s, original recorded wall timeline and no physics rerun. Regenerate: `On gpu5070ti, from the experiment root: XDG_DATA_HOME=/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime/render_env /home/sun/vla_exec/envs/newton_worker/bin/python scripts/run_managed.py --run-id NEW_UNIQUE_REVIEW_ID --deadline 900 -- /home/sun/vla_exec/envs/newton_worker/bin/python versions/v59/render_review.py --source-run v59_realtime_trial01`. [Full provenance](v59/REVIEW_VIDEO.json). Heavy states, frame arrays and raw captures remain remote.

[v60](v60/PLAN.md) is display-only: correct the ceiling-occluded v59 review camera, replaying the same v59 states and wall timeline. v59 remains the native navigation version; first-render visual failure is preserved.

[v61](v61/PLAN.md), display-only child ofv60: retain the ceiling-safe camera height and restore whole-robot framing. v60 footage crops rear legs and remains remote as failed visual evidence. Physical navigation stays v59.

### Final v59 review (display v61)

`output/2026-09-27_lite3_versions/v59_realtime_trial01_review_v61.mp4` (10488224 bytes), SHA-256 `03ade05cdc1f51e9c75650cb686f85dcfed6d53e8271ab3a9e6832814f8acc1a`. Remote: `gpu5070ti:/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runs/v61_review_v59_trial01/newton_stair_recorded.mp4`. Full decode,2449 frame/time/state selections and six visual samples verified. Source remains physical v59; v61 changes only display camera. Regenerate: `From the experiment root on gpu5070ti: XDG_DATA_HOME=/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime/render_env /home/sun/vla_exec/envs/newton_worker/bin/python scripts/run_managed.py --run-id NEW_UNIQUE_REVIEW_ID --deadline 900 -- /home/sun/vla_exec/envs/newton_worker/bin/python versions/v61/render_review.py --source-run v59_realtime_trial01`. [Provenance](v61/REVIEW_VIDEO.json). The earlier local v59 video is superseded by this view; its original bytes remain remotely preserved after visual failure.

[v62 Mac results](v62/RESULTS.md): frozen source, native parent v59, partial qualification. Actual eight-attempt FSM/manager regression changes sampled-time rebasing from1.259307862s to0; all available Mac native/recorded warm/PVA/controller/backend tests pass. Full corner/physics/tail/30 Hz remain pending. [v63 Mac results](v63/RESULTS.md): frozen two-file optimizer failure propagation, parent v62; actual optimizer/LBFGS fixture reduces failed searches3 to1 in both height modes, retaining outcomes and successful repair. All available Mac/native/recorded safety suites pass; full qualification and physics remain pending. No planner deadline or stop change. v48 stays the reference.

### Newton Mac validation — 2026-10-04

Dr Sun authorized actual Newton testing on Mac. Native source stays frozen v63; v64–v68 are host launch/storage packages with original v59 physics/policy/backend and no planner/control/safety change. v64/v65/v66 fail before physics and remain recorded. Actual v67 trial01 and prepared-cache v68 attempt02 stop at31.614/46.506s through original heartbeat_stale fault flow. They measure16.815/18.606 successful wallHz, max494.716/836.683ms and13.197/22.742m path. An additional cold v68 attempt fails its first sensor-period check. None completes90s or reaches post70s; no30Hz/tail/full-route acceptance or GPU-equivalent speedup is claimed. Source/install/host gates and state copyback pass; native/controller/goal/yaw/stop rules are unchanged. Temporary native build bytes were removed, raw archives remain outside repo with hashes/locators. [Full Mac report and plots](../audits/2026-10-04_mac_newton/REPORT.md). v48 stays the runnable reference.

| v69 | Display-only Mac recorded-state port of frozen v51 streaming renderer with v61 close camera | Latest physical v68 trial review MP4,1,616 causal frames/full decode/visual QA pass; FAILED heartbeat stop retained; no physics or planner changes. See [results](v69/RESULTS.md) |

| v70 | Observation-only backend callback/applied-read/JSON/GC timing trace, parent v68 with exact native v63 | 89.962s diagnostic, no heartbeat fault;23.423Hz and1316.856ms max still fail30Hz/tail; historical backend dispatch/delivery delay mechanism reproduced at original gate, exact old scheduler cause unproven. See [results](v70/RESULTS.md) |
| v71 | Pinned upstream ROS2 planning core with existing identity/cancel transport and round observation | Six-package build and actual transport smoke pass; frozen physical launch fails on inherited floor-publisher environment key before navigation. See [results](v71/RESULTS.md) |
| v72 | Correct only the inherited floor-publisher environment key, keeping exact v71 native installation | Actual Newton ends15.623s:64 unsuccessful upstream attempts,0moving plans,49.543ms max, FAILED initial_heartbeat_missing. Later corner and90s/30Hz acceptance untested. See [results](v72/RESULTS.md) |
| v73 | Display-only review of actual v72 upstream failure, reusing v51 causal renderer and Mac port |4.5s MP4/135 causal frames/full decode/visual QA pass; stationary robot and failed status retained,0physics steps. See [video receipt](v73/REVIEW_VIDEO.json) |

| v74 | Explicit corner-start fixture from the measured approach to the v70 late landing, exact native v63/runtime v59 | 39.990s Mac recording,19.65m,16.990Hz,max720.812ms; no arrival/30Hz. Frozen source/compact results survive, original temporary raw unavailable following interruption. See [results](v74/RESULTS.md) |
| v75 | Select exact v71 upstream core in the v74 corner condition | Build/transport pass; physical attempts fail receive/ACK/copyback. Frozen failures retained, raw unavailable following interruption; no completed navigation/video claim. See [results](v75/RESULTS.md) |
| v76 | Repeat v74 with durable raw archival before recorded-state rendering | Current planner crosses corner,20.04m,14.700Hz,max1307.535ms later on stairs; corner maximum397.826ms. Actual32.733s MP4,982 causal frames/decode/visual QA and remote raw hashes pass. See [results](v76/RESULTS.md) |
| v77 | Exact upstream probe in identical corner fixture, retain/archive/render incomplete failures | 10/1226 successful chains,1.13m then stall,0.323Hz,max311.138ms,at most3 initialization attempts; incomplete ACK/copyback failure. Actual30.700s partial MP4,921 causal frames/decode/visual QA and remote raw hashes pass. See [results](v77/RESULTS.md) |
| v78 | Observation-only native map replay and stage/operation profiling, parentv76/nativev63 | Two-package map build and three runs per arm pass;188scans/run, six final buffer/history hashes identical. Seven relevant scans fuse926,950voxels and visit25,175,190inflation neighbors; idle batch266.600–312.992ms does not fully reproduce original976.721ms. No production/physics/30Hz claim. See [results](v78/RESULTS.md) |

[Corner-start comparison](../audits/2026-10-04_corner_start/REPORT.md): the
current 11-attempt corner round takes41.318ms; its later1.308s spike is dominated
by repeated input/cloud/map work. The upstream arm's shorter maximum occurs on
a failed/stationary trajectory and is not a causal speedup. v48 remains the
reference; v49 stays frozen/excluded. Bulk data is SHA-verified under
gpu5070ti:/home/sun/vla_artifacts/2026-10-04_corner_start; remote access is storage only.

### Corner-start review video storage

Local-only `output/2026-09-27_lite3_versions/v76_mac_trial01_attempt01_review.mp4`
is 3,445,706 bytes, SHA-256
`25d638aa3f556f9a3297e0a2d35d26dfce0015c257a855665b1cd19d5f9c907a`.
Its verified remote copy is
gpu5070ti:/home/sun/vla_artifacts/2026-10-04_corner_start/v76_mac_trial01_attempt01_review/newton_stair_recorded.mp4.
The upstream partial video
`output/2026-09-27_lite3_versions/v77_mac_trial01_attempt02_review.mp4`
is 941,069 bytes, SHA-256
`ca83ed2a4303d3dd40ac88a5898b35ca590203baccaeda60b6e1852b74b58382`.
Its verified remote copy is
gpu5070ti:/home/sun/vla_artifacts/2026-10-04_corner_start/v77_mac_trial01_attempt02_review/newton_stair_recorded.mp4.
[Current receipt](v76/REVIEW_VIDEO.json) and [upstream receipt](v77/REVIEW_VIDEO.json)
bind physical/display source, full decode, causal frames and visual review.

Retrieve the associated physical directory from the same remote parent with
rsync and verify every `storage_manifest.json` SHA/size. Regenerate with the
corresponding frozen `versions/v76` or `versions/v77` `run_review.py` and
`render_capture.py`, the saved display contract and original renderer runtime.
Restore the contract's source paths or prepare a new path-bound contract with
the identical input/member hashes. Set `V76_RENDER_ROOT`/`V76_DISPLAY_CONTRACT`
(or the v77 names), choose a new unique display run and pass `--retention archive`;
the recorded review `request.json` supplies the exact supervisor command. Do
not rerun physics or overwrite the existing video. Full decode, timeline and
visual checks apply again. Bulk data is remote; temporary local data was removed
only after all current identities verified, with a [cleanup receipt](../audits/2026-10-04_corner_start/local_cleanup.json).

### Compact polling and versioned mapping — 2026-10-05

| v79 | Compact `/state` summaries and once-per-plan full evidence, parent v76/backend v59 | 23 HTTP/backend checks and actual ROS callback load test pass; original heartbeat/stop logic unchanged. |
| v80 | Equivalent semantic membership/inflation addressing, parent v79/native v63 | Eight-package build; every scan in three 188-scan paired runs and 14 sliding cases match. |
| v81 | Single-writer immutable map snapshots and publication lease, parent v80 | Snapshot and original safety suites pass; component-only qualification. |
| v82 | Guarded fixed-point duplicate backlog reduction, parent v81 | All builds/components pass; two actual 89.962s Mac trials preserve heartbeat but FAIL continuity/30Hz: 11.114/10.959Hz,491.143/312.939ms max,23.787/31.283s pauses. Frozen failed attempt; v48 stays reference. |
| v83 | Display-only review of failed v82 trial01 | 2,707-frame recorded-state MP4/full decode/visual QA pass; actual failed v82 status retained; no physics or planner change. |

[Repair report](../audits/2026-10-05_safe_mapping_repair/REPORT.md) records the
failed mapper freshness handover, all qualified/failed evidence and remote
storage locators. Do not promote reduced solve maxima into navigation acceptance.

The local review is `output/2026-09-27_lite3_versions/v82_mac_trial01_attempt01_review.mp4`
(5,371,631 bytes), SHA-256
`7ee56707550b30e171500ff8c4c494c2b807784921dfcb752408af1a5ee12179`.
Its verified remote copy is
gpu5070ti:/home/sun/vla_artifacts/2026-10-05_safe_mapping_repair/v82_mac_trial01_attempt01_review/newton_stair_recorded.mp4.
[The video receipt](v83/REVIEW_VIDEO.json) binds the physical v82 source, display-only
v83 renderer, full decode, visual review and regeneration. Review this as a
failed continuity candidate; no new navigation version has been accepted.

### Mapping admission and separated-lane investigation — 2026-10-08

| Version | One change | Evidence status |
|---|---|---|
| v84 | Native same-input FIFO versus timer/latest-slot admission replay, using exact v82 map | Six 188-scan arms and a native transient negative complete. Under two injected 650 ms stalls, latest drops 12 scans and loses 173 original occupied cells; timer drops 16 and loses 252. Full FIFO stays byte-identical. Plain latest-only is rejected. See [results](v84/RESULTS.md). |
| v85 | Three-thread mapping, sensor body-veto and execution-decision prototype | 26 contract checks pass; all 188 frames and original final map retained. Each 650 ms mapper stall still receives six sensor callbacks and nineteen execution decisions, with zero checked stale-map allowances. Component only: no actual command publisher, moving-trajectory/braking qualification or physics run. See [results](v85/RESULTS.md). |

[Combined report](../audits/2026-10-08_mapping_admission/REPORT.md) distinguishes
completion-time age from the age of the map held during a stall. The latter
still reaches about 0.86 s with newest-only admission. The existing 250 ms gate
is unchanged. v48 remains the reference; v82 remains failed; v85 is not a
replacement navigation runtime. The interrupted first temporary environment
and durable replacement attempt are recorded separately.

### Foxy SCAN plugins and Nav2 observation window — 2026-10-08

| Version | Change | Evidence boundary |
| --- | --- | --- |
| v86 | Actual Foxy controller/goal plugins, owned native SCAN executor, tagged server output and causal stop/goal contract | ARM64 build, 18 GoogleTest cases including 300-sample tracking parity, real ControllerServer protocol checks and packaged launch. Protocol inputs include synthetic planning/TF/stop proof; no complete route or robot acceptance. [Results](v86/RESULTS.md). |
| v87 | Nav2-style temporal observation buffering and periodic native 3D map updates | 37 actual-buffer comparisons/checks, six transient cases and two three-arm 188-scan replays. Selected 0.5 s window discards 2 scans and loses 23 originally occupied cells; stale intervals remain. [Results](v87/RESULTS.md). |

[Chinese delivery report](../audits/2026-10-08_nav2_foxy_plugin/REPORT.zh.md).
The runnable reference remains v48. Neither plugin loading nor bounded buffering
is navigation acceptance; PCT/BT client, full Newton route and Jetson/robot
integration retain separate gates.


### Full Nav2 Foxy integration — 2026-10-08

| Version | Change | Direct evidence / remaining limit |
| --- | --- | --- |
| v88 | Actual stock Nav2 flat kinematic goal/cancel control | Passed; not Newton or robot motion. |
| v89 | PCT GlobalPlanner, shared native-map TerrainLayer, mission gateway and BT binding/stop nodes | Actual Foxy plugins, 21 GTest cases; full protocol with explicitly synthetic SCAN inputs. |
| v90 | Pinned native PCT ARM64/Python 3.8 build | Actual native optimized flat route; original heights preserved. |
| v91 | 20 Hz mapper scheduling; normal and fault controls; native launch replay | All 188 normal frames retained, final map parity; max sampled age about 100 ms. Injected 650 ms stalls remain stale. |
| v92 | Legacy HTTP input, real frame/topic launch options and source export | Native-PCT goal/cancel/input-contract fixture passes; first original physics startup fails on old ZeroMQ architecture. |
| v93 | ARM64 ZeroMQ and measured body TF | Five actual ROS TF checks pass; original terrain helper fails on NumPy 1.17. |
| v94 | Isolated NumPy 1.24.4 | Three original terrain payloads and native PCT route identical; physics stops on first sensor JIT compile. |
| v95 | Sensor compile before timed sensing | Repeat ray outputs match and physics unchanged; default Foxy action ack timeout aborts goal. |
| v96 | Explicit bounded BT action acknowledgment timeout | Full gateway fixture passes; physics exposes early-stop acknowledgment and body-time failures. |
| v97 | Repeated cancel acknowledgment before first spline | Regression fails before repair, passes after; actual physics stop releases owner; body timestamp rounding error isolated. |
| v98 | Canonical ROS timestamps and integer Python command age | 23 controller + 1 tracking GTests; exact time/future/stale checks and full protocol pass. Physics has no pose-rounding failures but no motion; native startup rejection and later transport timeout/copyback mismatch remain. |
| v99 | Source export limits colcon discovery to ROS src | Same navigation code as v98; clean source build recorded separately. |

[Full implementation and failed-physics report](../audits/2026-10-08_nav2_full/REPORT.zh.md).
The selected reference remains v48. No full-route, steady 30 Hz, Jetson receive-only
or real-robot acceptance. All failed attempts remain evidence, not overwritten
versions. Dr Sun will provide Jetson access later.

### Original-scene Nav2 repair — 2026-10-08

| Version | Change | Direct evidence / remaining limit |
| --- | --- | --- |
| v100 | Independent Foxy clock lane; all native data work remains serialized | Actual clock-control and recorded-map regressions pass. Original physics moves0.466m but fails on residual future-body admission. |
| v101 | Admit original body messages only when their actual clock is due | Before/after actual map/FSM regression and14-package build pass. Original physics moves0.583m but fails; replanning state incorrectly revokes a safe old curve. |
| v102 | Renew a checked old curve while native replanning continues | Actual state-only regression passes. Physics still fails: real map freshness rejection and a compute/publish trajectory replacement race. |
| v103 | Discard superseded output tickets without cancelling the route | Actual plugin regression passes. No physics launch: repeated lifecycle test hangs; isolated earlier SIGSEGV retained. |
| v104 | Stop/join owned Foxy executors even when cancel precedes spin entry | Actual single/multithread regression,26 GTests, three24-test suite repetitions and full mission protocol pass. Physics attempt01 refused before execution because the launcher expected the old all-packages-build key. |
| v105 | Accept explicitly qualified14-package underlay/overlay runtime in launcher | Native bytes identical to v104. Physics incomplete on100ms ACK timeout; last acknowledged89 but committed90; copyback correctly refused. |
| v106 | Linux-local applied audit; explicit version-owned client and timings |690 ACKs, maximum3.263ms, verified copyback. Physics still fails progress after0.512m net XY; no complete route. |
| v107 | Activate exact fresh spline/proof pairs together |30 GTests and protocol pass. Physics fails combined evidence-age guard after0.632m XY. |
| v108 | Failure-only proof/observation timestamp diagnostics |33 colcon entries pass; actual failure isolates observation-age expiry at250–260ms. |
| v109 |100Hz mapper scheduling cap with unchanged native bytes |20-cloud/105-body replay map arrays equal and sampled age249→192ms. Physics still fails after1.400m XY. |
| v110 | Publish the existing final whole-curve validation with its exact spline |Native proof/time/identity tests pass. Actual14.347m path and1.383m elevation gain; goal fails on later map/proof age limits. |
| v111 | Display-only review of recorded v110 physics |914 frames fully decode; first/middle/final frames reviewed. Failed final state remains visible; no physics rerun. |
| v112 | Intrinsic native map profiling on268 moving clouds |17.286s CPU/17.288s wall; single cloud165.319ms excluding startup; no production change. |

See [ongoing causal diagnosis](../audits/2026-10-08_nav2_sim_repair/DIAGNOSIS.md).
The original scene, goal, policy and100/250ms age limits are preserved. No full
route or Jetson acceptance; v48 remains the selected reference.

- v113: Equivalent native inflation columns; all268 moving and14 sliding hashes unchanged. Original Newton ran22.835m but FAILED before final goal; [result](v113/RESULTS.md). v48 remains selected.

- v114: Controller-owned native full remaining-curve check; original scene arrives and stops once, with two protected retries. [Result](v114/RESULTS.md); repeated-run/30Hz acceptance remains open.
- v115: Actual v114 recorded-state video;54.833s/1645frames, full decode and visual QA pass; no new physics. [Provenance](v115/results/delivery.json).

- v116: Namespaced native curve recording only, exact v114 planner. Attempt01 transport/copyback failure; attempt02 complete recording but failed navigation.
- v117–v118: Causal controller-admitted curve video; v118 makes the cyan curve visible at unchanged sample positions.
- v119: Offline video/timing HTML with900 actual rounds and causal click-to-seek. [Report](../audits/2026-10-09_local_curve_timing/REPORT.md). Main navigation acceptance unchanged.

- v120: Restore the unobstructed close-follow camera; retain thick cyan actual native curves. Final checked video.
- v121: Final offline HTML binds v120 video and unchanged verified causal seeking/900 timing rounds. [Delivery](v121/results/delivery.json).

- v122: Typed planning failure diagnostics; original decision-token parity,
  native branches and bounded logging overhead tested. First Mac smoke failed
  navigation; compact analysis remains, temporary raw root is unavailable.
- v123: gpu5070ti x86_64 Foxy host port; both v114/v122 native builds and 36 tests
  per variant passed. First launch stopped before physics on output ownership.
- v124: Host-owned output parents; real factory startup reached the measured
  stand, then native ROS logging initialization failed before navigation.
- v125: Pre-created ROS log directories, host-user native outputs and verified
  Linux writer inspection. Both same-host physical trials reached the goal and
  measured PD hold. Step 1 is retained after full diagnostic coverage and exact
  fixed-input curve parity. [Report](../audits/2026-10-09_mppi_incremental/REPORT.md).
  The navigation reference remains v48; steps 2–5 remain pending.

| v126 | One reference-path recovery chain per round; remove two legacy outer initialization retries | Components pass (36 plugin tests, 12 actual-flow fixture cases, real-map identical curve/stale rejection); **parked**: same-host v122 arrives, v126 aborts after progress/stale-evidence/missing-trajectory failures. Max136.189->442.960ms; retain v122 / host v125. See [report](../audits/2026-10-10_mppi_step2/REPORT.md) |

| v127 | Extract independent native PVA/dynamic/collision/epoch validation interface from retained v122; full retries preserved | **Parked**. Original component/first-pair [report](../audits/2026-10-10_mppi_step3/REPORT.md). Follow-up six fresh runs per arm: v122 arrives0/6 (one fall), v127 arrives1/6; 28,720 captured curve /11,691 epoch /9 reconstructed-map verdicts agree. Original instability established; live timing equivalence unproved. Retain v122 / hostv125; [repeat diagnosis](../audits/2026-10-10_mppi_step3_repeats/REPORT.md) |

| Version | Change | Evidence and boundary |
| --- | --- | --- |
| v128 | Expose negative safety failure on the next controller tick; native parent v114 |14packages/38tests. Pilot arrived; closed6perarm comparison v1142/6, v1282/6. Notification fixed, full recovery unaccepted. |
| v129 | Allow10s for measured stop and11s for BT transport; proof criteria unchanged | Captured stream needs5.28s: old4s fails, new passes. Missing proof still fails. Pilot arrived; no full acceptance. |
| v130 | Use current due measured body for new-route search; preserve local PVA and future queue | Actual native origin probe0/4->4/4; unknown map still rejected. Pilot arrived with2recoveries; no full acceptance. |
| v131 | Bound mission recoveries at6; record existing stop proofs read-only for both arms | Actual BT eventual-success, exhaustion and missing-proof tests pass. Frozen2935sourcepairs/618inputs; final comparison1/6arrivals with1fall versus original2/6. Not adopted. |

| v132 | Record exact new-reference rejection reason and timing; no decision change |14packages/38tests and6recorded-map parity cases pass. First diagnostic captures body/map expiry during search;23.492m failure, no fall. Not a repair. |

| v133 | Read original arrived/due inputs after unsuccessful goal search before fallback queries | Controlled native due-body regression passes; missing/future data still fail.14packages/38tests; frozen3004sourcepairs/618inputs. Three diagnostic pilots2/3arrivals, nofalls; pilot gate failed, no acceptance. |

All recovery versions exclude MPPI adaptations. Original failures are preserved.
[Recovery evidence](../audits/2026-10-10_nav2_recovery/REPORT.md).

| v134 | Negative static support coverage from the original Building; no live mesh input | Actual255-scan query changes old permit to new reject;14packages/38tests. Three pilots0/3arrivals, no falls: global reference remains incompatible. Not adopted alone. |
| v135 | Couple global PCT costs to the same nativev134 support veto; separate map identity | Elevations/support payloads unchanged. New route0/2412vetoed footprint queries vs old100/2290. Three pilots2/3arrivals, nofalls; delayed recovery dispatch exhausts the failed trial's attempts. No acceptance. |
| v136 | Service queued cancellations/routes at FSM work boundaries; defer replacement during emergency exit | Preparing actual DDS/native regressions and repeated physical validation; no acceptance. |

[Support-gap diagnosis and repair evidence](../audits/2026-10-10_v133_posture/REPORT.md).

2026-10-10 continuation: v137 transient-input admission wait is frozen and
component checked; physical pilots 2/3 arrivals, no falls, not accepted. v138
adds the global static support body envelope to local queries (additive veto);
frozen/component checked, 3 fixed pilots running. See the posture audit REPORT.

v138 outcome: all three fixed pilots fail at start; rejected. v139 returns to
v137 and adds full-curve collision feedback through final refinement. Build01
failed the captured case; build02 passes the identical recorded-input regression
and component/graph gates. Frozen, three physical pilots running; no adoption.

Final v139 checkpoint (2026-10-10): 3/3 fixed pilots pass; six fresh candidate
trials pass6/6against parentv1375/6, neither arm falls; all11candidate replacement
proofs pass. Thirty new raw trials and all six frozen source/native identities
are reverified;569compact files returned and hash-checked locally. The declared
Building scenario gate is validated; maximum candidate round706.406ms keeps
30Hz/general navigation/Jetson acceptance open. See the posture audit RESULT.md
and SCENARIO_ACCEPTANCE.json. Broader reference and MPPI adoption remain unchanged.

v140 (2026-10-10): display-only Linux/EGL port of v120 for the passed v139
candidate_attempt08. Full54.867s/1646frames, cyan controller-admitted local
curves visible on1349frames, three protected replacements, final arrived state.
Zero replay physics steps; complete decode, causal indices, visual review and
returned regular-file hash pass. Delivered MP4 is6,555,740bytes. Source freezes
3,229pairs; v139 navigation and broader acceptance stay unchanged.

v141: Dr Sun requested video from the beginning. Include original startup
(native0.08s first captured pose) sampled by recorded simulation time, then
unchanged1:1wall-time navigation.1975frames/65.833s,137startup source states,
no invented wall stamps or new physics. Close camera from first frame; full
decode, clock/source/curve checks and start/mid/end visual QA pass. Actual
7,159,239-byte video returned atv141/delivered/v139_from_start.mp4. v140 preserved.


v142 / v143 (2026-10-11): Dr Sun requires actual native0.0s, which the old
v141 recording beginning0.08s cannot provide. v142 reads the actual unstepped
body/joint state before calling the unchanged factory initializer, checks native
clock0.0/steps0 and identical before/after state hashes. New gpu5070ti candidate
attempt01 arrives, no fall, applied-state copyback verified; nativev139 build02
and all navigation/physics/configuration remain unchanged. Frozen3276sourcepairs
and618runtime inputs;290closed physical files177,397,522bytes plus454archive
members reverified before rendering. This run is separate from prior6/6acceptance.

v143 renders the new actual-zero recording with138startup source states,332
startup display frames and1340wall-time navigation frames. Full1672-frame/
55.733s MP4 starts native0.000s;1069frames display admitted cyan local curves.
Full decode, all causal indices, startup/navigation clock separation and
start/mid/end visual QA pass.28allowlisted files7,201,696bytes returned/hash
checked, including the regular6,611,967-byte [MP4](v143/delivered/v139_true_zero.mp4).
Earlier videos and broader reference/MPPI/Jetson/30Hz gates remain unchanged.


v144-v148 original spatial full-route correction (2026-10-12): earlier
zero-timev142/v143corner video did not satisfy Dr Sun's clarified request.
v144runs pinnedhistorical_fullfrom original lower-floor spawn; FAILEDafter
23.126m, nofall/copyback pass. v145retains its61.633sfailed video.
v146ordered435-scan/reference/body native replay isolates a supported-turn
window: original3prefix proposals reject,6produce a1.24ssafe translation under
original PVA/dynamics/126full-curve samples; identical native map digest.
v147changes only the bounded prefix budget3->6, normal first-success behavior
and all safety gates retained.14packages/38native tests and host/graph/route
checks pass; frozen3357pairs/618inputs. One new original-start trial arrives
after76.883m/118.207native seconds, nofall, measured hold/copyback and both
replacement proofs pass. v148full117.967s/3539-frame original-route video
decode/causal/visual checks pass; returned regular15,122,573-byte
[MP4](v148/delivered/original_full_route.mp4).
Original failures remain; no repeated full-route reliability,30Hz/Jetson or
reference/MPPI promotion. See [full-route report](../audits/2026-10-12_original_full_route/REPORT.md).


### v147 original-route repeats, 2026-10-12

Unchanged v147 has 0/3 closed arrivals before reboot, a separate raw arrival with
interrupted copyback/retention, and 1/2 closed arrivals after reboot. Resource
admission paused the second cohort with four trials unstarted. All failures
and the interrupted capture remain retained. Five closed raw captures and all
returned compact files verify; full-route repeatability is not accepted. No new
version or reference promotion. See
[repeat report](../audits/2026-10-12_original_full_route_repeats/REPORT.md) and
[host incident report](../audits/2026-10-12_gpu5070ti_freeze/REPORT.md).


### v149 Mac host adaptation of native v147 (preparing, 2026-10-12)

User-authorized same-map/original-start local reproduction before recovery repair
and later Linux repeats. Native v147 source/configuration and CPU physics remain
unchanged; v149 changes host launch, ARM64 build receipts and temporary paths.
All618runtime inputs and seven package versions match the Linux reference;
10host/route/zero-state tests pass. Native build and real graph qualification
are still in progress. No physical-run or repair claim. See [plan](v149/PLAN.md).


### v149-v151 local recovery investigation, 2026-10-12

v149Mac host is frozen (3396source pairs/618inputs); nativev147unchanged,
14packages/38native tests/10host tests/real graph smoke pass. Attempts01/03are
retained sensor/ACK infrastructure failures;02is an actual28.406m navigation
failure, no fall, verified copyback/retention. No local full-route pass yet.

v150frozen recorded-input diagnostic (3402pairs) reproduces the latest Linux
curve2366clear-to-blocked change. Body counterfactual isolates the remaining-
interval sample grid as the reason a narrow support-clearance region was missed.
Published935versus mapped931startup discrepancy stays disclosed.

v151frozen native candidate (3438pairs) retains every original curve sample and
adds four interior samples per interval. The original bad curve is now rejected
before motion; negative cases remain negative. Seven exact-superset cases,
invalid/budget controls,38native tests,10host tests and graph smoke pass. First
Mac full-route candidate failed after33.803m, no fall, verified copyback. The
second trial was interrupted by the applied-state ACK deadline while moving;
copyback mismatch is retained as an infrastructure failure. No recovery/general-reliability/30Hz
acceptance or MPPI2–5promotion. Plans and actual evidence live in each version.

Correction to v150/v151 diagnostic wording: verdict6 is UnknownObstacle, not a
support-height failure. v151 also increases warm-seed sampling because the
manager uses the validator sample count; this coupling is under investigation.
v152 adds a recorded cold replacement probe against both native installations.


### v152-v157 local recovery continuation, 2026-10-12

v152cold original-failure replan finds valid alternate curves under the original
PVA/dynamic gates; diagnostic only. v153bounded idempotent applied-state transport
passes18Mac/8Foxytests but its first launch fails metadata admission before physics.
v154repairs that metadata, restores same nativev151from local frozen source after
the old temporary workspace disappeared, and revalidates14packages/38tests,
19host tests/real graph. Old Mac raw cohort unavailable; seev154RESULTS.md.
New environment archive34789375bytes and firstv154trial316231680bytes both verified
on5070ti. Trial fails36.197m/no fall after a23.387s stationary corner. It has
verified copyback and no transport timeout/retry. No local full-route arrival.

v156frozen actual-map diagnosis: current yaw clear, intended outgoing yaw blocked
by unchanged static ground-gap veto. Eight grid directions and eight knight
edges fail;65direction checks find8/5/5/0legal5/10/20/30cm segments. The ground-
inflation hypothesis is rejected. v157prepares one body-aligned lattice retry
only for an isolated start, within the original200ms search budget and unchanged
world-space safety predicates. Native build is underway; not frozen/accepted.
v155is an unbuilt warm-seed-density draft, not selected.


### v159-v161 recovery and full-route verification, 2026-10-12

v159freezes due-time body selection: actual old/new plugin regression, original
100ms freshness. Its only Mac run reaches the goal neighborhood but fails yaw
drift after irreversible hold; preserveFAILED. v160uses half-tolerance yaw
capture and tracker deadband while retaining final0.25rad acceptance and1s
causal stop proof. Local trials01FAILED35.235m;02FINISHED77.571m(sensor path),
5qualified replacement handoffs, finalPDhold, nofalls.1/2is not reliability.
All new raw/environment archives on5070tiare verified. v161is the LinuxAMD64
execution port with native646-file equality to v160; repeated runs pending.
Seev159/RESULTS.md, v160/RESULTS.md andv161/PLAN.md.


### v162 Linux repeat failure and v163 Nav2 reference reuse

v162fixes the Linuxhost guard missed byv161; nativev161still equalsMacv160.
Fiveclosedphysicalruns yield1/5arrivals,0falls, all14replacementproofs qualify.
Slot02preflightfails beforephysics and is retained. Seev162/RESULTS.md.
v163Macnativeparentv160adds explicit BT reference cache/restore and same-owner
measured-stop binding guards afterPCTno_route. Originalmap/start/safetygates
unchanged. Component/actualgraphchecks pass; frozen3695pairs; physicaltrial
pending. Do not promote this candidate based on component tests.


### v164 local recovery and v165 Linux repetition

v163's first local run fails on a stopped stair at27m; cached-reference branch
not triggered. v164 expands bounded steering directions while checking the full
turn sweep. Two actual native recorded-map regressions pass. Its first local
original-route trial arrives with six qualified replacement handoffs and final
PD hold. One short steering curve produces tagged commands; widened-offset
physical coverage is not established by that near-boundary event. v165 rebuilds
exactly the same647native sourcefiles on Linux and starts five serial original-
route repetitions. See v163/RESULTS.md, v164/RESULTS.md and v165/PLAN.md.


### v166 port isolation; v167 short reverse candidate

v165 full five attempts accepted0/5: four navigation failures, one startup bind
failure after physics initialization. Failed evidence remains remote and compact
analysis is returned. v166 uses nativev165 unchanged, isolates serviceports from
Linux automatic-client range and passes18hosttests/15sactualgraph; frozen3831pairs.
A replay ofv165/01 proves a5cm backward curve at measured heading is clear while
turning to drive forward crosses the support-gap mask. Parent controller's actual
regression returns vx0 and yawrate1. v167 adds explicit short reverse intent and
rebuilds all message consumers. Candidate, NOT physical acceptance yet.


### Local reproduction and full-route recovery repair, v166–v175

v165 accepted0/5 attempts. v166 isolates Linux service ports. v167 adds explicit
short reverse intent after the recorded turn-sweep deadlock; native map/controller
tests pass, but its first Mac episode is interrupted by an ACK delay. v169 handles
that bounded Mac transport delay, then fails near the goal after the cumulative
six-recovery limit. v170 adds measured spatial-progress renewal, with the original
stop and safety gates. Its Mac arrival does not cover that branch because of a
base/base_link mismatch. v172 propagates the configured frame into generated BT
XML; renewal runs, but the PCT process aborts on a singleton path near the goal.

v174 rejects degenerate PCT optimization and resets A* request state even after
empty/failed searches. Actual old/new native worker regressions cover the crash
and subsequent full-route request. Its Mac original-start episode arrives with
four measured-stop handoffs and four live budget renewals. The complete raw run
and native environments are remotely archived and verified. v175 rebuilds exactly
649 native source files on Linux;55colcon entries, native PCT lifecycle,18host,
9gateway,2profile and actual graph/library checks pass. Frozen4029source pairs.
Five serial original-route Linux repetitions closed with2/5arrivals and3failures;
v175 is not adopted. Unused intermediate Linux ports v168/v171/v173 remain unadopted. See the
per-version RESULTS files; failed attempts are retained and are not pooled.

v176 isolates one configuration change: local spline finish distance15cm→2cm.
The actual native tracker reproduces oldzero at4.9246cm recorded error and emits
an inward correction with the candidate;1cmerror stillstops.55inheritedcolcon,
19hostchecks,2profilecases,actualgraph/library checks pass. Frozen4027sourcepairs;
the actual running ControllerServer readsback0.02. Mac original-route attempt01
qualified77.659m with6measured-stop handoffs; all295rawfiles and nativeenvironment
are remotely verified. v177 ports the one profilechange toLinuxv175 binaryunderlay;
all649native sources equalMacv176. The Linux graph/hostpreflight passed; the completed cohort is summarized below. This is not a full recovery qualification or a fix claim for the two
separate v175 post-revocation drift failures.

v177 closed5/5original-route Linux repetitions with30qualified measured-stop
handoffs and0falls. Distances76.846/76.946/77.097/76.871/76.910m; all55compact
returnfiles individuallySHAverified. This qualifies the declared original-map
completion/recovery condition only. Longest low-speed pause10.694s and planning
peaks up to497.846ms remain; no smoothness,30Hz,othermap orJetson qualification.
See`v177/RESULTS.md` and`v177/results/cohort_summary.json`. The oldv175threefailures
are retained; already-occupied stopped-pose replays still fail closed.

v178 is a display-only full review ofv177attempt01. The local regular video
`v178/delivered/v177_full_route_attempt01.mp4` is19986833bytes,162.366667s,
4871frames, SHA256`2315e907b8e3c28e72733d69bfce64737b32b63e0a24594e641af8c333877854`.
Remote master:`/data/sun/vla_mppi_20261009/video_v178/runs/full01/newton_stair_recorded.mp4`.
Only that exact local MP4 is ignored; compact provenance is in
`v178/delivery_return.json` and`v178/returned/`. To regenerate, use the pinned
v178display sources plus retained`video_v178/display_contract.json` in a fresh
owned render root, constructing the unchanged CPU model and replaying original
poses without physics steps. Sourceframe0, all pauses, controller-admitted cyan
local curves, orange global route and causally available solve times are kept.
Full decoding,4871causal indices and beginning/middle/end/active-curve visual
inspection passed. This video is separate from the five physical repetitions.

## v177 stop-cause audit, 2026-10-12 (no new navigation version)

Read-only analysis matches35native revocations:30intermediate retries and5final stops.
20events have expired map source data,3fresh-input geometric rejections,3progress
timeouts and4first-curve timeouts.13upstream repositories inspected. Run01remains
in STAND_SETTLING and moves0.956651mwith effective zero command during the audited
recovery span;5/5arrival therefore does not validate stopped-pose retention.
See [per-stop report](../audits/2026-10-12_v177_stop_causes/REPORT.zh.md) and
[interactive ledger](../audits/2026-10-12_v177_stop_causes/stops.html). Frozen
v177source/runtime verification remains4079/618pass. No navigation change or
new physics run; holding repair and internal map-delay attribution remain open.

## v179–v183 policy stopping and speed correction, 2026-10-13

v179 executes twelve policy-only Mac Newton trials, six flat and six in the
original stair scene, with two 10 s stops each. Its 0.2/0.35/0.5 m/s commands
are below the existing 0.6 m/s planned-cruise rule and must remain **low-speed
controls**, not general model-stopping qualification. v180 is retained as failed
Retina-caption visual QA; v181 corrects display only and preserves all twelve
low-speed clips plus both complete six-trial videos.

v182 changes only walking amplitudes to 0.6/0.8/1.0 m/s with matched durations
and unchanged current model/startup/physics/gains. All twelve trials and twenty-four
stops completed. Flat late excursion over the descriptive 5 cm flag changes
from 4/12 to 0/12; maximum 31.15 to 3.67 cm. Stair-scene flags change from 7/12
to 4/12; maximum 14.54 to 10.08 cm. Stair stopping locations differ with speed.
This qualifies neither a standing repair nor the original navigation hold path.
The training sampler's dynamic per-axis low-speed exclusion is distinct from
the project's planned-cruise floor. See [v182 results](v182/RESULTS.md).

v183 renders the exact higher-speed captures, with all twelve frame/source/hash
and decode checks passed. `v183/delivered/{flat,stairs}_all6.mp4` each retain all
six trials and last 221.5 s. Example files are regular MP4s. Low-speed video
counterparts remain in v181. [Delivery and regeneration](v183/DELIVERY.md),
`v181/DELIVERY.json`, `v183/DELIVERY.json` and `v183/delivery_inventory.json`
record hashes and storage. Raw v179 and v182 archives are member-verified under
`gpu5070ti:/data/sun/vla_mppi_20261009/policy_stop_v{179,182}_mac/archives/`.
Only exact delivered MP4 paths are ignored; source/results/provenance are retained.

## v184–v185 stateful local capture, 2026-10-13

v184 changes the local endpoint capture from 2 to 3 cm and latches completion
for an expired accepted curve. New curves reset it; mission/stopped proof and
the RL model remain unchanged. Source comparison covers six pinned projects;
see `.pipeline/survey/2026-10-13_terminal_capture_upstream_survey.md`.
The actual C++ regression preserves inward movement at the recorded 4.9246 cm
recovery error. Mac component/graph tests passed, but attempt01 was refused
before physics because frozen quality metadata omitted a required package count.
The failed launch and frozen version remain intact.

v185 ports the identical 649-file native source tree to gpu5070ti over v177
binaries. Independent component, graph and 18 host tests pass. Five serial
original-start full routes are in progress; endpoint-crawl acceptance is
separate from arrival and from zero-command physical drift. Do not promote this
preparation to a validated fix. See v185/PLAN.md and its append-only results.

v185 closeout: all five trials closed,3/5 arrivals; attempt02 also fails the
endpoint-tail criterion with2.219s. Preserve and reject this candidate. See
[v185 results](v185/RESULTS.md). The route failures followed zero-command holds
and missing-trajectory recovery, so exclusive causal attribution remains open.

v186 restores2cm capture and adds a1s/5mm measured-progress condition only
inside the final3cm of an expired local curve. The latch and safety/mission
boundaries remain. Native tests passed; independent loaded-graph checks and
five original-start Linux route repetitions are the next acceptance steps.

v186 closed with2/5 arrivals and a5.477s terminal crawl in attempt04; rejected.
The unchanged contemporaneous v17706–10 control arrived5/5, with maximum
terminal crawl0.7996s. Keep cohorts separate.

v187 returns to v177 normal2cm behavior with no local completion latch. After
curve expiry, a continuous correction inside5cm below0.1m/s is limited to1.5s,
then fails through exact-owner cancel/zero/PlannerException into the existing
Nav2 measured-stop recovery.40 native controller cases (43 colcon entries),
18 host checks, profile tests and actual runtime policy/library checks pass.
Five original-start full routes are in progress; no physical acceptance yet.

v187 closed with3/5 arrivals (01/03/05 arrived,02/04 failed) and the endpoint
criterion5/5 (maximum actual-input interval1.579132s). Attempt03 exercised the
new timeout branch and still arrived. The failed attempts had no timeout event;
they stopped on ordinary safety rejection/evidence expiry. Not accepted; see
[v187 results](v187/RESULTS.md).

v188 is an unchanged-source rebuild control, not a repair: all649 native source
files equal v177; controller text/dynstr/data.rel.ro sections are identical.
Five original-start routes arrived3/5 (01/04/05), endpoint criterion4/5. The
existing v177 binary cohort (06–10) arrived5/5. Some failures therefore occur
without any new endpoint logic; the cause of the variation is still unknown.
Do not pool cohorts. See [v188 results](v188/RESULTS.md).
