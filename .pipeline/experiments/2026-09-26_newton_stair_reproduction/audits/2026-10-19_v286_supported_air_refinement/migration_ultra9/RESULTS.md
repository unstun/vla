# v286: offline gate passed; physical acceptance failed

**结论：离线 49/50、1.321 s 达标；十条各单次实跑全部失败，到达与几何双过均为 0/10。不能把 v286 称为已修复。**

ultra9 已按批准清单释放约 38.6 GiB，全部模型、实验归档与视频保留。十条完整失败视频均已返回本地。

## Outcome and scope

All 53 new-host native calls and independent audit entries closed. All ten selected routes then received one physical attempt, totaling 590,340 recorded physics steps. No physical retry or baseline promotion occurred. A04/G05 terminate with `controller_server -11`; the other eight terminate with Nav2 failure. Arrival/terminal-PD acceptance falls from 6/10 in the returned v285 batch to 0/10 here.

The new CPU, rebuilt binaries and ROS image differ from the inaccessible 9700x run. These are descriptive cross-batch results, not a controlled same-host causal estimate. The physical acceptance requirement is nevertheless unmet.

## Implemented changes and direct checks

- Supported Unknown air requires in-map, zero inflation, valid support/layer/edge/freshness checks, and clear exact source geometry. Observed occupancy and support gaps remain refused.
- Endpoint projection checks terrain-aligned candidates using real neighboring tangents; target-neighborhood checks use terrain A*. The quantization-residual segment check was removed.
- The second refinement objective no longer adds environmental cost. Rebound and final checks remain. Travel and phase use the same smooth scale with a 0.5 floor; the inherited 0.6/1.0 rad transition remains.
- A first-stage exact-source quartic soft buffer of 0.055 m was added. There was no existing exact-source 0.02 m knob in v285: this is a new objective term, not merely a parameter increment. ENV225 remains in the first stage; GPMP source repulsion was not reintroduced.

Hard radius 0.35 m, double-cylinder offset 0.18 m, body clearance 0.3 m, scanner period/deadline 0.1 s, factory PD/RL and scalar goal gates remain unchanged. No scene/coordinate navigation branch was added. [Frozen changes](../../../versions/v286/changes.patch), [native qualification](../../../versions/v286/qualification_report.json).

ultra9 rebuilt all 14 packages from 329 exact source files and the separate frozen v248 bridge from 20 files. The returned 20 XML suites contain 174 passing executions; repair/terrain/phase probes pass 13/13, 4/4 and 4/4. The original scanner deadline tests pass 7/7; causal overlay/timeline tests pass 10/10 and 4/4. These component checks do not establish streaming physical success.

## Complete 50+3 offline gate

| Metric | Result |
|---|---:|
| Legal end-to-end | 49/50 (98%) |
| Illegal controls refused | 3/3 |
| Admitted global median | 1.321080 s |
| All 50 legal global median | 1.355365 s |
| Global p95 / maximum | 1.827093 / 1.872022 s |
| First GPMP pass | 47/49 admitted; 47/50 all legal |
| Negative source/raw margins on admitted global or published local paths | 0 |
| Actual 50-start minimum extra gap / solid | 0.1499999 / 0.1441992 m |

The unchanged legal CS01 request returns `pct_no_route`; all ten selected cases pass the offline gate. All 50 legal spatial pairs remain distinct. The existing G05 replacement and uniform >=0.10 m start certificates are retained. Timing uses the original 2-CPU/6-GiB profile; initialization is separately reported.

All 11 core geometry files and three publisher metadata files match the original frozen hashes. All 53 scenario/endpoint hashes match; their nominal zero-step scans were freshly captured on ultra9, not claimed as old capture-byte replicas. Maximum nominal scan capture: 24.0433 ms. [Full gate](offline/offline_gate.json), [53-case table](offline/matrix_table.csv), [50-start audit](evidence/current_geometry01.json), [local return verification](evidence/local_offline_verification01.json).

The inherited offline probe disables asynchronous mapping and uses a controlled fixture clock. It does not advance live sensor age throughout a slow optimization as the physical run does. Passing this gate is not evidence of streaming timing closure. See [probe source](../../../versions/v280/native_probe.cpp).

## Ten single physical attempts

