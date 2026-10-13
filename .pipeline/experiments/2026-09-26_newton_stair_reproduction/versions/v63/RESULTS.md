# v63 Mac optimizer repair

Stage: experiment + analysis, 2026-10-04. Source parent frozen v62, which has partial Mac qualification and no new physics acceptance. v48 remains the runnable reference. gpu5070ti was neither queried nor used.

Two native files change: `bspline_optimizer.h/cpp`. The existing initialization API gains an optional status output. An empty no-collision path remains success; existing search-error and short-path returns report failure. The existing rebound collision-repair branch now returns its unsuccessful result when initialization failed, instead of continuing without usable constraints. A successful initialization retains the original restart count/weight schedule. Initial manager calls, outer warm/native/fixed-height/prefix fallbacks, failure counters and stop protocol are unchanged. No planner deadline, new stop reason, safety waiver or cached failure is introduced.

## Compared behavior

The regression compiles actual parent/candidate optimizer and LBFGS code, scripting occupancy, graph outcomes and graph-fixture lifetime. It does not qualify real collision/search latency. The useful-repair fixture makes the scripted obstruction clear after its successful graph path; original native map/search are exercised separately by the recorded fixtures.

| Repair condition | Parent searches | v63 searches | Returned result |
|---|---:|---:|---|
| No collision | 0 | 0 | Success |
| Graph search fails | **3** | **1** | Failure in both |
| Graph reports success with fewer than two points | **3** | **1** | Failure in both |
| Useful graph repair | 1 | 1 | Success |

Both height modes pass, including unchanged boundary control points and finite output. The candidate passes 40 optimizer checks; the parent passes 28 and reproduces repeated failed searches. [Parent cases](mac_tests/attempt03/parent_optimizer.json), [candidate cases](mac_tests/attempt03/candidate_optimizer.json). This removes two redundant failed repair searches per affected optimizer call; it is not a measured live max-latency reduction.

## Native and safety evidence

All eight packages and all probes build in the exact cached ROS image on the Mac. The inherited 34 retry-epoch checks, 35 native/FSM/stop, 64 cache, 15 controller-epoch, 10 endpoint/3,000 footprint-pair, 23 physical-role and 500 randomized goal-region cases pass. Both original recorded fixtures pass 47 warm/PVA, 10 epoch, 29 route-refresh and 12 goal-region checks each, with complete published-curve collision/dynamics checks active. All 17 inherited backend stop/goal/identity tests pass. Parent/candidate/native/test source hashes remain unchanged during the run. [Qualified Mac attempt](mac_tests/attempt03/result.json), [counts and limits](component_qualification.json). The frozen anchored-line parser reports36 optimizer checks because four follow inherited ANSI resets; [supplemental verification](analysis_verification.json) confirms the executable total40 without changing frozen metadata.

Attempt01 was stopped during build after fixture review found missing search-pool initialization. Attempt02 completed native build but the scripted probe hit a static-library duplicate-symbol conflict. Attempt03 implements the complete scripted search boundary, including lifecycle, so the native search object is not linked into this isolated probe. These fixture failures, executed sources, native deltas and results are preserved. No production code changed between these attempts.

## What remains open

Full component qualification still requires the original remote recorded-corner startup/freshness/physical-native fixtures. Full simulation continuity, max tail latency and 30 Hz are unmeasured for v62/v63. Mac emulation and scripted-search times are not gpu5070ti performance evidence. The latest full v59 recording remains26.42581 successful Hz and1236.709246ms maximum solve latency; there is no new full-run counterpart yet. The protected-heading target-connector problem remains unresolved, and the original drop/support guard stays intact.

Source is frozen after the declared Mac checks with full qualification pending. Do not launch as an accepted replacement, promote a subset into full qualification or change v48's reference. Temporary build/install products were deleted with the owned Docker container, verified absent. Only source and compact evidence remain local; no heavy data was downloaded and no commit or broad staging was performed.
