bool GridMap::reactiveFootprintSupportQuery(const Eigen::Vector3d &body_reference,
    const reactive_stair::NonTerrainVoxel &obstacle, reactive_stair::Query &query) {
  if (!body_reference.allFinite()) return false;
  const auto &raw = reactive_ground_;
  const auto &scored = reactive_terrain_;
  if (raw.source_id != scored.source_id || raw.frame != scored.frame ||
      raw.resolution_m != scored.resolution_m || raw.origin_x_m != scored.origin_x_m ||
      raw.origin_y_m != scored.origin_y_m) return false;
  auto body_query = query;
  body_query.x_m = body_reference.x();
  body_query.y_m = body_reference.y();
  body_query.z_m = body_reference.z();
  body_query.in_map = isInMap(body_reference);
  // This copy checks terrain support only. The original measured obstacle
  // still controls the final footprint verdict at the original physical XYZ.
  auto support_only = obstacle;
  support_only.occupancy = reactive_stair::Occupancy::Free;
  if (reactive_decision_.decide(body_query, support_only) != reactive_stair::Verdict::Free)
    return false;
  const auto associated_height = [&](double x, double y, double target, double limit, double &height) {
    const double ix = std::floor((x - raw.origin_x_m) / raw.resolution_m);
    const double iy = std::floor((y - raw.origin_y_m) / raw.resolution_m);
    if (!std::isfinite(ix) || !std::isfinite(iy) ||
        ix < std::numeric_limits<int>::min() || ix > std::numeric_limits<int>::max() ||
        iy < std::numeric_limits<int>::min() || iy > std::numeric_limits<int>::max()) return false;
    const reactive_stair::Cell2 cell{static_cast<int>(ix), static_cast<int>(iy)};
    const auto original = raw.cells.find(cell), classified = scored.cells.find(cell);
    if (original == raw.cells.end() || classified == scored.cells.end() ||
        original->second.size() != classified->second.size()) return false;
    // Associate before considering scored status. Never skip an unknown or
    // unsupported nearest layer in favor of a farther supported floor.
    const int layer = reactive_stair::nearestSurface(original->second, target, limit);
    if (layer < 0) return false;
    const auto &surface = classified->second[layer];
    if (surface.elevation_m != original->second[layer].elevation_m ||
        !reactive_stair::selectedSurface(surface)) return false;
    height = surface.elevation_m;
    return true;
  };
  double body_ground, footprint_ground;
  const double step = reactive_stair::StepScoreParameters{}.critical_height_m;
  if (!associated_height(body_query.x_m, body_query.y_m,
          body_query.z_m - reactive_parameters_.body_clearance_m,
          reactive_parameters_.body_height_tolerance_m, body_ground) ||
      !associated_height(query.x_m, query.y_m, body_ground, step, footprint_ground) ||
      std::abs(footprint_ground - body_ground) >= step) return false;
  // Only the support-layer height changes; do not move the robot, spline,
  // obstacle query, map-boundary query or retained measured LiDAR evidence.
  query.z_m = footprint_ground + reactive_parameters_.body_clearance_m;
  return true;
}
