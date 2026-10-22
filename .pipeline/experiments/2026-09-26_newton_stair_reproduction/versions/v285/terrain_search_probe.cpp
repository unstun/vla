#include "v84/recording.h"
#include <path_searching/dyn_a_star.h>

// A hill made of horizontal stair treads has equal-height endpoints. The old
// chord plane remains at the lower floor and cannot represent its middle.
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  rclcpp::NodeOptions options;options.parameter_overrides({rclcpp::Parameter("grid_map.asynchronous_mapping",false)});
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node",options);
  auto map=std::make_shared<GridMap>();initialize_map(*map,*node,"/work/fixtures/building");
  auto &state=map->mutableMapState();state.mp_.support_gap_mask_.reset();state.support_lattice_enabled_=false;
  state.reactive_physical_floor_topic_.clear(); // This synthetic fixture uses selected terrain; no imported physical-floor binding.
  auto &support=map->mutableSupportState();
  reactive_stair::TerrainSnapshot raw;raw.source_id="synthetic_stair_hill";raw.frame="world";raw.stamp_s=1.;
  raw.resolution_m=.1;raw.origin_x_m=raw.origin_y_m=-5.05;
  const auto elevation=[](double x) {return .1*std::max(0,std::min(6,int(std::floor((2.-std::abs(x))/.3))));};
  for(int x=0;x<101;++x)for(int y=0;y<101;++y)
    raw.cells[{x,y}]={{reactive_stair::Support::Flat,elevation(-5.+x*.1)}};
  support.reactive_ground_=support.reactive_terrain_=support.reactive_navigation_ground_=support.reactive_surface_ground_=raw;
  support.reactive_physical_floor_={};support.reactive_parameters_.body_clearance_m=.3;
  support.reactive_decision_=reactive_stair::CollisionDecision(support.reactive_parameters_);
  if(!support.reactive_decision_.acceptTerrain(raw))throw std::runtime_error("Synthetic support rejected");
  auto body=std::make_shared<nav_msgs::msg::Odometry>();body->header.frame_id="world";body->header.stamp=node->now();
  body->pose.pose.position.x=-2.2;body->pose.pose.position.z=.3;body->pose.pose.orientation.w=1.;
  map->slidingMapFrameCallback(body);map->updateSlidingMap(Eigen::Vector3d(-2.2,0,.3));
  state.reactive_cloud_ready_=true;state.reactive_cloud_stamp_s_=1.;map->reactive_body_stamp_s_=1.;
  std::fill(state.md_.occupancy_buffer_.begin(),state.md_.occupancy_buffer_.end(),state.mp_.clamp_min_log_);
  std::fill(state.md_.occupancy_buffer_inflate_.begin(),state.md_.occupancy_buffer_inflate_.end(),0);
  if(!map->planningInputsReady())throw std::runtime_error("Synthetic map inputs not ready");
  std::cout<<"TERRAIN_INPUT start="<<int(map->liveTraversability(Eigen::Vector3d(-2.2,0,.3),0.))
    <<" end="<<int(map->liveTraversability(Eigen::Vector3d(2.2,0,.3),0.))<<'\n';
  AStar astar;astar.initGridMap(map,Eigen::Vector3i(110,40,60));astar.use_upstream_search_plane=true;
  int passed=0;
  for(bool reverse:{false,true}) {
    Eigen::Vector3d a(-2.2,0,.3),b(2.2,0,.3);if(reverse)std::swap(a,b);
    const auto result=astar.AstarSearch(.1,a,b);const auto path=astar.getPath();bool heights=!path.empty();
    for(const auto &p:path) {
      reactive_stair::Cell2 cell;
      heights=heights&&map->supportQueryCell(p.x(),p.y(),cell);
      const auto layer=raw.cells.find(cell);
      heights=heights&&layer!=raw.cells.end()&&std::abs(p.z()-(layer->second.front().elevation_m+.3))<1e-8;
    }
    passed+=result==ASTAR_RET::SUCCESS&&heights;
    std::cout<<"TERRAIN_DIRECTION reverse="<<reverse<<" result="<<result<<" points="<<path.size()<<" heights="<<heights<<'\n';
  }
  // An unsupported nearest layer is not permission to jump to a farther floor.
  for(auto &entry:support.reactive_terrain_.cells)if(entry.first.x==50)entry.second[0].support=reactive_stair::Support::Unsupported;
  support.reactive_decision_.acceptTerrain(support.reactive_terrain_);map->invalidateRawContributorCache();
  const bool gap_refused=astar.AstarSearch(.1,Eigen::Vector3d(-2.2,0,.3),Eigen::Vector3d(2.2,0,.3))!=ASTAR_RET::SUCCESS;
  // A right-angle stair corridor has endpoint tangents different from its
  // chord. The old endpoint loop retreats diagonally off all support.
  raw.cells.clear();
  for(int i=-22;i<=0;++i)raw.cells[{50+i,50}]={{reactive_stair::Support::Flat,.1*std::max(0,std::min(3,(i+18)/5))}};
  for(int i=0;i<=22;++i)raw.cells[{50,50+i}]={{reactive_stair::Support::Flat,.3+.1*std::min(3,i/5)}};
  for(int x=-4;x<=4;++x)for(int y=-4;y<=4;++y)
    raw.cells[{50+x,50+y}]={{reactive_stair::Support::Flat,.3}};
  support.reactive_ground_=support.reactive_terrain_=support.reactive_navigation_ground_=support.reactive_surface_ground_=raw;
  support.reactive_decision_.acceptTerrain(raw);map->invalidateRawContributorCache();
  int tangent_passed=0;
  for(bool reverse:{false,true}) {
    Eigen::Vector3d a(-1.8,0,.3),b(0,1.8,.9);if(reverse)std::swap(a,b);
    const auto result=astar.AstarSearch(.1,a,b);const auto path=astar.getPath();
    tangent_passed+=result==ASTAR_RET::SUCCESS&&!path.empty();
    std::cout<<"TANGENT_DIRECTION reverse="<<reverse<<" result="<<result<<" points="<<path.size()<<'\n';
  }
  std::cout<<"TERRAIN {\"stair_directions_passed\":"<<passed<<",\"total\":2,\"unsupported_refused\":"<<gap_refused<<",\"tangent_directions_passed\":"<<tangent_passed<<"}\n";
  rclcpp::shutdown();return passed==2&&gap_refused&&tangent_passed==2?0:1;
}
