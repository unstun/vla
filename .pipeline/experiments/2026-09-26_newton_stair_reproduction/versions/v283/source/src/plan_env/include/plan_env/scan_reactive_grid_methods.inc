// Included only by scan_06 grid_map.cpp after GridMap is defined.
// PCT selected ground cells are a static support map, not live obstacle truth.
// The LiDAR raycasting path remains unchanged; only the common collision query
// uses positively classified measured LiDAR endpoints to waive terrain hits.
#include <cstdint>
#include <limits>
#include <pcl/point_types.h>
#include <plan_env/raw_return_classification.h>
#include <plan_env/known_lite3_trunk.h>
#include <plan_env/motion_heading.h>
#include <plan_env/static_support.h>

reactive_stair::TerrainSnapshot GridMap::decodeReactiveGround(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) const {
  reactive_stair::TerrainSnapshot terrain;
  terrain.frame = msg->header.frame_id;
  terrain.stamp_s = rclcpp::Time(msg->header.stamp).seconds();
  terrain.resolution_m = mapState().reactive_tomogram_resolution_m_;
  if (terrain.frame != mapState().mp_.frame_id_ || !std::isfinite(terrain.stamp_s) ||
      terrain.stamp_s <= 0.0 || !std::isfinite(terrain.resolution_m) ||
      terrain.resolution_m <= 0.0 || !std::isfinite(mapState().reactive_tomogram_z_offset_m_) ||
      !std::isfinite(mapState().reactive_cost_limit_) || mapState().reactive_cost_limit_ < 0.0 ||
      !std::isfinite(mapState().reactive_terrain_band_m_) || mapState().reactive_terrain_band_m_ < 0.0) {
    return {};
  }
  // Exact existing publisher layout; reject malformed metadata before PCL.
  if (msg->height != 1 || msg->width == 0 || msg->is_bigendian ||
      msg->point_step != 16 || msg->fields.size() != 4 ||
      uint64_t(msg->width) * 16 != msg->row_step ||
      uint64_t(msg->row_step) != msg->data.size()) return {};
  uint32_t expected_offset = 0;
  for (const char *field_name : {"x", "y", "z", "intensity"}) {
    bool found = false;
    for (const auto &field : msg->fields)
      if (field.name == field_name && field.datatype == sensor_msgs::msg::PointField::FLOAT32 &&
          field.count == 1 && field.offset == expected_offset) found = true;
    if (!found) {
      return {};
    }
    expected_offset += 4;
  }
  pcl::PointCloud<pcl::PointXYZI> points;
  pcl::fromROSMsg(*msg, points);
  double min_x = std::numeric_limits<double>::infinity();
  double min_y = std::numeric_limits<double>::infinity();
  for (const auto &point : points.points) {
    if (!std::isfinite(point.x) || !std::isfinite(point.y) || !std::isfinite(point.z) ||
        !std::isfinite(point.intensity) || point.intensity > mapState().reactive_cost_limit_) continue;
    min_x = std::min(min_x, static_cast<double>(point.x));
    min_y = std::min(min_y, static_cast<double>(point.y));
  }
  if (!std::isfinite(min_x) || !std::isfinite(min_y)) {
    return {};
  }
  terrain.origin_x_m = min_x - terrain.resolution_m / 2.0;
  terrain.origin_y_m = min_y - terrain.resolution_m / 2.0;
  // A lightweight content identity ties this static version to the exact
  // delivered bytes. It is not a cryptographic source-file provenance hash.
  uint64_t fingerprint = UINT64_C(14695981039346656037);
  for (uint8_t value : msg->data) {
    fingerprint ^= value;
    fingerprint *= UINT64_C(1099511628211);
  }
  terrain.source_id = "pct_tomogram/fnv64/" + std::to_string(fingerprint);
  for (const auto &point : points.points) {
    if (!std::isfinite(point.x) || !std::isfinite(point.y) || !std::isfinite(point.z) ||
        !std::isfinite(point.intensity) || point.intensity > mapState().reactive_cost_limit_) continue;
    const double ix = std::floor((point.x - terrain.origin_x_m) / terrain.resolution_m);
    const double iy = std::floor((point.y - terrain.origin_y_m) / terrain.resolution_m);
    if (ix < std::numeric_limits<int>::min() || ix > std::numeric_limits<int>::max() ||
        iy < std::numeric_limits<int>::min() || iy > std::numeric_limits<int>::max()) continue;
    // "Stair" here means a selected supported PCT cell; the topic carries no
    // flat-vs-stair semantic label. Multiple heights at one XY are retained.
    terrain.cells[{static_cast<int>(ix), static_cast<int>(iy)}].push_back(
        {reactive_stair::Support::Stair, point.z - mapState().reactive_tomogram_z_offset_m_});
  }
  return terrain;
}

