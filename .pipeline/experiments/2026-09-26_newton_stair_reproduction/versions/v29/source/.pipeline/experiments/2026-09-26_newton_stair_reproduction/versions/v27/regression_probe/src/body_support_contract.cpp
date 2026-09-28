#include <plan_env/grid_map.h>
#include <rosgraph_msgs/msg/clock.hpp>
#include <chrono>
#include <iostream>
#include <stdexcept>
#include <thread>

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<rclcpp::Node>("scan_planner_node");
  GridMap map;
  map.initMap(node.get());
  auto publisher = node->create_publisher<rosgraph_msgs::msg::Clock>("/clock", 10);
  for (int i=0; i<20; ++i) {
    rosgraph_msgs::msg::Clock clock; clock.clock.sec=1; publisher->publish(clock);
    rclcpp::spin_some(node); std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  const double now=node->now().seconds();
  if (now!=1.) throw std::runtime_error("Test simulation clock missing");
  using reactive_stair::Support;
  using reactive_stair::SurfaceCell;
  using reactive_stair::TerrainSnapshot;
  using reactive_stair::Query;
  using reactive_stair::NonTerrainVoxel;
  using reactive_stair::Occupancy;
  using reactive_stair::Verdict;
  const Eigen::Vector3d body(0.,0.,.30);
  const NonTerrainVoxel free{Occupancy::Free,"measured-sensor","world",now};
  auto load = [&](const std::vector<SurfaceCell> &layers) {
    TerrainSnapshot raw;
    raw.source_id="paired-test-source";raw.frame="world";raw.stamp_s=now;
    raw.resolution_m=.1;raw.origin_x_m=raw.origin_y_m=-.05;
    raw.cells[{0,0}]={{Support::Stair,0.}};
    raw.cells[{2,0}]=layers;
    for(auto &surface:raw.cells[{2,0}]) surface.support=Support::Stair;
    map.reactive_ground_=raw;
    auto scored=raw;scored.cells[{2,0}]=layers;scored.cells[{0,0}][0].support=Support::Flat;
    map.reactive_terrain_=scored;
    map.reactive_decision_=reactive_stair::CollisionDecision(map.reactive_parameters_);
    if(!map.reactive_decision_.acceptTerrain(scored)) throw std::runtime_error("Invalid test support");
  };
  int passed=0;
  auto check = [&](const char *name, bool expected, const Eigen::Vector3d &reference,
                   const NonTerrainVoxel &obstacle) {
    Query q{"world",now,.18,0.,.30,true};
    if(std::string(name)=="straddled_step" && map.reactive_decision_.decide(q,free)!=Verdict::WrongHeight)
      throw std::runtime_error("Positive fixture does not expose the old WrongHeight rejection");
    bool actual=map.reactiveFootprintSupportQuery(reference,obstacle,q);
    if(actual!=expected || q.x_m!=.18 || q.y_m!=0. || (!actual && q.z_m!=.30))
      throw std::runtime_error(name);
    if(actual && (std::abs(q.z_m-.44)>1e-12 ||
        (obstacle.occupancy==Occupancy::Free && map.reactive_decision_.decide(q,obstacle)!=Verdict::Free)))
      throw std::runtime_error("Support transform did not remove WrongHeight");
    if(actual && obstacle.occupancy!=Occupancy::Free &&
        map.reactive_decision_.decide(q,obstacle)==Verdict::Free)
      throw std::runtime_error("Support test waived an actual obstacle");
    std::cout<<"[BODY-SUPPORT] "<<name<<" passed, support_z="<<q.z_m<<std::endl;
    ++passed;
  };
  load({{Support::Flat,.14}});check("straddled_step",true,body,free);
  auto occupied=free;occupied.occupancy=Occupancy::Occupied;
  check("actual_obstacle_still_rejected",true,body,occupied);
  auto unknown=free;unknown.occupancy=Occupancy::Unknown;
  check("unknown_obstacle_still_rejected",true,body,unknown);
  auto stale=free;stale.stamp_s=now-.5;check("stale_measurement",false,body,stale);
  check("wrong_center_height",false,Eigen::Vector3d(0,0,1.3),free);
  load({{Support::Unknown,0.},{Support::Flat,.20}});check("closer_unknown",false,body,free);
  load({{Support::Unsupported,0.},{Support::Flat,.20}});check("closer_unsupported",false,body,free);
  load({{Support::Flat,-.10},{Support::Flat,.10}});check("equidistant_layers",false,body,free);
  load({{Support::Flat,.26}});check("exact_step_limit",false,body,free);
  load({{Support::Flat,.30}});check("above_step_limit",false,body,free);
  load({{Support::Flat,3.}});check("other_building_level",false,body,free);
  load({{Support::Flat,.14}});map.reactive_ground_.cells.erase({0,0});map.reactive_terrain_.cells.erase({0,0});
  map.reactive_decision_.acceptTerrain(map.reactive_terrain_);check("missing_center",false,body,free);
  load({{Support::Flat,.14}});map.reactive_ground_.cells.erase({2,0});map.reactive_terrain_.cells.erase({2,0});
  map.reactive_decision_.acceptTerrain(map.reactive_terrain_);check("missing_footprint",false,body,free);
  load({{Support::Flat,.14}});map.reactive_terrain_.cells[{2,0}][0].elevation_m=.15;
  map.reactive_decision_.acceptTerrain(map.reactive_terrain_);check("mismatched_elevation",false,body,free);
  load({{Support::Flat,.14}});map.reactive_terrain_.source_id="different-source";
  check("mismatched_source",false,body,free);
  std::cout<<"[BODY-SUPPORT] total="<<passed<<std::endl;
  rclcpp::shutdown();
}
