# v232: one original-route closed-loop physical comparison

## Result and scope

The sole physical attempt **passes the unchanged original full-route gate**.
Frozen v232 navigation (`ff4cb515`) runs under frozen v233 execution bindings,
v216 locomotion and the original v219 start/goal. It passes the previous
approximately 46.7 s abort point, traverses the stairs, reaches the original
goal and closes with a matching FINISHED request plus measured PD stand.
No SIGABRT, critical-process failure, fall or dropped physics step is recorded.
This is one successful route, not repeated reliability or sustained-30-Hz validation.
The prior v219/v220 reference remains available for human comparison.

The approved commits preceding this run are `1ad1862d` (prior v230/v231 physical
audit) and `ff4cb515` (v232 repair/offline evidence). Neither includes compiler
caches. v233 is an execution binding, not a new navigation algorithm.

## Boundaries actually verified

- Same original historical_full input, spawn/yaw/goal and factory-PD startup;
  exact RL policy SHA-256
  `7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b`.
- Same radius/support guard 0.35 m, cylinder offset 0.18 m, upper/lower inflation
  0.55/0.35 m, body/reference height 0.30 m, speed, controller goal/freshness
  gates and ENV225 bytes. No archived seed exists; no same-seed claim.
- All 317 composed source and 607 installed files match frozen v232 offline
  receipt; actual 14-package graph selects the v232 install. Both MissionBridge
  modules and installed launch resolve under `/work/install/lite3_nav2_bridge`.
- v233 graph adapter executes frozen v232 graph with VERSION still v232 and
  only adapts the execution tag. The actual launched
  `executed_long_route_driver_v232.py` matches frozen v232 driver bytes.
  Post-run source/install/driver parity passes.
- A 12-second no-physics graph/profile preflight passes. The first formal entry
  was stopped by a port-in-use check **before the formal trial directory or
  any physics existed**; the port cleared and the unchanged frozen entry then
  ran exactly once. No physical retry, reset or tuning was performed.

See `results/execution_receipts/actual_profile_equivalence.json`,
`post_run_source_parity.json`, `v232_runtime_binding.json`, and original
`nav2_params*.yaml` / `planner.yaml` copies.

## Physical outcomes

| Measurement | v219 reference | v230 / run v231 | v232 / run v233 |
|---|---:|---:|---:|
| Original full-route gate | pass | fail | **pass** |
| Physics end, s | 123.564 | 600.517 | **121.565** |
| Recorded terminal | FINISHED | absent; bounded end | **FINISHED** |
| Controller SIGABRT | absent | approximately 46.7 s | **absent** |
| Final measured PD suffix, s | 4.338 | post-crash stand, no arrival | **4.398** |
| Final XY error, m | 0.0939 | not arrived | **0.1412** |

For v233, final yaw error is 0.0726404 rad (4.162 degrees), final body-height
error 0.0062073 m; final control is FIXED_STAND, policy_owns_joints=false,
command `[0,0,0]`. Measured final stand suffix is 117.167236–121.564819 s,
221 telemetry samples. Initial recorded state precedes the first physics step;
5668 video states are strictly increasing, maximum consecutive position step
0.04846 m. The shared host/container finish bytes agree.

Physics records 121620 steps, actual navigation RTF 0.999715, zero dropped
steps. The original analyzer succeeds and the unmodified spatial/terminal
verifier (execution tag only rebound) returns `passed=true`. Raw archive
integrity checks all 1110 members, 322757248 bytes, SHA-256
`5bbfd9a9be771275704523efece5f1531b605f6fae8f64929ab12b6475e5a8eb`.

## Stair window and matching geometry

Rounds below are completed nominal replans starting in [45,55) physical/ROS
seconds; internal seed attempts are excluded. A pause requires measured XY
speed below 0.05 m/s for at least one second. Body edge margin uses the same
frozen field and actual body XYZ/yaw for all runs, capped at an additional
0.15 m beyond the 0.35 m envelope. It is an offline geometry diagnostic,
not leg contact or a proof for every instant between samples.

| [45,55) measurement | v219 | v231 | v233 |
|---|---:|---:|---:|
| Completed / successful rounds | 208 / 118 | 42 / 42, then missing | **275 / 273** |
| Success fraction of completed rounds | 56.73% | incomplete window | **99.27%** |
| Incomplete starts | 0 | 1 | **0** |
| Low-speed pause overlap, s | 3.298 | 7.794, largely post-abort | **0** |
| Minimum extra body edge margin, m | -0.02316 | +0.15, largely post-abort | **+0.15 (cap)** |
| Negative-margin samples / 100 | 18 | 0, largely post-abort | **0** |

v233 has completed replans in every one-second bin and no process gap. Its
100/100 window samples and all 45 samples in the same spatial stair box reach
the capped target. Stair-box traversal spans 43.807552–48.205135 s, compared
with v219 44.607113–53.102444 s. Thus both time and spatial comparisons are
reported. v231 remains at that box after its abort and is explicitly split;
its standing margins and 42/42 early rounds do not qualify the full window.
The common pre-abort prefix [45,46.686) is separately preserved.

## Limits and remaining work

The original analyzer's `full_qualification=false` and
`sustained_30hz_validated=false` remain unchanged. This successful route has
2837 completed / 2813 successful rounds, average successful frequency
25.44 Hz, p95 solve 30.37 ms, p99 110.17 ms, maximum 389.14 ms. Thirty rounds
exceed 100 ms, none exceed one second. It includes 25 optimizer repair-failure
messages and five emergency transitions without process death. Route success
does not imply that every local solve succeeds.

Only one global route delivery is recorded; no `pct_live_feedback` count-change
message appears. This run establishes combined route execution after the
exception repair; it does not demonstrate a feedback-induced detour or isolate
the causal contribution of soft costs, height alignment and feedback. Two
initial PCT evidence-unavailable requests are preserved in the runtime context.
No extra physical experiment was run to investigate them.

## Review artifacts

- `delivered/v232_full_attempt01.mp4`: entire new attempt, including startup,
  all pauses and final measured PD stand; causal v220 recorded-state display.
- `delivered/full_physics_comparison.mp4`: v219 / v231 / v233 on one physical
  clock. Recordings that end become black with an end-time label; v231's
  600-second failed record is retained in full.
- `delivered/stairs_physics_45_55.mp4`: the same three-way physical-time window.
- `results/full_route_verification.json`, `outcome.json`, `metrics.json`,
  `comparison.json`, `body_edge_margin_comparison.json`,
  `common_active_prefix.json`, `terminal_pd_hold.json` and execution receipts.

Display creates zero new physics steps. Frame/source/curve causality, complete
first/last states, whole MP4 decode and returned regular-file hashes are
verified in the display/delivery receipts. Large raw captures and renderer or
compiler work directories remain on gpu5070ti at
`/data/sun/vla_mppi_20261009/trials/v233_linux_full_attempt01/`.
