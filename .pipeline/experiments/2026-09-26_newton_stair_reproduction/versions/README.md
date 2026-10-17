# Local Newton navigation versions

Dr Sun designated the delivered empty-floor system as v3 on 2026-09-27 and requested one version per change. These version numbers describe this local simulation integration, separately from native SCAN candidate/build numbers.

## Current single-route physical baseline — v232 / v233

Adopted by Dr Sun on 2026-10-17: **v232 is the latest validated navigation
source; v233 is its execution/display binding.** The one authorized original
Building route passes the unchanged v219 spatial/terminal gates: FINISHED at
121.564819 s, measured final PD stand 4.397583 s, XY error 0.141198 m, no
SIGABRT or fall. The actual v232 native install, launch and long-route driver
are source-bound; RL, original endpoints and 0.35 m hard guards are unchanged.

Stair [45,55): 273/275 successful rounds (99.27%), no measured low-speed pause
lasting at least one second, and all 100 body-edge samples at the extra 0.15 m
score cap. **One successful route only:** no repeated reliability, sustained
30 Hz, feedback-induced detour, other-map/start, leg-contact or robot claim.
The original analyzer's `full_qualification=false` and
`sustained_30hz_validated=false` are preserved; mean successful planning is
25.44 Hz. This adoption changes mutable selection metadata, not frozen
manifests or the original acceptance rules.

[Physical results](v233/RESULTS.md),
[full audit and three-way videos](../audits/2026-10-17_v232_physical_comparison/RESULTS.md),
[local delivery hashes](../audits/2026-10-17_v232_physical_comparison/LOCAL_DELIVERY.json).
**v219/v220 remains the preserved comparison source/display pair** (one earlier
full-route pass); v231's failed v230 execution and all earlier failures remain
intact. Historical "current" statements below describe their checkpoint only.

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

v189 is frozen and component-qualified on Mac ARM64 over the archived v176
binary underlay (649 source entries match the v177/v188 baseline). It adds
0.5 m route lookahead at expired stopped local stubs, with zero translation.
All 46 GTest cases, two profile tests, both native probe markers, 23 Mac host
tests and the actual loaded-library/profile graph preflight passed. The quality
receipt includes the required 14-package count; v184 remains unchanged.

The authorized `v189_mac_full_attempt01` closed with Nav2 arrival and measured
PD hold at 187.681 simulated seconds, but **failed full-route acceptance**:
final held yaw error 0.377481 rad exceeds the unchanged 0.25 rad limit. Final
XY error is 0.138237 m; copyback passed and all 20 replacement owners have
recorded stop proofs. Preserve this single Mac result; no repeated reliability
or sustained 30 Hz acceptance is claimed. See [v189 results](v189/RESULTS.md)
and [the recorded rejection](v189/results/v189_mac_full_attempt01/full_route_verification.json).

v190 is a frozen display-only version (`parent: v189`, `display_parent: v178`)
that renders `v189_mac_full_attempt01` from its recorded `video_states.json`,
`raw_capture.zip`, and `latency.csv` on Mac ARM64 Cocoa with zero physics steps
(`6,708` frames at `30 fps`, `223.600 s`, `4,744` visible local curve frames).
Local review video: `versions/v190/delivered/v189_mac_full_attempt01.mp4`
(`17,515,391` bytes, SHA-256 `3ed8e52d98c3ffd16ce55cb5fe3ed19b2949fd02cb330c32d8063a7fbb7f51e9`,
remote copy `gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v189_20261013/v189_mac_full_attempt01_review.mp4`).
It preserves the failed full-route gate (`passed: false`, final held yaw error
`0.377481 rad > 0.25 rad`) and claims no navigation acceptance. See
[v190 visual QA](v190/VISUAL_QA.md) and [v190 delivery return](v190/delivery_return.json).


v191 is the **Option B direct Nav2 + SCAN** candidate, with **v190 as its
version parent** and the archived Mac ARM64 **v176 binary underlay**. It removes
the P2B messages, BindRoute service/BT node, gateway/control gate and inherited
backend/service packages from its source. Nav2 now supplies a standard Path to
the embedded SCAN worker; the controller consumes Bspline and publishes Twist
directly on `/quad_0/cmd_vel`. The source inventory has 272 files, 37 changed/new
paths and 33 deletions relative to its native underlay inventory.

The Mac qualification passed 45 colcon entries (including CTest wrappers),
22 controller-package GTests, eight plugin GTests, nine bridge pytest cases,
two generated-profile tests, both terminal/heading probe markers and 25 host
tests. The repaired graph launches a wait-only recovery server at `/wait` and
verifies the actual v191 controller/native libraries, embedded SCAN node,
direct topic types and all four active Nav2 lifecycle nodes. Preflight used a
labelled static identity TF fixture; no physics or navigation goal was run.
The 0.02 m capture and 0.5 m route-heading lookahead remain enabled.

