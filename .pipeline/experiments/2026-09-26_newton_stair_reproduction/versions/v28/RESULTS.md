# v28 physical trial: no native crash, route failed on odom_stale

Component results in `COMPONENT_RESULTS.md` remain valid. The trial followed
`PHYSICAL_RUN_PLAN.md`, with exactly `v27_historical_full01`'s profile.

## Outcome of `v28_historical_full01`

- **Gates and route:** the version, native-identity and reviewed-candidate gates
  passed. The PCT route is the historical profile (automatic layers, historical
  route length and goal level all pass). The goal was accepted at 12.27 s sim.
- **No native crash:** SCAN survived v27's 13.24 s crash point and ran until the
  episode ended at 17.68 s sim. `scan.log`, `native_graph.log` and `run.log`
  contain no segmentation fault, abort or core dump. There is no
  `native_failure.json`, and the guard's fail-closed abort fired 379 times live.
  The live run does not prove that seed 269's exact state recurred. Removal of
  the live crash is supported, not proven.
- **Navigation failed:** the first failing gate is `odom_stale`, raised by the
  native controller for trajectory 2 at 15.563 s sim, then by the FSM. The
  driver finished `case_failed`.
  - Net displacement is 4.3 cm; the XY path is 0.068 m. There was one moving
    curve (0.56 m over 2.30 s, at 12.30 s) and three curve messages in total.
  - Goal XY error is 11.77 m. There is no arrival and no final PD hold (0 s),
    and no fall.
  - Copyback is verified. The Building review returns `passed=false`, and the
    local review fails only process and driver completion.

## Why odom_stale fired

1. The clock sync rejected 35 samples, with round-trip times of 37–46 ms.
2. The command channel then reported `clock_observation_stale` (2 protocol
   errors, 2 reconnects). At sim 15.583 s the physics control step logged
   `disconnected` and took 0.344 s of wall time; the median is 0.039 s.
3. The body-pose stream paused for 372 ms of wall time across a single 5 ms
   sim step (15.5627 → 15.5677 s).
4. The backend's wall-clock gate (`odom_stale_s` 0.25) fired during that pause.
5. The stamps advanced normally, so the stall was on the producer side and not
   a backend queue.

This is the separately recorded wall-time freshness class: v17 262 ms, v25
219/280/286 ms. It is not the optimizer guard.

## Planner state

The planner was thrashing at the start throughout:

- 806 replans in 5.4 s of active sim, with only one successful plan and 259
  failed final plans;
- 75 emergency stops;
- 289 A* "Ran out of pool … Unable to handle the initial or end point" errors,
  and repeated `reactive_stair_seed_search_failed status=2`.

The same pattern predates v28. `v26_historical_full02` had 6,299 replans, one
successful plan and 48,044 A* pool errors over 98 s, with control stalls up to
0.156 s but no freshness trip. v27 replanned at 281 per sim second before its
crash; v28 replanned at 149. The guard therefore did not raise the replan rate,
but the thrash keeps the host loaded while the stalls occur.

## Evidence

- `runs/v28_historical_full01/` holds the raw run, with reviews in
  `validation/v28_historical_full01_review.json` and `_building.json`.
- The failure video is
  `output/2026-09-27_lite3_versions/v28_historical_full_odom_stale.mp4`
  (17.6 s, 220 frames, SHA256 `47b2f52b…`). It is fully decoded and was
  visually checked at frames 155 and 219. See `video_receipt.json`. It shows
  standing near the start, not a route.

## Status

v28 is frozen and unvalidated. Its component scope passed, and no crash
occurred in its one physical trial. v3 remains the last accepted navigation
condition. Full-floor navigation, the final PD handoff and Isaac A4 remain open.
