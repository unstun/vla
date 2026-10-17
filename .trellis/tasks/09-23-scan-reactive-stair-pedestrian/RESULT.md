# Reactive SCAN stairs and moving-person tracking: bounded result

Date: 2026-09-23/24. Stage: experiment and analysis.

## What was implemented

- `scan_06`: a hash-gated SCAN candidate with separate PCT ground support,
  raw LiDAR occupancy, and typed complete current-person snapshots. A*, spline
  optimization, and the 50 ms safety path use the same conservative occupancy
  query. Missing or stale required inputs block. Accepted `scan_04` and the
  frozen pilot `planner.yaml` are unchanged.
- `scan_07`: a precomputed two-pass step score adapted from the pinned ETH
  `StepFilter` at commit `14d24c059e1c43466aadf328280adf6394d78039`.
  Sparse/multilevel PCT handling, complete-window refusal, and the local
  0.26 m hard gate are project adaptations. The ETH ROS 1 filter was not
  imported wholesale and upstream behavior was not reproduced.
- `scan_08`: a separate Foxy moving-cluster tracker package. It pairs current
  LiDAR and pose stamps, removes selected PCT ground, associates person-shaped
  moving clusters by last observed center, and publishes the current complete
  set. It has no velocity extrapolation or pedestrian trajectory prediction.
  It is a candidate moving-object tracker, not verified human recognition.
- `scan_09`: a one-line, hash-gated correction to the tracker's PCT intake.
  The actual pinned Humble `sensor_msgs_py.create_cloud` sets `is_dense=false`
  even for finite records; `scan_08` had incorrectly rejected this map. The
  correction accepts finite, correctly framed/typed records independent of
  that metadata flag.
- `pct_sim_clock_publisher.py`: a separate PCT topic sidecar built from the
  pinned Building map and exact publisher point logic. It waits for two
  advancing positive `/clock` samples before sending the selected terrain
  cloud. It does not alter the frozen PCT runtime or current pilot launcher.

## Direct evidence

| Gate | Result | Local evidence |
| --- | --- | --- |
| ETH source and parameters | Pinned `StepFilter.cpp`, `StepFilter.hpp`, example robot YAML, license and SHA-256; local numeric fixtures pass | `references/upstream/2026-09-23_eth_stepfilter_reference/`; `reactive_stair/test_eth_step_score_adaptation.cpp` |
| Source identity | Hash-gated copies from accepted `scan_04` through built `scan_09`; previous candidates unchanged | `p2b_execution/builds/scan_06/` through `scan_09/` manifests and local materializer tests |
| Foxy builds | `scan_06`, `scan_07`, `scan_08`, and `scan_09` passed; `scan_09` finished seven packages with before/after source identity equal | `p2b_execution/builds/scan_09/build_result.json`, `build.log`, `install_identity.json` |
| SCAN process startup | `scan_07` initialized to `INIT` for 10 s without odometry/goal | `.pipeline/experiments/2026-09-23_scan_reactive_stair/scan07_startup_probe/` |
| PCT map coverage | 86,775 selected Building ground cells; 70,501 supported after local step score. An example stair route has two sampled height mismatches (~0.13 m vs 0.12 m query tolerance) | `reactive_stair/actual_pct_step_score_diagnostic.json`; `stair_route_support_probe.log` |
| Clock-aware PCT ROS topic | CPU-only Humble probe received 86,775 `world` points at stamp 1.01 s and exact pinned payload SHA-256 `71550de5fde87043da3da73de00a8e1c1437c751bc939b87a718059d54949577` | `.pipeline/experiments/2026-09-23_scan_reactive_stair/pct_sidecar_ros_probe/` |
| Tracker ROS transport | CPU-only Humble/Foxy probe received terrain and produced five complete snapshots from six synthetic LiDAR sweeps. One ID `cluster-1`; observed centers x=-0.88,-0.76,-0.64,-0.52,-0.40 m | `.pipeline/experiments/2026-09-23_scan_reactive_stair/synthetic_track_ros_probe/` |
| Sidecar shutdown correction | A separate bounded Humble ROS rerun published the same map after the cleanup fix and exited without the earlier duplicate-shutdown traceback | `.pipeline/experiments/2026-09-23_scan_reactive_stair/pct_sidecar_ros_probe_cleanup/` |