reactive_stair::PhysicalFloorSnapshot GridMap::decodePhysicalFloor(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) const {
  if (!msg || msg->header.frame_id!=mapState().mp_.frame_id_ || msg->height!=1 || msg->width==0 || msg->is_bigendian ||
      msg->point_step!=16 || msg->fields.size()!=4 || uint64_t(msg->width)*16!=msg->row_step || uint64_t(msg->row_step)!=msg->data.size()) return {};
  uint32_t offset=0;
  for(const char *name:{"x","y","z","intensity"}) {
    bool found=false;for(const auto &field:msg->fields)
      if(field.name==name && field.datatype==sensor_msgs::msg::PointField::FLOAT32 && field.count==1 && field.offset==offset)found=true;
    if(!found) return {};
    offset+=4;
  }
  uint64_t fingerprint=UINT64_C(14695981039346656037);
  for(uint8_t value:msg->data){fingerprint^=value;fingerprint*=UINT64_C(1099511628211);}
  reactive_stair::PhysicalFloorSnapshot physical;
  physical.source_id="pct_physical_floor/fnv64/"+std::to_string(fingerprint);
  physical.frame=msg->header.frame_id;physical.stamp_s=rclcpp::Time(msg->header.stamp).seconds();
  physical.resolution_m=mapState().reactive_tomogram_resolution_m_;
  if(physical.source_id!=mapState().physical_floor_source_id_ || !std::isfinite(physical.stamp_s) || physical.stamp_s<=0.0 ||
     !std::isfinite(physical.resolution_m) || physical.resolution_m<=0.0 || !std::isfinite(mapState().reactive_tomogram_z_offset_m_))return {};
  pcl::PointCloud<pcl::PointXYZI> points;pcl::fromROSMsg(*msg,points);
  double minimum_x=std::numeric_limits<double>::infinity(), minimum_y=minimum_x;
  for(const auto &point:points.points) {
    if(!std::isfinite(point.x)||!std::isfinite(point.y)||!std::isfinite(point.z)||!std::isfinite(point.intensity)||point.intensity<0.0)return {};
    minimum_x=std::min(minimum_x,double(point.x));minimum_y=std::min(minimum_y,double(point.y));
  }
  physical.origin_x_m=minimum_x-physical.resolution_m/2.0;physical.origin_y_m=minimum_y-physical.resolution_m/2.0;
  if(physical.origin_x_m!=mapState().physical_floor_origin_x_m_ || physical.origin_y_m!=mapState().physical_floor_origin_y_m_ || physical.resolution_m!=mapState().physical_floor_resolution_m_)return {};
  // Metadata is available now; do not rescan all cells inside per-cell lookup helpers.
  for(const auto &point:points.points) {
    const double ix=std::floor((double(point.x)-physical.origin_x_m)/physical.resolution_m);
    const double iy=std::floor((double(point.y)-physical.origin_y_m)/physical.resolution_m);
    if(!std::isfinite(ix)||!std::isfinite(iy)||ix<std::numeric_limits<int>::min()||ix>std::numeric_limits<int>::max()||
       iy<std::numeric_limits<int>::min()||iy>std::numeric_limits<int>::max())return {};
    physical.cells[{int(ix),int(iy)}].push_back({double(point.z)-mapState().reactive_tomogram_z_offset_m_,double(point.intensity)});
  }
  return reactive_stair::validPhysicalFloor(physical) ? physical : reactive_stair::PhysicalFloorSnapshot{};
}

const reactive_stair::PhysicalFloorSnapshot *GridMap::qualifiedPhysicalFloor() const {
  const double now=queryNow().seconds();
  if(mapState().reactive_physical_floor_topic_.empty() || !supportState().physical_floor_decoded_valid_ ||
     supportState().reactive_physical_floor_.source_id!=mapState().physical_floor_source_id_ ||
     supportState().reactive_navigation_ground_.source_id!=mapState().physical_floor_navigation_source_id_ ||
     supportState().reactive_surface_ground_.source_id!=mapState().physical_floor_surface_source_id_ ||
     supportState().reactive_navigation_ground_.frame!=mapState().mp_.frame_id_ || supportState().reactive_surface_ground_.frame!=mapState().mp_.frame_id_ ||
     !reactive_stair::fresh(now,supportState().reactive_physical_floor_.stamp_s,supportState().reactive_parameters_.terrain_max_age_s) ||
     !reactive_stair::fresh(now,supportState().reactive_navigation_ground_.stamp_s,supportState().reactive_parameters_.terrain_max_age_s) ||
     !reactive_stair::fresh(now,supportState().reactive_surface_ground_.stamp_s,supportState().reactive_parameters_.terrain_max_age_s))return nullptr;
  return &supportState().reactive_physical_floor_;
}

bool GridMap::physicalFloorReady() const {
  return mapState().reactive_physical_floor_topic_.empty() || qualifiedPhysicalFloor()!=nullptr;
}

void GridMap::rescorePhysicalFloorChange() {
  mutableSupportState().reactive_ground_=supportGround(mutableSupportState().reactive_navigation_ground_);
  auto scored=reactive_stair::precomputeEthStyleStepScores(mutableSupportState().reactive_ground_, {}, &mutableSupportState().reactive_surface_ground_, qualifiedPhysicalFloor());
  if(mutableSupportState().reactive_decision_.acceptTerrain(scored.support)) {
    mutableSupportState().reactive_terrain_=scored.support;mutableSupportState().reactive_step_result_=std::move(scored);
  }
}

