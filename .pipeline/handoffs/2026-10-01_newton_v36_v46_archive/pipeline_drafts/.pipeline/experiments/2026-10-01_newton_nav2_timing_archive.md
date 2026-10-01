---
origin: ai+web
reviewed: false
date: 2026-10-01
status: integrated_timing_and_route_failed
---

# Newton Nav2 Timing And Wall-Time Video Archive

Execution date: 2026-09-30. Archive date: 2026-10-01, America/Los_Angeles.
Stage: experiment + analysis. Local source of truth:
`/Users/sun/tongbu/study/phdproject/vla`; `gpu5070ti` was an execution copy.
This record summarizes existing evidence; archiving starts no new run.

## Requested Contract

Dr Sun selected local planning and controller 30 wall Hz, global planning
1 wall Hz, goal XY tolerance 0.25 m and yaw tolerance 0.25 rad. The default
final yaw comes from the initial route's final distinct horizontal segment.
The 0.20 m Z tolerance and measured stopped dwell are explicit Lite3 additions.
Simulation/native time should approach wall time; actual pauses must remain
visible in an ordinary playable video. Original PD/physics remains 1 ms and
policy inference 20 ms. No physical robot or formal training was authorized.
No Trellis task was created because Dr Sun declined it earlier in the session.

Nav2's controller loop uses wall-rate scheduling, but a configured timer is
not proof of achieved frequency. [Pinned Nav2 controller](https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_controller/src/controller_server.cpp#L355),
[ROS 2 clock design](https://design.ros2.org/articles/clock_and_time.html).
See the [time survey](../survey/2026-09-30_realtime_clock_upstream_survey.md)
for clock-domain, RTF and playback distinctions.

## Versioned Implementation And Component Evidence

Every logical change has a preserved integer version and source snapshot under
[the version index](2026-09-26_newton_stair_reproduction/versions/README.md).
Failed attempts remain evidence. Component passes do not accept full navigation.

| Version | Change and directly recorded evidence | Claim boundary |
| --- | --- | --- |
| v36 | Frozen Nav2 goal/identity/clock/stop contract; 34 native and 15 backend checks, two readonly review axes; component controller 29.9993 Hz and PCT 1.00028 Hz | Local plans 87.8/120.3 ms exceeded 33.3 ms; no physical v36 trial |
| v37 | Device selection; 200-row CPU trace exactly matched original CPU; eager CUDA slightly slower | Device component only |
| v38 | CUDA solver graph; physics-only RTF about 1.58 | Fixed-target joint difference 0.007906556 rad exceeded the predeclared 0.001 rad gate; CUDA was not adopted |
| v39 | Scoped raw-contributor cache; 46 cache and 34 native checks; recorded v32/v33 geometry exactly matched v36; 17.648/22.788 ms | Frozen harness used the wrong parent basename; corrected actual comparison is bound in v41 |
| v40 | CPU solver graph; continuous 4.1 s, all 200 closed-loop rows exactly equal to original CPU, 4099 launches and per-step guards passed; zero-command RTF 1.584524 | Physics and policy only; no sensing/transport/navigation acceptance |
| v41 | Integrates qualified v39/v40 with v36 contract | No physical v41 run |
| v42 | Actual-native-clock absolute wall pacing, preserving every 1 ms step | Full-stack timing targets missed; raw controller observer used the wrong message type |
| v43 | Display-only renderer using native-time samples at 30 FPS | Diagnostic playback; not wall-time 1:1 |
| v44 | Raw cache shared across a complete executor callback; nested reuse and unchanged empty drains; actual mutations invalidate; 48 cache and 34 native checks; exact replay geometry; 11.759/12.763 ms | Recorded components only; corrected parent comparison bound in v45 |
| v45 | Adopts v44, CPU quota 4 to 6, correct raw command type, pacing anchor after factory initialization without resetting native state/time | Complete physical stack ran, but timing and route gates failed |
| v46 | Display-only causal original-pose sampling on the actual wall timeline, no interpolation or physics | Video delivery only |

CPU graph support was checked against [Warp 1.17 runtime documentation](https://nvidia.github.io/warp/v1.17/user_guide/runtime.html)
and the pinned Newton 1.6.0 AnyMal example. The adoption gate used actual
closed-loop CPU parity, rather than the CUDA speed result. Runtime pins:
Newton 1.6.0, Warp 1.17.0, MuJoCo/MuJoCo-Warp 3.12.0 and ORT 1.22.1.

The wrong parent-basename comparison in frozen v39/v44 harness output was
preserved; it was not rewritten to conceal an earlier false equality field.
Actual parent `result.json` comparisons and source/install SHA bindings are in
[v41 qualification](2026-09-26_newton_stair_reproduction/versions/v41/component_qualification.json)
and [v45 qualification](2026-09-26_newton_stair_reproduction/versions/v45/component_qualification.json).

## Complete-Stack Timing Results

| Measurement | v42_realtime_preview01 | v45_realtime_preview01 |
| --- | --- | --- |
| Actual physics steps | 120000 | 64880 |
| Actual total native time | 119.945709 s | 64.855987549 s |
| Navigation native/wall RTF | 0.890032 | 0.940006703 |
| Local planning rate | 9.063762 Hz | 16.861924492 Hz |
| Local budget overruns / skipped slots | 838 / 2568 | 625 / 684 |
| Raw controller rate | Unavailable: wrong observer type | 29.964754893 Hz |
| Actual observed PCT global refresh | Not used here as a final rate claim | 0.999981374 Hz, 52 unique computations |
| Terminal boundary | Bounded recording, no full-route arrival | `FAILED: global_refresh_failed:pct_no_route` |
| Original returned files SHA-verified locally | 1207 | 661 |

v45 initialized-navigation time was 53.835164 native seconds over 57.271043
wall seconds. Nominal local solve median was 42.2255895 ms and maximum
411.559189 ms. Gated Twist counts contain extra stop publications and must not
be labelled raw controller timer frequency. The original stop flow and Linux
tmpfs state copyback were verified. Supervisor exit 0 means recording cleanup
completed, not route success. See [v45 results](2026-09-26_newton_stair_reproduction/versions/v45/RESULTS.md)
and [actual measurements](2026-09-26_newton_stair_reproduction/runs/v45_realtime_preview01/recording_measurements.json).

## Delivered Video

Ordinary file: [v45_actual_wall_57s.mp4](../../output/2026-09-30_lite3_realtime/v45_actual_wall_57s.mp4).
It contains 1711 frames at 1280x720/30 FPS, lasts 57.033333 s against
57.022285 s of captured wall time, and retains the pauses and final stop.
Causal latest-known original poses were sampled without interpolation; no
physics steps were generated by the renderer. Full decode and a displayed
frame inspection passed. Human visual review remains pending.

File size: 3310665 bytes. SHA-256:
`38d099900d89b3745092fed6044934d7a11e3f54296fcc1155012d86a1486a31`.
The [video receipt](2026-09-26_newton_stair_reproduction/versions/v46/video_receipt.json)
and [timeline check](2026-09-26_newton_stair_reproduction/versions/v46/timeline_check.json)
bind the file to v45/v46. Frozen v45/v46 source and snapshot maps were
rehashed with zero mismatch (6159/6167 files).

Wall-time 1:1 **playback** does not establish simulation 1:1. Display 30 FPS
does not establish local planning 30 Hz. Both runtime targets remain unmet.

## Diagnosis And Unimplemented Continuation

The [optimization audit](2026-09-26_newton_stair_reproduction/audits/2026-09-30_local_30hz_opportunities/PLAN.md)
contains 878 completed nominal rounds (877 success, 1 fail), with one more
started round incomplete. First seed search failed in 647 rounds; 736 used a
shorter reference prefix and ultimately succeeded. The 140 one-attempt rounds
averaged 19.670 ms but 21 still exceeded 33.333 ms. The 630 two-attempt rounds
averaged 56.467 ms. These groups differ in geometric difficulty and do not
prove a causal speedup or achievable 30 Hz.

No A* 200 ms timeout or same-mode exact-initializer duplicate was observed in
completed rounds. Passed initialization flags are unused by the current graph
initializer, but inputs and targets can change across attempts; deleting all
retries is not supported. Failed-search log spans include printing/checks and
are not isolated CPU profiles.

Priorities are separate new versions for feasible-window reuse, remaining
valid-trajectory initialization, a shared solve/recovery budget, and measured
revision-aware cache/diagnostic-output work. Preserve fresh terrain, identity,
PVA, collision and dynamics checks, safe stops and actual progress. None of
these proposals is implemented; v47 does not exist. The separate global
`pct_no_route` failure also remains unresolved. [Original SCAN frequency check](../survey/2026-10-01_scan_planner_frequency.md).

v3 remains the last accepted navigation condition: one 12 m empty-floor run.
No complete Building arrival or dynamic-obstacle acceptance is claimed.