All source copies, logs, identity files, and probe scripts are local. The
remote host was a CPU execution copy; no GPU was used for these probes.
Targeted Python syntax and owned-path whitespace checks passed. A repo-wide
`git diff --check` reports four trailing-whitespace lines in the already
modified `isaac_runner/runner_external_episode.patch`; that unrelated dirty
file was left untouched. This task's new paths remain uncommitted for review.

## Review and unresolved gates

1. The current integrated P2B launcher still starts the socket PCT worker,
   not the new `/pct_tomogram` sidecar or tracker. Thus no end-to-end SCAN
   collision query, 50 ms correction timing, controller command, or Isaac
   stair/pedestrian episode has been observed. The synthetic ROS probe is
   topic-level evidence only.
2. No person-labelled Building stair sensor sequence or Building pedestrian
   actor is present in the current pilot. LiDAR shape/motion clustering can
   miss a person or include a moving nonhuman object. It needs labelled
   false-positive/false-negative evaluation before a pedestrian claim.
3. A confirmed track lost from the sensor stays incomplete until reacquired;
   this prevents silent clearing but may halt navigation indefinitely. The
   SCAN collision query uses XY person radius and can block a different floor
   at the same XY. Both are conservative functional limits.
4. The example stair reference path's two sampled height mismatches require
   checking against the actual PCT route. Aggregate step-score counts and a
   startup smoke do not prove route continuity or locomotion safety.
5. At the first preflight the execution GPU was occupied by ComfyUI PID 5744
   (14,812 MiB). On Dr Sun's explicit request, that process was identified,
   terminated with SIGTERM, and rechecked: no GPU compute process remained,
   with 240 MiB used. GPU occupancy is no longer the blocking condition.
   No real robot or formal training was started.

The next reviewable runtime package must launch the sidecar and tracker in
the same simulation-time ROS domain as `scan_09`, provide a labelled moving
pedestrian on an actual stair route, and log input stamps, SCAN correction
latency, contact/fall, route completion or safe yield. The current pilot's
flat two-goal run cannot substitute for that episode.

## 2026-09-24 official-human update

Dr Sun requires an official human asset for the Isaac stair trial. A bounded
source audit found that the Building runner has no human actor option or
moving human LiDAR target; the current pilot goals are on one flat level.
The exact audit is in
`.pipeline/experiments/2026-09-23_scan_reactive_stair/isaac_candidate/BLOCKER.md`.
The NVIDIA Isaac Sim 5.1 police character USD, three relative textures, and
the prior ControlRig retargeted animation cache have since been copied into
local date/topic paths with SHA-256 provenance. Official binary content is
locally stored and ignored by exact path; it is not part of a public commit.
This closes the initial asset-availability gap. The hash-gated Building
source candidate remains inactive: its route approval hash is unset, and no
Building pedestrian episode has been run from it.

Two isolated no-robot Isaac probes have since been executed with the official
police USD as the sole raycast target. `isaac_candidate/first_hit_v1/` failed
at the test sensor's missing canonical transform operations. After that setup
was corrected, `first_hit_v2/` loaded the official asset but failed inside
IsaacLab's mesh-ID output assignment: a `[5808]` tensor could not be assigned
to `[1, 5808, 1]`. Both failures and the exact executed source snapshots are
retained locally. Neither result proves that the mesh follows the actor.
The second failed process remained in Isaac shutdown and received a targeted
SIGTERM only after its PID and command were rechecked. Its process exit code
was zero despite `result.json` being false; the result JSON is authoritative.

