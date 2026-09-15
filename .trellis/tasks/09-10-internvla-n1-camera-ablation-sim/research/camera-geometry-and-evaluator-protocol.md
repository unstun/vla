---
origin: ai+local_evidence
date: 2026-09-10
status: verified_locally_unless_marked
---

# Camera geometry and the InternNav evaluator protocol

All paths relative to `/Users/sun/tongbu/study/phdproject/vla` unless noted.
`EXP` = `.pipeline/experiments/2026-09-08_dualvln_rented4090`.

## 1. Lite3 sensor rig (local URDF)

Source: `/Users/sun/tongbu/study/phdproject/machine-dog-nav/references/locomotion/2026-08-13_v17a4_e3/source/v17a4/resources/lite3_sensor_rig/urdf/lite3_pro_sensor_rig_real_with_interface.urdf`.
The `lite3_rviz_v2.urdf` and `_isaac.urdf` variants carry identical joint origins.

| Joint | Parent -> child | xyz (m) | rpy (rad) |
| --- | --- | --- | --- |
| `sensor_carrier_joint` | TORSO -> sensor_carrier_link | 0.219, 0, 0.061387 | 0 |
| `d435i_body_joint` | sensor_carrier_link -> d435i_body_link | 0.013681, 0, 0.019734 | 0, 0.349066, 0 (20 deg pitch down) |
| `d435i_depth_optical_joint` | d435i_body_link -> optical frame | 0.0207, 0, 0 | optical convention |

Optical centre relative to TORSO origin: x = 0.252 m, z = 0.074 m.
Torso height at the default stance: `BASE_HEIGHT_TARGET = 0.345`
(`.../source/v17a4/source/robot_lab/robot_lab/tasks/lite3/env_cfg.py:43`, FK of the
vendor default stance). Camera height standing = 0.419 m. The LightNav Lite3
run recorded a minimum base height of 0.290 m while walking, giving about 0.36 m.

Lite3 front camera stream in the OmniVLA receive-only experiment: `/dev/video0`
MJPEG 1280x720 (`.pipeline/experiments/2026-08-19_omnivla_lite3_receive_only/decision_log.md:22`).
Whether that device is the D435i colour stream is not recorded; the D435i is
the only camera in the URDF.

D435i colour field of view (69, 42) degrees: quoted from the NavDP paper,
section III "Data Engine" (`docs/research/papers/NavDP2025.pdf`). Intel's page
could not be fetched this session. At a 4:3 profile the colour image is a
horizontal crop, so the vertical field of view is kept. Habitat's structured
config types `hfov` as an integer, so HFOV 54 is used: at 4:3 it gives
VFOV 2*atan(tan(27 deg)*3/4) = 41.9 degrees, against the D435i's 42.

## 2. What InternVLA-N1 was evaluated and trained with

- Habitat eval (`EXP/work/InternNav/scripts/eval/configs/vln_r2r.yaml` and the
  derived `EXP/public_scenes/configs/vln_public_scenes.yaml`): only width,
  height (640x480), and hfov 79 are set. Sensor position and orientation
  inherit habitat-lab 0.2.4 defaults: position [0, 1.25, 0], orientation
  [0, 0, 0], agent height 1.5, radius 0.1 (fetched from
  `habitat-lab/habitat/config/default_structured_configs.py` at tag v0.2.4;
  `task/vln_r2r.yaml` and `agents/rgbd_agent.yaml` set none of these).
  `EXP/public_scenes/setup/frozen_public_episodes.json` records the same
  resolved geometry for the baseline runs. VFOV = 63.5 degrees.
- VLN-PE / Isaac trainer config: `internnav/configs/trainer/task.py:22`
  `robot_height = 1.55` (H1 humanoid).
- System 1 (NavDP data engine, paper section III): robot height randomized in
  (0.25 m, 1.25 m), camera pitch randomized in (-30, 0) degrees, two FOV
  profiles: D435i (69, 42) and Zed 2 (110, 70).
- Real-world deployment (DualVLN paper section 5.2): Turtlebot4, Go2, G1 with
  D455 "mounted at varying heights and angled downward by 15 degrees"; the
  paper claims robustness "despite variations in camera height" without
  numbers. InternNav ships `assets/3d_printing_files/go2_stand.STEP` whose
  bounding box measured locally is 239 x 346 x 347 mm (orientation of the
  part unknown), plus `downwards_slope.3mf`. The community Go2 guide says
  "3D-print mounts for better forward ground view".

## 3. Evaluator protocol in `dual_system` mode

