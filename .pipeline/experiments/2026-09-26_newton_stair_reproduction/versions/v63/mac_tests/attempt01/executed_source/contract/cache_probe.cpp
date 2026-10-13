// Actual GridMap classifier/mutation methods, not a replica of cache logic.
#include <plan_env/grid_map.h>
#include <iostream>
#include <stdexcept>

void check(bool value, const char *name) {
  if (!value) throw std::runtime_error(name);
  std::cout << "V39_CACHE_CHECK " << name << " PASS\n";
}

void terrain_lookup_checks(GridMap &map) {
  using reactive_stair::Cell2;
  using reactive_stair::SurfaceCell;
  using reactive_stair::Support;
  map.invalidateRawContributorCache();
  map.reactive_ground_.cells.clear(); map.reactive_terrain_.cells.clear();
  const Cell2 key{-9, 13}, missing{13, -9};
  map.reactive_ground_.cells[key] = {{Support::Flat, 1.25}, {Support::Unknown, 2.5}};
  map.reactive_terrain_.cells[key] = {{Support::Stair, 1.25}, {Support::Unsupported, 2.5}};
  const auto direct = map.terrainCellLayers(key);
  check(direct.raw && direct.scored && direct.raw->at(1).elevation_m == 2.5, "terrain_uncached_layers");
  check(map.terrain_cell_cache_.empty(), "terrain_outside_scope_has_no_cache");
  {
    GridMap::RawContributorCacheScope scope(map);
    auto first = map.terrainCellLayers(key);
    auto second = map.terrainCellLayers(key);
    check(first.raw == direct.raw && first.scored == direct.scored && second.raw == direct.raw,
          "terrain_borrowed_layers_are_exact_original_vectors");
    check(map.terrain_cell_cache_evaluations_ == 1 && map.terrain_cell_cache_hits_ == 1,
          "terrain_same_cell_avoids_repeated_tree_lookups");
    auto absent = map.terrainCellLayers(missing);
    check(!absent.raw && !absent.scored, "terrain_signed_key_no_alias");
    absent = map.terrainCellLayers(missing);
    check(!absent.raw && !absent.scored && map.terrain_cell_cache_hits_ == 2, "terrain_missing_cell_cached_exactly");
    { GridMap::RawContributorCacheScope nested(map); map.terrainCellLayers(key); }
    check(map.terrain_cell_cache_.size() == 2, "terrain_nested_scope_preserves_outer_entries");
    map.refreshSensorInputs("TERRAIN_CACHE_TEST");
    check(map.terrain_cell_cache_.size() == 2, "terrain_empty_drain_preserves_lookup_data");
    map.terrain_cell_cache_enabled_ = false;
    const auto hits = map.terrain_cell_cache_hits_;
    auto bypass = map.terrainCellLayers(key);
    check(bypass.raw == direct.raw && bypass.scored == direct.scored && map.terrain_cell_cache_hits_ == hits,
          "terrain_uncached_oracle_exact_pointer_parity");
    map.terrain_cell_cache_enabled_ = true;
    for (int x=0; x<5000; ++x) map.terrainCellLayers(Cell2{x, -400});
    check(map.terrain_cell_cache_.size() == 4096, "terrain_cache_memory_bounded");
    auto over = map.terrainCellLayers(Cell2{6000,-400});
    check(!over.raw && !over.scored && map.terrain_cell_cache_.size() == 4096, "terrain_capacity_falls_back_to_original_lookup");
    auto invalid=std::make_shared<sensor_msgs::msg::PointCloud2>(); invalid->header.frame_id="wrong_frame";
    map.reactiveTomogramCallback(invalid);
    check(map.terrain_cell_cache_.empty(), "terrain_actual_ground_replacement_drops_borrowed_pointers");
    auto replaced = map.terrainCellLayers(key);
    check(!replaced.raw, "terrain_removed_cell_cannot_reuse_previous_layer");
    map.reactiveSurfaceGroundCallback(invalid);
    check(map.terrain_cell_cache_.empty(), "terrain_actual_surface_replacement_invalidates");
    map.terrainCellLayers(key);
    map.cloudCallback(invalid);
    check(map.terrain_cell_cache_.empty(), "terrain_actual_cloud_callback_invalidates");
  }
  check(map.terrain_cell_cache_.empty() && !map.raw_contributor_cache_active_, "terrain_scope_exit_clears");
  std::cout << "V52_TERRAIN_LOOKUP_PASSED\n";
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
    check(map.raw_contributor_cache_.size()==1,"empty_refresh_preserves_unchanged_raw_inputs");
    { GridMap::RawContributorCacheScope nested(map);
      check(map.rawContributorOccupancy(id)==reactive_stair::Occupancy::Free,"nested_scope_same_verdict"); }
    check(map.raw_contributor_cache_active_ && map.raw_contributor_cache_.size()==1,"nested_scope_preserves_outer_cache");
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
  terrain_lookup_checks(map);
  std::cout << "V39_CACHE_PASSED\n";
  rclcpp::shutdown();
}