`first_hit_v3/` disabled the unused mesh-ID output without changing the
official target or hit thresholds. The nine official mesh prims produced
317 finite hits, but the two hit clouds had identical bounds and mean y
(`0.0058594695` m) while USD root readback changed from y=0 to y=1 m. The
two-pose test therefore failed. This is direct evidence that the current
USD-only root write does not update the headless raycaster's observed pose.
Dynamic transform synchronization is being diagnosed; no moving-human
sensor claim is accepted from this candidate. The failed test process was
again stopped by exact script identity after result creation, and all
88 source files matched before and after execution.

An independent review also reproduced a tracking defect on frozen `scan_09`:
at 10 Hz, a cluster moving at 0.3 m/s moved 0.3 m over eleven observations
without ever producing a track. The motion test compared consecutive centers
against 0.08 m and reset its reference each frame. The failure evidence is
`scan09_slow_motion_review.json`; a new source candidate was prepared
to use observed displacement from an anchor, without velocity or prediction.

That correction is now `scan_10`. The lead reviewed its only changed runtime
file, repeated seven tracker and three materializer tests, and built all
seven packages in the pinned Foxy image with identical before/after source
hashes. The installed identity covers 451 files. A separate CPU check in
that image imported the installed tracker core and confirmed the slow
cluster at frame 3 with a stable ID and current position/stamp through
frame 10 (`scan10_slow_motion_foxy_review.json`). This closes the reproduced
slow-motion bug for the tested sequence; it is not a human-recognition or
Isaac/SCAN timing result.

The local Building/PCT route audit found a supported short stair corridor,
but its proposed robot/person starts are only 0.60 m apart, below the current
0.73 m combined longitudinal envelope. It is explicitly marked
`initial_placement_pass=false` and `geometry_reviewed=false`. The planner
must not be launched from that overlapping initial placement. The audit also
corrected a provenance-only x/y cell-index error before regenerating its
evidence; current raw rows are in `isaac_candidate/route_audit/`.

`first_hit_v4/` subsequently passed the isolated official-mesh translation
test. The public raycaster target-view pose setter synchronized Fabric with
the official root. Real ray returns changed from 317 to 334 points, with
mean y moving 0.966181 m for the 1 m actor shift. Actual returned points and
all source identities are local. The measurement passed before a targeted
SIGTERM released the Isaac process stuck in stage cleanup; this was not a
natural application exit and is recorded separately in `cleanup.json`.
The final GPU check found no compute process and 241 MiB used
(`gpu_after_first_hit_v4.json`).

Feeding those actual returns through the unchanged `scan_10` shape screen
with an explicit flat-ground fixture produced zero candidates at both poses
(`official_mesh_shape_review.json`). Filtered horizontal spans of 0.949 m
and 1.636 m exceed its 0.90 m gate. Thresholds have not been changed.
`isaac_candidate/ANIMATED_MESH_LIDAR_AUDIT.md` confirms from pinned source
that MultiMeshRayCaster copies `Mesh.points` once and subsequently updates
only target poses, while the official animation updates joint attributes.
Thus the sensor does not incorporate the walking skin deformation. The
available RTX API is a candidate for a separate controlled geometry test;
its skin sensing, import/teardown behavior, and MID-360 parity are unverified.
This is the next sensing dependency, before detector tuning or a Building
episode. The isolated root-motion fix is not yet ported to the Building runner.

`runtime_integration/prepared/local_review_02/` is a local preparation overlay
for the historical `scan_09`/`first_hit_v2` inputs, not an executable ROS
launcher. Its seven local tests pass. The lead corrected two scoring/health
issues: a deadline cancel followed by measured stillness is
`DEADLINE_STOPPED`, not pedestrian yielding; a complete empty current-track
set is allowed. Actual process supervision, contact/fall scoring, input-to-
correction timing, and an approved nonoverlapping stair encounter remain open.

Claim labels: ETH source **surveyed**; local ETH-style adaptation and
current-cluster tracker **implemented and Foxy-built**; ROS input transport
**smoked with synthetic data**; SCAN stair/pedestrian behavior **not yet
integrated or validated**. The missed-box result belongs to its prior task
and is not being reopened here.

## 2026-09-26 RTX sensing and video continuation

