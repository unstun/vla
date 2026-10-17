# scan_10: slow observed-motion confirmation correction

Status: **hash-gated Foxy build and installed tracker-core regression passed;
no ROS transport replay or Isaac pedestrian episode for scan_10 yet**.

The built `scan_09` tracker compares each shape candidate against its last
observed center to confirm movement at 0.08 m. At 10 Hz, a pedestrian moving
at 0.3 m/s shifts only 0.03 m between adjacent frames. The independently
recorded `2026-09-23_scan_reactive_stair/scan09_slow_motion_review.json`
(SHA-256 `7f5d4e7cc5da15b1827a430548728c8ac3761d3f46326418add2deac9c77208b`)
shows 11 frames, 0.3 m total observed displacement, and zero published tracks
from the built `scan_09` core
(SHA-256 `6e4bc9ad96e5a15827335dd983d9ce405a340ce8a2c2827d5c64a87244b4d42f`).

`scan_10` retains the first observed center of each cluster as a motion
confirmation anchor. Association and each published center still use the last
**observed** center. The anchor is evidence of displacement in current and
past observations; it is never extrapolated. The source label changes to
`sensor_lidar_moving_cluster_candidate_v2`. A bounded static jitter sequence
within 0.025 m of the first center remains unconfirmed. A confirmed cluster
lost from view still produces incomplete snapshots indefinitely until
reacquired. Shape and motion clustering remains a candidate, not validated
human recognition; a displaced box or localization drift could be mistaken
for a person.

`materialize_scan_10.py` verifies the complete successful `scan_09` Foxy
source manifest and candidate manifest, including all 82 source files, then
copies the source into `builds/scan_10/src/`. Only
`scan_reactive_tracker/scan_reactive_tracker/core.py` changes. The new core
SHA-256 is `2051acc08d22acc4ed681486412d7aa78817d68a917123cc58013490173ebc53`;
the materialized manifest SHA-256 is
`3bfd8c6c81281a75f05cc27f87d38746481d2fc2dd85a209587defe5ab673079`.
The accepted `scan_04`, built `scan_09`, frozen planner config, and existing
simulator runner were not edited.

Local commands, from repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/reactive_stair/test_moving_cluster_core.py -v
PYTHONDONTWRITEBYTECODE=1 python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/reactive_stair/test_materialize_scan_10.py -v
PYTHONDONTWRITEBYTECODE=1 python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/reactive_stair/test_tracker_lost_liveness.py -v
```

Outcomes: 7/7, 3/3, and 1/1 passed. The materializer test loads the built
`scan_09` core and the materialized `scan_10` core against the same slow
motion sequence: zero tracks versus confirmation at frame 3, then a stable
`cluster-1` ID and current stamp/position through frame 10. These are
pure-logic results, not a ROS safety-loop timing or Isaac integration claim.

The lead independently reviewed the diff and repeated the seven tracker and
three materializer tests. `builds/scan_10/build_result.json` records a successful
seven-package build in the pinned Foxy image with identical source hashes
before and after. `install_identity.json` covers 451 installed files; its
SHA-256 is `88c8a78dc3a4af11d08d4d893645037c4c7946a6348f47adc4a91d49ebb6e421`.
An additional CPU-only check imported the installed core inside that image
and confirmed `cluster-1` from frame 3 through 10, with current observed
positions and stamps. The exact command and raw result are in
`2026-09-23_scan_reactive_stair/scan10_slow_motion_foxy_review.json`.

Next gate: separately test ROS transport and the official-human sensor
episode. Simulator truth must remain outside tracker input. No pedestrian
trajectory prediction is present.
