---
origin: ai_only
reviewed: false
date: 2026-09-26
---

# Actual local stair loop: integrated, navigation incomplete

`stair_native_walk_v2` connects actual Newton CPU dynamics, the qualified
geometric Livox-pattern sensor, current-cloud pedestrian tracker, original
native PCT/SCAN33/controller and original backend/driver. It generates two
moving curves and applies nonzero commands for797 of1,403 policy updates.
The run ends with a measured stop after28.056 physics seconds. Navigation
fails with `command_timeout`; the robot remains4.639m from the goal in XY.

The delivered video is the regular file
`output/2026-09-26_newton_macos/lite3_newton_stairs.mp4` under the project root.
It is28s,1280x720,H.264,350frames. Newton ViewerGL renders the recorded body and
joint states without advancing physics; native curve messages are displayed at
their recorded simulation times. The official human's original UsdSkel pose is
evaluated at those same times. Final status explicitly shows failed timeout.
`validation/stair_video_review.json` records decoding, frame hashes, visual
inspection and the delivered SHA-256.

## Fixes supported by direct comparisons

1. **Different Mac/Linux monotonic origins.** A narrow BSD-licensed MAVROS
   filter port matches extracted C++ across1,124 samples (maximum0.109375ns
   difference). The real clock channel and negative command cases pass. The
   adapter adds conservative source-time mapping and rejects unavailable sync.
   Original250ms watchdog,25ms future tolerance and planner limits remain.
2. **Backend callback starvation.** Independent ROS observation saw150 body
   poses but the multi-threaded backend processed2. The standard single-threaded
   entrypoint processes149/149 in its comparison and meets readiness. Backend
   core callbacks and native planning sources remain unchanged.
3. **Cross-OS shared-file corruption.** The first full loop emits a moving curve,
   then stops on invalid JSON. A standalone atomic-file reproduction preserves
   truncated reads for overlapping and disjoint mounts. Standard PyZMQ now
   transfers complete original-schema JSON into Linux tmpfs; the unchanged
   reader validates it before acknowledgment. All1,398 positive messages in
   the latest full run match source bytes, sequence and actual policy commands.
   No applied-reader error occurs after the first snapshot.
4. **Incorrect tmpfs evidence retrieval.** The first two channel probes used
   `docker cp`, which returned the underlying host directory. Equal JSON values
   did not establish byte identity. The documented `docker exec tar` route in
   the full run returns the exact final acknowledged bytes before cleanup.

Upstream commits, licenses and source links are in the dated survey and the
experiment's `references/` and `setup/` manifests. The old attempts and their
limitations remain intact; there was no sensor or planner threshold relaxation.

## What the latest run actually shows

| Evidence | Result |
| --- | --- |
| Physics |28,060 continuous1ms steps;1,403 policy updates; minimum body up-z0.8658; no recorded fall threshold crossing |
| Pose and sensor |1,403 independently observed body messages;280 paired raw/planner clouds; identical point counts and no ground filtering |
| Perception |177 nonempty current-track messages from `sensor_lidar_static_background_cluster_v3`; actor truth remains a separate scoring/animation stream |
| Planning |One native PCT route; five spline messages: two moving, three stopped |
| Motion |Net displacement(+0.0774,-0.3750,+0.0103)m relative to first recorded body pose; final goal XY error4.6385m |
| Stop |Original35wall-second command timeout; final1physics-second window meets original command/speed/yaw stop limits |
| Timing limitations |19 rejected clock samples;10 command reconnects;18 disconnected and4 unsynchronized policy updates, all applying zero |
| Source parity |32 scenario inputs,99 runtime copies,93 native source files and490 installed files match recorded hashes |

The original driver's `execution_completed=true` and finish request `FINISHED`
mean bounded observation/recording and stop completed. They do **not** mean the
navigation goal succeeded. The backend terminal result is `failed`.
Human physical collision and avoidance remain unvalidated; this run does not
reach the pedestrian. Geometric sensing and MuJoCo-Warp CPU contacts are an
explicit platform adaptation, not RTX/Isaac parity. Old Isaac A4 stays open.

## Next diagnosis: time allocation before changing limits

The first moving curve arrives at5.600s with8.116s duration and ends near the
first stair. The second arrives at13.402s: its control-point endpoints span
about1.5m, but `timed_cubic_initialized` scales the1.6s seed by21.4064 to34.250s.
Only about8.4 additional physics seconds elapse before timeout cancellation.
Both slow retiming and the wall/physics clock distinction matter; these records
do not establish how the low-speed locomotion policy would perform given more
time.

First capture the exact seed samples entering native
`bspline_opt/include/bspline_opt/timed_cubic_initialization.h`, preserving the
93-file baseline. This run records published curves and timing summaries, not
the initializer's full seed array. Inspect its upstream/reference derivation and actual
velocity/acceleration constraint calculations, then reproduce the retiming
offline before any fix. Compare ROS2's simulation-time abstraction and Nav2's
progress checker for a separately declared simulation progress budget; keep
transport freshness/watchdogs in wall time. Do not simply extend35s or change
thresholds and call that a planner repair.

Authoritative evidence: `validation/stair_native_walk_v2_review.json`, the
immutable run's `scan.log`, `controller.log`, `backend_states.jsonl`,
`telemetry.jsonl`, `applied_sent.jsonl` and `state_copyback.json`.

## Follow-up diagnosis, 2026-09-26

[DIAGNOSIS.md](DIAGNOSIS.md) records the subsequent measured-cloud replay,
frozen-state ray controls and unchanged native spline checks. Two repeated
replays match all 280 live tracker snapshots and each other byte-for-byte.
The two interrupted frames fail only the 0.45 m vertical-span gate. Restoring
the preceding sensor orientation alone restores a candidate in both frames;
position, scan pattern and authored-visibility controls do not. The first stop
reports `MissingInput`, despite the generic occupied-target message.

The published curves pass native feasibility checks. The local initializer
expands timing before geometry optimization; later code does not shorten it.
The exact seed arrays were not recorded, so the logged 21.4064 scale has not
been exactly replayed. Compressed final-geometry controls are explicitly
different inputs. No production behavior or limit changed.

`runs/trajectory_diagnosis_review_v3/result.json` passes all 26 diagnostic
checks and verifies 93 native source files, 490 installed files, 32 inputs,
99 runtime copies and 6 upstream reference files. Navigation stays unvalidated.
The adjacent `tracking_coverage.png` / `.pdf` plot actual candidate points.
Review attempts v1/v2 stopped before checking because their interpreters lacked
Matplotlib; v3 uses a separately pinned plotting environment.
# 2026-09-26 generic measured-geometry follow-up

See `repairs/2026-09-26_generic_occupancy/RESULTS.md` and `UPSTREAM_REUSE.md`.
The mandatory person-track dependency, terrain-classification lifetime,
pre-optimization timing order and physical contact-capacity defects have direct
component evidence. Full class-independent physical avoidance remains open;
do not promote the earlier frozen-cloud curves into route completion.
