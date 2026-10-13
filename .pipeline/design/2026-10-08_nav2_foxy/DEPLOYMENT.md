# Foxy source export and receive-only handover

The local VLA repository is authoritative. Target Ubuntu 20.04, ROS 2 Foxy,
Python 3.8 and ARM64. Jetson access is pending; the existing JetPack, sensor
drivers and locomotion process have not been inspected. No hardware commands
or live goals are authorized by this handover.

## Export and provenance

From the VLA repository, choose a **new** destination outside the repository:

```bash
python3 .pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v99/assemble_workspace.py /path/to/new/nav2_source
```

The exporter verifies frozen parents, composes source overrides and includes
PCT, patched ControllerServer, SCAN, all local plugins, OSQP/QDLDL and licenses.
`source_identity.json` binds all exported bytes to v99. The 292 package source
files were compared against the actual tested native/PCT/bridge workspaces.
Copy source, not the Mac container's binaries, to the target. After transfer,
recheck every listed hash before building or launching.

Upstream identities:

- Nav2 Foxy 0.4.7: `a947ab5656e46ae3aa1afdf95e1706a16e478974`.
- PCT-SCAN-ROS2: `1cf45a1c12ca785ce533293302be09d51daf0ccb`, with recorded
  PCT lineage `ae9a0406e138f3b609ee1b9a2dd4208ab73a0d15`.
- OSQP 1.0.0 and QDLDL 0.1.8: source/license/commit/file hashes in the export's
  `third_party/*provenance.json`. No build-time replacement download is needed.

## Build prerequisites

Use the existing Foxy installation and inspect installed versions before any
target changes. The tested container uses the official Foxy navigation2,
nav2-bringup, PCL ROS/conversions, cv_bridge, image_transport, Eigen, OMPL,
nlohmann-json3, GTSAM 4.2, pybind11_vendor, ament_cmake_gtest and colcon packages.
Exact Debian versions are retained in `versions/v98/packages.tsv`.

OSQP needs CMake >= 3.18; the tested tool is 3.27.9. Build into this export only:

```bash
cd /path/to/new/nav2_source
LITE3_NAV_CMAKE=/path/to/cmake-3.27.9/bin/cmake bash build_export.sh
```

The script verifies source bytes, builds pinned OSQP/QDLDL and the ROS workspace,
then runs controller/tracking/map-layer tests. It neither installs apt packages
nor starts a robot process. The original Newton Python terrain helpers separately
use isolated NumPy 1.24.4 and system ARM64 ZeroMQ; those simulator compatibility
files are not a reason to replace Jetson's existing Python environment globally.

## Launch contract

After build, the packaged entry is:

```bash
source install/setup.bash
ros2 launch lite3_nav2_bridge navigation.launch.py \
  native_planner_config:=/absolute/native_planner.yaml \
  backend_config:=/absolute/receive_only_backend.json \
  pct_map:=/absolute/pinned_map.pickle \
  generated_params:=/absolute/new_run/nav2.yaml \
  use_sim_time:=false base_frame:=base_link odom_topic:=/odom
```

These frame/topic examples are placeholders until target inventory; do not assume
the physical robot matches the Newton `world`, `base`, `/quad_0/body_pose` graph.
The generated parameter file must be new. Native planner parameters define the
actual point-cloud/body input topics. SCAN still receives its native 3D sensor
inputs; the custom Nav2 layer consumes SCAN's completed map projection.

The backend JSON must set a unique run ID/positive epoch, map identity, actual
body topic and a **diagnostic-only** `topics.gated_cmd_topic` such as
`/nav2_validation/cmd_vel`. Keep it disconnected from locomotion for receive-only
validation. `legacy_http` is false by default. Do not send a goal during that
check. Missing applied evidence must keep mission admission closed; do not
fabricate an applied-state file to make readiness green.

## Next target-side checks

1. Read OS/JetPack/architecture/Foxy and installed package inventory.
2. Observe cloud/odometry/TF frames, QoS, source stamps and rates. Resolve topic
   adapters without starting another owner of an existing TF.
3. Build verified source, launch into diagnostic output only, inspect lifecycle
   and completed-map source age. No goal and no locomotion subscriber.
4. Design and verify actual applied-command/state evidence using the existing
   locomotion interface. Simulator truth is not physical stop evidence.
5. Only after receive-only review and explicit motion authorization, validate
   physical goal/cancel/stop. Keep the original freshness and stop thresholds.

Success on a Mac ARM64 Foxy container is a compatibility result. It is not a
Jetson runtime, full stair-navigation, or real-robot acceptance result.