The freeze records component/graph qualification only; **full navigation is
not accepted**. Option B's Wait delay does not retain the removed P2B
measured-stop/owner-admission protocol. v189, v190, `recovery_v176`, and
`recovery_v189` match their protected file/symlink baseline. See
[v191 plan](v191/PLAN.md), [quality](v191/quality.json),
[manifest](v191/manifest.json), and
[protected-path comparison](v191/verification/v191_protected_comparison.json).

## v192 shared-state Mac harness (2026-10-14)

v192 is frozen with v191 as its parent and native_version=v191. The native
overlay was reused without rebuilding. The harness removes synchronous applied
ZMQ ACKs and the tmpfs shadow; state and finish requests use the trial bind mount.
Its 24 host tests, actual loaded v191 libraries, four active Nav2 lifecycle nodes,
bidirectional mount probe and protected-path comparison passed. Driver observation
allows 10-second snapshot age and 15-second navigation-loop reads; command/native
freshness and terminal criteria are unchanged. Full-route outcome is separate.

See [plan](v192/PLAN.md), [quality](v192/quality.json),
[manifest](v192/manifest.json), and
[protected-path comparison](v192/verification/v192_protected_comparison.json).

Attempt01 ended FAILED/nav2_failed at 118.886 s physics after 72.572 m of the
original route. Shared-state closure passed; there was no arrival or final hold.
The log records seven trajectory timeouts and six completed Wait recoveries.
The 13 direct-command stops / 6.120 s zero-command exposure are not equivalent
to v189's 20 measured-stop proofs / 34.225 s wait, and the route is incomplete.
See [v192 results](v192/RESULTS.md). Dr Sun subsequently authorized the full failure-review video; it is delivered by v193 below.


## v193 full v192 display review (2026-10-14)

v193 is a frozen display-only version (`parent: v192`, `display_parent: v190`)
for Option B direct Nav2 + SCAN. It renders `v192_mac_full_attempt01` from
original physical frame 0 through factory PD startup and the final
118.88629150390625 s state, preserving the complete 72.57228851559466 m run.
The source still ends FAILED/nav2_failed: no arrival or full-route acceptance.

The [full MP4](v193/delivered/v192_mac_full_attempt01.mp4) is a regular local file:
1280 x 720, 30 fps, 3,857 frames, 128.566667 s, 12,804,690 bytes. Startup uses
recorded simulation timestamps and navigation uses recorded wall time at 1:1.
All 3,857 source indices, endpoint coverage, direct Bspline/Twist freshness,
PCT route causality, full decoding and ten decoded visual samples passed.
No physics steps were executed, and all protected versions/recovery folders
and original recording bytes remain unchanged. Ten overlay tests and four
timeline tests passed; freeze/verify passed for 4,622 source pairs.

SHA-256: `3e441643b5c42410bd21e73bbb2aad563ecde613fd7801fc4acdfe2a084956cd`.
The matching archive copy is
`gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v192_20261014/v192_mac_full_attempt01.mp4`.
See [plan](v193/PLAN.md), [visual QA](v193/VISUAL_QA.md),
[quality](v193/quality.json), [manifest](v193/manifest.json), and
[delivery provenance](v193/delivery_return.json). No next-step navigation fixes
were made in this display-review session.


## v194 spline watchdog and canonical goal qualification (2026-10-14)

v194 is frozen and component/graph-qualified, with `parent: v193`,
`navigation_parent: v192`, `native_version: v194`, and
`native_binary_underlay: v176`. It adds a bounded explicit spline-wait state,
clears the stale tracker terminal latch, retains the stock six-retry RecoveryNode
with integer `Wait=1`, locks each job's complete terminal Pose across PCT replans,
and coordinates the 0.125 rad inner yaw band with 0.25 rad external acceptance.
A controller-owned braking latch survives ControllerServer's same-goal
`GoalChecker::reset()`. Cached paths are retained for inspection; failed PCT
replans remain failures.

The fresh Mac ARM64/Foxy overlay rebuilt 11 packages with 14 available. All 45
colcon entries passed (22 unique controller-package GTests), as did 2 generated
profile tests, both native terminal probes and 24 host tests. The live graph
activated four lifecycle nodes, verified the loaded v194 libraries and shared
mount, and sent no navigation goal or physics steps. All eight protected trees
match the pre-edit recursive file/symlink inventory without exceptions. Freeze
and verify passed for 4,814 source/snapshot pairs and 618 runtime inputs.

