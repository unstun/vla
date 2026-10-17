# v219: full historical route and final PD hold passed

One original-start gpu5070ti run passed the unchanged full-route gate. PCT/SCAN
geometric decisions, velocity tracking, map, policy and motor limits are unchanged.
v216 supplies four-foot supported admission and immediate transition abort;
v219 requests a new global route after 0.75 s of consecutive failed local rounds,
without discarding a still-usable trajectory. No periodic global refresh.

## Physical result

- Terminal: FINISHED; no fall; 123.564 s actual physics.
- Measured body path: 77.789 m.
- Final XY error: 0.093919 m; height error:
  0.007980 m; yaw error: 0.104949 rad.
- Final fixed PD: 4.337616 s, gains 60/1,
  policy_owns_joints=false, exact zero command.
- Final FL/FR/HL/HR support: [42.88542938232422, 41.27605438232422, 18.432781219482422, 27.700550079345703] N.
- Final measured speed: 0.0002283 m/s.

## Stair window, original physics seconds 45-55

| Version | Successful / completed local rounds | Success | Max body tilt | Result |
|---|---:|---:|---:|---|
| v210 | 250/253 | 98.81% | 17.61 deg | Full route passed |
| v212 | 29/137 | 21.17% | 63.48 deg | Fell at 54.14 s |
| v217 | 2/181 | 1.10% | 28.14 deg | Stood upright; navigation failed |
| v219 | 118/208 | 56.73% | 25.22 deg | Recovered; full route passed |

v212's available window ends at its fall. These are completed native planning
rounds, not counts of individual failed A-star seeds inside a round. Whole-window
tilt includes walking on steps; it is not the tilt during PD transfer. Normal
swing legs can measure zero support during walking. PD admission is checked
separately: both v219 entries had all feet >=10 N. Stair entry at 48.105 s had
forces [80.07,30.27,12.42,29.13] N. See stair_pd_support.json for actual transfer
support and tilt, and staircase_comparison.json for the full breakdown.

The stair STAND_TRANSITION itself lasted 48.105-50.104 s: maximum tilt
4.846 deg; per-foot minima [69.58,24.21,7.97,11.31] N. After transfer, FIXED_STAND
lost hind support (first loss at 50.504 s) and reached 18.227 deg tilt. The
unchanged fixed-hold disturbance rule returned to RL at decision time 50.864 s.
RL recovered, and its walking/recovery peak was 25.219 deg. This is a recovered
disturbance, not an uninterrupted stable stair hold. No transition-abort event
occurred in this run; immediate transition abort is covered by component tests.

The route is now completed, but stair planning is less smooth than v210 in this
single comparison. Do not present the 56.73% success rate as parity with 98.81%.

## Diagnosis and actual recovery

The local reference projection was recomputed each round; it was not a stale
index stuck at the start of the route. Captured v212 rounds rejected nearby
prefix points as occupied and failed searches to other prefixes. A far-target
connectivity query also exceeded the bounded A-star pool and fell back normally.
The failure became persistent because no native planning-result signal reached
the global-plan owner. An expired braking curve still satisfied haveTrajectory(),
so its failure was hidden until a later emergency/long timeout. Periodic refresh
had previously supplied new routes independently of that missing signal.

v217 exposed expired-curve starvation but aborted FollowPath only after stopping.
It did request a new global path, yet the captured optimizer then rejected initial
control points near the current body as obstacles. Six retries exhausted. That
failure is retained and is not overwritten by this passing result.

v219 adds only a direct boolean result callback at the two existing native local
planning sites, stored in MotionExchange with generation/revision binding.
Continuous failure requests a replan for the exact current Path header. The BT
ignores old-route requests and keeps FollowPath active while PCT computes. A
successful local round or route replacement resets failure history. The existing
ordinary recovery and terminal stand-timeout non-retry branch remain.

Actual request times: 29.630,47.565,49.689,50.519 s. A normal starvation recovery
also occurred near 47.80 s; do not claim every pause disappeared. Observed global
route deliveries were 7, versus v210's 99 over its full run. These are delivered
route messages, not an instrumented count of internal PCT solver calls.

## Verification and retained evidence

Four packages built on gpu5070ti; 132 distinct tests passed (149 includes 17 CTest
wrappers), including installed BT route-bound requests and continuing FollowPath,
old-route rejection, native status revision isolation, ordinary retry exhaustion,
and typed terminal-timeout no-retry. v216 has 14 passing hold tests. A Foxy API
compatibility build error and test-environment errors were retained and corrected
before physics. All final tests have zero failures and skips.

Native callback removal reproduces the exact parent source SHA-256, proving no
SCAN geometry/search/optimizer edits (native_geometry_equivalence.json). The
parent native files match local frozen v202, inherited by v206. Runtime receipts
and source identities were verified before and after execution. The original
full-route verifier only rebinds the version label.

Raw data stays at /data/sun/vla_mppi_20261009/trials/v219_linux_full_attempt01/runs/v219_linux_full_attempt01; raw_capture.zip is 329590458 bytes,
SHA-256 5b6b4f430fa90008ea6d4e332afdfa1a3ac13ebbe5ddaec3704dad69f24b4fb0, all 1130 members verified.
Local reports, source and video retain provenance. Reanalysis: run analyze_full.py
and window_report.py with the pinned Newton worker Python on gpu5070ti. v220
renders the original capture only; v218 preserves the failed v217 video.

This is one successful full-route condition, not repeated reliability evidence.
