# gpu40901 v235 physical attempt and comparison

**FAILED before navigation goal.** Exactly one physical attempt was executed;
there was no automatic rerun. The full route,45–55s staircase window and terminal
PD were not exercised. The accepted physical baseline remainsv232/v233.

| Item | Result |
|---|---|
| Source/install/offline tests | Exactv232 source; all14 packages;165 cases/186 records pass on40901 |
| Complete host-entry preflight | Actual graph12s and generated profile pass; zero physics |
| Invariants | Original RL/hash, original start/goal and0.35m hard collision/support guards unchanged |
| Physical run | v235_linux_full_attempt01; recorder exit1 after68.576s wall, including compilation/startup |
| Retained physical record | 227 states; last12.801543235778809s;16 completed scans |
| Failure | `Captured scan did not finish before the next sensor period` |
| Goal/terminal | Goal not sent; original result.json and finish_request absent; shared terminal proof fails |
| Full-route/stair/terminal PD | Not reached; no success-rate or edge-margin comparison possible |

Completed scan times span39.6–83.1ms, mean62.1ms. The failed pending scan's
complete latency was not recorded. Warm zero-step scan36.6ms does not establish
headroom during concurrent physics. The2-CPU physics affinity and shared-host
load are diagnosis leads; this attempt does not establish exclusive causation.
Do not relax the0.1s scanner period or navigation admission thresholds.

The native container uses4 CPUs/6GiB/shares128; host physics2 CPUs/nice19.
No peer signals, shared Python/driver changes or GPU reservation were made.
Before/after process identities are retained; exited/replaced peer entries do
not prove this task stopped them or establish unchanged training throughput.

## Evidence preservation

Heavy artifacts stay at
`gpu40901:/home/ubuntu/sun/vla_v234_20261017/trials/v235_linux_full_attempt01`.
Global lsof inaccessible-mount warnings prevented inherited pruning. All
originals remain. A separate non-pruning snapshot verifies every retained member:
7,615,632bytes, SHAbc35eb1d1604410779d684ec00930eb83a4a27f98fe66d6808b038ddfa3f5a16.
See results/capture_snapshot.json for member hashes and retrieval location.

results/outcome.json reports failure without synthesizing a recorder result.
The original analyzer and route gate remain failed; diagnostic display scalars
are labeled pre-navigation and do not claim planner throughput.

## Videos

The412-frame partial video uses only original states: startup sampled by actual
physics time, the short post-startup segment by original wall timestamps.
All frame indices/times and full MP4 decode are verified with zero new physics.
No route/spline is displayed because no navigation goal/path was recorded.

The three-panel comparison showsv219,5070Tiv232/v233 and40901v232/v235 on the
same physical-time grid. After12.802s the40901 panel explicitly shows recording
ended. The45–55s clip therefore shows no40901 stair traversal. Historical
panels are reused from the already verified local comparison video;5070Ti was
not accessed. Cross-host timings are descriptive, not an algorithm ablation.

- [Actual partial recording](delivered/v235_partial_attempt01.mp4)
- [Physical-time comparison](delivered/full_physics_comparison.mp4)
- [45–55s window,40901 not reached](delivered/stairs_physics_45_55.mp4)

Display preparation failures are retained: attempt01 omitted the explicitv216
adapter; attempt02 encountered the qualified renderer's no-spline guard;
attempt03 selects the original adapter and supports a verified empty overlay.
These are recorded-state display attempts, with no further physical execution.

Next: profile captured-scan scheduling under bounded shared-host execution and
record sufficient timing before any separately authorized new physical trial.

## Local verification

All54 returned payloads match remote SHA/size (13,191,197bytes). The full
physical-time comparison has3708 frames through123.564s; the stair clip301
frames. Direct visual review confirms correctv235/40901 labels, recorded
standing at the original start and an explicit ended panel after12.802s.
No build cache, native binary, raw NPZ or archive was returned locally.