The first test attempt and its fixture correction are retained with the final
passing evidence. The subsequently authorized `v194_mac_full_attempt01` ran once
and closed **FINISHED, route_arrived=true, full_route_verification.passed=true**.
Its original-start continuity, final PD hold, XYZ/yaw and shared-state checks
passed. This validates one declared Mac original route; repeated reliability,
sustained 30 Hz and general navigation acceptance remain open.

| Attempt 01 measurement | Exact measured result |
|---|---:|
| Sensor-sampled body path | 77.03407366997271 m |
| Final XY / reference-height / yaw error | 0.1211678512749522 m / 0.006756114959716786 m / 0.10415752320636183 rad |
| Recorded physics endpoint | 137.5282745361328 s |
| Navigation simulation / wall time | 126.50745105743408 / 126.54035995799859 s |
| Navigation RTF | 0.999739933562893 |
| Successful local planning / direct controller rate | 23.6762405369673 / 29.811494709748814 wall Hz |
| Emergency entries / exits / self-transitions | 9 / 9 / 10; frozen analyzer total 19 includes repeats |
| Completed stock Wait recoveries / spline-wait timeouts | 1 / 0 |
| Direct command stops / restarts / zero exposure | 17 / 16 / 9.422262201125704 wall s |

v189 arrived but failed final held yaw (0.3774812462295072 rad); v192 failed
before arrival (4.832351783345226 m final XY error). Their respective navigation
wall times were 212.74850833300025 and 117.58489762499994 s, RTF 0.8303702824160138
and 0.9173411739423418, and successful planning 17.946071772329205 and
26.066272641362957 Hz. v192's runtime covers an incomplete route, and v189's
20 P2B measured-stop proofs / 34.225421601 s waiting are a different protocol
from Option B's command-zero observations. These single trials do not establish
a causal speed or stop-reduction result. See the [full comparison](v194/results/v194_mac_full_attempt01/comparison.json).

The 445,890,560-byte raw TAR is archived under
`gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v194_20261014/` with SHA-256
`c09b9a3c42338ff11e7598d0a1a7e4fa8d4c64ba56a66027dceaad5b575d7550`.
Remote verification passed for all 287 files, one symlink and 1,269 raw ZIP
members. Post-trial freeze and all nine protected trees, including the full
3,721-entry `recovery_v194` tree, passed without changes.

The new [physical-trial report](v194/results/v194_mac_full_attempt01/RESULTS.md)
is separate because `v194/RESULTS.md` is included in the frozen manifest.
Its pre-trial statements remain historical qualification evidence; the frozen
file, v192's failed trial and v193's display remain unchanged.

See [frozen qualification results](v194/RESULTS.md), [plan](v194/PLAN.md),
[quality](v194/quality.json), [manifest](v194/manifest.json),
[protected comparison](v194/verification/v194_protected_comparison.json), and
[source changes](v194/changes.patch).


## v195 full v194 display review (2026-10-14)

v195 is frozen and display-only: physical parent `v194`, display parent `v193`,
native implementation `v194`. It replays the complete `v194_mac_full_attempt01`
from physical frame 0 through factory PD startup and the exact final
137.5282745361328 s state. The source is the one passed original-route trial:
FINISHED, route_arrived=true, full_route_verification.passed=true and final PD hold.
This render executes zero physics steps and adds no physical acceptance.

The [regular MP4](v195/delivered/v194_mac_full_attempt01.mp4) is 1280 x 720,
30 fps, 4,125 frames, 137.500000 s and 13,030,771 bytes.
Startup uses recorded simulation time; navigation uses original wall time at 1:1.
All 4,125 causal source indices, both endpoints, curve/route/solve clocks,
full decoding, 10 decoded visual samples and 14 overlay/timeline tests passed.
The final caption is `arrived (nav2_arrived)`. The last stored spline #3005 is
expired and its zero direct command is stale; no cyan curve is displayed during
the final recorded FIXED_STAND state. All 12 protected trees remain unchanged.
Freeze and separate verification passed for 4,826 source pairs.

SHA-256: `d3f6ea4caae09a9f607428061362581fbabdffb44ecb2e4fa45431a0176d61b4`.
The remote MP4 at
`gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v194_20261014/v194_mac_full_attempt01.mp4`
has the same hash and size. The frozen display source and review evidence are
also archived and [verified](v195/returned/source_archive_verified.json).
An initial partial display attempt was retained after correcting a new check
that confused Retina framebuffer size with encoded video size; the subsequent
full run_mac.py execution passed. No physical rerun occurred.

See [plan](v195/PLAN.md), [visual QA](v195/VISUAL_QA.md),
[quality](v195/quality.json), [manifest](v195/manifest.json),
[protected comparison](v195/returned/protected_after.json), and
[delivery provenance](v195/delivery_return.json). v194 remains the latest
physical trial in that historical record. The later v196/v197 delivery is recorded below.


