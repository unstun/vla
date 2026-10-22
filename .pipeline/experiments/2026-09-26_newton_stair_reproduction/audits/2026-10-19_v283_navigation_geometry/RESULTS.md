# v283 — Full offline and ten-route physical evaluation

The updated offline gate passes 49/50 legal cases (98%) and correctly refuses 3/3 illegal controls, with CPU2 median global solve 1.301129 s. All ten frozen physical routes were then executed once. Goal and terminal-PD acceptance passes 5/10; 2/10 also clear the sampled geometric screen. Overall physical repair acceptance is NOT met.

CD12 now has no sampled SupportGap and positive solid clearance. Solid-envelope violations remain in D07/S04/CE03, including a new S04 regression. Three other routes contain WrongHeight refusals; local progress/trajectory/settling failures also remain. These failures prevent acceptance of v283 as a completed repair.

Every failed outcome and complete recorded video prefix is retained. Five earlier disk-gate launch rejections performed zero physics and are excluded from the ten-attempt denominator. No physical retry, frozen navigation-source change, 0.35 m/0.1 s relaxation, production scene/coordinate special case, policy change or baseline adoption occurred.

## Changes and source identity

- Global route-selection feedback is request-scoped at endpoint attachment cells and connections. Required static checks remain authoritative. Reused references trim the obsolete prefix and validate the remaining route and measured connector. Initial static readiness polls within the original 1500 ms total request budget.
- The common local optimizer/publication/controller collision query now checks the same exact StaticSolidField/static traversability as global planning before the existing live query. No second approximate static ESDF was introduced.
- Warm continuation must agree with both measured cylinder centers within half the existing map resolution; otherwise the existing measured-state initializer owns the seed. This addresses the recorded CD12 stale theoretical seed, without certifying later physical tracking.
- All 50 legal starts require physical support-gap and source-solid extra margins>=0.10 m. Eight geometry-only replacements: G05,CU04,CU08,CU11,CU12,CU13,CM01,CM02. The other 42 starts, all goals/headings and three illegal controls are unchanged. There are exactly 50 distinct spatial start/goal pairs.

Native SHA256: `caeea41b0dbb99ca10ae74b1cf6239535d4c2c4d25327f53988d8afe7b1393f4`. Execution SHA256: `8d22f7e0ebeb90432b6811462d95dd175613bb3e4902d5b4634fe6b0ca38cc71`. The unchanged profile is radius 0.35 m, offset 0.18 m, original vertical envelope, factory PD/RL and scanner period/deadline 0.1 s.

The 171 inherited native tests pass. Endpoint contrasts pass 0/12 on v280 and 12/12 on v283 under translation/rotation. The same source-wall witness with a free live buffer is allowed by the parent local query and rejected by v283. Readiness resumes after 30.475 ms; persistent absence times out 1.50008 s within the original request budget. Recorded CD12 reconstruction found 0.32–0.36 m displacement and 0.43–0.54 rad yaw disagreement despite a clear newly published curve. This reconstruction is not an exact original asynchronous replay.

## Complete 53-case offline result

All 53 scored calls and 53 independent audits finished once. First GPMP passes 47/50 (94%) or 47/49 admitted (95.92%). CPU2 admitted global median/p95/max are 1.301129/1.803867/1.956208 s; all 50 legal median/p95/max are 1.316707/1.916303/2.589370 s. Cold initialization is separate. CS01 retains its no-route failure; CS02/CE01 retain first-GPMP SupportGap failures before successful graph fallback. All ten physical selections pass offline admission. Admitted/published independent support/source/raw checks have no negative hard margin. The minimum global source/raw margins are +0.005710/+0.006174 m at CD12; local minima cap at +0.15 m.

An offline pass means global route admission plus a local publication from the captured request. It is not a complete physical mission rollout.

See [full 53-case table](offline/matrix_table.csv), [offline report](../../versions/v283/OFFLINE_RESULTS.md), [native ledger](offline/native_ledger.json), [audit ledger](offline/audit_ledger.json) and [all 50 start certificates](../../versions/v283/start_admission.json), with an [all 50 old/new start table](all50_start_audit.csv). New 98% versus v281 96% is not an algorithm-only paired comparison because eight starts changed.

