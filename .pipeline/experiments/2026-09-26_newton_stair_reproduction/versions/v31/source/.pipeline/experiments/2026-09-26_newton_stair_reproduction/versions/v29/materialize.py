"""Preserve v28 and test the known-footprint waiver at the queried point, up to the LiDAR origin.

v28 tests the measured-trunk band |local z - 0.01| <= 0.06 at the centre of the
voxel that contains the query. Under the RL gait the walking body is about
4.7 cm lower than the stand, and the voxel-centre test then leaves the
never-observed cells beside the trunk blocked. The resulting emergency stop
and replan thrash are in audits/2026-09-28_v28_start_thrash/RESULT.md.

The same audit shows that the point test alone fails 4 of 6 saved walking
heights. The remaining blocks lie between the trunk band and the Mid-360 scan
origin, a slice the 15-degree nose-down sensor cannot observe near itself.
Dr Sun chose "Point + LiDAR column" on 2026-09-28.

v29 changes two expressions and nothing else:
1. scan_reactive_grid_methods.inc rotates the queried point, not its voxel
   centre, into the body frame. The now-unused centre lookup is removed.
2. knownNavigationFootprintInterior's vertical test becomes
   -0.05 <= z <= 0.10854. That is the trunk bottom up to the mid360_scan_frame
   origin in TORSO, from the pinned Isaac URDF.
Only never-observed, non-inflated cells inside the current two-circle footprint
with a pose fresher than 0.1 s are waived. Observed obstacles still block.
"""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
OLD = BASE / "runtime/scan60_constraint_guard_v28"
NEW = BASE / "runtime/scan61_sensor_column_v29"
GRID = "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc"
TRUNK = "src/plan_env/include/plan_env/known_lite3_trunk.h"
URDF = BASE / "inputs/sensor_rig/lite3_pro_sensor_rig_real_with_interface_isaac.urdf"
URDF_SHA256 = "803d552703bcc4f72ce15f38b95bc3f62e3e4ada0b42bf3ecf71b32b6590bb9d"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

GRID_BEFORE = """    Eigen::Vector3i id;
    posToIndex(point, id);
    Eigen::Vector3d cell_center;
    indexToPos(id, cell_center);
    const Eigen::Vector3d local = reactive_body_quaternion_.conjugate() *
                                 (cell_center - md_.sliding_map_frame_pos_);
"""
GRID_AFTER = """    Eigen::Vector3i id;
    posToIndex(point, id);
    // Test the queried point, not its voxel centre, so the waiver does not
    // depend on how the grid aligns with the body height.
    const Eigen::Vector3d local = reactive_body_quaternion_.conjugate() *
                                 (point - md_.sliding_map_frame_pos_);
"""
TRUNK_BEFORE = """// Unlike Nav2's unconditional footprint clearing, an observed obstacle wins.
inline bool knownNavigationFootprintInterior(double x, double y, double z,
    double now, double pose_stamp, double radius, double offset) {
  if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z) ||
      !std::isfinite(radius) || radius < 0.0 || !std::isfinite(offset) || offset < 0.0 ||
      pose_stamp <= 0.0 || !fresh(now, pose_stamp, 0.1)) return false;
  const double dx = std::min(std::abs(x - offset), std::abs(x + offset));
  return dx * dx + y * y <= radius * radius && std::abs(z - 0.01) <= 0.06;
}
"""
TRUNK_AFTER = """// Unlike Nav2's unconditional footprint clearing, an observed obstacle wins.
// Vertically it spans the trunk bottom (-0.05 m) up to the mid360_scan_frame
// origin (+0.10854 m in TORSO, pinned Isaac URDF 803d5527). The 15-degree
// nose-down Mid-360 cannot observe that slice beside and behind itself.
inline bool knownNavigationFootprintInterior(double x, double y, double z,
    double now, double pose_stamp, double radius, double offset) {
  if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z) ||
      !std::isfinite(radius) || radius < 0.0 || !std::isfinite(offset) || offset < 0.0 ||
      pose_stamp <= 0.0 || !fresh(now, pose_stamp, 0.1)) return false;
  const double dx = std::min(std::abs(x - offset), std::abs(x + offset));
  return dx * dx + y * y <= radius * radius && z >= -0.05 && z <= 0.10854;
}
"""