## v196 replanning and recovery qualification (2026-10-14)

v196 is frozen with version parent **v195**, navigation source parent **v194**,
native version **v196** and Mac ARM64 binary underlay **v176**. It restores the
1 Hz Foxy replanning pipeline with same-mission cached-route fallback, suppresses
identical active /pct_path refreshes, removes redundant initializer calls,
recovers expired/stalled local planning from odometry, rebases trajectory freeze
accounting and uses a version-scoped 0.35 s cloud-age budget. Non-hover emergency
replanning uses horizontal speed < 0.15 m/s; geometric checks remain active.

The ARM64 build and all rebuilt-package tests passed: **93 colcon entries / 81
actual cases**, zero errors/failures/skips; 24 Mac host tests; 2 generated-profile
tests; terminal capture and v196 corner probes. The live graph preflight verified
four active lifecycle nodes, the actual v196 libraries, runtime cloud-age setting
and shared mount. All **14 protected trees / 12,427 entries** are unchanged.
Freeze and separate verification passed for **5,019 source pairs / 618 runtime
inputs**. Earlier failed/incomplete test attempts remain in the evidence bundle.

**At component freeze, run_mac_full.py had not been executed; no navigation goal or physics advance had occurred.**
That historical record covers component and graph qualification only. At that
point, v194 was the latest physical trial and v195 its display review. The
authorized v196 execution and v197 display are recorded below.

See [results](v196/RESULTS.md), [plan](v196/PLAN.md), [quality](v196/quality.json),
[manifest](v196/manifest.json), [source delta](v196/changes.patch), and
[protected verification](v196/verification/v196_protected_comparison.json).


## v196 reboot recovery, physical trial and v197 delivery (2026-10-14)

The execution workspace was restored from all 11 pinned environment archives.
The native overlay was rebuilt and passed 93 colcon test entries with zero
errors, failures or skips. An initial receipt mismatch stopped before physics;
the failure is retained. Every one of 3,650 pinned source/install files was
verified after restoring the semantically identical source-identity JSON's
original formatting. The original runtime receipt then passed the unchanged
gate. Fresh build/test evidence remains separate. Frozen v196 files are unchanged.

The new **v196_mac_full_attempt01 passed the original full-route gate**:
FINISHED, route arrival, final PD hold and held XYZ/yaw all passed. The erased
pre-reboot capture is not combined with this result. Navigation took
115.561238 simulation seconds / 118.348344 wall seconds (RTF 0.976450), versus
126.507451 / 126.540360 for v194. Successful planning measured 24.630678 wall Hz;
controller output measured 29.935137 wall Hz. The old 10.194397-second
second-floor stall did not recur within its 1 m neighborhood. Direct-command
stops fell from 17 to 9, while emergency entries increased from 9 to 12.
PCT published 102 routes; final refresh_status=terminal_approach, retained_count=3.
These are individual captures, not repeated reliability or a causal speedup test.

See the [complete trial analysis](v196/results/v196_mac_full_attempt01/RESULTS.md),
[four-version comparison](v196/results/v196_mac_full_attempt01/comparison.json),
and [verified trial/overlay archives](v196/results/v196_mac_full_attempt01/ARTIFACTS.json).
The trial archive contains 287 regular files, one symlink and 1,160 verified
raw ZIP members, at gpu5070ti:/data/sun/vla_mppi_20261009/mac_archive_v196_20261014/.

**v197 is the frozen display version**, with parent/native implementation v196
and display parent v195. The [regular MP4](v197/delivered/v196_mac_full_attempt01.mp4)
contains 3,880 frames at 1280x720/30 FPS (129.333333 seconds), from actual physics
time 0.0 through the final 126.582062-second held state. All pauses remain;
startup uses recorded simulation time and navigation uses original wall time.
All 14 overlay/timeline tests, every causal frame, full decode, source identity,
nine decoded visual samples, remote video SHA and display freeze checks passed.
No physics steps were executed during rendering. See [visual QA](v197/VISUAL_QA.md),
[delivery provenance](v197/delivery_return.json), and
[source archive verification](v197/returned/source_archive_verified.json).


## Architecture refactor — v198 through v200

The first refactor stage is component-checked. The last physical route evidence
remains v196 and the display selection remains v197; this first stage ended at v200.

| Version | Logical change | Evidence |
|---|---|---|
| [v198](v198/RESULTS.md) | Typed physical execution feedback on the existing TCP connection | Interface build; six host tests; real socket-to-ROS checks |
| [v199](v199/RESULTS.md) | ControllerServer becomes the sole velocity publisher | Four packages built; 65 distinct component cases including 300 tracking samples |
| [v200](v200/RESULTS.md) | Two-second physical stand completion, terminal progress exemption, no automatic route replay | Four packages built; 79 distinct component cases including actual BT failure propagation |