File: `EXP/work/InternNav/internnav/habitat_extensions/vln/habitat_vln_evaluator.py`
(worktree hash `a05268d5e4fac8ab6147d2c828e16ae76d413fe074d2e7f0f99e26ae6fcbf3e7`
in baseline runs v2 to v5; differs from pristine only by the two lazy-import
shims and the output-only trace/video patch).

Per step (lines 376 to 430):
1. Level RGB frame resized to `resize_w x resize_h` (384x384) is appended to
   the System-2 history.
2. Unless the previous action was LOOKDOWN, the evaluator steps LOOKDOWN twice
   (2 x `tilt_angle` 15 = 30 degrees down), captures the RGB-D frame for
   System 1 (depth clipped at 5 m, resized 224x224), then steps LOOKUP twice.
3. System 2 may itself emit LOOKDOWN (action code 5); the next frame, at native
   640x480 and 30 degrees down, is fed back as the `look_down_followup` branch.
4. When System 2 outputs a pixel goal, `generate_latents` + `generate_traj`
   produce the trajectory from the look-down RGB-D; `traj_to_actions` converts
   it to discrete actions. No camera transform or intrinsic is used here.
5. `self._camera_height` (from `rgb_sensor.position[1]`) and the hard-coded
   `np.deg2rad(30)` transform are only used by `pixel_to_gps` in the
   `system2` mode (line 967). Changing sensor height or pitch does not alter
   `dual_system` control logic.

Real-world agent (`internnav/agent/internvla_n1_agent_realworld.py`,
`scripts/realworld/http_internvla_client.py`): one fixed camera, RGB and
aligned depth from `/camera/camera/...`, the `look_down` flag only switches the
prompt branch; there is no physical tilt. So a fixed-pitch Habitat camera with
`tilt_angle: 0` is the closest simulation of the real deployment path.

## 4. Field-of-view geometry (computed)

| Condition | Height | Pitch | VFOV | View span (deg from horizontal) | Floor first visible |
| --- | --- | --- | --- | --- | --- |
| B0 Habitat default | 1.25 m | 0 | 63.5 | -31.7 to +31.7 | 2.02 m |
| C1 Lite3 rig | 0.42 m | -20 | 41.9 | -41 to +1 | 0.48 m |
| C2 height only | 0.42 m | 0 | 63.5 | -31.7 to +31.7 | 0.68 m |
| C3 FOV only | 1.25 m | 0 | 41.9 | -21 to +21 | 3.27 m |
| C4 raised mount | 0.65 m | -15 | 41.9 | -36 to +6 | 0.90 m |

Ground distance of the bottom-edge ray d = h / tan(pitch + VFOV/2). Habitat's
depth image is z-depth along the optical axis, so a flat floor at a row whose
ray is theta_r below the axis reads h / (sin p + tan(theta_r) cos p); this
equals d only for a level camera. The preflight compares the 90th percentile of
the bottom 16 rows (central 200 columns) with the same percentile of that
per-row expectation: about 0.62 m (C1), 0.72 m (C2), 3.48 m (C3), 1.07 m (C4),
tolerance 25 percent. Found by the trellis-check pass on 2026-09-10; the
ground-distance formula would have failed C1 by about 28 percent. The pinned
`internnav/habitat_extensions/vln/utils.py:94` unprojects depth as
`x = (u - cx) * z / fx`, consistent with z-depth.

## 4b. Round-1 preflight measurements (2026-09-10)

Sensor state at the episode-1 reset matched every condition exactly (height,
forward offset, pitch sign: C1 sensor rotation is 20.000 degrees down). The
bottom-row floor z-depth exceeded the flat-floor expectation by a constant
implied gap of 0.158 to 0.163 m across all four conditions (three heights,
three pitches, two fields of view), so the agent origin (navmesh point,
agent y = 0.111 at reset) sits about 0.16 m above the rendered floor at this
start pose. Habitat navmeshes are height-quantized, so the gap varies along a
route; it applies equally to the baseline. Conditions keep nominal Habitat
sensor heights; the preflight now checks the implied gap bounds instead of a
25 percent ratio. Evidence: `REQ/preflight/*_stdout.txt`, `REQ/OPUS_RETURN.md`
section 3.3, and the eight start-frame PNGs.

## 4c. Round-2 tilt no-op measurement (2026-09-10)

