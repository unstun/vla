# Source and dependency provenance

The algorithm source is the hash-verified `recovery_v174/src/pct_planner`
snapshot selected by the frozen v196 ARM64 Foxy runtime. All 116 original source
entries matched `recovery_v174/source_identity.json` before copying. The full
per-file record is retained in `verification/pct_parent_identity.json`.

The earlier imported lineage is recorded at
`references/upstream/2026-09-16_lite3_isaac_harness_backend/repository_manifest.yaml`:
PCT-SCAN-ROS2, https://github.com/yagami-light7/PCT-SCAN-ROS2,
commit `1cf45a1c12ca785ce533293302be09d51daf0ccb`. PCT originates from
https://github.com/byangw/PCT_planner with a ROS 2 port lineage through
https://github.com/2473o/PCT_planner/tree/feat/ros2pkg. The local v174 snapshot
includes subsequent recorded repairs; it is not claimed byte-identical to the
initial upstream commit.

PCT's existing package and NOTICE declare GPL-2.0-or-later; its original LICENSE
and NOTICE are retained here. The common smoothing subtree retains its Apache
license. The planner plugin now links native PCT and its package metadata lists
that component license alongside the existing Apache terrain code. New map
conversion and planner adapter code derive their semantics from the PCT wrapper.
No upstream licensing is flattened or replaced.

Algorithm files under `pct_planner/lib/src` are unchanged. Local PCT package
changes export headers/libraries for C++ consumers and install existing notices.
The Python bindings remain available for compatibility and regression reference;
the online planner plugin does not call or link a Python interpreter.

Build dependencies are the existing `vla-newton-foxy:v149` ARM64 image, GTSAM,
Eigen and the archived OSQP install at
`/task/recovery_v167/dependencies/osqp-install`. No new dependency was downloaded.
The original v174 build command is in `../v174/build_native.sh`.

The fixed Building map is the v135 coverage-constrained tomogram with SHA-256
`fe34d46edee9fde5efb0cfb6f2df265995a53ea93f0d1dc645012bc700018ee5`.
Binary bundles and large executable outputs remain regenerable in the temporary
build workspace; source, hashes, compact test results and map receipts stay here.