All preceding versions are retained. No new full-route experiment or physics
step was executed. Direct C++ PCT, LocalMotion consolidation, terrain/startup
cleanup and event-driven replanning remain pending. [Rebuild instructions](v200/BUILD.md).


## Direct native PCT — v201

Step 2 now uses `PCTPlanner -> OfflineElePlanner` in C++, with a pre-exported map
bundle. MissionBridge has no planner service or route cache. Six packages built;
11 fixed-input comparisons matched all 2,033 XYZ points exactly, and 21 affected
component cases passed. PCT native algorithm source is unchanged. No new physical
route experiment was run; 756 protected files were reverified unchanged.

The requested goal pose is now fixed by Nav2; omitted HTTP yaw defaults to zero.
The launch argument is `pct_map_bundle`. See [results](v201/RESULTS.md),
[build and interface contract](v201/BUILD.md), and [provenance](v201/PROVENANCE.md).
At the v201 checkpoint the latest source was v201; the earlier physical/display evidence remains
v196/v197. Steps 3–5 remain pending.


## LocalMotion direct execution — v202

Step 3 is implemented: LocalMotion owns the native SCAN worker and Tracker.
Routes and trajectory-scoped freeze feedback enter a bounded immutable snapshot;
completed splines arrive through a direct callback and bounded output slot.
Cancellation and changed routes invalidate late outputs. Internal route, spline
and freeze subscriptions are removed; their ROS publishers remain observations.
External sensor/pose/clock/execution-state input and standalone SCAN are retained.

Seven packages built; 77 unique component cases and 300 fixed tracking samples
passed, including three worker lifecycle cycles, real native direct output,
ROS injection isolation, cancellation and terminal/command-owner regressions.
See [results](v202/RESULTS.md), [rebuild](v202/BUILD.md), and [manifest](v202/manifest.json).
All 927 protected v196-v201 files are unchanged. No new full-route or physics run.
At v202, the latest source was v202; physical baseline v196 and display/current v197 are retained.
Steps 4 (map/startup cleanup) and 5 (event-driven global planning) remain pending.


## Unified static terrain and startup cleanup — v203

Step 4 is implemented. One terrain manifest binds the native PCT map, navigation
support, surface evidence, physical presence and negative-only gap mask. One
runtime node replaces the three static publishers without changing their payload
bytes or roles. LocalMotion's 2D projection, TerrainLayer and default Nav2
inflation are removed, as is the unused Wait recovery server.

Foxy retains a one-cell, 1 Hz TF/lifecycle shell with a disabled input-free stock
ObstacleLayer: its parser rejects an empty plugin array, and zero update rate
would block activation. Native SCAN mapping, geometry and support code are unchanged.
Seven packages built; 97 ROS component cases, one fake-child graph check and
300 tracking samples passed. No new full-route or physics run. See
[results](v203/RESULTS.md), [build/launch contract](v203/BUILD.md), and
[manifest](v203/manifest.json). At v203, latest source was v203; physical/display v196/v197
remain retained. Only step 5 (event-driven global planning) remains pending.


## Restore original mission behavior — v204

Restore v196 terminal pose/yaw selection, same-mission cached-route behavior and
ordinary Wait 1 s / six-retry recovery. Terminal-settle timeout remains nonretryable.
Keep the v198-v203 C++ PCT, LocalMotion, single robot command owner and static-terrain
architecture. Global refresh stays 1 Hz; step 5 is deferred. No new navigation policy.

Seven packages built, including a final clean rebuild of all five owned packages.
106 unique ROS component cases plus one host graph check passed, with 28 fixed-input
requests compared to the actually executed frozen v196 methods and 300 tracking
samples. The two-second terminal hold contract, failure UUID, cancel/replacement,
stock Wait lifecycle and retained terrain/geometry checks passed. First failed test
fixtures and the build repair history are retained. 1,116 predecessor files unchanged.

See [results](v204/RESULTS.md), [rebuild](v204/BUILD.md), and [manifest](v204/manifest.json).
Latest source is v204. Physical baseline v196 and display/current v197 stay selected;
no new physics, whole-route acceptance or robot actuation. Previous HTML is preserved
under `v204/previous_html/`.


### v204 physical validation — 2026-10-15