void GridMap::reactivePhysicalFloorCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) {
  if (async_mapping_) { enqueueMapping({5, rclcpp::Time(msg->header.stamp).nanoseconds(), nullptr, msg}); return; }

  invalidateRawContributorCache(); // Borrowed terrain pointers must not survive rescoring.
  mutableSupportState().reactive_physical_floor_=decodePhysicalFloor(msg);
  mutableSupportState().physical_floor_decoded_valid_=reactive_stair::validPhysicalFloor(mutableSupportState().reactive_physical_floor_);
  // Selected-terrain labels, sensor stamps/readiness and all nonterrain history
  // stay unchanged: physical presence has no LiDAR classification authority.
  rescorePhysicalFloorChange();
}

reactive_stair::TerrainSnapshot GridMap::supportGround(const reactive_stair::TerrainSnapshot &navigation) {
  // v34: PCT's navigation ground is inflated; the surface evidence is its
  // uninflated selection. Add the evidence floor that the navigation ground lacks,
  // except beside drops (audits/2026-09-29_corridor_entry, versions/v34/PLAN.md).
  reactive_stair::EvidenceFloorFill fill;
  auto ground = reactive_stair::addGuardedEvidenceFloor(navigation, &mutableSupportState().reactive_surface_ground_,
      mutableSupportState().reactive_parameters_.body_height_tolerance_m, reactive_stair::StepScoreParameters{}.critical_height_m,
      mutableMapState().mp_.double_cylinder_radius_, &fill, qualifiedPhysicalFloor());
  size_t layers = 0;
  for (const auto &entry : navigation.cells) layers += entry.second.size();
  RCLCPP_INFO(node_->get_logger(),
      "evidence_floor_fill evidence_used=%d navigation_layers=%zu added=%zu drop_rejected=%zu",
      fill.evidence_used ? 1 : 0, layers, fill.added, fill.drop_rejected);
  return ground;
}

void GridMap::reactiveTomogramCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) {
  if (async_mapping_) { enqueueMapping({3, rclcpp::Time(msg->header.stamp).nanoseconds(), nullptr, msg}); return; }

  invalidateRawContributorCache();
  mutableSupportState().reactive_ground_ = reactive_stair::TerrainSnapshot{};
  mutableMapState().reactive_cloud_ready_ = false;
  mutableMapState().reactive_pending_cloud_ = false;
  mutableMapState().reactive_terrain_hits_.clear();
  auto terrain = decodeReactiveGround(msg);
  // v34: keep the navigation ground as decoded, and give SCAN's copy the guarded
  // evidence floor. An invalid ground passes unchanged.
  mutableSupportState().reactive_navigation_ground_ = terrain;
  terrain = supportGround(terrain);
  if (terrain.cells.empty()) {
    mutableSupportState().reactive_decision_.acceptTerrain(terrain);
    return;
  }
  // The surface evidence decides whether a neighbour without this level is a drop.
  reactive_stair::StepScoreResult scored =
      reactive_stair::precomputeEthStyleStepScores(terrain, {}, &mutableSupportState().reactive_surface_ground_, qualifiedPhysicalFloor());
  if (mutableSupportState().reactive_decision_.acceptTerrain(scored.support)) {
    mutableSupportState().reactive_ground_ = terrain; // Preserve source elevations independently of step scores.
    mutableSupportState().reactive_terrain_ = scored.support;
    mutableSupportState().reactive_step_result_ = std::move(scored);
  }
}

void GridMap::reactiveSurfaceGroundCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) {
  if (async_mapping_) { enqueueMapping({4, rclcpp::Time(msg->header.stamp).nanoseconds(), nullptr, msg}); return; }

  invalidateRawContributorCache();
  mutableSupportState().reactive_surface_ground_ = decodeReactiveGround(msg);
  // A changed source must not retain positive labels from an older source.
  // Historical nonterrain evidence remains conservative and is not cleared.
  mutableMapState().reactive_terrain_hits_.clear();
  mutableMapState().reactive_cloud_ready_ = false;
  mutableMapState().reactive_pending_cloud_ = false;
  // The step score consults this evidence, so rescore the accepted navigation
  // ground. Unusable evidence scores exactly as without evidence.
  // v34: re-augment the navigation ground as decoded with this evidence, so the
  // result does not depend on which message arrived first.
  if (!mutableSupportState().reactive_ground_.cells.empty()) mutableSupportState().reactive_ground_ = supportGround(mutableSupportState().reactive_navigation_ground_);
  if (!mutableSupportState().reactive_ground_.cells.empty()) {
    reactive_stair::StepScoreResult scored = reactive_stair::precomputeEthStyleStepScores(
        mutableSupportState().reactive_ground_, {}, &mutableSupportState().reactive_surface_ground_, qualifiedPhysicalFloor());
    if (mutableSupportState().reactive_decision_.acceptTerrain(scored.support)) {
      mutableSupportState().reactive_terrain_ = scored.support;
      mutableSupportState().reactive_step_result_ = std::move(scored);
    }
  }
}

bool GridMap::reactiveSurfaceGroundReady() const {
  if (!physicalFloorReady()) return false;
  if (mapState().reactive_surface_ground_topic_.empty()) return true;
  const double now = queryNow().seconds();
  const auto fresh = [&](const reactive_stair::TerrainSnapshot &surface) {
    return !surface.cells.empty() && surface.frame == mapState().mp_.frame_id_ &&
        std::isfinite(surface.stamp_s) && surface.stamp_s > 0.0 &&
        surface.stamp_s <= now && now - surface.stamp_s <= supportState().reactive_parameters_.terrain_max_age_s;
  };
  return fresh(supportState().reactive_ground_) && fresh(supportState().reactive_surface_ground_);
}

