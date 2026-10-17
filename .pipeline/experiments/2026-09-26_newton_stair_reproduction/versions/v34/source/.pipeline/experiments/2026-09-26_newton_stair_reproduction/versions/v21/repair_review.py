"""Apply the pre-freeze review corrections, without changing terrain policy."""
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parents[1]
def apply():
 p=B/'runtime/scan55_surface_ground_v21/src/plan_env/include/plan_env/scan_reactive_grid_methods.inc';s=p.read_text()
 old='  for (const char *field_name : {"x", "y", "z", "intensity"}) {'
 new='''  // Exact existing publisher layout; reject malformed metadata before PCL.
  if (msg->height != 1 || msg->width == 0 || msg->is_bigendian ||
      msg->point_step != 16 || msg->fields.size() != 4 ||
      uint64_t(msg->width) * 16 != msg->row_step ||
      uint64_t(msg->row_step) != msg->data.size()) return {};
  uint32_t expected_offset = 0;
  for (const char *field_name : {"x", "y", "z", "intensity"}) {'''
 assert s.count(old)==1;s=s.replace(old,new)
 old='          field.count == 1) found = true;';new='          field.count == 1 && field.offset == expected_offset) found = true;';assert s.count(old)==1;s=s.replace(old,new)
 old='''    if (!found) {
      return {};
    }
  }
  pcl::PointCloud''';new='''    if (!found) {
      return {};
    }
    expected_offset += 4;
  }
  pcl::PointCloud''';assert s.count(old)==1;s=s.replace(old,new)
 old='''  reactive_surface_ground_ = decodeReactiveGround(msg);
  reactive_cloud_ready_ = false;''';new='''  reactive_surface_ground_ = decodeReactiveGround(msg);
  // A changed source must not retain positive labels from an older source.
  // Historical nonterrain evidence remains conservative and is not cleared.
  reactive_terrain_hits_.clear();
  reactive_cloud_ready_ = false;''';assert s.count(old)==1;s=s.replace(old,new)
 old='''  const auto &surface = reactive_surface_ground_;
  const double now = node_->now().seconds();
  return !reactive_ground_.cells.empty() && !surface.cells.empty() && surface.frame == mp_.frame_id_ &&
      std::isfinite(surface.stamp_s) && surface.stamp_s > 0.0 &&
      surface.stamp_s <= now && now - surface.stamp_s <= reactive_parameters_.terrain_max_age_s;'''
 new='''  const double now = node_->now().seconds();
  const auto fresh = [&](const reactive_stair::TerrainSnapshot &surface) {
    return !surface.cells.empty() && surface.frame == mp_.frame_id_ &&
        std::isfinite(surface.stamp_s) && surface.stamp_s > 0.0 &&
        surface.stamp_s <= now && now - surface.stamp_s <= reactive_parameters_.terrain_max_age_s;
  };
  return fresh(reactive_ground_) && fresh(reactive_surface_ground_);''';assert s.count(old)==1;s=s.replace(old,new);p.write_text(s)
if __name__=='__main__':apply()