Dr Sun authorized one original-route physical trial after the component-only
refactor. `v204_mac_full_attempt01` **passed** the original v196 full-route gate:
FINISHED, continuous original start/goal, final PD hold, shared-state verification,
78.948 m recorded body path and 143.591 s actual physics. Frozen sources unchanged.
Navigation wall time was 155.602 s versus v196's 118.348 s (+31.48%); successful
local planning was 14.762 Hz versus 24.631 Hz. This is a successful full-route
capture with a measured slowdown, not performance parity or repeated reliability.
See [physical results](v204/results/v204_mac_full_attempt01/RESULTS.md) and
[comparison](v204/results/v204_mac_full_attempt01/comparison.json). No second
physical attempt or navigation tuning. v197 display/current remains selected.


## Display of the v204 physical capture — v205

The complete v204_mac_full_attempt01 video is delivered as a regular
[MP4](v205/delivered/v204_mac_full_attempt01.mp4): 4,998 frames, 1280x720 at 30 FPS,
166.6 seconds. Startup uses original simulation time; navigation retains original
wall time at 1:1, including pauses and final standing. All causal frames, full
decode, source hashes, nine decoded visual samples and the remote video checksum
passed. See [visual QA](v205/VISUAL_QA.md). Zero new physics steps; frozen v204
navigation and prior v196/v197 evidence retained. Current display is v205.

## Route and command continuity — v206

Latest source/current is v206, derived from navigation v204. v205 remains the
review video of v204's physical capture. Normal same-goal route refresh no longer
invalidates the local solver generation, completed output or execution feedback.
Tracking uses smooth heading attenuation with 1.0/0.6 rad hysteresis and one
independent command slew history, including the outer normal terminal brake.
An expired low-speed local curve brakes to exact zero without claiming arrival;
active small/reverse corrections and the original completion gates are retained.
PCT/SCAN geometry, 1 Hz global planning and ordinary retries are unchanged.

**gpu5070ti Linux x86_64:** all 14 packages built; 117 distinct native/ROS cases
plus one lightweight host graph check passed. Colcon's 134 count includes 17
CTest wrappers. Source, installed libraries and returned evidence are hash-bound.
No local compilation and no new physical trial. v204 remains the last physical
result, and v206 performance is not yet physically measured.

See [results](v206/RESULTS.md), [remote build](v206/BUILD.md),
[changes](v206/changes.patch), and [manifest](v206/manifest.json).

## v206 physical follow-up and v207 video — 2026-10-15

The one moving Linux original-start trial reached the goal vicinity (9.46 cm XY)
but failed terminal_settle_timeout; final state STAND_SETTLING, not PD hold.
The unchanged full-route gate failed. A preceding infrastructure startup stopped
at zero integrations and is retained. No navigation retuning or moving retry.
See [physical result](v206/results/v206_linux_full_attempt02/RESULTS.md).

v207 displays the exact recorded attempt: 3,785 frames /126.1667 s, 1280x720,
30FPS. Full decode, causal timeline, source hashes and visual review pass.
[Video](v207/delivered/v206_linux_full_attempt02.mp4) · [visual QA](v207/VISUAL_QA.md).
Last physically accepted full-route evidence remains v204; v207 adds no physics.

## v208 — stillness-based RL-to-PD return — 2026-10-15

Navigation remains v206. The versioned locomotion adapter replaces the entry
load-share gate with body/joint stillness, a two-second PD crossfade and a
0.2 rad target offset cap, preserving V12's torque-matched stand target.
10 candidate and 53 original-hold tests pass on gpu5070ti. Two recorded-state
physical pairs pass for the candidate: fixed PD at 2.359/2.299 s, with measured
holds lasting 7.656/7.713 s. Neither original control completes the same hold
within ten seconds. 40,040 actual integrations; no new full route.

The original sources and v204/v206 results remain frozen. The full-navigation
default is unchanged; the last accepted full route remains v204.
[Results](v208/RESULTS.md) · [Declared scope](v208/PLAN.md) · [Changes](v208/changes.patch).

## v209 — recorded stop comparison video — 2026-10-15

Display-only left/right replay of the four completed v208 physical probes.
604 frames / 20.133 seconds; full decode, source identity, causal frame mapping
and returned MP4 hash pass. No additional physics or navigation changes.
[Video](v209/delivered/newton_stair_recorded.mp4) · [Results](v209/RESULTS.md).

## v210 — v208 locomotion in full navigation — 2026-10-15

One original-start gpu5070ti trial passed the unchanged full-route gate: 137.005 s
physics, final XY error 0.1264 m and 4.351 s final fixed PD. Frozen v206 navigation
strategy and binaries remain unchanged. [Results](v210/RESULTS.md).

## v211 — complete v210 physical video — 2026-10-15

4,104 frames / 136.8 seconds, including original startup and final PD hold.
Full decode, causal-state/curve checks and local delivery hash pass.
[Play video](v211/delivered/v210_linux_full_attempt01.mp4) · [Visual QA](v211/VISUAL_QA.md).

