# Head-camera live check, 2026-09-11 04:50-04:58 UTC (robot clock 12:50 CST)

Access (read-only, no actuation): Mac on the robot Wi-Fi AP (Mac 192.168.2.103, AP 192.168.2.1 = motion host p2p0).
`ssh ysc@192.168.2.1` works with the existing key; Xavier via `ssh -J ysc@192.168.2.1 ysc@192.168.1.103` (hostname `lite`).
Orin 192.168.1.5 was down. Both robot hosts had been up about 10 minutes.

## Posture at capture
`/joint_states` (Xavier, ROS Noetic): knees LF/RF/LB/RB = -2.749 / -2.528 / -2.701 / -2.388 rad; hips-Y = 0.018 / 0.235 / -0.173 / -0.096 rad.
=> legs folded: power-on crouch (lying), NOT standing. Camera height is therefore roughly 0.1-0.2 m (not measured).
`/imu/data` (base_link): roll -0.47 deg, pitch +0.34 deg => torso level.
`/us_publisher/ultrasound_distance` = 0.665 m (nearest object ahead; the tripod at image lower-left is the likely return).

## What the two saved frames show (frame_20260911T045002Z_crouch.png, frame_20260911T045135Z_crouch.png)
- Ceiling and a fluorescent fitting are in the top of the frame; the far wall's floor line (door bottom) is at v ~ 540 of 720;
  the rover's wheel hubs (~0.17 m high) are at v ~ 600-620; the image centre is v = 360.
  With the torso level, the horizon lies well BELOW the image centre => the camera's optical axis points ABOVE horizontal.
- Vertical edges converge weakly towards a point above the image (pipe +6.7 px lean over 410 px, tripod pole -6.9 px over 330 px,
  partition post +39 px over 305 px; door left jamb ~0 px). Pairwise vanishing points are unstable (v from -250 to -12500 px).
- The upward pitch cannot be pinned down from this frame: with the third-party fy ~495 px the horizon offset (180-250 px) implies
  20-27 deg up, but the weak vertical convergence implies 5-11 deg up. The two agree only if fy is ~750-1150 px (HFOV ~58-82 deg),
  i.e. the lens may be narrower than the 103 deg third-party figure. Conclusion: sign = UP relative to the torso; magnitude
  UNKNOWN (5-27 deg); focal length UNKNOWN. A target of known size/height at known distance is required.
- The 2026-08-19 frame (.pipeline/experiments/2026-08-19_omnivla_vla_evidence_audit/inputs/real_lite3.jpg, also a crouch) puts the
  wheel hubs at v ~ 450, i.e. a smaller upward offset; torso pitch was not recorded then, so the two frames cannot be reconciled.

## Zero-tool measurement protocol (robot stays lying; no actuation)
1. Tape-measure the lens centre height above the floor (h_cam) and place a vertical tape/ruler at a measured distance D (1.0 m) in front of the lens.
2. Capture one frame (ffmpeg from rtsp://192.168.2.1:8554/test) and one /imu/data sample.
3. Read the ruler height at the image centre row (h_c), top row (h_t) and bottom row (h_b).
   pitch = atan((h_c - h_cam)/D)  (positive = up);  VFOV ~= atan((h_t - h_cam)/D) - atan((h_b - h_cam)/D);  fy ~= 360 / tan(VFOV/2).
4. Optional: a printed checkerboard (A4, 25 mm squares) at 3-4 poses gives fx, fy, cx, cy and distortion with OpenCV.

## Web identity search (subagent, 2026-09-11)
USB ID 1bcf:2cc8 / "LRCP F1080P" is unlisted in every public USB-ID database and marketplace; no lens spec exists online.
Reseller pages (Leobotics, myrobotsolution) quote "horizontal FOV 130°, 1920x1080@30fps" for the built-in camera; vendor docs give no numbers.

## Measured (2026-09-11 05:35-05:42 UTC, robot lying, torso IMU pitch +0.03..+0.05 deg)

Intrinsics (`intrinsics_burst_20260911T0535Z/calibration.json`, 36 poses of an 11x8 / 20 mm A4 checkerboard, RMS 0.29 px):
fx 490.1, fy 486.7, cx 614.4, cy 347.2 (1280x720); k1 -0.022, k2 -0.021, p1 0.0039, p2 -0.0025, k3 0.0013.
Pinhole HFOV 105.1 deg, VFOV 73.0 deg (DFOV 112.7). Coverage thin at the right edge and top (see corner_coverage.png), so the
distortion model is extrapolated there; the field-of-view figures are robust. Confirms the third-party fx 508.7 / fy 494.9 (fx within 4 %);
the reseller "130 deg" figure is wrong for this unit. Label: measured (reprojection-validated).

Elevation of the optical axis relative to gravity, from the sheet held flat on the vertical face of a white box standing on the floor
(assumption: box face vertical within ~1-2 deg; a tapered bin would bias this by its draft angle):
- `capture_20260911T052808Z_board_check` (board at 0.27 m): +15.1 deg up, roll +0.04 deg (both frames).
- `capture_20260911T054141Z_two_sheets_upright` (board at 0.73 m): +16.7, +16.6, +16.7 deg up, roll +0.2 deg, reproj 0.13-0.14 px.
- Scene cross-check: cabinet base line on the far floor at v ~ 490-500 puts the horizon ~120 px below the principal point -> ~+14 deg.
Adopted: elevation = +16 deg +/- 2 deg (UP). With the torso level this is the camera-to-torso pitch. The second sheet lay flat on the
floor in the same frames and was too foreshortened (~5 px per square row) to detect at 2-5x upscaling, so the floor-based lean-free
estimate was not obtained. A one-minute lean-free check remains possible: repeat with the box upside down; the mean cancels any draft.

Implication (effective VFOV up 36.2 / down 37.8 deg about the axis):
- bottom image edge reaches only 37.8 - 16.7 = 21.1 deg below horizontal -> at a standing camera height of 0.40 m the floor is first
  visible 1.04 m ahead (0.35 m height: 0.91 m).
- A virtual evaluation camera (HFOV 79 at 4:3, VFOV 63.5) pitched 15 deg down needs 46.75 deg below horizontal: impossible.
  Even a LEVEL virtual evaluation camera needs 31.75 deg: impossible. The lowest-pointing 63.5-deg-VFOV crop is pitched ~10.6 deg UP.
- Therefore the stock head camera cannot feed InternVLA-N1 in either the C5 (level) or C6 (15 deg down) configuration without re-mounting.
  Conditions C5/C6 were simulated at 0 / -15 deg; the real mount is about +16 deg. The D435i carrier (20 deg down) remains the only
  fixed downward-looking mount on the robot.
