# v62 Mac validation

Stage: experiment + analysis, 2026-10-04. Native parent frozen v59; v60/v61 are display-only. Source is frozen after the declared Mac checks, with full qualification and physics pending. v48 remains the runnable reference.

The FSM now captures the checked spline PVA timestamp once and passes it through the complete prefix/initialization retry chain. Old-curve expiry during a failed attempt cannot relabel that same PVA with a later timestamp. Four manager/FSM files change; controller, optimizer, map/search, production configurations and all existing goal, yaw, dynamics, occupancy, stair and stop code remain exact v59. The helper retains the original finite-value rejection, including overflow of derived PVA. No planner timeout was added.

## Direct regression result

The probe compiles the actual parent/candidate FSM and manager retry/publication control flow. Target admission and solver outcomes/delays are scripted from the observed eight-attempt shape; this is not collision, optimizer, physical continuity or performance acceptance.

| Value | v59 parent | v62 |
|---|---:|---:|
| Original sample | 81.027099609 s | 81.027099609 s |
| Publication after eight attempts | 82.286407471 s | 82.286407471 s |
| Published curve origin | 82.286407471 s | 81.027099609 s |
| Sample timestamp rebased by | **1.259307862 s** | **0 s** |

The candidate passes 34 checks: all eight retries keep the original timestamp and PVA, a new round uses its own timestamp, expired initial parents are not captured, ordinary callers retain their derivation, initial/odometry callers retain their original default, and future/incompatible/invalid derived values are rejected. [Parent red evidence](mac_tests/attempt02/parent_retry_epoch.json), [candidate evidence](mac_tests/attempt02/candidate_retry_epoch.json), [actual checks](mac_tests/attempt02/candidate_retry_probe.log).

## Build and safety components

All eight packages and all native probes compile in the exact cached ROS image on the Mac (linux/amd64 emulation). Native/FSM/controller, cache, 15 controller epoch, 10 endpoint/3,000 footprint-pair, 23 physical-role and 500 randomized goal-region cases pass. Both original recorded fixtures pass 47 warm/PVA, 10 epoch, 29 route-refresh and 12 goal-region checks each; full published-curve collision and dynamics checks remain active. All 17 inherited backend stop/goal/identity tests pass. The 1,556 recorded input members were hash-verified and no clouds were downloaded. [Qualification and counts](component_qualification.json), [immutable attempt result](mac_tests/attempt02/result.json).

Attempt01 built successfully but its clock fixture failed before exercising the desired chain: default map bounds did not cover the recorded corner. Its inputs, executed native delta, build logs, failure and source identity remain under `mac_tests/attempt01`; attempt02 corrected the fixture's map/reference setup. The unfrozen capture helper was also corrected before attempt02 to preserve parent rejection of nonfinite derived residuals. No frozen v59 source was edited.

## Limits and next repair

This corrects timestamp identity under controlled delayed recovery; it does not remove the long recovery chain or establish physical continuity. Live max latency and 30 Hz remain unmeasured for v62. Original recorded-corner startup/freshness/physical-native gates require the remote event stream and remain pending; the physical-role checks above are a separate synthetic contract. No full component qualification or simulator acceptance is claimed.

Next, explicitly propagate an obstacle-repair initialization failure to stop repeating that failed optimizer problem, retaining native fallback and stop behavior. The separate invalid-heading connector remains unresolved.

Mac build/install products were kept inside the owned Docker container, which is verified absent after the run. Only source, compact logs/hashes and probe outputs remain locally. gpu5070ti was neither queried nor used. No commit or broad staging was performed.