bool GridMap::planningInputsReady() const {
  return mapperHealthy() && reactiveSurfaceGroundReady() && mapState().reactive_cloud_ready_ &&
      observationStamp()>0.0 && reactive_stair::fresh(queryNow().seconds(),observationStamp(),
          supportState().reactive_parameters_.obstacle_max_age_s);
}

bool GridMap::reactiveTerrainReturn(const Eigen::Vector3d &point) const {
  if (!reactiveSurfaceGroundReady()) return false;
  // A configured source replaces the classification evidence, not navigation support.
  const auto &evidence = mapState().reactive_surface_ground_topic_.empty()
      ? supportState().reactive_ground_ : supportState().reactive_surface_ground_;
  return reactive_stair::selectedGroundReturn(evidence,
      point.x(), point.y(), point.z(), mapState().reactive_terrain_band_m_);
}

bool GridMap::supportQueryCell(double x, double y, reactive_stair::Cell2 &cell) const {
  const auto &s=supportState();const auto &raw=s.reactive_ground_;
  if (!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(raw.resolution_m)||raw.resolution_m<=0.) return false;
  const auto same=[](const reactive_stair::TerrainSnapshot &a,const reactive_stair::TerrainSnapshot &b) {
    return a.source_id==b.source_id && a.frame==b.frame && a.resolution_m==b.resolution_m &&
        a.origin_x_m==b.origin_x_m && a.origin_y_m==b.origin_y_m;
  };
  const auto *physical=qualifiedPhysicalFloor();
  if (mapState().support_lattice_enabled_ && physical && same(raw,s.reactive_navigation_ground_) && same(raw,s.reactive_terrain_) &&
      std::abs(raw.resolution_m-physical->resolution_m)<=1e-9) {
    const double ox=mapState().support_lattice_origin_x_m_,oy=mapState().support_lattice_origin_y_m_;
    const auto aligned=[&](double origin,double nominal) {
      const double shift=std::round((origin-nominal)/raw.resolution_m);
      return std::abs(origin-nominal-shift*raw.resolution_m)<=raw.resolution_m*1e-5;
    };
    if (aligned(raw.origin_x_m,ox)&&aligned(raw.origin_y_m,oy)&&
        aligned(physical->origin_x_m,ox)&&aligned(physical->origin_y_m,oy)) {
      return reactive_stair::staticSupportCell(x,y,raw,true,ox,oy,cell);
    }
  }
  return reactive_stair::staticSupportCell(x,y,raw,false,0.,0.,cell);
}

GridMap::TerrainCellLayers GridMap::terrainCellLayers(const reactive_stair::Cell2 &cell) {
  // Unsigned packing preserves every signed int32 XY pair, including negatives.
  const std::uint64_t key = (static_cast<std::uint64_t>(static_cast<std::uint32_t>(cell.x)) << 32) |
      static_cast<std::uint32_t>(cell.y);
  const bool cache = raw_contributor_cache_active_ && terrain_cell_cache_enabled_;
  if (cache) {
    const auto found = terrain_cell_cache_.find(key);
    if (found != terrain_cell_cache_.end()) {
      ++terrain_cell_cache_hits_;
      return found->second;
    }
  }
  TerrainCellLayers layers;
  const auto raw = supportState().reactive_ground_.cells.find(cell);
  const auto scored = supportState().reactive_terrain_.cells.find(cell);
  if (raw != supportState().reactive_ground_.cells.end()) layers.raw = &raw->second;
  if (scored != supportState().reactive_terrain_.cells.end()) layers.scored = &scored->second;
  if (cache) {
    ++terrain_cell_cache_evaluations_;
    if (terrain_cell_cache_.size() < terrain_cell_cache_capacity_)
      terrain_cell_cache_.emplace(key, layers);
  }
  return layers;
}

bool GridMap::reactiveFootprintSupportQuery(const Eigen::Vector3d &body_reference,
    const reactive_stair::NonTerrainVoxel &obstacle, reactive_stair::Query &query) {
  return footprintSupportVerdict(body_reference,obstacle,query,false)==reactive_stair::Verdict::Free;
}

reactive_stair::EvidenceFloorDiagnostic GridMap::physicalSupportDiagnostic(const Eigen::Vector3d &body) const {
  const auto &s=supportState();
  reactive_stair::Cell2 cell;
  const auto &raw=s.reactive_ground_;const auto &nav=s.reactive_navigation_ground_;
  const bool same=raw.source_id==nav.source_id && raw.frame==nav.frame && raw.resolution_m==nav.resolution_m &&
      raw.origin_x_m==nav.origin_x_m && raw.origin_y_m==nav.origin_y_m;
  const auto *override_cell=same && supportQueryCell(body.x(),body.y(),cell) ? &cell : nullptr;
  return reactive_stair::diagnoseEvidenceFloor(s.reactive_navigation_ground_,s.reactive_surface_ground_,
      qualifiedPhysicalFloor(),body.x(),body.y(),body.z()-s.reactive_parameters_.body_clearance_m,
      s.reactive_parameters_.body_height_tolerance_m,reactive_stair::StepScoreParameters{}.critical_height_m,
      mapState().mp_.double_cylinder_radius_,override_cell);
}