Dr Sun authorized continuing the work and requested the resulting video
(2026-09-25 Pacific: "可以，你做好后视频给我"). A4 remains open while the
Building integration is exercised. The work below is under
`2026-09-23_scan_reactive_stair/rtx_sensing/`.

- `import_v2_instrumented` exposed the original hidden exception:
  `isaacsim.sensors.rtx` was not enabled in the IsaacLab experience. The
  default fast shutdown hid `ModuleNotFoundError` behind exit code 0.
  Explicit extension enablement passed `import_v3_enabled` with full import
  and teardown markers.
- The actual RTX renderer senses official walking skin at a fixed root.
  `sensing_v5_default_shutdown` passed the unchanged four-capture test and
  returned a real 960x720, 90-frame, 10 FPS video. The pose-change point-set
  distance is about 0.065 m versus about 0.0011 m repeated-pose variation.
  The initial four actual RTX clouds all yielded one candidate through the
  unchanged `scan_10` shape filter, using explicitly synthetic flat support.
- Preserved failures separated shutdown problems from sensor measurements.
  IsaacLab's STOP callback waited indefinitely for PLAY. Disabling that
  interactive callback fixed the hang; full extension cleanup then caused
  interpreter SIGSEGV. The operational path now releases task-owned resources
  and calls Isaac Sim's documented default fast shutdown. Parent-side zero
  exit, GPU release, source hashes and returned artifact hashes are required.
  `teardown_pass: false` is retained separately from `process_release_pass`.
- `mid360_v5_release_order` passed an opt-in RTX geometric adapter using the
  pinned Livox CSV: two 20,000-ray windows agree with analytic cube intersections
  to maximum errors 0.000007835 m and 0.000007232 m. The implementation had to
  use typed USD arrays, 1-based RTX channel IDs, and reverse RTX's clockwise
  azimuth to preserve the CSV's ROS coordinate convention. Earlier failed
  attempts remain in the ledger. No manufacturer-calibrated RTX model is claimed.
- The same run moved the official actor at 0.3 m/s and retained actual RGB,
  point clouds and the unchanged tracker-core output. Frames 4–39 (36/40)
  contain one confirmed `cluster-1`; all 40 frames match their requested CSV
  ray window. The 4-second video is local. This establishes an isolated
  sensor-to-tracker integration with synthetic flat support, not a ROS,
  Building, collision, or stair-navigation result.

`runtime_integration/prepared/stair_video_scenario_v1/` screens a robot start
at `(-5.3, 6.0, 0.0580444)` and goal at `(-5.3, 1.0, 0.876465)` against the
unchanged PCT/Building checks. The official actor stays on the measured
0.740234 m tread, y=1.4–1.9. Initial separation is 4.6 m. The endpoint/actor
screen is a Codex geometry review, not a human-review or continuous-contact
claim. The native PCT route must still be computed in the episode.

The new `run_stair_video.py` prepares the RTX runner, PCT support publisher,
`scan_10` tracker, ROS health/correction recorder and a bounded observation
driver. Three local input-integrity/readiness/assembly checks pass. It first
runs a standing scene before a walking episode. A deadline cancellation is
explicitly not counted as avoidance. Full-rate collision/fall/yield/timing
and video review remain required before closing A4.

### Live Building observations and native planning diagnoses

`runtime_integration/runs/stand_v2` completed the standing integration with
201 actual RTX sweeps, sensor-derived `cluster-1`, no commanded motion,
no nonfoot contact, no fall/reset, and 47 matching returned artifact hashes.
`walk_v1` and `walk_v3_yaml` completed recordings but issued no nonzero walking
command. `walk_v2_clearance` failed before walking because of a generated YAML
indentation error; the corrected generator has a parser regression check.
Execution completion is explicitly separate from navigation success.

`scan_11` separates physical body clearance (0.35 m) from the frozen planner's
zero route-height offset. It passed a real Foxy build and installed-file
identity capture. A native pure-C++ regression reproduces the old WrongHeight
verdict and verifies person/static/stale-input precedence after the fix.

