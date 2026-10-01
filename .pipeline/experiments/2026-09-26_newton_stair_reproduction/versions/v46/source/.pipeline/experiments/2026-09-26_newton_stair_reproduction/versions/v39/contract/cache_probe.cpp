// Actual GridMap classifier/mutation methods, not a replica of cache logic.
#include <plan_env/grid_map.h>
#include <iostream>
#include <stdexcept>

void check(bool value, const char *name) {
  if (!value) throw std::runtime_error(name);
  std::cout << "V39_CACHE_CHECK " << name << " PASS\n";
}

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("scan_planner_node");
  GridMap map;
  map.initMap(node.get());
  map.occ_timer_->cancel(); map.vis_timer_->cancel();
  const Eigen::Vector3i id = (map.mp_.map_bound_min_idx_ + map.mp_.map_bound_max_idx_) / 2;
  const Eigen::Vector3i source = id - Eigen::Vector3i(1, 0, 0);
  check(map.isInMap(id) && map.isInMap(source), "fixture_in_map");
  map.md_.inflate_offsets_ = {Eigen::Vector3i::Zero(), Eigen::Vector3i(1,0,0)};
  map.applyOccupancyUpdate(id, map.mp_.clamp_max_log_);
  const auto key = std::make_tuple(id.x(),id.y(),id.z());
  map.reactive_terrain_hits_.insert(key);
  check(map.rawContributorOccupancy(id) == reactive_stair::Occupancy::Free, "classified_raw_contributor_free");
  {
    GridMap::RawContributorCacheScope scope(map);
    for (int i=0;i<30;i++) check(map.rawContributorOccupancy(id)==reactive_stair::Occupancy::Free,"same_raw_verdict");
    check(map.raw_contributor_cache_evaluations_==1 && map.raw_contributor_cache_hits_==29,"actual_cache_reuses_classification");
    map.refreshSensorInputs("CACHE_TEST");
    check(map.raw_contributor_cache_.empty(),"refresh_invalidates_even_without_new_messages");
    check(map.rawContributorOccupancy(id)==reactive_stair::Occupancy::Free,"refresh_recompute_same_inputs");
    map.applyOccupancyUpdate(source,map.mp_.clamp_max_log_);
    check(map.raw_contributor_cache_.empty(),"actual_occupancy_update_invalidates_neighbour_dependents");
    check(map.rawContributorOccupancy(id)==reactive_stair::Occupancy::Occupied,"unclassified_added_contributor_blocks");
    map.resetCellByAddress(map.toAddress(source));
    check(map.raw_contributor_cache_.empty(),"actual_cell_reset_invalidates");
    check(map.rawContributorOccupancy(id)==reactive_stair::Occupancy::Free,"classified_surviving_contributor_free");
    auto invalid=std::make_shared<sensor_msgs::msg::PointCloud2>(); invalid->header.frame_id="wrong_frame";
    map.reactiveTomogramCallback(invalid);
    check(map.raw_contributor_cache_.empty(),"actual_ground_callback_invalidates");
    check(map.rawContributorOccupancy(id)==reactive_stair::Occupancy::Occupied,"removed_terrain_label_cannot_reuse_free");
    map.reactiveSurfaceGroundCallback(invalid);
    check(map.raw_contributor_cache_.empty(),"actual_surface_callback_invalidates");
    map.resetAllMapData();
    check(map.rawContributorOccupancy(id)==reactive_stair::Occupancy::Unknown,"no_raw_contributor_conservative_unknown");
  }
  check(!map.raw_contributor_cache_active_ && map.raw_contributor_cache_.empty(),"scope_exit_disables_and_clears");
  map.applyOccupancyUpdate(id,map.mp_.clamp_max_log_);
  map.reactive_terrain_hits_.insert(key); map.reactive_nonterrain_history_.insert(key);
  {
    GridMap::RawContributorCacheScope scope(map);
    check(map.rawContributorOccupancy(id)==reactive_stair::Occupancy::Occupied,"retained_nonterrain_history_blocks_positive_terrain");
  }
  try { GridMap::RawContributorCacheScope scope(map); throw std::runtime_error("fixture"); }
  catch(const std::runtime_error&) {}
  check(!map.raw_contributor_cache_active_ && map.raw_contributor_cache_.empty(),"exception_scope_exit_clears");
  std::cout << "V39_CACHE_PASSED\n";
  rclcpp::shutdown();
}