| Route | Recorded terminal | Physics s | Measured path m | No executable | Inside log | Max local round ms |
|---|---|---:|---:|---:|---:|---:|
| [A04](delivered/v286_A04_full_attempt01.mp4) | controller -11 | 56.36 | 28.422 | 1 | 19 | 906.19 |
| [G05](delivered/v286_G05_full_attempt01.mp4) | controller -11 | 50.74 | 27.724 | 0 | 4 | 352.26 |
| [CU06](delivered/v286_CU06_full_attempt01.mp4) | Nav2 failed | 93.92 | 32.681 | 6 | 101 | 1317.01 |
| [D07](delivered/v286_D07_full_attempt01.mp4) | Nav2 failed | 66.89 | 12.735 | 7 | 96 | 1685.43 |
| [S04](delivered/v286_S04_full_attempt01.mp4) | Nav2 failed | 51.38 | 0.003 | 6 | 42 | 634.64 |
| [CD12](delivered/v286_CD12_full_attempt01.mp4) | Nav2 failed | 54.66 | 0.856 | 7 | 218 | 3317.11 |
| [CM02](delivered/v286_CM02_full_attempt01.mp4) | Nav2 failed | 49.48 | 1.640 | 6 | 140 | 3009.46 |
| [CM07](delivered/v286_CM07_full_attempt01.mp4) | Nav2 failed | 57.74 | 10.288 | 6 | 71 | 1330.61 |
| [CS03](delivered/v286_CS03_full_attempt01.mp4) | Nav2 failed | 51.46 | 0.003 | 6 | 37 | 639.85 |
| [CE03](delivered/v286_CE03_full_attempt01.mp4) | Nav2 failed | 57.48 | 3.790 | 6 | 131 | 1132.43 |

All 4,796 recorded scanner jobs retain the 0.1 s period, with zero deadline failures; maximum completed scan 45.384 ms. This does not mean every local planning round fits 100 ms: the maximum local round is 3317.11 ms. S04/CS03 record about 3 mm of body motion and no published native spline; CD12 travels only 0.856 m. Their clear recorded prefixes do not validate traversal of the original corner-risk region.

All ten preserve one global epoch and the original global geometry or its suffix. Global endpoint rejection lines remain zero. All actual submitted/published terminal headings match the frozen requests. [Heading proof](evidence/explicit_heading_verification01.json), [physical summary](physical_summary.json), [terminal/error bill](physical_return/failure_terminal_bill.json).

## Geometry: clear recorded prefixes, incomplete routes

| Route | Navigation support free | Extra gap min m | Source-solid min m | Raw-point min m |
|---|---:|---:|---:|---:|
| A04 | 430/430 | 0.150000 | 0.150000 | 0.150000 |
| G05 | 373/373 | 0.073152 | 0.150000 | 0.150000 |
| CU06 | 805/805 | 0.052380 | 0.142819 | 0.142925 |
| D07 | 528/528 | 0.030482 | 0.150000 | 0.150000 |
| S04 | 381/381 | 0.150000 | 0.150000 | 0.150000 |
| CD12 | 412/412 | 0.150000 | 0.150000 | 0.150000 |
| CM02 | 361/361 | 0.079468 | 0.150000 | 0.150000 |
| CM07 | 443/443 | 0.150000 | 0.150000 | 0.150000 |
| CS03 | 382/382 | 0.150000 | 0.150000 | 0.150000 |
| CE03 | 442/442 | 0.150000 | 0.150000 | 0.150000 |

All ten sensor-recorded prefixes, including the post-navigation tail, have nonnegative sampled support-gap/source/raw margins. The inherited field name `all_recorded` refers to the available10-Hz sensor stream, which starts after factory startup; it must not be interpreted as the initial PD segment. Values saturate at +0.15 m. These are sampled-body audits, not continuous-time or foot-contact certification. Arrival plus full-route geometric acceptance is **0/10**, not 10/10. CD12 did not complete its route, so removal of its former -1.84 cm corner excursion is **not validated**.

The separate startup audit uses all 1380 original factory video-state poses (138 per case,0 to10.9608s). All ten sampled factory envelopes are clear. Maximum observed PD planar drift is 0.121814m. G05 minimum startup extra gap is 0.048217m, with source/raw margins +0.15m. Factory crouch returns the expected nominal-standing-height verdict10 on111/138frames per case; this is separate from support-gap/solid geometry. [Startup proof](startup_return/summary.json).

The observed12.2cm drift exceeds the illustrative10cm admission floor. This frozen cohort actually has at least14.4cm extra initial solid margin and15cm reported initial gap, and its ten sampled startups pass. A10cm rule alone is not a demonstrated general bound for future starts.

## Literal error comparison

| Same extraction rule | v285 | v286 |
|---|---:|---:|
| Ran out of pool | 23 | 0 |
| Endpoint adjustment failed | 218 | 0 |
| A-star failed | 279 | 6 |
| The robot is inside an obstacle | 314 | 859 |
| L-BFGS -1008 | 4915 | 84 |
| Native SCAN has no executable trajectory | 20 | 51 |