The recorded `walk_v3_yaml` clouds contain no robot-surface returns near the
failed initial body position. `scan_12` adds bounded near-sensor diagnostics.
CPU replay confirms that the queried voxels are unobserved, with no inflated
hit, rather than occupied by self echoes. The preserved first replay also
exposes a scheduling race: a query can arrive after cloud receipt but before
the 50 ms occupancy update. The second replay waits for fusion and reproduces
the geometric blocker. Replay is not live timing evidence.

`scan_13` completes the existing map fusion inside the cloud callback (the
native executor is single-threaded). An opt-in rule recognizes only the exact
two URDF TORSO boxes at the current measured 6D body pose, age <=0.1 s. It does
not clear map cells or the surroundings. An inflated hit, external unknown
voxel, invalid/stale required input or current person remains blocking. Five
native C++ contract checks pass; the actual Foxy build and installed identity
are recorded. At the old start this remains insufficient: the native support
classifier also rejects rear query positions near a map boundary.

`support_audit/` runs the exact native ETH-style header on the delivered PCT
payload. The separately screened `stair_video_scenario_v2` start is
`(-5.42, 6.013188839, 0.0580444)`. Its center and +/-0.18 m reference points
are supported; the original unchanged mesh/placement checks pass. The first
attempt at x=-5.4453 failed that screen and was not executed.

`walk_v4_ego` then completed a 29.08 s live observation with `scan_13`, 291
current RTX sweeps, 190 nonempty `cluster-1` snapshots, no nonfoot contact,
no fall/reset/pose injection, and matching returned hashes. Actor motion at
10.02 s was followed by the first track at 10.12 s. Navigation still failed
with `initial_heartbeat_missing`: all admitted walking commands remained zero.
The 2.25 cm maximum incidental displacement is not navigation. The observer
camera now includes the complete robot and human; its video is local and
visually reviewed. This is still not reactive yielding.

Native replay uncovered additional assumptions in the flat-navigation code:
`dyn_a_star.cpp` assigns one linearly interpolated height to each XY neighbor,
and both optimizer cost combinations explicitly zero their Z gradients.
`scan_14` restores 26-neighbor search while preserving the same conservative
query, resolution and time cap. It builds, but replay still fails optimization.
`scan_15` separately restores the already-computed vertical optimizer gradient;
its runtime outcome is pending. No collision threshold is relaxed.

Full-rate V12 records also show the original goal arrived during
`STAND_TRANSITION` at 1.7 s. Controlled replays retain actual input data but
delay route dispatch to 5 s; both `scan_13_settled` and `scan_14_settled` still
fail to produce a moving spline. The live driver now requires at least 5 s
of simulation time plus 0.5 s of measured speed <=0.01 m/s and yaw rate
<=0.03 rad/s, with current healthy feeds and zero command. It neither resets
the robot nor zeros its measured velocity. Five launcher regression checks
pass. A4 remains open; source/build readiness is not live avoidance evidence.

### Video-first review handoff

After native builds and recorded-input diagnoses through `scan_19`, the full
search still produced no accepted path (329 search failures in the bounded
replay; no search-time-cap warning). See
`runtime_integration/replay/scan19_settled/review.json`. This is not proof that
all possible configurations are infeasible. The optimizer-margin ablation
failed and was not adopted. The heading and height candidates have not been
promoted to a successful live stair-navigation result.

Dr Sun asked to see the video and the problem first before selecting further
input changes. Real, nonsymlink video copies and their hashes are in
`output/2026-09-26_stair_human/`: the 4.00 s isolated sensor clip and the
29.12 s, 364-frame, 1920x1080 `stair_scene_scan13_no_navigation.mp4`. Both decode
fully; representative frames show the whole robot and human. In the stair
clip the robot never receives a walking command. Actor motion begins at
10.02 s and the first current track appears at 10.12 s. This is a problem
recording, not a successful avoidance demonstration. A4 remains open.