reactive_stair::Verdict GridMap::footprintSupportVerdict(const Eigen::Vector3d &body_reference,
    const reactive_stair::NonTerrainVoxel &obstacle, reactive_stair::Query &query, bool static_only) {
  using reactive_stair::Verdict;
  if (!body_reference.allFinite()) return Verdict::InvalidQuery;
  const auto &raw = supportState().reactive_ground_;
  const auto &scored = supportState().reactive_terrain_;
  if (raw.source_id != scored.source_id || raw.frame != scored.frame ||
      raw.resolution_m != scored.resolution_m || raw.origin_x_m != scored.origin_x_m ||
      raw.origin_y_m != scored.origin_y_m) return Verdict::MissingInput;
  auto body_query = query;
  body_query.x_m = body_reference.x();
  body_query.y_m = body_reference.y();
  body_query.z_m = body_reference.z();
  body_query.in_map = static_only || isInMap(body_reference);
  // This copy checks terrain support only. The original measured obstacle
  // still controls the final footprint verdict at the original physical XYZ.
  auto support_only = obstacle;
  support_only.occupancy = reactive_stair::Occupancy::Free;
  reactive_stair::Cell2 body_cell;
  if (!supportQueryCell(body_query.x_m,body_query.y_m,body_cell)) return Verdict::InvalidQuery;
  const auto body_verdict=static_only ? supportState().reactive_decision_.supportVerdict(body_query,&body_cell) :
    supportState().reactive_decision_.decide(body_query,support_only,&body_cell);
  if (body_verdict!=Verdict::Free) {
    if (body_verdict==Verdict::WrongHeight || body_verdict==Verdict::UnknownSupport) {
      const auto association=physicalSupportDiagnostic(body_reference);
      if (association.physical_floor && association.edge_blocked) return Verdict::EdgeClearance;
    }
    return body_verdict;
  }
  const auto associated_height = [&](double x, double y, double target, double limit, double &height) {
    reactive_stair::Cell2 cell;
    if (!supportQueryCell(x,y,cell)) return false;
    const auto layers = terrainCellLayers(cell);
    if (!layers.raw || !layers.scored || layers.raw->size() != layers.scored->size()) return false;
    // Associate before considering scored status. Never skip an unknown or
    // unsupported nearest layer in favor of a farther supported floor.
    const int layer = reactive_stair::nearestSurface(*layers.raw, target, limit);
    if (layer < 0) return false;
    const auto &surface = (*layers.scored)[layer];
    if (surface.elevation_m != (*layers.raw)[layer].elevation_m ||
        !reactive_stair::selectedSurface(surface)) return false;
    height = surface.elevation_m;
    return true;
  };
  double body_ground, footprint_ground;
  const double step = reactive_stair::StepScoreParameters{}.critical_height_m;
  if (!associated_height(body_query.x_m, body_query.y_m,
          body_query.z_m - supportState().reactive_parameters_.body_clearance_m,
          supportState().reactive_parameters_.body_height_tolerance_m, body_ground) ||
      !associated_height(query.x_m, query.y_m, body_ground, step, footprint_ground)) return Verdict::UnknownSupport;
  if (std::abs(footprint_ground-body_ground)>=step) return Verdict::UnsupportedTerrain;
  // Only the support-layer height changes; do not move the robot, spline,
  // obstacle query, map-boundary query or retained measured LiDAR evidence.
  query.z_m = footprint_ground + supportState().reactive_parameters_.body_clearance_m;
  return Verdict::Free;
}

reactive_stair::Verdict GridMap::staticTraversability(Eigen::Vector3d pos,double yaw) {
  using reactive_stair::Verdict;
  if (!mapperHealthy() || !reactiveSurfaceGroundReady()) return Verdict::MissingInput;
  const auto &state=supportState();
  auto verdict=reactive_stair::staticSupportGeometry({{pos.x(),pos.y(),pos.z()}},yaw,
      state.reactive_ground_,state.reactive_terrain_,state.reactive_decision_,
      state.reactive_parameters_,mapState().mp_.double_cylinder_offset_,
      [&](double x,double y,reactive_stair::Cell2 &cell){return supportQueryCell(x,y,cell);},
      mapState().mp_.support_gap_mask_.get());
  if(verdict==Verdict::WrongHeight||verdict==Verdict::UnknownSupport) {
    const auto association=physicalSupportDiagnostic(pos);
    if(association.physical_floor&&association.edge_blocked)return Verdict::EdgeClearance;
  }
  if(verdict==Verdict::Free&&state.static_solid_) {
    if(!pos.allFinite()||!std::isfinite(yaw))return Verdict::InvalidQuery;
    if(state.static_solid_->collides(pos,yaw))return Verdict::StaticObstacle;
  }
  return verdict;
}

