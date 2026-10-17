# v204 Mac attempt 01 — original full route passed

**Result: FINISHED. The dog traversed the original complete Building route and
passed the inherited v196 full-route gate, including final PD standing.**
One continuous physical episode, 143,540 actual integration steps, 143.591 s
physical duration and 78.948 m recorded body path. No mid-route reset, reported
fall, dropped physics step, or second physical attempt.

## Comparison with the preserved v196 attempt

| Measurement | v196 | v204 |
|---|---:|---:|
| Original full-route gate | Passed | Passed |
| Final PD hold | Passed | Passed |
| Navigation simulation duration | 115.561 s | 132.570 s |
| Navigation wall duration | 118.348 s | 155.602 s |
| Actual real-time factor | 0.976 | 0.852 |
| Successful local planning frequency | 24.631 Hz | 14.762 Hz |
| Controller publication frequency | 29.935 Hz | 29.833 Hz |
| Final XY error | 0.1325 m | 0.1841 m |
| Final height error | 0.00616 m | 0.00730 m |
| Final yaw error | 0.1573 rad | 0.1628 rad |

v204 completes this route, but this capture is slower: navigation wall duration
increased 31.48%, and successful local planning frequency decreased 40.07%.
The controller still publishes approximately 30 Hz. This does not establish the
cause of the slowdown or repeated reliability. No tuning or extra trial was
performed to improve the result. Navigation duration excludes physical startup;
the 143.591 s total physical time is a different interval.

The longest low-speed interval was 6.848 simulation seconds at terminal holding.
There were zero completed task-level Wait recoveries, zero progress-checker
failures and zero terminal-settle timeouts. Thus this physical capture exercises
arrival/hold, but ordinary retry and terminal-timeout branches still have their
separate v204 component evidence.

## Identity and acceptance

- Frozen v204 navigation manifest:
  `5d7ee82e02b1c55ebfd78815919487c6a5100ca557544e91aac81407730c1419`.
- Mac Warp CPU physics uses the inherited v198 telemetry producer and the same
  v196 Building geometry, original start/goal, policy, factory/PD startup, native
  configuration, RTF target and original long-route driver.
- The installed overlay was checked before launch, and real running process maps
  record loaded v204 PCT, SCAN, controller and BT libraries with SHA-256.
- `executed_full_route_verifier.py` retains the original v196 acceptance predicates;
  only its required version identity and result description are rebound to v204.
  It checks the true initial state, continuous increasing physical time, position
  continuity, original target, canonical terminal pose, final XYZ/yaw, PD hold and
  host/container final-state byte identity.
- `source_gate_before.json` and `source_gate_after.json` match. Frozen v196, v198,
  v204 and all 298 composed source files remained unchanged.

The execution adapter lives only in this appended result directory. It selects
v204's installed components, v198 physical telemetry and the v203 terrain bundle;
it does not edit navigation, physics or locomotion policies. `execution.json`
records process completion, while `full_route_verification.json` records semantic
acceptance. The historical component-only results and previous versions remain.

## Evidence

See `full_route_verification.json`, `trial_analysis.json`, `comparison.json`,
`metrics.json`, `loaded_runtime_libraries.json`, and the original source copies
inside the raw capture. `trial_archive_manifest.json` describes all 119 closed
capture files, including the verified raw ZIP containing 1,329 members.

Raw local capture:
`/private/tmp/vla_v204_physics_20261015/runs/v204_mac_full_attempt01`.
Archive: 422,348,800 bytes, SHA-256
`cec3c5bdc7ac9857c93175fe552b057a379523f7bb3ca97d5e4cdd6d1ea77163`.
Remote archive verified on gpu5070ti at
`/data/sun/vla_mppi_20261009/mac_archive_v204_20261015/v204_mac_full_attempt01.tar`.
Its complete SHA-256 and all 119 tar members match local evidence; see
`remote_verification.json`. No raw local data was deleted.