The new continuation documentation is `runtime_integration/RTX_BUILDING_VIDEO.md`.
The original `runtime_integration/README.md` for the older preparation-only
overlay was restored byte-for-byte from this task's initial command output
after the continuation notes inadvertently replaced it. No old preparation
package, accepted scan_04, frozen baseline or sibling repository was changed.

### Controlled right-side actor placement

After viewing the video, Dr Sun requested placing the actor on the right to
check whether the central actor was blocking passage. The new actor route is
translated by 0.65 m in world -X, from x=-5.30 to -5.95; y/z, animation timing,
speed, robot start, goal, scan_13 configuration and the original goal driver
are preserved. `runtime_integration/prepare_actor_right.py` screens the actual
Building mesh and records a 0.3540 m continuous torso-side clearance lower
bound against a 0.35 m radius-plus-margin requirement. The earlier selected
PCT ground-mask rejection was overly conservative for human placement and
was not treated as the physical stair boundary. Three geometry checks and
five launcher regression checks pass.

`walk_v5_actor_right_v2` completed 29.08 simulated seconds. All 47 returned
hashes match; all 291 actual RTX sweeps were ready. Actor truth confirms
x=-5.95 throughout and motion at 10.02 s. The robot still received no nonzero
admitted command across 1,454 records. Incidental XY displacement peaked at
2.257 cm; nonfoot force, resets and pose injections were zero. The native
terminal remained `initial_heartbeat_missing`, with the same initial
UnknownObstacle query as the reference run. Moving the human right did not
restore navigation in this trial. The right-side actor produced zero nonempty
tracks, compared with 190 in the reference; this tracking limitation remains
unresolved and the episode is not an avoidance success. A4 stays open.

The first local package `walk_v5_actor_right` was never remotely executed:
its comparison gate initially failed to normalize the new external run ID.
It is preserved with a preparation-failure marker and cannot be executed by
the launcher. The corrected package preserves original execution behavior,
including its pre-settling goal dispatch, to avoid adding a second variable.

The real delivered copy is
`output/2026-09-26_stair_human/stair_actor_right_comparison.mp4` (29.12 s,
364 frames, 1920x1080; all frames decoded). The 10.8 s walking and 12 s standing
frames were visually inspected and show the human beside the image-right
windows. Paired measurements, provenance and post-run cleanup evidence are
saved beside the video; the GPU and containers were idle after completion.

### Independent root-cause review and native trace

Dr Sun requested careful review and authorized one subagent. The reviewer
audited planner source and prior replay evidence while the primary agent
replayed tracking and reconstructed live goal timing. Detailed evidence and
boundaries are in
`runtime_integration/diagnostics/2026-09-26_root_cause/REVIEW.md`.

Two defects now have direct evidence. First, A* marks collision-rejected
nodes explored before enqueue and uses zero (`1 >> 20`) as its initial
infinite score. The isolated logging-only `scan19_audit_trace` passed the
native build and source/install identity gates. On captured walk_v4 inputs,
its first native search logged 982 later-free candidate encounters that had
never entered the queue; it exhausted the queue after 851 pops in 5.36 ms,
without hitting the 200 ms cap. This establishes occurrence in the candidate
replay, not a successful repair or physical no-path proof. The same source
pattern exists in live scan13.

Second, the right-side actor lies outside the tracker's selected robot-ground
mask. Same-source replay reproduces all positive-track timestamps (190 old,
0 right); 21,927 of 21,954 returns in the right actor spatial region are
discarded because selected ground is absent. Live right-side output has 281
complete-empty batches and one incomplete-empty batch; empty detection does
not prove full spatial ground coverage. Truth is offline ROI attribution only.

The first Unknown warning is a global-target check, followed by target retreat;
it is not sufficient evidence of the start blocker. Live navigation cancels at
2.16 s with no matching controller heartbeat, before the actor moves at
10.02 s. Height interpolation/Z-gradient restrictions and cross-floor support
association cause further recorded rejections. No safety policy, accepted
runtime source, original video, or frozen scan_04 was changed. A4 stays open.