## All ten physical attempts

Margins below use 10 Hz measured body poses during navigation, including planning waits and turns, excluding startup and final PD. +0.15 m is a reporting cap. SupportGap clearance and source/raw solids are distinct from the retained ENV soft proxy.

| Route | Recorded terminal | Goal + PD | Geometry | Support free / poses | Physical gap min m | Source solid min m | Raw point min m |
|---|---|---|---|---:|---:|---:|---:|
| A04 | FAILED | FAIL | FAIL | 1959/1969 | 0.150000 | 0.150000 | 0.150000 |
| G05 | FAILED | FAIL | FAIL | 1795/1797 | 0.073152 | 0.150000 | 0.150000 |
| CU06 | FAILED | FAIL | FAIL | 1897/1899 | 0.150000 | 0.119083 | 0.122055 |
| D07 | FINISHED | pass | FAIL | 2634/2634 | 0.142477 | -0.002732 | 0.000241 |
| S04 | FINISHED | pass | FAIL | 346/346 | 0.150000 | -0.130589 | -0.128264 |
| CD12 | FINISHED | pass | pass | 2927/2927 | 0.114431 | 0.015583 | 0.017665 |
| CM02 | FAILED | FAIL | pass | 1465/1465 | 0.071989 | 0.150000 | 0.150000 |
| CM07 | FINISHED | pass | pass | 844/844 | 0.150000 | 0.150000 | 0.150000 |
| CS03 | FAILED | FAIL | pass | 506/506 | 0.150000 | 0.077548 | 0.077677 |
| CE03 | FINISHED | pass | FAIL | 217/217 | 0.150000 | -0.011862 | -0.011825 |

Sampled support refusals occur in: A04, G05, CU06. Negative source-solid margins occur in: D07, S04, CE03. The 14 support refusals are WrongHeight(10); no navigation-window sample has SupportGap(11). A positive gap margin does not waive another hard support verdict.

### Endpoint and remaining failure evidence

There are 1 endpoint-pose rejection log lines; 0 have both static supportFree and solidFree. These typed diagnostics do not substitute for the measured-pose audit.

Global planner action failures, including recovered events:

| Route | Reason and count |
|---|---|
| A04 | `pct_endpoint_pose_rejected role=start xyz= 8.5738248825073242 -2.5569250583648682  2.0021090507507324 yaw=0.73307269810728581 support=10 solid=0 repair=0 live_hint=0` ×1; `pct_shared_traversability_no_route` ×6 |
| G05 | `pct_native_traversability_timeout` ×1; `pct_shared_traversability_no_route` ×6 |
| CU06 | `pct_shared_traversability_no_route` ×6 |
| S04 | `pct_native_traversability_timeout` ×1 |
| CD12 | `pct_shared_traversability_no_route` ×1 |
| CM02 | `pct_native_traversability_timeout` ×1; `pct_shared_traversability_no_route` ×6 |
| CM07 | `pct_native_traversability_timeout` ×1 |
| CS03 | `pct_native_traversability_timeout` ×1 |
| CE03 | `pct_native_traversability_timeout` ×1 |

Failed-route controller/mission errors from the original log:

- A04: `Navigation failed`.
- G05: `Failed to make progress`.
- G05: `Navigation failed`.
- CU06: `Failed to make progress`.
- CU06: `Native SCAN has no executable trajectory before timeout`.
- CU06: `Navigation failed`.
- CM02: `Native SCAN has no executable trajectory before timeout`.
- CM02: `Navigation failed`.
- CS03: `Failed to make progress`.
- CS03: `terminal_settle_timeout`.
- CS03: `Navigation failed`.

Refinement -1008/line-search errors also occur on arrived routes; they are retained in the [full terminal bill](results/failure_terminal_bill.json) and are not by themselves proof of the terminal cause.


### D07, CD12 and CS03 comparison