parent = json.loads((HERE.parent / "v28/manifest.json").read_text())
assert not NEW.exists() and not (HERE / "prepared.json").exists()
for name, digest in parent["source_files"].items():
    assert sha(ROOT / name) == digest, name
native = json.loads((OLD / "source_sha256.json").read_text())
for name, digest in native.items():
    assert sha(OLD / name) == digest, name
assert sha(URDF) == URDF_SHA256
blind_zone = json.loads((BASE / "audits/2026-09-28_v28_start_thrash/optimizer_trace/voxel_dump/blind_zone.json").read_text())
assert blind_zone["lidar_mount"]["urdf_sha256"] == URDF_SHA256
assert blind_zone["lidar_mount"]["origin_in_root_m"][2] == 0.10854 and blind_zone["lidar_mount"]["root_link"] == "TORSO"

shutil.copytree(OLD / "src", NEW / "src")
changes, preimages = [], {}
for relative, before_text, after_text in ((GRID, GRID_BEFORE, GRID_AFTER), (TRUNK, TRUNK_BEFORE, TRUNK_AFTER)):
    path = NEW / relative
    before = path.read_text()
    assert before.count(before_text) == 1, relative
    after = before.replace(before_text, after_text)
    path.write_text(after)
    preimages[relative] = before
    changes.append("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                fromfile="v28/" + relative, tofile="v29/" + relative)))
for relative, before in preimages.items():
    preimage = HERE / "parent_source" / relative
    preimage.parent.mkdir(parents=True, exist_ok=True)
    preimage.write_text(before)
(HERE / "changes.patch").write_text("".join(changes))

manifest = {str(p.relative_to(NEW)): sha(p) for p in sorted((NEW / "src").rglob("*")) if p.is_file()}
assert set(manifest) == set(native)
assert {name for name in manifest if manifest[name] != native[name]} == {GRID, TRUNK}
(NEW / "source_sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
identity = BASE / "repairs/2026-09-26_generic_occupancy/candidate61_sensor_column_v29_identity.json"
identity.write_text(json.dumps({
    "source_sha256": manifest, "integration_version": "v29",
    "parent": {"native_build": str(OLD.relative_to(ROOT)), "grid_sha256": native[GRID], "trunk_sha256": native[TRUNK]},
    "lidar_origin": {"urdf": str(URDF.relative_to(ROOT)), "urdf_sha256": URDF_SHA256,
                     "mid360_scan_frame_in_torso_m": blind_zone["lidar_mount"]["origin_in_root_m"]},
    "claim": "Unvalidated: known-footprint waiver tested at the queried point, vertical extent -0.05..+0.10854 m "
             "(trunk bottom to LiDAR origin); footprint circles, pose freshness, Unknown-only rule and all planner gates unchanged"},
    indent=2) + "\n")
for name in ("building_planner.yaml", "flat_planner.yaml"):
    shutil.copyfile(HERE.parent / "v28" / name, HERE / name)
(HERE / "prepared.json").write_text(json.dumps({
    "parent": "v28", "status": "unfrozen_candidate", "native_build": str(NEW.relative_to(ROOT)),
    "changed_files": [str((NEW / GRID).relative_to(ROOT)), str((NEW / TRUNK).relative_to(ROOT)),
                      str(identity.relative_to(ROOT))],
    "native_parent": str(OLD.relative_to(ROOT))}, indent=2) + "\n")
print(json.dumps({"v29": "native candidate prepared; acceptance pending", "changed": [GRID, TRUNK]}))