reactive_stair::Occupancy GridMap::rawContributorOccupancy(const Eigen::Vector3i &id) {
  if (!isInMap(id)) return reactive_stair::Occupancy::Unknown;
  const int address = toAddress(id);
  if (raw_contributor_cache_active_) {
    const auto cached = raw_contributor_cache_.find(address);
    if (cached != raw_contributor_cache_.end()) {
      ++raw_contributor_cache_hits_;
      return cached->second;
    }
  }
      // Every raw occupied source contributing to SCAN's inflated hit must
      // have a retained, positively observed terrain classification. One unclassified
      // return, even at a supported XY, keeps the result occupied.
      bool contributor = false;
      bool unclassified = false;
      for (const auto &offset : mapState().md_.inflate_offsets_) {
        const Eigen::Vector3i source = id - offset;
        if (!isInMap(source) || mapState().md_.occupancy_buffer_[toAddress(source)] <= mapState().mp_.min_occupancy_log_)
          continue;
        contributor = true;
        const auto key = std::make_tuple(source.x(), source.y(), source.z());
        if (!reactive_stair::mayWaiveRawContributor(
                mapState().reactive_terrain_hits_.count(key) != 0,
                mapState().reactive_nonterrain_hits_.count(key) != 0,
                mapState().reactive_nonterrain_history_.count(key) != 0)) {
          unclassified = true;
          break;
        }
      }
      const auto result = !contributor ? reactive_stair::Occupancy::Unknown :
          (unclassified ? reactive_stair::Occupancy::Occupied : reactive_stair::Occupancy::Free);
  if (raw_contributor_cache_active_) {
    ++raw_contributor_cache_evaluations_;
    raw_contributor_cache_.emplace(address, result);
  }
  return result;
}

bool GridMap::bodyEndpointMayBeObserved(const Eigen::Vector3d &point) {
  if (!mapperHealthy()) return false;

  const double offset = std::abs(mapState().mp_.double_cylinder_offset_);
  const double resolution = mapState().mp_.resolution_;
  if (!point.allFinite() || point.cwiseAbs().maxCoeff() > 1e6 ||
      !std::isfinite(offset) || !std::isfinite(resolution) || resolution <= 0.0 ||
      !std::isfinite(mapState().mp_.double_cylinder_radius_) || mapState().mp_.double_cylinder_radius_ < 0.0 ||
      !std::isfinite(mapState().mp_.clamp_min_log_) || mapState().md_.occupancy_buffer_.empty() ||
      !std::isfinite(1.0 / resolution) ||
      (point.cwiseAbs().maxCoeff() + offset + resolution) / resolution >
          std::numeric_limits<int>::max() / 4.0) return true;
  // The existing measured-footprint waiver can admit unknown space beside the
  // robot. Keep every possibly waived endpoint, even with stale/invalid pose.
  // A 1 m margin strictly encloses its [-0.05, 0.10854] m vertical slice.
  if (mapState().reactive_known_trunk_enabled_ &&
      (!queryBodyPosition().allFinite() || !reactive_body_quaternion_.coeffs().allFinite() ||
       std::abs(reactive_body_quaternion_.squaredNorm() - 1.0) > 1e-6 ||
       (point - queryBodyPosition()).norm() <=
           2.0 * offset + mapState().mp_.double_cylinder_radius_ + 1.0)) return true;
  // Front and rear are reflected about the endpoint at every yaw. Enumerate
  // an outward-rounded superset of their XY cells, at the exact query Z. A
  // known front cell must have a possibly known reflected rear cell. We do
  // not require the cells to lie on the yaw circle: uncertainty keeps search.
  const double slack = resolution * 1e-5;
  const Eigen::Vector3d extent(offset + slack, offset + slack, 0.0);
  Eigen::Vector3i lower, upper;
  posToIndex(point - extent, lower);
  posToIndex(point + extent, upper);
  lower = lower.cwiseMax(mapState().mp_.map_bound_min_idx_);
  upper = upper.cwiseMin(mapState().mp_.map_bound_max_idx_);
  if ((lower.array() > upper.array()).any()) return false;
  const Eigen::Vector3d sizes = (upper - lower + Eigen::Vector3i::Ones()).cast<double>();
  if (sizes.prod() > 1000000.0) return true;
  auto observed = [&](const Eigen::Vector3i &index) {
    const double value = mapState().md_.occupancy_buffer_[toAddress(index)];
    return !std::isfinite(value) || value >= mapState().mp_.clamp_min_log_ - 1e-3;
  };
  for (int x = lower.x(); x <= upper.x(); ++x)
    for (int y = lower.y(); y <= upper.y(); ++y) {
      if (!observed(Eigen::Vector3i(x, y, lower.z()))) continue;
      // posToIndex uses floor(p / resolution + 1e-6). The slack strictly
      // encloses that bias and both boundaries before reflection.
      const Eigen::Vector3d front_lo(x * resolution - slack, y * resolution - slack, point.z());
      const Eigen::Vector3d front_hi((x + 1) * resolution + slack, (y + 1) * resolution + slack, point.z());
      Eigen::Vector3i rear_lo, rear_hi;
      posToIndex(2.0 * point - front_hi, rear_lo);
      posToIndex(2.0 * point - front_lo, rear_hi);
      rear_lo = rear_lo.cwiseMax(lower);
      rear_hi = rear_hi.cwiseMin(upper);
      for (int rx = rear_lo.x(); rx <= rear_hi.x(); ++rx)
        for (int ry = rear_lo.y(); ry <= rear_hi.y(); ++ry)
          if (observed(Eigen::Vector3i(rx, ry, lower.z()))) return true;
    }
  return false;
}

