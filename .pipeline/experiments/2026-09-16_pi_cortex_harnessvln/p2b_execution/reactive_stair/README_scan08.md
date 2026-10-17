# scan_08: sensor LiDAR moving-cluster track candidate

Status: **hash-gated local source candidate, Foxy-built with a known PCT intake defect**. This adds a
separate Foxy `ament_python` package to the built `scan_07` source tree. It
does not edit SCAN's accepted source, frozen planner configuration, the Isaac
runner, or any previous build.

## Inputs and output

The bridge publishes `/quad_0/lidar_pose` as world-frame `nav_msgs/Odometry`
and `/quad_0/cloud` as sensor-frame little-endian XYZ `PointCloud2`. Both come
from one decoded sensor payload with the **same timestamp**. The candidate
requires exact stamp and frame pairing, a finite unit quaternion, a complete
nonempty LiDAR sweep, and a fresh clock. It transforms points to world with
the observed pose; no velocity estimate is used.

The candidate also requires the one-shot `/pct_tomogram` selected-ground
PointCloud2. It preserves its world frame and layered elevations, subtracts
the display z offset of 0.03 m, and records a SHA-256 of delivered bytes.
Nearby supported ground removes low stair/tread returns from cluster inputs.
Missing or stale PCT input makes every output snapshot incomplete. The
integrated P2B launcher still needs to start the standalone PCT publisher.

`moving_cluster_tracker` publishes `/tracked_person_snapshot` using the
existing typed `scan_planner_msgs/TrackedPersonSnapshot` message. The source
label is `sensor_lidar_moving_cluster_candidate_v1`. Every complete snapshot
has a world frame, timestamp, stable cluster IDs, current observed centers,
and conservative radii. There is **no predicted position**, velocity field,
or time-indexed occupancy. An invalid, unmatched, stale, or lost confirmed
cluster produces `complete=false`; scan_07 then blocks its shared collision
query. A fresh observation of a stopped confirmed cluster retains its ID.

## Detection claim boundary

The ROS-free core bins nonground points in XY, keeps clusters with a bounded
person-like extent, and confirms one as moving only after observed centroid
displacement between synchronized scans. Association compares detections to
the **last observed** centers only. A static box remains a static obstacle in
SCAN's LiDAR map and is not published as a moving track after three unchanged
observations. A moving box or a human-shaped artifact can be published as a
track; a stationary or occluded person may be missed by this heuristic.
Thus this is a moving-obstacle candidate, **not validated human recognition**
or evidence that the sensor has an exhaustive current-person set. The
`complete` flag describes the candidate's processed scan and unresolved-track
state; it must not be promoted to a semantic all-humans guarantee. SCAN still
keeps unclassified raw LiDAR returns occupied.

The existing scan_07 collision decision uses **XY-only** person footprints.
It discards `center.z`, so a cluster on another floor at the same XY blocks
the robot. That conservative behavior can prevent routing on multilevel
stairs. This candidate has no measured person vertical extent, and it does
not add a floor-aware overlap rule.

The bridge currently supplies no human class, instance segmentation, unique
object IDs, or labelled moving-person examples. A claim that this identifies
pedestrians needs recorded data with people, boxes, stair returns, occlusions,
and false-positive/false-negative measurements. A real robot or Isaac motion
episode is outside this slice.

## Local checks and next gate

`materialize_scan_08.py` verifies every file in the successfully Foxy-built
`scan_07` source manifest before adding the new package. Pure Python tests
exercise a moving cluster, stable ID, static box, stair returns, lost track,
stale/incomplete sweeps, exact clock/frame matching, sensor-to-world rotation,
multi-elevation ground, and malformed PointCloud2 payloads. These tests do
not import ROS or establish runtime tracking.

From `p2b_execution`:

```sh
python3 reactive_stair/test_moving_cluster_core.py -v
python3 reactive_stair/test_moving_cluster_io.py -v
python3 reactive_stair/test_materialize_scan_08.py -v
```

The Foxy `colcon build` and generated-message/tracker import passed. Review
then found that this candidate rejects the actual finite Humble PCT cloud
because `sensor_msgs_py.create_cloud` sets `is_dense=false`. The hash-gated
`scan_09` copy corrects that gate, and a bounded synthetic ROS transport probe
passed there. A person-labelled sensor replay and Isaac episode remain open.
The eventual node command, after sourcing the Foxy install, is:

```sh
ros2 run scan_reactive_tracker moving_cluster_tracker --ros-args -p use_sim_time:=true
```

This command is documented but has not been run here. The node requires the
PCT publisher and the bridge to be active in the same ROS domain and clock.
