# Lite3 camera height feasibility for InternVLA-N1

## Source requirement

Dr Sun, 2026-09-10. After the session finding that the Lite3 sensor-rig camera
sits at about 0.42 m above ground, pitched 20 degrees down, on a RealSense
D435i, while InternVLA-N1 DualVLN is evaluated in Habitat with a level camera at
1.25 m, Dr Sun decided: test the performance in simulation first, then move to
the real robot afterward.

## Goal

Decide, with recorded evidence, whether InternVLA-N1 DualVLN can be used from
the current Lite3 camera mount, or whether the mount must be raised or
re-pitched before real-robot trials.

## Task map

| Child | Deliverable | Status |
| --- | --- | --- |
| `09-10-internvla-n1-camera-ablation-sim` | Official InternNav evaluator on the two frozen skokloster-castle episodes under four Lite3-motivated camera conditions, compared with the recorded baseline; condition summary; mount recommendation. | planning |
| real-robot camera trial (not created yet) | Lite3 front-camera frames through the official real-world agent path with the recommended geometry, receive-only first. Created only after child 1 returns its recommendation and after explicit real-robot authorization from Dr Sun. | not created |

Ordering: child 1 must reach `review` with a written recommendation before the
real-robot child is created. The parent has no direct implementation work.

## Cross-child constraints

- Model, evaluator, scenes, and episodes stay pinned to the DualVLN experiment
  `.pipeline/experiments/2026-09-08_dualvln_rented4090`: InternNav
  `7a5c62400ac45b313d9b709c740b64191556a242`, checkpoint
  `InternRobotics/InternVLA-N1-DualVLN` at
  `a698a9e898b4001621a319e1bc89f02ec715cc86`, Habitat test scenes at
  `910c783fb954da8497ea5f811b843a76590ddddc`, frozen annotation SHA-256
  `49f1bff7e1623e312b303b4b938a2c821c015e8ebad001a66c01a0f72e597889`.
- Public-scene functional tests only. No R2R or Matterport3D claim, no
  training or fine-tuning, no locomotion actuation. Real-robot actuation needs
  separate explicit authorization.
- Execution on the rented RTX 4090 through a manually dispatched Opus execution
  package; the local repository is the only source of truth and all evidence
  returns to local paths through a stated Sync Gate.
- Evidence labels: results are "official evaluator on custom public-scene
  tasks" plus a named camera condition. Never `reproduced` or `validated`.

## Acceptance criteria

- [ ] Child 1 is archived with a lead review verdict and a written mount
      recommendation (keep, raise, or re-pitch) stated as effect sizes against
      the recorded baseline, with its statistical limits stated.
- [ ] The recommendation names the exact camera geometry (height, pitch,
      field of view, resolution) to carry into the real-robot child, and into
      the URDF and the LightNav Lite3 adapter if the mount changes.
- [ ] The real-robot child exists with its own PRD and authorization gate, and
      the parent integration review compares simulated and real outcomes.
- [ ] Hot zone, experiments index, and terminology are updated.

## Status 2026-09-10

Child 1 executed and lead-accepted (20 runs, three rounds). Recommendation in
`.pipeline/experiments/2026-09-08_dualvln_rented4090/public_scenes/requests/2026-09-10_lite3_camera_ablation/review/LEAD_REVIEW.md`: keep 0.42 m height, change pitch to level (at most a small
downward angle), widen the colour field of view to about HFOV 79 (VFOV 63 at 4:3), and run a
confirmatory fixed-camera sim pair (C5 level, C6 15 deg down, both HFOV 79, 0.42 m, tilt 0)
under new authorization before creating the real-robot child. Child 1 archival and the
acceptance rows above wait for Dr Sun's review and commit.

## Non-goals

- Retraining or fine-tuning InternVLA-N1.
- Changing the Habitat agent body, navmesh, or scenes.
- Authoring new episodes; the two-episode limit is recorded as a limitation.

## Status update 2026-09-10 (round 4)

Dr Sun kept the built-in head camera and authorized the confirmatory pair in
simulation. C5 (0.40 m, level, HFOV 79, fixed) 2/10; C6 (0.40 m, 15 deg
down, HFOV 79, fixed) 5/10, equal to the baseline total, with episode 1 at
5/5. Revised recommendation: keep the head camera at its existing downward
pitch, crop the stream to HFOV 79 at 4:3, do not re-mount level. Next
decision: authorize the camera-only on-robot measurement, then create the
real-robot child. Geometry is estimated until measured. Details:
`.pipeline/experiments/2026-09-08_dualvln_rented4090/public_scenes/requests/2026-09-10_lite3_camera_ablation/review/LEAD_REVIEW.md`.

## Status update 2026-09-11 (on-robot measurement, read-only)

Head camera measured with a checkerboard while the robot lay level: fx 490 / fy 487 (HFOV 105°, VFOV 73°), optical axis
+16 ± 2° UP relative to gravity. The stock head mount therefore cannot provide the near-floor view InternVLA-N1 needs, and no
crop of its stream can emulate the evaluation camera. Child C5/C6 results describe hypothetical 0°/−15° mounts only.
Next decision for Dr Sun: wide camera on the existing 20°-down carrier (sim C7 first) versus re-mounting the head camera versus
dropping this model. Evidence: child task `research/head_camera_live_2026-09-11/`.

## Status update 2026-09-11 (round 5, fused virtual camera)

c7 (level virtual evaluation camera fused from the real head camera at +16.7 deg and the D435i at 20 deg down, 6 percent of the
image uncovered): 0/10 on the frozen castle episodes versus 2/10 for the ideal render at the same pose (c5) and 5/10 for the
ideal 15-deg-down camera (c6). The fused input is verified to reach the model and is used normally; episode 1 fails by one
deterministic System-2 route choice repeated in all five runs. c8 (1.3 percent uncovered) is running as round 5b.
Implication for the parent decision: fusion does not recover the downward-camera advantage; the 20-deg carrier with a wide camera
(or a new head bracket) remains the path that matches the authors' setup.