| Route | v282 source solid min m | v283 source solid min m | v282 physical gap min m | v283 physical gap min m | v283 SupportGap(11) poses |
|---|---:|---:|---:|---:|---:|
| D07 | -0.004884 | -0.002732 | 0.106317 | 0.142477 | 0 |
| CD12 | -0.183185 | 0.015583 | -0.020260 | 0.114431 | 0 |
| CS03 | -0.145919 | 0.077548 | 0.150000 | 0.150000 | 0 |

These are single independent physical attempts with evolving state; the comparison does not isolate one mechanism causally.

**S04 is a regression:** its earlier v282 sampled geometry passed, while this attempt has a negative source/raw solid margin despite goal/PD completion.

### Remaining command/physical tracking gap

At the inspected D07/S04 excursions, all sampled published-curve poses in this reconstruction are source/support-clear. D07 at 270.462830 s has 7.90 mm position discrepancy and 1.629964 rad nominal heading discrepancy; the applied command is pure yaw `[0,0,+1]`. S04 at 37.610958 s has 0.312647 m position discrepancy and applied command `[0,0,-1]`. At the first S04 excursion 36.511562 s, the applied command is zero while horizontal velocity remains about 0.423 m/s in STAND_SETTLING.

The pinned tracker emits final/in-place yaw through `publishStop(yaw_rate)` before advancing curve phase. `LocalMotion::command` checks finite command values but does not apply a measured-pose swept-rotation query to that returned command. This uncovered command-owner gap is outside the new local curve query and warm-start binding. Later work must cover actual heading/terminal commands and zero-command drift with the same geometry; this frozen version is not silently repaired or retried.

See [curve query/geometry reconstruction](results/candidate_recording/recorded_summary.json) and [actual applied-control/source evidence](results/candidate_recording/control_witnesses.json). This uses nominal published-time phase; actual tracker phase freezes during yaw control. It is not an exact asynchronous tracker replay, and time past the nominal curve end does not prove the internal phase expired.

### Factory-PD start screen

The following nearest 10 Hz goal-request samples check the measured post-PD state. They are not maximum drift over the entire crouch/stand trajectory.

| Route | Post-PD XY shift m | Support verdict | Physical gap extra m | Source solid extra m |
|---|---:|---:|---:|---:|
| A04 | 0.096714 | 0 | 0.150000 | 0.150000 |
| G05 | 0.096744 | 0 | 0.073256 | 0.150000 |
| CU06 | 0.096746 | 0 | 0.150000 | 0.150000 |
| D07 | 0.092714 | 0 | 0.150000 | 0.150000 |
| S04 | 0.096798 | 0 | 0.150000 | 0.150000 |
| CD12 | 0.096787 | 0 | 0.150000 | 0.150000 |
| CM02 | 0.096771 | 0 | 0.150000 | 0.150000 |
| CM07 | 0.096712 | 0 | 0.150000 | 0.150000 |
| CS03 | 0.096838 | 0 | 0.150000 | 0.150000 |
| CE03 | 0.096722 | 0 | 0.150000 | 0.150000 |

### Local planning, pauses and scanner timing

| Route | Local success / completed | Pauses >=0.5 s / >=1 s | Max pause s | Scan jobs | Deadline failures | Max scan ms |
|---|---:|---:|---:|---:|---:|---:|
| A04 | 2176/2227 | 4/2 | 87.950150 | 1991 | 0 | 30.356 |
| G05 | 1848/1946 | 4/3 | 81.103226 | 1820 | 0 | 30.259 |
| CU06 | 2192/2264 | 10/5 | 82.940536 | 1923 | 0 | 33.259 |
| D07 | 4798/4911 | 7/5 | 5.559082 | 2666 | 0 | 29.013 |
| S04 | 323/355 | 9/3 | 4.337616 | 379 | 0 | 26.195 |
| CD12 | 5085/5199 | 7/6 | 9.095001 | 2960 | 0 | 30.579 |
| CM02 | 1462/1477 | 2/2 | 76.312271 | 1488 | 0 | 28.296 |
| CM07 | 1591/1636 | 5/3 | 5.057220 | 876 | 0 | 28.989 |
| CS03 | 768/824 | 4/3 | 14.891815 | 530 | 0 | 26.272 |
| CE03 | 313/323 | 2/2 | 10.334320 | 248 | 0 | 25.161 |

