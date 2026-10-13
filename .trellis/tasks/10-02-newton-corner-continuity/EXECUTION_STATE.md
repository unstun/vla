# Latest delivery: 2026-10-03

v58/v59 component repairs and both 90-second physical validations are complete. Successful planning is 27.53/26.43 Hz; v59 still has a 1.237-second cold-recovery solve and 1.099-second pause. Updated plot and final v61 display replay are verified. GPU-wait heartbeat is paused. Continue from [current v59 execution state](../10-02-newton-v59-trajectory-epoch/EXECUTION_STATE.md) and its acceptance limits. Earlier entries below are historical; do not repeat their run commands.

---

# Execution state 2026-10-02

Dr Sun approved latest plan with "ok"; authorized implementation and two final idle-host 90-s Building recordings (360-s original external supervisor). No subagents. English, replies start Dr Sun. No planner timeouts/cancellation/stop changes; preserve goal/yaw/PVA/dynamics/safety. Bulk stays gpu5070ti; compact results and one review MP4 only return. No global memory edits or commits yet.

Completed:
- v53 (scan75_reference_continuity_v53), parent52, freezes exact requested-pose warm identity and compatible transactional refresh/world-window reprojection. Build03/contracts03 passed 35 native+64 cache+47 warm/fixture +callback/goal/backend; actual corner post-refresh two failed v52 rounds 195/194 ms become 2.27/1.98 ms. Source freeze component only, no navigation acceptance.
- Actual pre-trajectory DDS fixture then exposed frozen53 mixed-clock subtraction before checking traj ID0. Preserved in v53/POST_FREEZE_FINDING.md and remote versions/v54/freshness/red01 (exit134). Allocated v54 for isolated guard per approved failure/version rule. D2 shifted55, D3 shifted56; original approved parent PRD/design/implement copies in parent/research/approved_*.md.
- v54 (scan76_warm_clock_guard_v54), parent53, only early trajectory-ID/clock-type guard. Build01/contracts01/corner01 and exact materialization pass. Qualified frozen.
- v55 (scan77_recovery_freshness_v55), parent54, actual recoveryTargetOccupancy drains existing queued FSM body+GridMap input before prefix admission, fixed PVA and .25 s cloud limit; shares one query with debug line. Parent54 real-DDS red reproduced stale rejection despite queued fresh input. New9 DDS freshness checks +all inherited component/corner gates passed; qualified frozen.

Active: v56 (scan78_physical_floor_presence_v56), parent55, D3 typed floor presence. Trellis active legacy slug .trellis/tasks/10-02-newton-v55-floor-presence, metadata version56. Parent remains in_progress. Six Env files changed, manager/FSM/control unchanged. Separate PhysicalFloorSnapshot has costs/elevations and NO Support labels, used only in evidence-fill drop and ETH neighbor association. Source-paired/readiness gated, optional absence preserves parity. Native build01 passed 44.8 s; local23 pure role/true-drop/ambiguity/cost50/obstacle/stale/etc tests pass; exact materializer passes101 hashes.
- Native full contract attempt01 failed test compilation: missing timed_cubic_initialization.h for matchesBoundaryPva. Test header fixed, no product edit.
- Native full contract attempt02 is running (last started session). Includes original optional-input startup/freshness tests using v55 YAML, new configured v56 physical_native_probe source/callback/cache/history/recorded corner and two sequential accepted curves requiring spatial+expiry reserve extension and full PVA/dynamics/safety, then inherited35/64/warm/cold/goal/backend gates.
- v56/corner source modified SFINAE loadPhysical: candidate loads typed source, parent55 skips it, allowing same event replay.
- Product source not frozen yet. Preserve attempts and snapshot before changing code used by running build/test.

Remote ROOT /home/sun/vla_exec/vla; BASE .pipeline/experiments/2026-09-26_newton_stair_reproduction; PATH /home/sun/vla_exec/bin:$PATH. WorkerPython /home/sun/vla_exec/envs/newton_worker/bin/python. Cached ROS image sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb. SSH gpu5070ti approved. Latest preflight idle, ~21GiB free initially. Never stop competing processes. Native tests Docker no-network3CPU6g, domain217; corners219. CPU diagnostics are not live 30 Hz.

