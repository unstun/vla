"""Add observation-only bulk scopes/counters to a copy of the frozen native map."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
NATIVE = BASE / "runtime/scan82_optimizer_failure_v63"


def replace_once(text, old, new):
    assert text.count(old) == 1, old[:90]
    return text.replace(old, new)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = NATIVE / "src/plan_env/src/grid_map.cpp"
    expected = json.loads((NATIVE / "source_sha256.json").read_text())["src/plan_env/src/grid_map.cpp"]
    original = source.read_text()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == expected
    text = '#include "map_meter.h"\n' + original
    replacements = [
        ("  pcl::fromROSMsg(*img, latest_cloud);", "  { map_meter::Scope scope(map_meter::Decode); pcl::fromROSMsg(*img, latest_cloud); }\n  map_meter::meter.counts[map_meter::Points] += latest_cloud.points.size();"),
        ("  for (size_t i = 0; i < latest_cloud.points.size(); ++i)", "  map_meter::Scope projection_scope(map_meter::Projection);\n  for (size_t i = 0; i < latest_cloud.points.size(); ++i)"),
        ("    md_.proj_points_cnt++;\n    if (isInMap(pt_world))", "    md_.proj_points_cnt++;\n    ++map_meter::meter.counts[map_meter::KeptPoints];\n    if (isInMap(pt_world))"),
        ("      if (reactiveTerrainReturn(pt_world))", "      ++map_meter::meter.counts[map_meter::TerrainCalls];\n      if (reactiveTerrainReturn(pt_world))"),
        ("  if (md_.proj_points_cnt == 0)\n    return;\n\n  md_.use_cloud_update_ = true;", "  projection_scope.finish();\n  if (md_.proj_points_cnt == 0)\n    return;\n\n  md_.use_cloud_update_ = true;"),
        ("  for (int i = 0; i < md_.proj_points_cnt; ++i)", "  map_meter::Scope traversal_scope(map_meter::Traversal);\n  for (int i = 0; i < md_.proj_points_cnt; ++i)"),
        ("    pt_w = md_.proj_points_[i];", "    ++map_meter::meter.counts[map_meter::Rays];\n    pt_w = md_.proj_points_[i];"),
        ("    raycaster.setInput(pt_w / mp_.resolution_, md_.ray_pos_ / mp_.resolution_);", "    ++map_meter::meter.counts[map_meter::UniqueRays];\n    raycaster.setInput(pt_w / mp_.resolution_, md_.ray_pos_ / mp_.resolution_);"),
        ("    while (raycaster.step(ray_pt))\n    {", "    while (raycaster.step(ray_pt))\n    {\n      ++map_meter::meter.counts[map_meter::RaySteps];"),
        ("  min_x = min(min_x, md_.ray_pos_(0));", "  traversal_scope.finish();\n  min_x = min(min_x, md_.ray_pos_(0));"),
        ("  while (!md_.cache_voxel_.empty())\n  {", "  map_meter::Scope fusion_scope(map_meter::Fusion);\n  while (!md_.cache_voxel_.empty())\n  {\n    ++map_meter::meter.counts[map_meter::FusedVoxels];"),
        ("void GridMap::applyOccupancyUpdate(const Eigen::Vector3i& id, double new_log_odds)\n{", "void GridMap::applyOccupancyUpdate(const Eigen::Vector3i& id, double new_log_odds)\n{\n  ++map_meter::meter.counts[map_meter::OccupancyCalls];"),
        ("  if (was_occ != now_occ)\n    updateInflation(id, now_occ ? 1 : -1);", "  if (was_occ != now_occ) {\n    ++map_meter::meter.counts[map_meter::OccupancyTransitions];\n    updateInflation(id, now_occ ? 1 : -1);\n  }"),
        ("  for (const auto& offset : offsets)\n  {", "  ++map_meter::meter.counts[map_meter::InflationCalls];\n  map_meter::meter.counts[map_meter::InflationOffsetVisits] += offsets.size();\n  for (const auto& offset : offsets)\n  {"),
        ("void GridMap::updateSlidingMap(const Eigen::Vector3d& center)\n{", "void GridMap::updateSlidingMap(const Eigen::Vector3d& center)\n{\n  map_meter::Scope slide_scope(map_meter::Slide);\n  ++map_meter::meter.counts[map_meter::SlideCalls];"),
        ("  if ((shift_num.cwiseAbs().array() >= mp_.map_voxel_num_.array()).any())", "  ++map_meter::meter.counts[map_meter::RealSlides];\n  if ((shift_num.cwiseAbs().array() >= mp_.map_voxel_num_.array()).any())"),
        ("  const int buffer_size = mp_.map_voxel_num_(0) * mp_.map_voxel_num_(1) * mp_.map_voxel_num_(2);", "  map_meter::Scope mask_scope(map_meter::SlideMask);\n  const int buffer_size = mp_.map_voxel_num_(0) * mp_.map_voxel_num_(1) * mp_.map_voxel_num_(2);"),
        ("  for (int addr : clear_addrs)\n    resetCellByAddressForSliding(addr, clear_mask);", "  mask_scope.finish();\n  map_meter::meter.counts[map_meter::ClearedVoxels] += clear_addrs.size();\n  map_meter::Scope reset_scope(map_meter::SlideReset);\n  for (int addr : clear_addrs) {\n    if (md_.occupancy_buffer_[addr] > mp_.min_occupancy_log_) ++map_meter::meter.counts[map_meter::ClearedOccupied];\n    resetCellByAddressForSliding(addr, clear_mask);\n  }"),
        ("  mp_.map_origin_idx_ = new_origin_idx;\n  updateMapBoundaryFromIndex();\n  boundIndex", "  reset_scope.finish();\n  mp_.map_origin_idx_ = new_origin_idx;\n  updateMapBoundaryFromIndex();\n  boundIndex"),
    ]
    for old, new in replacements:
        text = replace_once(text, old, new)
    recovered = text.removeprefix('#include "map_meter.h"\n')
    for old, new in reversed(replacements):
        recovered = replace_once(recovered, new, old)
    assert recovered == original, "Removing only observation code must recover exact parent"
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "instrumented_grid_map.cpp").write_text(text)
    (args.output / "instrumentation.patch").write_text("".join(difflib.unified_diff(
        original.splitlines(True), text.splitlines(True), fromfile="frozen_v63/grid_map.cpp", tofile="v78/instrumented_grid_map.cpp")))
    readers = (NATIVE / "src/geometry_probe/src/measured_cloud_probe.cpp").read_text()
    readers = readers[readers.index("sensor_msgs::msg::PointCloud2 read_cloud"):readers.index("int main(")]
    (args.output / "recorded_readers.h").write_text(readers)
    print(json.dumps({"original_sha256": expected, "instrumented_sha256": hashlib.sha256(text.encode()).hexdigest(), "replacements": len(replacements), "observation_removal_recovers_original": True}))


if __name__ == "__main__":
    main()