Total scans: 14881; deadline failures: 0; native process failures: 0. Successful-local-round rate and measured travel speed are separate. Long failed-route holds remain in pause counts.

## Recovery, storage and media delivery

Five original disk-gate failures (A04/G05/CU06/D07/S04) contain only entry setup files and exact pre-simulator tracebacks; the processes exited after about 0.03 s. The original misleading early-ledger status is preserved with an evidence-based [correction receipt](results/recovery/zero_physics_launch_failures01/summary.json). All failed task directories/receipts remain remote with per-file hashes.

The inactive 5,288,964,998 byte archive was copied to `/home/sun/vla_exec/relocated_archives/mac_archive_20261012`; all 37 files/modes were verified before freeing the redundant source. The old `/data` path remains a symlink. [Relocation receipt](results/recovery/archive_relocation.json) records free space rising from 10,550,161,408 to 15,839,219,712 bytes. No source or gate changed.

All ten real local MP4 s total 171,510,095 bytes; the primary compact evidence bundle contains 465 files totaling 20,481,372 bytes. Each video has matching source-state coverage, full decode, SHA256, first/last recorded-state and zero-render-physics checks. At least two local frames per route were visually inspected. See [video index](delivered/README.md), [return inventory](physical_return/return_inventory.json), [visual review](results/visual_review.json), [physical table](physical_table.csv) and [machine-readable summary](physical_summary.json).

CM07 uses camera-only revision03 because local review found a pillar blocking the original terminal view. The near follow camera and wider FOV restore full-body visibility; scene geometry is unchanged. All 2951 source frame indices/times, physical input hashes and terminal labels match the [original view](physical_return/CM07/results/camera_revision_verification.json). Original camera01 and intermediate02 masters/source snapshots remain remote; the original failed visual sample is retained locally. No physical attempt was repeated.

Heavy raw/archive/build data remains at `gpu5070ti:/home/sun/vla_exec/physical_runs_v283/` and the private native/benchmark root. Per-case capture snapshot receipts bind remote archive sizes and hashes. Regenerate media from unchanged captured states using the locally versioned audit tools; never repeat formal physics for a video.

The [physical resource summary](results/physical_resource_summary.json) contains 38 one-minute observations during formal dispatches: no sampled GPU-compute overlap or resource-gate failure, minimum available RAM 25,044,774,912 bytes and output free disk 46,489,845,760 bytes. This is not continuous exclusivity proof. The [post-physics full source/install check](results/post_all_physics_source_gate.json) passes.

All physical admission gates were retained. After six videos, the recorded-state dispatcher was resumed with separate rendering admission (all ten physical cases already closed, 8 GiB available RAM, 2 GiB free GPU memory, 10 GiB disk; nice10). This permits shared-GPU video work without changing any physical source, threshold, run or outcome. [Transition](results/render_dispatch_transition.json) and [render resource probes](results/render_resource_observations.jsonl) retain the original completed six results and subsequent peer GPU overlap.

## Acceptance and limits

- AC3/AC4/AC5: all 50 starts, fixed profile/version contracts and complete offline gate pass.
- AC1/AC2: component and recorded-input contrasts pass; remaining physical failures and typed rejection evidence above determine the narrower supported claim.
- AC6: FAILS the declared all-ten sampled geometry / endpoint screen. This version must not be presented as a completed physical repair.
- AC7: ten full-prefix local videos and verified compact evidence delivered.

Ten-hertz torso geometry does not certify continuous motion or foot contact. One attempt per route does not establish statistical reliability. CPU2 is a shared-host protocol, not exclusive-host timing. Resource observations and every unsuccessful prefix are preserved. No frozen failed version is rewritten and no selected baseline is advanced.

Report inputs: physical summary SHA256 `3e4c8002e90d5b59ce506890e475274ae50f7dfa9c0827b4d72773e8df8cdcd8`; return inventory SHA256 `f5fd5609ee4e39b117673ea8c027aaa43c870ad7ec7a5c55ed972722d5d9fa68`.