D3 asset derivation: verified historical dense inputs map.pickle/map_float32.npz/raw_cost_observation.npz; actual pinned pct_sim_clock_core.py producer SHA828056...; selected_ground_points(cost_limit=None) generates150500 records/2408000 bytes; SHA20acd5cf1ef156c5bd336b12651efe9a18e9959816905b05178ed44b1a181c96. Selected surface and navigation payload bytes asserted equal original frozen sources.
- Physical FNV3260540598421060437; selected FNV14798634034717650828; navigation FNV5659108921681646177.
- Origin x-7.795314598083496,y-9.436811256408692,res.1,zvisual .03.
- Generator source task/derive_physical_floor.py copied byte-identical into v56. Remote preview .trellis/tasks/10-02-newton-v55-floor-presence/research/physical_asset01 (provenance erroneously relative absolute_root, compact v56 metadata normalizes published storage). Primary binary copied verified to remote versions/v56/assets/physical_floor.f32. NO local binary. Local v56/physical_floor_input.json pins metadata/source/roles/regeneration; native YAML exact source IDs/origin/res.
- New v56/physical_floor_publisher.py verifies SHA, uses original SimClockGate/cloud_payload, distinct reliable/transient static /pct_physical_floor; native_graph launches alongside unchanged selected/nav publishers for Building. Flat optional none unchanged.

Next:
1. Check running v56 native attempt02. Diagnose any failure; do not bypass gate. Preserve source attempts for product revisions, rebuild unfrozen candidate with --attempt N, refresh manifest/patch/preparation, exact materialize.
2. Run native corner parent-red/candidate replay v56 after gate. Check actual late front full-cylinder support, complete rounds, sequential endpoint/expiry extension. Add actual publisher ClockGate runtime validation if needed.
3. Review invariants/owned diff; freeze qualified v56 via adapted freeze_source.py (must include root producer/metadata and new native header; predecessor snapshot references). All component flags truthful; physics false until tested. Sync source/config/manifests only.
4. Idle-host preflight then two approved versions/v56/remote_trial.py --attempt1/2 (90 simsec, original360s external bound), never alter settings/safety/deadlines. Source/install/asset SHA gate.
5. Analyze remotely using version/analyze_trial.py and comparison/time-series; native per-round Hz/latency +39–55 corner +progress/reserve/startup/goal/hold, independent physical paths caveat. Render ONE v51 managed streaming MP4; bulk NPZ/JSONL/build/ZIP stays remote. Return compact allowlist and video <=128MiB. Need do these; current component pass is not main task completion.
6. Update versionsREADME/current compact experimental records, applicable specs/Trellis journals, keep v48 reference and failed frozen49/50/52/53 evidence. No blanket staging or auto-commit. Main parent complete only all declared work done; strict30/arrival truth flags separate.

Useful scripts: parent/create_candidate.py creates next integer only after predecessor qualification; source-only. Each version materialize.py +changes.patch/preparation reproduces exact source. Each freeze_source.py references inherited snapshots and copies delta, verifies all parent current/snapshot hashes (7213 filenames by55; local manifests ~4MiB are compact provenance, not raw).

Final if memory used must append exact citation block: MEMORY.md:19-19 note Preserved frozen failures and separate integer repairs; rollout ID01a0dbb2-f7aa-7662-a385-906341bfb14a. No memory writes.


## Latest 2026-10-02

v56 build02/fullcontracts03 pass, with30 native physical/sequence checks and23 pure checks. Preserve candidate build01/test01-02 failures. Physical callback now retains unchanged selected labels and sensor state, clears borrowed caches, retains nonterrain history. Isolated sequence extends endpoint0.63m and absolute expiry43.3796->46.5048; cold93.37ms thenwarm1.30ms. Corner replay allrounds succeed. Qualified frozen56,7374files. Trial01 exits0.6s BEFORE physics: launcher expects legacy qualification keys missing innewschema. Preservefrozen56 andPOST_FREEZE_FINDING. Allocate57 METADATAWIRINGONLY, reuses native scan78_physical_floor_presence_v56 source/install and same physicalasset. Own v57 runtime labels plusfivelegacyaliases from56passingflags. v57 verify_entry_gate.py --before-freeze tests real entry native/source/key/asset gate onremote; thenfreeze57 andrunactual gateagain. Actualtwo90-s physics recordings stillauthorized (failed56startup usedzero). v57 activeTrellis slug10-02-newton-v57-qualification-wiring. Renderer port wrapperv57/render_review.py path-only ports frozen51stream renderer; remoteNewtons/pyglet/PIL/scipy/pxravailable, matplotlib is availableviaBASE/runtime/matplotlib onPYTHONPATH. NEVEReditfrozen56/55/etc. Needsource-onlysync,freezeactualschema gate,thenperform2physics,remoteanalysis/report/plots/oneMP4,compactreturnsandversion/spec/journalupdates;mainnotcomplete.