With `tilt_angle: 0`, a look_down action leaves the sensor position and pitch
unchanged (pitch delta 5.5e-7 degrees) but re-normalises the sensor quaternion
by 1 to 2 ULP, which flips 939 of 307,200 pixels (0.31 percent, mean absolute
channel delta 0.0014) at geometric edges; a second look_down and the look_up
change nothing further, and rendering without an action is deterministic.
Evidence: `REQ/preflight/diag_round2_tilt_noop_c1_lite3_rig.json`. The preflight
therefore bounds the pitch delta and changed-pixel fraction instead of
requiring a bit-identical frame.

## 5. Baseline facts to compare against

- Runs `public_eval_v1` to `v5`: episode 1 success 3/5 (NE 1.050 to 4.057 m,
  0 collisions), episode 2 success 2/5 (NE 2.154 to 5.911 m, 8 to 10
  collisions); all ten runs ended on a learned System-2 STOP; 92 pixel-goal
  events, all from the `look_down_followup` branch. Total wall 721.9 s for five
  supervisor records. Source: `EXP/review/PUBLIC_SCENES_LEAD_REVIEW.md`,
  `EXP/public_scenes/setup/run_summary.json`.
- Input hashes recorded in `EXP/public_scenes/runs/public_eval_v5/inputs.json`.
- Seeding: numpy only (`np.random.seed(local_rank)`); torch unseeded; System 1
  flow-matching noise differs per run (memory note
  `internnav-habitat-eval-is-not-seeded`).

## 6. Open verification items

- Habitat sensor `orientation` units and order are confirmed from habitat-sim
  v0.3.3 `src/esp/sensor/Sensor.cpp` (`setTransformationFromSpec`):
  `node().translate(spec_->position)` then `rotateX(Magnum::Rad(orientation[0]))`,
  `rotateY`, `rotateZ`, so the x component is a pitch in radians. The sign
  (negative = down) is not yet verified from source; the preflight render with
  the depth floor-distance check settles it empirically before any GPU run, and
  an inverted sign fails that check loudly. habitat-lab v0.2.4 `actions.py`
  sources the look_up/look_down actuation amount from `tilt_angle` (degrees in
  the structured config).
