# v29 physical trial: the start thrash is gone; the route stalls at an upper landing

Component results in `COMPONENT_RESULTS.md` remain valid. The trial followed
`PHYSICAL_RUN_PLAN.md`, with exactly `v28_historical_full01`'s profile. Only
the native build, the planner YAML path (a byte-identical copy) and the
integration version differed.

## Outcome of `v29_historical_full01`

- **Gates and route:** the version, native-identity and reviewed-candidate
  gates passed before physics. In the Building review, the automatic native
  layers, historical route length and correct goal level all pass.
- **The robot leaves the start.** The RL policy took over at 12.64 s, and the
  body was more than 0.10 m from the start by 13.14 s. v28 entered a permanent
  hold at 12.69 s and moved 4.3 cm in total. Along the way the body:
  - reached the first landing (z 0.90 m) at 26.6 s;
  - reached z 1.40 m on the next flight at 46.8 s;
  - reached the upper landing (z 1.65 m) at 60.7 s.
- **Totals:** the actual XY path is 9.77 m, with a net displacement of
  (0.57, -8.55, +1.31) m. There are 13 moving curves; v28 had one.
- **Navigation still failed.** The first failing gate is
  `native_replan_exhausted` at 88.32 s sim, after 1,000 failed replans at the
  upper landing. The driver finished `case_failed`.
  - Goal XY error is 6.97 m (v28: 11.77 m). There is no arrival and no final
    PD hold (0 s), and no fall. Physics is continuous.
  - The Building review returns `passed=false`. Compared with v28, its only
    changed check is `actual_motion`, which went from false to true. The local
    review fails only process and driver completion, as v28's did.
- **No crash and no freshness trip:** `scan.log`, `native_graph.log` and
  `run.log` contain no crash. No `odom_stale`, `heartbeat_stale` or
  `command_timeout` fired. The clock sync rejected 24 of 7,281 samples, with
  no reconnect or protocol error. The v28 stall chain (reconnect, 0.344 s
  control stall, 372 ms pose gap) did not occur in this run. The wall-clock
  gate itself is unchanged, so this is not a fix of that class.

## Why the route stopped

The 13th successful plan ended its local reference window at 8.64 s of the
73.60 s global path ("Local reference window complete"). The robot then stood
on the upper landing near (-5.00, -2.45, body z 1.70). After that, every
REPLAN/GEN attempt proposed the reference frontier at t = 8.645 s,
(-5.0008, -2.4976, 1.7226), which is the robot's own position. The optimizer
was never reached again.

- The optimizer's A* repeatedly logged "Ran out of pool … Unable to handle the
  initial or end point": 2,303 times after the last success.
- The throttled collision lines show UnknownObstacle at (-0.39 to -0.44, -4.26,
  1.861), about 4.6 m further along the route beyond the landing turn.
- After 1,000 failures the FSM raised the emergency stop, and the backend
  reported `native_replan_exhausted`.

This is a different failure class from the start thrash. The frontier stops at
never-observed space beyond a turn, outside the robot's footprint, where v29's
waiver correctly does not apply. It has not been diagnosed from saved inputs
yet.

## Planner statistics

- **Replans:** 6,002 in total, with 13 successful and 1,942 failed final plans.
- **Emergency stops:** 552.
- **Seed searches:** 4,374 returned status 2.
- **A* pool errors:** 5,503.
- **Fail-closed aborts:** 65 fired from the v28 rebound guard.

Grouped by the planner's start position (`start:` lines):

| Segment | Replans | Successful plans |
|---|---|---|
| Start area | 23 | 2 |
| First flight | 108 | 2 |
| First landing (the 30-42 s pause) | 353 | 1 |
| Second flight | 3 | 2 |
| Beyond y = -0.4 m, the upper stairs and landing | 5,515 | 6 |

v28 replanned 806 times at the start with one success. v29 needed only 23.

## Evidence

- **Raw run:** `runs/v29_historical_full01/`. The reviews are in
  `validation/v29_historical_full01_review.json` and `_building.json`.
- **Video:** `output/2026-09-27_lite3_versions/v29_historical_full_replan_exhausted.mp4`
  (88.2 s, 1,103 frames, SHA256 `709ceb59…`). It is fully decoded and was
  visually checked at frames 375 and 1100; see `video_receipt.json`. It shows
  the robot climbing the stairs and then standing on the upper landing with
  "Navigation: failed (native_replan_exhausted)".

## Status

v29 is frozen and unvalidated. Its component scope passed. In its one physical
trial it removed the start thrash and climbed about 1.3 m of stairs, but it did
not arrive. v3 remains the last accepted navigation condition.

Still open:
- the landing frontier stall;
- the unchanged wall-clock freshness class;
- the emergency-hold feedback;
- the 13 cm protrusion choice;
- full-floor navigation, the final PD handoff and Isaac A4.