## v212 — event-triggered global planning — 2026-10-15

Two packages built and 51 cases pass. One same-route physical trial failed at
54.142 s during an intermediate stop/PD transfer. Same-window route deliveries
fell from 39 to 1. Do not adopt over v210; no extra physics or strategy retuning.
[Results](v212/RESULTS.md) · [Comparison](v212/results/comparison_v210.json).

v213/v214 display preparations are preserved; v215 handles the recorded physical
fall without inventing a Nav2 terminal result.

## v215 — complete v212 failure video — 2026-10-15

1,618 frames / 53.933 seconds; full decode, causal source checks and local MP4
hash pass. The last frame explicitly shows physical fall; no fabricated Nav2
terminal result or physical success.
[Video](v215/delivered/v212_linux_full_attempt01.mp4) · [Visual QA](v215/VISUAL_QA.md).

## v216-v220: supported PD transfer and local-failure event replanning

v216 requires four-foot support throughout the stillness dwell and immediately
returns to RL on transition disturbance. 14 host component tests pass on
5070Ti; the new suite fails against the frozen v208 implementation.

v217 detects absent/expired-braking trajectories, but its one physical attempt
still exhausted six retries at the stair after 84.665 s. It remained upright and
held PD there. [Failure report](v217/RESULTS.md) and the complete
[v218 video](v218/delivered/v217_linux_full_attempt01.mp4) are preserved.

v219 additionally reports actual consecutive SCAN failures to the BT route
owner after 0.75 s, with exact route identity and without discarding a usable
curve. Native geometry remains byte-identical after removing result-reporting
lines. Four packages and 132 distinct cases pass on 5070Ti. One original-start
full route passes: 123.564 s, 9.39 cm final XY error, 4.338 s final fixed PD.
The stair still has a recovered PD disturbance and lower local success fraction
than v210 (56.7% versus 98.8% over 45-55 s). [Results](v219/RESULTS.md).

v220 displays all recorded v219 states, including pauses and final hold: 3,700
frames / 123.333 s. Full decode, causal indexing, visual QA and local delivery
hash pass. [Video](v220/delivered/v219_linux_full_attempt01.mp4). No extra physics.
At that checkpoint, latest validated source was v219 and display was v220. v210 and all failures
remain available. This is one successful condition, not repeated reliability.

## v221-v224: shared checking, precise floor rejection and environmental preference

v221 is the retained component-tested shared PCT/SCAN hard-checking parent
(attempt03, source identity recorded in v223). v222 remains the separately
planned spatial-feedback change and is not part of this implementation.

v223 restores a diagnostic association to the physical floor and reports
`EdgeClearance` without granting selected support. Nine packages build and all
158 colcon test records pass. The 126,324-query v217 replay and three exact
planning queries preserve every binary decision. The report separates first
rejections, overlapping edge/history/envelope predicates, and the 1,847
queries for which a torso-only occupancy substitution could remove the final
remaining rejection. None of the recorded-body failures or three exact
planning failures falls into that last group. [Results](v223/RESULTS.md).

v224 owns the shared environmental soft scorer and its PCT search, PCT GPMP and
SCAN spline integrations. Nine packages and 164 colcon records pass. The real-map
A* score improves by 98.6%, but GPMP loses that clearance advantage; total scored
planning still takes 8.023 s versus 0.032 s with the score disabled. The actual
plugin's bounded static admission/repair comparison returns truthful no-route in
both modes. This is a component-validated candidate, not an accepted Building
route improvement. Failed attempts and exact-source receipts are retained in
[Results](v224/RESULTS.md). No new physics or current-run promotion occurs; the
accepted physical source/display pair remains v219/v220.

### v225 — offline atlas and analytic environmental gradients

Performance candidate on frozen v224. The shared PCT probe drops from 8.023 s
to 0.113 s; active SCAN environmental evaluation from 35.24 ms to 0.043 ms.
Nine packages and 144 distinct test cases pass. Raw-oracle approximation errors,
including large uniform-height-switch outliers, remain explicit. Actual final
admission still returns no-route; GPMP interpolation and support-cell boundary
repairs remain follow-up work. [Results](v225/RESULTS.md). No physics run or
accepted-source promotion; v219/v220 remains the physical source/display pair.

### v226 — continuous shared-mode GPMP cost interpolation

Integer-anchored bilinear sampling removes the measured legacy extrapolation
and half-cell jump in shared mode. Nine packages and 145 distinct test cases
pass; legacy route bytes match v225. Shared smoothing retains 0.1424/0.1458 m
edge/solid margin in 0.639 s, but final admission still fails. [Results](v226/RESULTS.md).