reactive_stair::Verdict GridMap::liveTraversability(Eigen::Vector3d pos,double yaw) {
  reactive_stair::Verdict result=reactive_stair::Verdict::Free;
  const int occupied=reactive_stair::twoCylinderQuery({{pos.x(),pos.y(),pos.z()}},yaw,
    mapState().mp_.double_cylinder_offset_,[&](const std::array<double,3> &point) {
      return reactiveOccupancy(Eigen::Vector3d(point[0],point[1],point[2]),&pos,&result);
    });
  return occupied && result==reactive_stair::Verdict::Free ? reactive_stair::Verdict::InvalidQuery : result;
}

int GridMap::reactiveOccupancy(const Eigen::Vector3d &point, const Eigen::Vector3d *body_reference,
    reactive_stair::Verdict *typed) {
  const auto refuse=[&](reactive_stair::Verdict reason) {if(typed)*typed=reason;return 1;};
  if(typed)*typed=reactive_stair::Verdict::Free;
  if (!mapperHealthy()) return refuse(reactive_stair::Verdict::MissingInput);

  if (!reactiveSurfaceGroundReady()) return refuse(reactive_stair::Verdict::MissingInput);
  if (!point.allFinite()) return refuse(reactive_stair::Verdict::InvalidQuery);
  if (mapState().mp_.support_gap_mask_ && mapState().mp_.support_gap_mask_->blocks(
      point.x(),point.y(),point.z()-supportState().reactive_parameters_.body_clearance_m)) return refuse(reactive_stair::Verdict::SupportGap);
  const double radius = mapState().mp_.double_cylinder_radius_;
  if (!std::isfinite(radius) || radius < 0.0 ||
      point.x() - radius < mapState().mp_.map_min_boundary_.x() ||
      point.x() + radius > mapState().mp_.map_max_boundary_.x() ||
      point.y() - radius < mapState().mp_.map_min_boundary_.y() ||
      point.y() + radius > mapState().mp_.map_max_boundary_.y() ||
      point.z() - mapState().mp_.obstacles_inflation_z_down < mapState().mp_.map_min_boundary_.z() ||
      point.z() + mapState().mp_.obstacles_inflation_z_up > mapState().mp_.map_max_boundary_.z()) return refuse(reactive_stair::Verdict::OutOfMap);
  reactive_stair::Query query;
  query.frame = mapState().mp_.frame_id_;
  query.stamp_s = queryNow().seconds();
  query.x_m = point.x(); query.y_m = point.y(); query.z_m = point.z();
  query.in_map = isInMap(point);
  reactive_stair::NonTerrainVoxel obstacle;
  obstacle.frame = mapState().mp_.frame_id_;
  obstacle.stamp_s = mapState().reactive_cloud_stamp_s_;
  if (mapState().reactive_cloud_ready_) obstacle.source_id = "scan_lidar_cloud";
  if (query.in_map) {
    Eigen::Vector3i query_id;
    posToIndex(point, query_id);
    const int address = toAddress(query_id);
    if (mapState().md_.occupancy_buffer_[address] < mapState().mp_.clamp_min_log_ - 1e-3) {
      obstacle.occupancy = reactive_stair::Occupancy::Unknown;
    } else if (mapState().md_.occupancy_buffer_inflate_[address] == 0) {
      obstacle.occupancy = reactive_stair::Occupancy::Free;
    } else {
      obstacle.occupancy = rawContributorOccupancy(query_id);
    }
  }
  if (mapState().reactive_known_trunk_enabled_ && query.in_map && reactive_body_stamp_s_ > 0.0) {
    Eigen::Vector3i id;
    posToIndex(point, id);
    // Test the queried point, not its voxel centre, so the waiver does not
    // depend on how the grid aligns with the body height.
    const Eigen::Vector3d local = reactive_body_quaternion_.conjugate() *
                                 (point - queryBodyPosition());
    const bool inside = reactive_stair::knownNavigationFootprintInterior(
        local.x(), local.y(), local.z(), query.stamp_s, reactive_body_stamp_s_,
        mapState().mp_.double_cylinder_radius_, mapState().mp_.double_cylinder_offset_);
    obstacle.occupancy = reactive_stair::measuredTrunkQuery(
        obstacle.occupancy, mapState().md_.occupancy_buffer_inflate_[toAddress(id)] != 0, inside);
  }
  if (body_reference) {
    const auto support_verdict=footprintSupportVerdict(*body_reference,obstacle,query,false);
    if(support_verdict!=reactive_stair::Verdict::Free) {
      if(support_verdict==reactive_stair::Verdict::EdgeClearance && !query_context_) {
        const auto d=physicalSupportDiagnostic(*body_reference);
        RCLCPP_WARN_THROTTLE(node_->get_logger(),*node_->get_clock(),1000,
            "physical_floor_edge_clearance floor_z=%.9f square_gap_m=%.9f guard_radius_m=%.9f witness=(%.9f,%.9f) witness_kind=%d; selected_surface_rejected",
            d.floor_z,d.square_gap_m,mapState().mp_.double_cylinder_radius_,d.witness_x,d.witness_y,d.witness_kind);
      }
      return refuse(support_verdict);
    }
  }
  reactive_stair::Cell2 support_cell;
  const auto verdict = supportQueryCell(query.x_m,query.y_m,support_cell) ?
      supportState().reactive_decision_.decide(query,obstacle,&support_cell) : reactive_stair::Verdict::InvalidQuery;
  if(typed)*typed=verdict;
  // Controller query views never share the native logger throttles or diagnostic set.
  if (query_context_) return verdict == reactive_stair::Verdict::Free ? 0 : 1;
  static std::set<std::tuple<int, int, int>> diagnosed;
  Eigen::Vector3i diagnostic_id;
  posToIndex(point, diagnostic_id);
  const auto diagnostic_key = std::make_tuple(diagnostic_id.x(), diagnostic_id.y(), diagnostic_id.z());
  if (query.in_map && (reactive_diagnostic_force_ || ((point - mapState().md_.ray_pos_).norm() < 0.8 &&
      diagnosed.size() < 120 && diagnosed.insert(diagnostic_key).second))) {
    const int diagnostic_address = toAddress(diagnostic_id);
    RCLCPP_WARN(node_->get_logger(),
        "near_sensor_verdict verdict=%d voxel=%d q=(%.5f,%.5f,%.5f) sensor=(%.5f,%.5f,%.5f) log_odds=%.5f inflation=%d stamp=%.3f",
        static_cast<int>(verdict), static_cast<int>(obstacle.occupancy),
        point.x(), point.y(), point.z(), mapState().md_.ray_pos_.x(), mapState().md_.ray_pos_.y(), mapState().md_.ray_pos_.z(),
        mapState().md_.occupancy_buffer_[diagnostic_address], static_cast<int>(mapState().md_.occupancy_buffer_inflate_[diagnostic_address]), query.stamp_s);
  }
  if (verdict != reactive_stair::Verdict::Free) {
    RCLCPP_WARN_THROTTLE(node_->get_logger(), *node_->get_clock(), 1000,
        "reactive_collision_blocked verdict=%d voxel=%d q=(%.3f,%.3f,%.3f) support_z=%.3f now=%.3f cloud_stamp=%.3f cloud_ready=%d terrain_cells=%zu body_clearance=%.3f",
        static_cast<int>(verdict), static_cast<int>(obstacle.occupancy),
        point.x(), point.y(), point.z(), query.z_m, query.stamp_s, obstacle.stamp_s,
        mapState().reactive_cloud_ready_, supportState().reactive_terrain_.cells.size(), supportState().reactive_parameters_.body_clearance_m);
  }
  return verdict == reactive_stair::Verdict::Free ? 0 : 1;
}

