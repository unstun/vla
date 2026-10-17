# PCT simulation-clock terrain sidecar and scan_09 density correction

Status: **local tests and bounded CPU-only ROS transport passed**. No Isaac
simulator episode or robot actuation was performed.

## Why a separate publisher is needed

The actual P2B planner uses `baseline_config/planner.yaml` with
`use_sim_time: true`. The bridge stamps `/quad_0/cloud` and `/clock` in
simulation time. The standalone `pct_planner.planner_node` publishes
`/pct_tomogram` once in its constructor, before spinning; it can publish
wall time or simulation stamp zero. A future or zero PCT stamp makes scan_07
and scan_08 fail closed. A prior topic echo did not establish an empirical
stamp from the standalone node.

`pct_sim_clock_publisher.py` is an isolated sidecar. It loads only the pinned
Building tomogram (SHA-256
`ab5499ff100fe233f6cfabb59ce7592290cddd042c92ead5e37e9e2b593d24da`),
creates a reliable transient-local `/pct_tomogram` publisher, and spins while
listening to `/clock`. It publishes after **two progressing positive** clock
callbacks and stamps the cloud with the second clock message. Zero clock,
unchanged clock, and the first positive sample never publish. A clock reset
rearms the gate and replaces the latched cloud only after two new progressing
positive samples. The sidecar publishes no action or robot command.

The selected cells reproduce pinned
`pct_runtime/python/pct_planner/planner_node.py` SHA-256
`8392343358f37e636f415e1dd8dd238b8dbb55b8bbb0386f7f2decb51642576b`:
86,775 float32 `x/y/z/intensity` records, including the +0.03 m display z
offset and layered-cell deduplication. Tests execute the pinned publisher
method with ROS transport stubs and compare every output float32 value in
both `identity` and `sim_to_pct_180deg` modes. Payload SHA-256 is
`71550de5fde87043da3da73de00a8e1c1437c751bc939b87a718059d54949577`
for identity and
`086443241a8b5cb628285c060624a896ee2ba87b7f2710ddd0a16a9667c94ef5`
for the 180-degree mode.

The pinned Humble `sensor_msgs_py.point_cloud2.create_cloud` sets
`is_dense=false` even for these finite points. scan_08 rejects that metadata
before checking records. The **new** hash-gated `scan_09` copy changes only
its PCT callback to accept the flag while retaining world-frame, float32
field, and finite-value validation. A regression executes the original and
patched callback methods: finite `is_dense=false` points pass only in
scan_09; NaN values and wrong frames remain blocked. scan_08 is unchanged.

## Commands and boundaries

Local, ROS-free checks from `p2b_execution`:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 reactive_stair/test_pct_sim_clock_core.py -v
PYTHONDONTWRITEBYTECODE=1 python3 reactive_stair/test_pct_sim_clock_sidecar.py -v
PYTHONDONTWRITEBYTECODE=1 python3 reactive_stair/test_pct_sim_clock_shutdown.py -v
PYTHONDONTWRITEBYTECODE=1 python3 reactive_stair/test_materialize_scan_09.py -v
PYTHONDONTWRITEBYTECODE=1 python3 reactive_stair/test_tracker_lost_liveness.py -v
```

The sidecar needs the PCT Humble environment, the map mounted at
`/inputs/new_building.pickle`, the same ROS domain as SCAN, and an active
bridge `/clock`. The command shape is:

```sh
python3 pct_sim_clock_publisher.py --ros-args \
  -p map_path:=/inputs/new_building.pickle \
  -p coord_mode:=identity \
  -p use_sim_time:=true
```

The correct coordinate mode must be checked against the route transform
before an episode. The sidecar has no clock publisher and cannot create
simulation time by itself. It must be the sole `/pct_tomogram` publisher in
the ROS domain; running it beside the standalone PCT node could mix clock
domains on one topic. A Foxy build of scan_09, topic-level stamp check, and
synchronized synthetic track transport check passed. Their exact commands,
source hashes, and logs are recorded in
`.pipeline/experiments/2026-09-23_scan_reactive_stair/`. The integrated P2B
launcher has not been wired or run with these inputs.

On executor shutdown, the sidecar destroys its node and calls
`rclpy.shutdown()` only while its context remains active. A ROS-free
regression covers external shutdown, normal spin return, and Ctrl-C. A second
bounded pinned-Humble transport probe exited without the earlier duplicate
shutdown traceback.

The moving-cluster tracker has a separate **liveness limit**: after a
confirmed cluster disappears, every subsequent otherwise valid sweep remains
`complete=false`. It can recover only if the cluster is observed again within
0.5 s and 0.65 m of its **last observed** center. After that association gap,
the current core has no automatic recovery, even if a similar cluster later
appears. It never silently clears unseen occupancy. This can stop planning
indefinitely after an occlusion; no evidence-based clearing or human
recognition is implemented.
