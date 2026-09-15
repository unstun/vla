---
origin: ai+local_evidence
date: 2026-09-10
label: official evaluator on custom public-scene tasks, per camera condition
status: executed_and_lead_accepted
---

# Result: Lite3 camera-condition ablation of InternVLA-N1 DualVLN

Twenty supervised runs of the pinned InternNav evaluator (InternNav
`7a5c624`, checkpoint `a698a9e`, Habitat-Lab 0.2.4 / Habitat-Sim 0.3.3) on the
two frozen skokloster-castle episodes, five runs per camera condition, on the
rented RTX 4090 across three execution rounds on 2026-09-10. Baseline B0 is the
recorded `public_eval_v1..v5`.

| Condition | Geometry | Success (episodes) |
| --- | --- | --- |
| B0 baseline | 1.25 m, level, HFOV 79, look-down protocol | 5/10 |
| C1 Lite3 rig faithful | 0.42 m, 20 deg down fixed, HFOV 54, no tilt | 1/10 |
| C2 height only | 0.42 m, level, HFOV 79, look-down protocol | 5/10 |
| C3 FOV only | 1.25 m, level, HFOV 54, look-down protocol | 3/10 |
| C4 raised mount | 0.65 m, 15 deg down fixed, HFOV 54, no tilt | 2/10 |

Claim boundary: public-scene functional test; effect sizes only; not R2R,
not a published-score reproduction; System 1 sampling unseeded; two episodes.
Evidence: `runs/cam_*`, `preflight/`, `matrix_log.jsonl`,
`condition_summary.{json,md}`, `ffprobe_frame_counts.json`, `manifest.sha256`
(1,571 files verified locally), `OPUS_RETURN.md` (three rounds), and
`review/LEAD_REVIEW.md` (verdict and mount recommendation).

## Round 4 (2026-09-10): head-camera proxy pair

Dr Sun kept the Lite3 built-in head camera and asked for the simulation
check first. Two conditions rendered with the evaluation camera (HFOV 79,
which the deployment adapter obtains by centre-cropping the head-camera
stream), fixed camera with no look-down, 0.40 m high and 0.27 m ahead
(estimated): C5 level, C6 15 deg down. Ten runs, all exit 0; manifest 2,211
OK; details in `review/LEAD_REVIEW.md`.

| Condition | Height | Pitch | HFOV | Look-down | Ep1 success / oracle | Ep1 NE median | Ep2 success / oracle | Ep2 NE median | Ep2 steps median | Total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 baseline (recorded) | 1.25 m | 0 | 79 | yes | 3/5 / 3/5 | 1.25 m | 2/5 / 5/5 | 4.89 m | 107 | 5/10 |
| C2 height only | 0.42 m | 0 | 79 | yes | 3/5 / 3/5 | 1.41 m | 2/5 / 4/5 | 3.06 m | 98 | 5/10 |
| C5 head proxy, level | 0.40 m | 0 | 79 | no | 1/5 / 1/5 | 4.69 m | 1/5 / 5/5 | 5.13 m | 113 | 2/10 |
| C6 head proxy, 15 deg down | 0.40 m | 15 down | 79 | no | 5/5 / 5/5 | 0.66 m | 0/5 / 5/5 | 5.84 m | 165 | 5/10 |
| C1 current rig (for reference) | 0.42 m | 20 down | 54 | no | 1/5 / 2/5 | 12.18 m | 0/5 / 0/5 | 12.00 m | 155 | 1/10 |

Outcome: with a fixed camera, 15 deg down (5/10) beats level (2/10) and lands
in the baseline's range; episode 2 fails by stopping late in every wide-FOV
condition, including the baseline (oracle success 5/5). Recommendation: keep
the head camera at its existing downward pitch, crop to HFOV 79 at 4:3, do not
re-mount level; measure the camera on the robot before the real-robot child.
Claim boundary unchanged: two custom public-scene episodes, five unseeded
runs per condition, effect sizes only, geometry estimated until measured.

## Round 5 (2026-09-11): fused virtual camera c7

c7_fused_level (level virtual evaluation camera at the head-camera pose, composed from the rendered head camera at +16.7 deg and
the rendered D435i colour+depth at 20 deg down, 6.0 percent of the image uncovered): 0/10 (ep1 0/5 with oracle 0/5, NE 7.1-7.9 m;
ep2 0/5 with oracle 5/5). Five runs, exit 0, wall 272-332 s, learned STOP 10/10. Preflight proved the fused image is what the model
receives (bit-identical offline recompute) and matches the ideal render at 35 dB outside the corners. Episode 1 fails by a single
consistent System-2 route choice towards nearer chairs; see review/LEAD_REVIEW.md round-5 addendum. c8 (D435i at 1280x720,
1.3 percent uncovered) deferred to round 5b after a provisional fusion-cost bound (200 ms) was exceeded at 226 ms.

## Round 5b (2026-09-11): fused virtual camera c8