void GridMap::logInitialSplineCollision(const Eigen::Vector3d &pos, double yaw) {
  RCLCPP_WARN(node_->get_logger(),
      "initial_spline_collision pos=(%.8f,%.8f,%.8f) yaw=%.8f body=(%.8f,%.8f,%.8f) body_q=(%.8f,%.8f,%.8f,%.8f) body_stamp=%.8f now=%.8f",
      pos.x(), pos.y(), pos.z(), yaw,
      queryBodyPosition().x(), queryBodyPosition().y(), queryBodyPosition().z(),
      reactive_body_quaternion_.w(), reactive_body_quaternion_.x(), reactive_body_quaternion_.y(), reactive_body_quaternion_.z(),
      reactive_body_stamp_s_, queryNow().seconds());
  const Eigen::Vector3d heading(std::cos(yaw), std::sin(yaw), 0.0);
  reactive_diagnostic_force_ = true;
  reactiveOccupancy(pos + mapState().mp_.double_cylinder_offset_ * heading, &pos);
  reactiveOccupancy(pos - mapState().mp_.double_cylinder_offset_ * heading, &pos);
  reactive_diagnostic_force_ = false;
}

double GridMap::collisionSegmentYaw(const Eigen::Vector3d &from, const Eigen::Vector3d &to) const {
  const Eigen::Vector3d direction = reactive_body_quaternion_.toRotationMatrix().col(0);
  const double body_yaw = std::atan2(direction.y(), direction.x());
  return reactive_stair::motionHeading(to.x() - from.x(), to.y() - from.y(), body_yaw,
                                      queryNow().seconds(), reactive_body_stamp_s_);
}

bool GridMap::collisionFreeSegment(const Eigen::Vector3d &from, const Eigen::Vector3d &to,
                                   int *blocked_sample) {
  return reactive_stair::collisionFreeSegment(from, to, getResolution(), collisionSegmentYaw(from, to),
      [this](const Eigen::Vector3d &point, double yaw) { return getInflateOccupancy(point, yaw); },
      blocked_sample);
}

double GridMap::collisionTrajectoryYaw(const Eigen::Vector3d &from, const Eigen::Vector3d &ahead,
                                       const Eigen::Vector3d &velocity) const {
  if (!from.allFinite() || !ahead.allFinite() || !velocity.allFinite())
    return std::numeric_limits<double>::quiet_NaN();
  if ((ahead - from).head<2>().squaredNorm() < 1e-4)
    return collisionSegmentYaw(Eigen::Vector3d::Zero(), velocity);
  return collisionSegmentYaw(from, ahead);
}