## Delivery completed 2026-10-02

Both authorized v57 90-second recordings completed on gpu5070ti (89.962189 native seconds each, 90,000 steps, no dropped steps). Trial01/02: successful full-window planning25.6489/25.7616Hz, max660.9747/290.1491ms, measured path46.2047/46.6163m, no measured pauses over1s, no emergency transitions or remaining_spline_invalid. Corner passed at46.606/45.906s, then5.083/6.937m measured travel by55s; minimum observed focus reserve0.710/0.314s. Strict30Hz and >=100ms-tail elimination FAIL (211/252 >33.333ms;17/9 >=100ms). No full-route arrival. v48 stays reference.

All7408 source and519 installed hashes pass; each raw archive verifies795 members. Two archives237929107/238301058bytes remain remote, along with NPZ/JSONL/build/derived arrays. Compact28-file return5058472bytes verified. Remote plotting library was absent (runtime/matplotlib was a font-cache directory); numeric analysis stayed remote and only compact tables were plotted locally. Preserved executed_data_analysis.py exactly; current compare_trials.py changes only the pause-title wording for plotting.

Review MP4: output/2026-09-27_lite3_versions/v57_realtime_trial02_review.mp4,8773409bytes,SHA d96b73a44c36bd6c9be4b1a3d844a1d158eb045632c20d061702d7fc48d9fb5b. Remote render v57_review_trial02_attempt03; first two render failures (missing frozen51 files, then Mac font) preserved. Exact51 renderer/reference files and original Helvetica supplied; XDG_DATA_HOME points to runtime/render_env. Frozen source unchanged. Full decode2460frames at30FPS/82s and three preview QA passed; no resimulation.

Results: versions/v57/RESULTS.md,acceptance.json,REMOTE_ARTIFACTS.json,REVIEW_VIDEO.json and analysis/*. Remaining issue: isolated cold recovery (worst63.142s) plus growing final-goal search70-90s (mean19.34/27.47ms per round) and input application8.20/11.52ms despite warm acceptance. These inclusive timers overlap. Main task remains open; next behavior change requires a new integer and reviewed scope, never edit frozen57. No further physics or code repair was started in this delivery turn.

Git staging of the new REVIEW_VIDEO.json encountered an existing .git/index.lock. The lock was not removed and no index changes/commit were made. Exact video hash, storage and regeneration are additionally recorded in the already-tracked versions/README.md; all user changes remain intact.


## Post-70-second analysis 2026-10-02

Analysis-only audit: audits/2026-10-02_v57_after70/REPORT.md. No new runtime version or physics. Spatial AStar pool trigger at72.7966/69.3335s, planned startY~1.95 vs final-goalY-2.9868. Once within100x100x100 pool at.05m, unsuccessful far-goal searches execute before warm seed every round; native replay20cases x2 repeats confirms identical outcomes/nodes, growing to615/691expanded nodes and no goal path. Goal CPU/wall~99.98/99.65%. Late clouds add~27-33ms; maxone in-round cloud, freshness remains<.25s.

Also confirmed inherited timing gap: planFromCurrentTraj samplesoldPVA before solving, updateTrajInfo stamps completion, controller resets exec_time. All four relevant function bodies matchv48 exactly.604/529matched observed curve transitions; late85-90s median sample-to-stamp40/60ms, reference backward steps3.3/4.9cm. Robot ahead ofplannedstart~0.93/0.97m, kp_pos.8 subtracts~.75/.78m/s fromplanned~.81m/s, rawcommandmedian.138/.086m/s at30Hz. This reveals a separate tracking/time-alignment gap; previous corner acceptance onlycovered39-55s.

Nativeprobe55.865s, no-network3CPU6GiB, frozen workspace RO, source7408/install519checks pass.23compact returns1203794bytes verified; eventstreams/build/raw remainremote. Diagnosticfigureinspected. Repairs are recommendations only: avoid redundant goal search and validate actual-time curve handover; do not restorev49abort, weakenchecks or maskerrorwithgain/speed/tolerance changes.