c8_fused_level_720 (as c7 but D435i colour+depth at 1280x720, 1.2 percent uncovered): 2/10 (ep1 2/5, oracle 5/5, two runs stop at
2.0 and 2.8 m, three overshoot to 17 m; ep2 0/5, oracle 5/5, late stops 7.5-9.7 m). Equal to c5 (ideal level render at the same
pose). Fused-camera conclusion: usable input, corner size matters for the route, performance capped at the level-camera level;
the 15-deg-down advantage (c6) is not reachable by fusion. All 40 authorised runs used.

## Route decision (2026-09-11): software-only fusion

Dr Sun selected the fusion route (c8 geometry, D435i colour at 1280x720) for deployment, with no hardware change.

Two corrections to the round-5b close-out, from `condition_summary.json`:

- c8 is not equal to c5. Counting runs that entered the success radius, c8 is 10/10 (tied with c6, above the 1.25 m
  baseline's 8/10); c5 is 6/10. Every c8 failure is a late stop, not a failure to find the goal. The binding constraint on
  the chosen route is STOP arbitration.
- Fusion is not restricted to a level virtual camera. The covered band is -41.1 to +52.9 deg, so a 640x480 HFOV 79 virtual
  camera can be pitched to about 9 deg down (uncovered 1.28 -> 3.05 pct, floor first visible 0.65 -> 0.46 m ahead, against
  c6's 0.38 m). A full 15 deg down costs 14.56 pct uncovered and is not usable. Measured on the self-test render, which
  reproduces c8's reported 1.2-1.3 pct at 0 deg.

Proposed C9 `c9_fused_down9` (five runs, needs authorization; all 40 runs used): the c8 sensor set with the virtual camera at
9 deg down. Requires relaxing the level-only guard in `fused_camera_plugin.py`; the fusion maths, model, and evaluator are
unchanged. Analysis, the deployment gap list, and the risk that 3.05 pct uncovered behaves like c7 rather than c8 are in
`.trellis/tasks/09-10-internvla-n1-camera-ablation-sim/research/camera-geometry-and-evaluator-protocol.md`, section 6k.

## Round 6 (2026-09-11): fused virtual camera pitched 9 degrees down, c9

c9_fused_down9 (c8's sensor set unchanged, only the virtual evaluation camera pitched 9 deg down; 3.30 pct uncovered):
**1/10** (ep1 0/5 with oracle 0/5, NE 3.5-7.4 m; ep2 1/5 with oracle 5/5, NE median 4.04 m). Five runs, exit 0, wall
301-367 s, learned STOP 10/10. Preflight passed all nine stages with the fused image bit-identical to an offline recompute,
every sensor pose exact, and an implied floor gap of 0.1576 m matching every earlier condition.

| Condition | Geometry | Ep1 succ / oracle | Ep2 succ / oracle | Ep2 NE median | Total |
| --- | --- | --- | --- | --- | --- |
| B0 baseline | 1.25 m level, look-down | 3/5 / 3 | 2/5 / 5 | 4.89 m | 5/10 |
| C6 ideal render, 15 deg down | 0.40 m | 5/5 / 5 | 0/5 / 5 | 5.84 m | 5/10 |
| C7 fused, level, D435i 640x480 | 6.0 pct uncovered | 0/5 / 0 | 0/5 / 5 | 7.58 m | 0/10 |
| C8 fused, level, D435i 1280x720 | 1.2 pct uncovered | 2/5 / 5 | 0/5 / 5 | 8.71 m | 2/10 |
| C9 fused, 9 deg down, D435i 1280x720 | 3.3 pct uncovered | 0/5 / 0 | 1/5 / 5 | **4.04 m** | 1/10 |

Outcome: the pitched fused camera did not recover C6's behaviour, and C8 remains the configuration to deploy. Two findings
qualify the headline. C9 has the lowest episode-2 navigation error of any condition at the head pose and lower than the
1.25 m baseline, and it converts one episode-2 run, which no other fused condition did. And its `s1_stop_mid_segment` count
is the lowest of the fused set despite carrying the most uncovered pixels, which does not support the round-5 hypothesis
that black pixels drive System 1 to stop mid-segment.

Claim boundary, and the limitation this round exposes: episode-1 oracle success across conditions is 3, 1, 5, 0, 5, 0 for
B0, C5, C6, C7, C8, C9 with near-unanimous runs inside each condition, and is not monotone in pitch, field of view or
uncovered fraction. System 2 locks one route per image stream and the lock flips on small input changes, so at one condition
per geometry episode 1 cannot separate geometry from route lock. That weakens C6's 5/5 as much as C9's 0/5. More runs on
these two episodes will not fix it; more episodes would. Evidence: `runs/cam_c9_fused_down9_v1..v5`,
`preflight/c9_fused_down9.json`, `condition_summary.{json,md}`, `manifest.sha256`, `review/LEAD_REVIEW.md` round-6 addendum.