v286 has 4 refinement-stage -1008 mentions and 80 rebound-stage mentions. CU06 refinement-stage -1008 falls to one, but its progress failure remains one and its no-executable count becomes six. Counts are log mentions with different exposure durations; they are not independent failure probabilities. [Exact counter comparison](error_comparison.csv), [returned v285 counters](../results/reference_v285_error_counts.json).

Unknown 6:0 mentions are zero, while verdict 7 appears with voxel2 (177 mentions) and voxel0 (20). In v285 the raw Unknown test preceded the inflation test, so 6:0 alone never proved a zero inflation bit. Verdict7 is the shared StaticObstacle enum and may come from observed occupancy or the source-solid normalization check. A counter label change cannot establish successful removal of false rejection.

The optimizer message “The robot is inside an obstacle” is emitted when a backward control-point search finds no Boolean-free point. It is not a direct measured-body or FSM-start collision test; stale/missing/height failures can also return non-free. The inherited `initial_spline_collision` logger is itself an unconditional recovery diagnostic in one candidate-time window, including a +0.05 m X probe. Those logs are not collision-event witnesses. Corrected diagnostic JSON is explicitly marked `diagnostic_only` and `collision_event_proven=false`; the first interpretation is preserved separately. [Source/counter review](REVIEW.md), [semantic correction](evidence/initial_point_diagnostic_semantics02.json).

## Remaining failure boundary

1. A04/G05 controller segmentation faults are unresolved. No corresponding core/backtrace was available; no C++ root cause is claimed.
2. Local availability regresses: inside-log mentions increase to 859 and no-executable mentions to 51. The fresh-air and A* changes are insufficient to establish executable streaming navigation.
3. Actual S04 logs contain a roughly 590 ms rebound round and cloud age 0.6903 s, above the unchanged 0.35 s freshness parameter. Local timing closure and typed per-control-point refusal reasons require replay analysis. An extra exact-source objective is a plausible timing contributor, but no controlled ablation has established causality.
4. The exact S04 SCAN YAML is byte-identical to the returned v285 hash, PCT parameters compare equal, and actual navigation RTF is 0.9999615. Configuration drift was not found. CPU/image/binary differences remain an experimental confound. [Parameter comparison](evidence/full_profile_comparison01.json).

The next evidence needed is a zero-physics replay around the first refusal/crash with typed query/input-age provenance, plus a local source-cost ablation and a native backtrace. Do not add more gates, relax 0.35 m/0.1 s, or overwrite frozen v286. The requested physical repair remains unachieved.

## Storage, provenance and delivery

Only the approved old Noetic image and 543 downloaded Conda archives were removed. Immediate free space rose 74.6133 -> 113.1768 GiB (+38.5636 GiB). Models, teacher banks, installed environments, experiment archives, videos and the active Foxy image were retained. [Cleanup report and exact receipts](STORAGE.md).

Original 9700x evidence remains a separate inaccessible batch (53 timed calls, last confirmed 10/53 independent audits, zero physical attempts). It was not overwritten or combined with new-host timing. The first ultra9 deployment batch stopped after 21 invocations because a legacy raw-control mount path was missing; all failure bytes remain in `benchmark_failed_binding01`. Restoring the already hash-matching field path changed no navigation bytes. [Migration record](MIGRATION.md).

- Original frozen v286 native manifest: `49b08d38cd2fddf5d26fb9f5e8661d513d749697dcb46f23e7eb0b80066e8601`.
- New-host native/input manifest: `ffd9194f5563b6abc68ffe3ea4d641f01061b309e86e1d9d53aa565fa431e4bc`.
- New-host physical manifest: `5381e00b41df419696f58c8d42a95e650999f69c0c8373dd26ff7dd7fbd3e741`.

Local source of truth is `/Users/sun/tongbu/study/phdproject/vla`; heavy raw data remains at `/home/ubuntu/sun/vla_v286_20261020/physical_runs` on ultra9. The inherited managed retention returns2 because `lsof` warns about unrelated inaccessible mounts; original files are retained and verified non-pruning snapshots are used. That return code is separate from the recorded navigation terminal. No data loss or physical rerun was used to regenerate media.

All ten regular MP4s (45,132,111 bytes) and 716 compact files (10,914,262 bytes) are locally hash-verified. Videos are 1280x720,30FPS, full decoded; complete first/last states and causal overlays are checked. Twenty decoded temporal samples were visually reviewed. No new physics was used for rendering. [Ten actual videos](delivered/README.md), [media verification](evidence/local_media_verification01.json), [return inventory](physical_return/return_inventory.json).

**Final status: implemented and executed; offline validated; physical repair not validated. No automatic commit, archive or baseline promotion.**