- `tilt_angle: 0` makes LOOKDOWN/LOOKUP no-ops; confirm through the preflight
  that the composed action config accepts it and that episode step counting is
  unchanged (the evaluator's `step_id` counts only policy steps).

## 6. Camera facts verified from primary sources (added 2026-09-10, web subagent)

Sources, quotes, URLs, and SHA-256 are in
`.pipeline/survey/2026-09-10_lite3_cameras_web_sources/README.md`.

| Fact | Value | Source (primary) |
| --- | --- | --- |
| D435i colour FOV | H 69 / V 42 / D 77 deg, OV2740 | RealSense D400 datasheet 337029-017 Rev 021, Table 3-49 p67 |
| D455 colour FOV | H 90 / V 65 / D 98 deg, OV9782 global shutter | same table |
| InternVLA-N1 real robots | "All robots are equipped with Intel Realsense D455 cameras, which are mounted at different height but angled downward at 15°" | InternVLA-N1 technical report p14 §5.5 |
| InternNav real-world intrinsics | fx = fy = 386.5, cx = 328.9 at 640x480, i.e. HFOV 79.2 deg (derived) | `scripts/realworld/http_internvla_server.py:90` at commit 7a5c624 |

This confirms the section-4 assumption that HFOV 54 (VFOV 41.9 at 4:3)
represents the D435i colour stream, and that the authors' D455 at 640x480 is
close to the Habitat evaluation camera's `hfov: 79`.

Lite3 second camera: the Jueying Lite3 user manual (CE V1.0.7 §1.4) lists
"Wide Angle Camera x1" beside the D435i, and the motion-host communication
manual (V1.0.7 §1.2.11) publishes it at `rtsp://<motion host>:8554/test`. On the
project robot the vendor process `/home/ysc/rtsp_stream/start_stream.sh` owns
`/dev/video0` at MJPEG 1280x720 and restreams it (receive-only experiment
2026-08-19, one real frame captured). No manufacturer document, local or
fetched (US/CN product pages, 2025 brochures, perception manual V2.2.2), gives
its FOV, resolution, sensor, or mount pose; the "130 deg / 1080p" figure that
appears in search-engine snippets is secondary and unattributed. Its geometry
must be measured on the robot before a condition is derived from it.

### 6b. Lite3 wide-angle camera: round-2 web findings (2026-09-10, labelled)

Rows, quotes, and files are in section 2b of the survey README; the evidence
files (official `Lite3_Track` pull script, a third party's calibration JSONs
and commissioning notes) are saved with SHA-256 in the same directory.

| Fact | Value | Label |
| --- | --- | --- |
| Placement | front face of the head, below the D435i bracket, above the front ultrasonic sensor | primary (Lite3 Pro user manual V2.0.0 §1.3 labels) |
| Stream | H.264 over RTSP, decoded at 1280x720 (`rtph264depay` in the official `Lite3_Track` pull script) | primary (code) |
| Intrinsics at 1280x720 | fx 508.7, fy 494.9, cx 640.9, cy 339.5, pinhole + small polynomial distortion, RMS 2.94 px over 26 ArUco views | secondary-technical (one Lite3 Venture unit, `armwaheed/mappo-arm-cloud-physical-ai` @ dc4c50c) |
| Derived FOV | HFOV 103.0 deg, VFOV 72.1 deg at 16:9; a 4:3 centre crop (960x720) gives HFOV 86.7 deg | derived from the row above |
| Lens type | nearly rectilinear; an equidistant fisheye fit gave RMS 52.9 px | secondary-technical |
| Mount | optical centre about 0.40 m above ground standing, pitch about 15 deg down (elevation fit); the same author elsewhere writes 0.37 m and about 11 deg | secondary-technical, internally inconsistent |
| Distributor figure | "horizontal FOV 130 deg, 1920x1080@30fps" | secondary-prose; inconsistent with the calibrated fx (130 deg rectilinear at 1280 px would need fx about 298 px) |

Implication for the ablation: if the third-party geometry holds for the
project robot, the head camera at 15 deg down with VFOV 72 deg spans
-51 to 21 deg from horizontal, so it still sees the horizon,
unlike C1 (-41 to +1). It is close to the authors' real-world D455 at 15 deg
down (VFOV 65, HFOV 79 at 4:3). The proposed confirmatory condition C6
(0.42 m, 15 deg down, HFOV 79, no tilt) is therefore a usable proxy for the
head camera; C5 (level) remains the alternative if a level mount is chosen.
All of this still needs the on-robot measurement before it is treated as
the project robot's geometry.

### 6c. Vendor torso mesh check for the head camera (2026-09-10, local)

`torso.STL` in the pinned Lite3 resources (machine-dog v17a4, SHA-256
6f3f5fc4b9985db5..., 26,365 faces, not watertight) is a coarse hull: extent
0.548 x 0.217 x 0.126 m, front-most point x = 0.279 m from the TORSO origin,
nose cap z from -0.018 to +0.049 m, no lens aperture or slanted camera face
modelled (a plane fit to the nose vertices is within 4 deg of vertical).
What it does give, primary: the head camera lies at most 0.28 m ahead of the
TORSO origin and within about -0.02 to +0.05 m of its height, so at the
0.345 m standing torso height the optical centre is 0.33 to 0.40 m above
ground. This brackets the third party's 0.37 to 0.40 m. The mount pitch
cannot be read from the mesh; only the third party's 11 to 15 deg exists.

### 6d. Prior art: Lite3 head camera in robot description files (2026-09-10, round 3)

Section 2c of the survey README (files and SHA-256 saved). Result: no
URDF/xacro/SDF/MJCF/USD on GitHub models the built-in wide-angle head camera.
Fourteen code-search queries returned nothing; 38 Lite3 model files from 30
repositories (vendor `deep_robotics_model`, `sdk_deploy`, robot_lab, rl_sar,
legubiao, TopHill, Lite3_VMC, parkour_lite3, navigation stacks) contain no
camera sensor. Camera elements that do exist:

| Source | What | Values | Label |
| --- | --- | --- | --- |
| DeepRoboticsLab `deep_robotics_model` @ 549eb9a `Lite3/mjcf/Lite3.xml` (same in `sdk_deploy` @ 2367375) | two MuJoCo `mode="track"` chase cameras under TORSO | pos (0, 2.0, 0.5) and (-2, 0, 0.5), fovy 90; viewer cameras, not sensors | primary |
| legubiao/quadruped_ros2_control @ 5434c58 `lite3_description/xacro/gazebo.xacro` | optional add-on D435 on the torso top, `EXTERNAL_SENSORS=false` by default | origin xyz 0.23 0 0.06, rpy 0 0.1 0 (5.7 deg down; Go2 file uses the same 0.1 rad, so a default, not measured) | secondary-technical |
| LaoGordon/lite3_gazebo_classic @ f42239b `sensors/d435i_sensor.xacro` | D435i macro on TORSO | horizontal_fov 1.211 rad (69.4 deg, i.e. the D435i colour HFOV; the comment says 87 deg), 1280x720 | secondary-technical |
| armwaheed @ dc4c50c | no model file; pose only in calibration JSON | 0.40 m, -15.04 deg | secondary-technical |

Consequence: a head-camera link for the Lite3 would be new work with no
upstream to import; the position bracket comes from the vendor mesh (6c),
pitch and intrinsics from the third-party calibration (6b) until measured.

### 6e. Research use of the Lite3 built-in camera (2026-09-10, round 4)

Section 2d of the survey README (17 code files saved, 52 checksums verify).
No paper or thesis uses the Lite3 head camera as perception input. Every
consumer found is a code project reading `rtsp://192.168.1.120:8554/test`
with OpenCV/FFmpeg or GStreamer: person following and face tracking
(IbrahimXXs/Jueying-Lite-3---Full-Python-Control @ e5a6715), YOLO11 segmentation
tracking running on the motion host's RK3588 NPU with the stream treated as
native 1280x720 (xnymerian/DeepRobotics-Lite3-Tracking-Segment-Algorithm @
0b36e83), face/emotion HRI (liusiqi05/Lite3_dog @ 5001640), two teleoperation
UIs, and one SDK wrapper. None reads `/dev/video0`, publishes a ROS topic,
measures latency, or calibrates; only the armwaheed calibration (6b) exists.
Lite3 papers found used other sensors: PUMA (D435i), PIE arXiv 2408.13740
(egocentric depth camera), arXiv 2512.01052 (arm-mounted D435i), arXiv
2512.21293 (LiDAR/IMU). Nearest published analogue: Sensors 25(23):7247, 2025,
staircase detection from the Unitree Go1's built-in fisheye head cameras.
Side fact: the RTSP service and the NPU project both run on the motion host,
which is an RK3588; this explains the Rockchip `mpp` decode errors seen on
the project robot on 2026-08-19 and points to decoding on the Xavier NX
(`nvv4l2decoder`, as the vendor's Lite3_Track does) for a low-latency path.

## 6f. Head-camera module identity and live check (2026-09-11, read-only on the robot)

On-robot facts (primary, verified by ssh to the motion host `ysc@192.168.2.1`, see `head_camera_live_2026-09-11/`):
USB ID `1bcf:2cc8` Sunplus, UVC card name "LRCP  F1080P", MJPEG-only, modes up to 1920x1080@30 plus 1280x960 (4:3);
vendor pipeline gst v4l2src 1280x720 -> mpph264enc -> mediamtx `rtsp://192.168.2.1:8554/test`. No calibration file on the host.
Robot lying (knees -2.4..-2.7 rad), torso IMU level (pitch +0.3 deg): the frame's horizon lies 180-250 px below the image
centre, so the camera axis points UP relative to the torso; magnitude (5-27 deg) and focal length remain unknown.

Web search for the module (subagent, 2026-09-11; URLs reported by the subagent, not re-fetched locally, so `surveyed`
by proxy only): `1bcf:2cc8` and "LRCP F1080P" are absent from usb.ids, DeviceHunt, linux-hardware.org, IPFire and h-node,
and from GitHub, Taobao/1688 and Chinese web results. No sensor, focal length, distortion model or VFOV is published.
The only FOV figure is reseller-level: Leobotics and myrobotsolution list "built-in wide-angle camera, horizontal FOV 130°,
1920x1080@30fps"; Deep Robotics' own brochures and the Lite3 Pro user manual give no camera numbers. The Perception
Development Manual V2.2.2 mentions only the "h264-encoded 720p rtsp video stream" decoded with DeepStream. Consequence:
the 130° figure stays unverified and contradicts the third-party 103° calibration; only an on-robot calibration resolves it.

## 6g. Head camera measured on the robot (2026-09-11) — supersedes the proxy geometry of C5/C6

Checkerboard calibration (11x8 inner corners, 20 mm, 36 poses, RMS 0.29 px) of the stock head camera at 1280x720:
fx 490.1, fy 486.7, cx 614.4, cy 347.2, nearly rectilinear (k1 -0.022). HFOV 105 deg, VFOV 73 deg. Label: measured.
Optical-axis elevation relative to gravity, robot lying with the torso IMU level, sheet on a vertical box face: +15.1 deg (0.27 m)
and +16.7 deg (0.73 m) UP; adopted +16 +/- 2 deg, subject to the box face being vertical. Label: measured (single-reference).
Consequence: the bottom image edge sees only ~21 deg below horizontal; at 0.40 m the floor appears from ~1.0 m ahead; no crop of
this stream can synthesise the evaluation camera even level (needs 31.75 deg below), let alone 15 deg down (46.75 deg).
C5 (level) and C6 (15 deg down) therefore do not describe the stock mount; the stock mount is ~16 deg UP and is unusable for
InternVLA-N1 without re-mounting. Evidence: `head_camera_live_2026-09-11/`.

## 6h. Fusing the two real cameras into one RGB image (assessment, 2026-09-11)

Vertical coverage relative to horizontal: head camera (+16 deg up, VFOV 73) -22..+52 deg, +/-52 deg wide; D435i colour (20 deg down,
VFOV 42) -41..+1 deg, +/-27 deg wide at 640x480 (+/-34.5 at 1280x720). Overlap band -22..+1 deg.
A LEVEL virtual evaluation camera (HFOV 79 at 4:3, VFOV 63.5: -32..+32, +/-39.5) is fully covered in height: top ~82 % of the
image from the head camera (rotation-only remap, exact with the measured intrinsics, fixed LUT), bottom ~18 % from the D435i
(depth-based reprojection or ground-plane homography), blend in the overlap. A 15-deg-down virtual camera is NOT covered: its
bottom ~14 % (below -41 deg) is blank. Virtual pitch 0..-9 deg is feasible.
Gaps: below -22 deg only the D435i contributes, narrower than +/-39.5 -> blank bottom-corner triangles, ~7 % of the image at
640x480, ~3 % at 1280x720 (inpaint or leave black; out of the training distribution). Seams: different sensors, exposure, blur.
Timing: pair frames by timestamp; the head stream has H.264 encode/decode latency; 200 ms at walking speed = 10 cm parallax.
Compute: ms-level on the Xavier, which already decodes the head stream (vendor tracking demo) and receives D435i colour (LIVO).
Comparison: a wide module on the 20-deg carrier gives one clean image matching the authors' setup; fusion needs no hardware and
is the more interesting thesis result (camera-layout-independent deployment) but carries seam/corner risk.
Validation path: render both real mounts as two Habitat sensors, fuse in a preprocessing hook, run the castle episodes against
the level and 15-deg-down references (C2/C6). New condition set; needs authorization (~10 runs).

## 6i. Round 5 result (2026-09-11): fused level camera c7 = 0/10

Mechanism verified in Habitat (preflight): task sensor overrides `rgb`, bit-identical offline recompute, sensor poses exact
(head +16.7 deg up confirms the positive-orientation sign), 6.0 percent uncovered, 136 ms per fusion. Outcome: 0/10 versus c5 2/10
(same pose, ideal render) and c6 5/10. Episode 1: all five runs take one route (System 2 is deterministic on the image) and stop at
the nearer high-backed chairs 7.1-7.9 m from the goal, zero collisions; the divergence from c5 is a pixel goal shifted by a few
pixels at step 17. Episode 2: late-stop failures as everywhere. Conclusion so far: the fused input is usable by the model but does
not recover the near-floor advantage of a downward camera, and small input changes flip System 2's route on this instruction.

## 6j. Round 5b result (2026-09-11): c8 = 2/10, equal to the ideal level camera

c8 (1.2 percent uncovered) restores the leftward episode-1 route that c7 (6.0 percent) lost: ep1 oracle 5/5 vs 0/5
(p = 0.008), success 2/5; three runs overshoot after reaching the goal area (late-stop). Ep2 0/5 as everywhere. Fusion with
small corners behaves like the ideal level camera at the head pose (c5 2/10); the downward camera (c6 5/10, ep1 5/5) remains
out of reach for fusion. Evidence: cam_c8_fused_level_720_v1..5, LEAD_REVIEW round-5b addendum.

## 6k. Route decision (2026-09-11): software-only fusion, and two corrections

Dr Sun: "Let's go with the algorithm fusion route (c8 dual-camera fusion with D435i at 1280x720) so we can achieve deployment
purely through software without any hardware modifications." Recorded as the deployment route for the parent task. Two claims
made in the round-5b close-out do not survive a re-read of `condition_summary.json` and are corrected here.

### Correction 1: c8 reaches the goal as often as the best condition, not as often as the level camera

Oracle success (`n_entered_success_radius`, both episodes, 10 runs per condition) against success:

| Condition | Geometry | Reached goal radius | Stopped inside it |
| --- | --- | --- | --- |
| B0 baseline | 1.25 m, level, look-down | 8/10 | 5/10 |
| C2 height only | 0.42 m, level, look-down | 7/10 | 5/10 |
| C5 ideal render, level | 0.40 m, level | 6/10 | 2/10 |
| C6 ideal render, 15 deg down | 0.40 m, 15 down | 10/10 | 5/10 |
| C7 fused, D435i 640x480 | 6.0 pct uncovered | 5/10 | 0/10 |
| C8 fused, D435i 1280x720 | 1.2 pct uncovered | 10/10 | 2/10 |

C8 is not "equal to C5": it reaches the goal region in 10 of 10 runs, tying C6 and beating the 1.25 m baseline (8/10), while C5
reaches it in 6. Every C8 failure is a stop-timing failure, not a perception failure. The earlier "capped at level-camera
performance" summary conflated the two metrics. The binding constraint on the chosen route is STOP arbitration, which is also
software.

Supporting detail: on episode 1, C8 takes a median 167 steps with 19 pixel goals against C6's 69 steps and 7 pixel goals, and
overshoots to a median 17.3 m after entering the radius. `s1_stop_mid_segment` is 13 (C8 ep1) and 16 (C7 ep1) against 5 for C6
and 2 for the baseline, so residual uncovered pixels do disturb System 1 even when the route is right.

### Correction 2: fusion is not restricted to a level virtual camera

The virtual camera is synthetic, so its pitch is free within the covered elevation band; `Cam`, `head_lut`, `warp_d435` and
`fuse` are all pose-general (`head_lut` is `virt.rays() @ virt.R.T @ head.R`; `warp_d435` back-projects into the agent frame
and reprojects). The only obstacle is a guard in `fused_camera_plugin.py`:
`raise ValueError('FusedRGBSensor: the virtual (rgb_sensor) camera must be level')`, written for rounds 5/5b where every
condition was level by construction.

Covered band from the two real mounts (measured head +16.7 deg, VFOV 72.5; D435i 20 deg down, VFOV 42.3): -41.1 to +52.9 deg,
with 20.7 deg of overlap. A 640x480 HFOV 79 virtual camera has VFOV 63.5, so on geometry alone it can be pitched up to
9.4 deg down before its bottom edge leaves the D435i band.

Measured on the analytic self-test scene (`test_fused_camera.py` render, c8 D435i):

| Virtual pitch | Uncovered | Floor first visible |
| --- | --- | --- |
| 0 deg (C8 as run) | 1.28 pct | 0.65 m ahead |
| 5 deg down | 2.08 pct | 0.54 m ahead |
| 9 deg down | 3.05 pct | 0.46 m ahead |
| 12 deg down | 8.78 pct | 0.42 m ahead |
| 15 deg down (C6 geometry) | 14.56 pct | 0.38 m ahead |

Calibration of the sweep: at 0 deg the analytic harness gives 1.28 pct uncovered against the 1.2272 pct that the c8 preflight measured in Habitat on the castle scene, so the harness is a fair proxy for the coverage the model actually saw. Correct statement: fusion cannot reach a
full 15 deg down, but it can reach about 9 deg down, which recovers most of the near-floor geometry that made C6 win
(0.46 m against C6's 0.38 m and the level camera's 0.65 m). Whether that converts into C6-like success is untested.

Diagnosis of the extra 1.8 points at 9 deg: not a geometric shortfall. Depth in the test scene spans 0.6-3.67 m and raising
`depth_valid_max` to 1e6 changes nothing; no image row is more than 50 pct empty. They are forward-splat gaps, where the D435i's
near floor is magnified on reprojection into a more downward virtual camera. Extra 3x3 hole-fill passes at the shipped
`cnt >= 5` threshold close none of them (converged after the existing two passes) and `cnt >= 3` recovers only 3.05 -> 2.33 pct,
so they are thin structured streaks rather than isolated pixels. Removing them properly means a backward warp (per virtual pixel,
inverse-map into the D435i with a depth test) in place of the forward splat, which is a real code change needing re-validation
against AC10.

Risk to weigh before running: 3.05 pct uncovered sits between C8 (1.28 pct, 10/10 oracle) and C7 (6.0 pct, 5/10 oracle, 0/10
success). The C7 shortfall was in the corners; a 9 deg-down shortfall is a scatter near the bottom. Whether the model cares about
the pattern or only the fraction is unknown, which is the reason to run it rather than assert it.

### What software-only deployment on the robot still needs

Available now: head-camera intrinsics and distortion at 1280x720 (36 poses, RMS 0.2883 px), head elevation +16 deg +/- 2,
the RTSP 720p head stream, D435i colour 69x42 deg matching the C8 condition, and a fusion core validated inside the official
evaluator by a bit-identical offline recompute.

Not yet available, in dependency order:

1. D435i-to-head rigid transform (R, t). The sim knew both poses exactly; on the robot the D435i warp needs the full 6-DoF
   transform into the virtual frame. Translation error enters as parallax scaling with 1/depth. Feasible with the characterised
   A4 board (11x8, 20 mm) held in the 20.7 deg overlap band, solvePnP in each camera, then compose. Needs the robot.
2. Lens distortion in the head LUT. `head_lut` is a rotation-only pinhole map, correct for the rendered pinhole and wrong for the
   real lens. The measured k1..k3, p1, p2 must enter the LUT. Doable offline against the 36 frames already captured locally.
3. D435i colour at 1280x720 with colour-aligned depth, and what the Xavier NX can actually publish at that rate.
4. Time sync between an RTSP H.264 head stream and the ROS D435i stream. At 0.5 m/s a 200 ms offset smears the seam by 10 cm.
5. Throughput. 226-244 ms/frame at 720p on a 4090 in preflight; the LUT is static under a rigid transform and can be precomputed,
   leaving the splat as the only per-frame cost.
6. Photometric seam. Two sensors with independent auto-exposure; the feather blends geometry, not radiometry.
7. Compute placement. The Xavier NX cannot host Qwen2.5-VL, so the loop is robot -> network -> GPU host -> action.

### Proposed next simulation condition (needs authorization; all 40 runs are used)

C9 `c9_fused_down9`: the C8 sensor set with the virtual camera pitched 9 deg down, five supervised runs on the same two
episodes. Cost: relax the level-only guard to allow a non-zero x rotation (keeping yaw/roll zero and the shared optical centre),
one new YAML from `make_fused_yamls.py`, one preflight with `max_uncovered` set from the measured 3.05 pct. No change to the
fusion maths, the model, or the evaluator. It is the direct test of whether the software-only route reaches C6-like performance,
and it is the last camera-geometry question the simulation can answer.

## 6l. Round 6 result (2026-09-11): C9, the fused camera pitched 9 deg down = 1/10

The pitched fused camera works mechanically and does not recover C6. Preflight passed all nine stages: uncovered 3.30 pct
(self-test predicted 3.05, Habitat came in higher rather than lower, the opposite of the level case), head 63.6 pct,
head-region PSNR 34.66 dB, fusion 256 ms, all sensor poses exact, fused rgb bit-identical to the offline recompute. The
corrected floor-depth expectation returned an implied gap of 0.1576 m, matching the 0.158-0.163 m of every earlier
condition; the level-only form it replaced would have reported 0.046 m, inside the accepted band and wrong.

Result: 1/10. Ep1 0/5 with oracle 0/5 (NE 3.5-7.4 m, 62 steps, 15 System-2 calls). Ep2 1/5 with oracle 5/5 and a navigation
error median of 4.04 m, the lowest of every condition at the head pose and below the 1.25 m baseline's 4.89.

Two things worth carrying forward:

- **The uncovered-pixel hypothesis from 6i does not survive.** C9 carries the most uncovered pixels of the fused set
  (3.30 pct against C8's 1.23 and C7's 6.0 measured in Habitat) yet has the fewest `s1_stop_mid_segment` events on
  episode 1: 4, against C7's 16, C8's 13 and C6's 5. Scattered bottom black behaves differently from corner black, or the
  count was never about coverage at all.
- **Episode 1 cannot discriminate camera geometry at this sample size.** Oracle success is 3, 1, 5, 0, 5, 0 for B0, C5, C6,
  C7, C8, C9, near-unanimous within each condition and not monotone in pitch, field of view or uncovered fraction. System 2
  locks one route per image stream (6i) and the lock flips on small input changes, so with one condition per geometry the
  episode-1 success metric measures the lock, not the camera. C9 vs C8 and C9 vs C6 both give Fisher p = 0.0079, and neither
  is evidence about pitch. This weakens C6's 5/5 exactly as much as C9's 0/5, and it means the round-5b reading of C8 as
  "reaches the goal 10/10" is also partly a lock. The two-episode design is the binding limitation; more runs on the same
  two episodes cannot fix it, more episodes could.

Route status unchanged: C8 is the configuration to deploy, the decisive problem is stop arbitration rather than geometry,
and the unmeasured D435i-to-head rigid transform remains the first real-robot blocker (6k).