### v227 — failed physical-origin canonical support lookup

Preserved failure. All three old corner witnesses become Free, but full
admission fails at two new equivalent corners. Physical float32-derived origin
is itself offset from the PCT lattice. Original 126,324+3 replay queries and
all independent occupancy predicates retain binary parity. Nine packages and
146 distinct cases pass; no physical-run promotion. [Results](v227/RESULTS.md).

### v228 — original PCT lattice and checked full-goal references

Nominal support-cell origin comes from the SHA-bound PCT header, with ULP
normalization and half-open cells. Nine packages and 147 distinct cases pass.
Both actual installed planner modes return full-goal references with zero final
native-static rejection. Shared final extra edge margin is 0.147524 m and raw
PCD solid margin 0.064950 m; full repair/admission takes 1.032 s. Both use the
existing checked raw-graph fallback; GPMP height smoothing remains an explicit
limitation. Original v217 126,324+3 query verdicts and occupancy predicates are
unchanged. [Results](v228/RESULTS.md). No new physics or accepted-source promotion.

### v229 — support-aligned GPMP output height

Shared mode admits the actual installed GPMP reference on its first native
check (0/3821 rejected, exact XYZ goal). Full call is 0.727 s versus v228
1.032 s; the requested ~0.35 s remains unmet. Raw PCD solid margin is +0.056539 m.
Nine packages and 148 distinct cases pass. Original 126324+3 replay verdicts
and occupancy predicates are unchanged. [Results](v229/RESULTS.md).
No new physics or accepted-source promotion.

### v230 — mission-scoped local obstruction feedback

Reuse typed native LIVE queries and the existing Header/BT trigger. Actual
installed PCT fixture routes detour 0.179713 m from a 0.15 m obstruction, retain
the detour on unknown, and recover the exact original geometry on newer Free
or new mission. A blocked terminal cache is never republished. Nine packages/
154 distinct cases pass; 126324+3 native typed/binary decisions and occupancy
predicates are unchanged. Building retains the v229 first-round reference,
0/3821 rejected, raw solid margin +0.056539 m; shared full call 0.731 s.
[Results](v230/RESULTS.md). Component/recorded-input gate only; no new physics.

### v231 — one physical execution binding for frozen v230 navigation

Original v219 endpoints/gates, v216 locomotion, unchanged RL and 0.35 m guards.
The single authorized full-route attempt fails: controller_server aborts with
SIGABRT (-6) near 46.7 s. It records standing to its original 600000-step bound
without arrival or terminal notification. Early edge-margin samples improve,
but 42/42 successful completed stair rounds end at 46.376 s; later planning is
absent. This is not full-window 100% success or physical promotion.
[Results](v231/RESULTS.md). At that failed checkpoint the physical source/display pair remained v219/v220.

### v232 — native exception containment and critical-process failure closure

On frozen v230, short-circuit stopped rebound objectives, keep soft headings
finite without changing hard freshness, contain exceptions inside native ROS
callbacks/complete optimizer entries, and close failed tasks when actual ROS
children exit or critical nodes stop responding. Nine packages/165 distinct
cases (186 colcon records) pass, including a running Action with paused ROS
clock and a real SIGABRT child whose launch parent survives. Original126324+3
hard verdicts/predicates remain unchanged; installed Building first admission
has0/3821 rejected and identical v230 route bytes. Actual14-package graph runs
12s and shuts down cleanly with zero physics. [Results](v232/RESULTS.md).
This frozen v232 record is the offline gate. Its subsequent physical pass and
user-adopted source/display pair are recorded separately as v232/v233 above.

### v233 — one successful original-route physical execution of frozen v232

After commits1ad1862d (v230/v231 physical audit) andff4cb515 (v232 repair),
freeze the v232 native install, launch graph and long-route driver under a
new execution binding. The sole physical attempt passes the original v219
route/terminal gates, unchanged endpoints/RL/0.35m guards: FINISHED121.565s,
measured final PD4.398s, XY error0.1412m, no SIGABRT/fall. Source/install and
shared finish parity pass. Stair45–55s:273/275 successful rounds, no >=1s
low-speed pause; body edge samples reach the extra0.15m capped target.
One route only; no repeated reliability, sustained30Hz or physical feedback
detour claim. [Results](v233/RESULTS.md) and linked three-way comparison.
Frozen v232's manifest retains its pre-physics status; this separate record
binds its successful physical execution without rewriting predecessor evidence.

Baseline adoption: Dr Sun approved v232/v233 on 2026-10-17 after reviewing the
single physical result and videos. v219/v220 remains a comparison, not the
latest selected pair. The two frozen manifests retain their original status.
