#include "v84/recording.h"
#include <path_searching/dyn_a_star.h>
#include <plan_manage/planner_manager.h>
#include <bspline_opt/bspline_optimizer.h>
#include <fstream>
#include <cstring>

namespace {
std::string save(const std::string &name,const std::string &bytes) {
  std::ofstream file("/evaluation/"+name,std::ios::binary);file.write(bytes.data(),bytes.size());file.close();
  uint64_t h=14695981039346656037ULL;for(unsigned char c:bytes){h^=c;h*=1099511628211ULL;}
  return std::to_string(h);
}
std::shared_ptr<const reactive_stair::StaticSolidField> solid(bool wall) {
  const std::string bytes="SOLID256B .1 -5.05 -5.05 .35 .18 .55 .35 .3 .15 0\nF 1\n50 50 0 2 0\nO "+
    std::string(wall?"1\n.18 .38 .3 -1e100 -1e100 -1e100 -1e100\n":"0\n");
  const std::string name=wall?"probe_wall.solid":"probe_empty.solid";
  return std::make_shared<reactive_stair::StaticSolidField>("/evaluation/"+name,save(name,bytes));
}
std::shared_ptr<const reactive_stair::EnvironmentalField> environment() {
  std::ostringstream text;text<<"ENV225 .1 -5.05 -5.05 .35 .18 .55 .35 .3 .15 0\nF 121\n";
  for(int x=45;x<=55;++x)for(int y=45;y<=55;++y)text<<x<<' '<<y<<" 0 2 0\n";
  text<<"A 1 .3 -1 -1 0 3 3 3\n";std::string bytes=text.str();const float value=.05f;
  for(int i=0;i<27;++i)bytes.append(reinterpret_cast<const char*>(&value),sizeof(value));
  return std::make_shared<reactive_stair::EnvironmentalField>("/evaluation/probe.env",save("probe.env",bytes));
}
}

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);rclcpp::NodeOptions options;
  options.parameter_overrides({rclcpp::Parameter("grid_map.asynchronous_mapping",false)});
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node",options);
  auto map=std::make_shared<GridMap>();initialize_map(*map,*node,"/work/fixtures/building");
  auto &state=map->mutableMapState();auto &support=map->mutableSupportState();
  state.mp_.support_gap_mask_.reset();state.support_lattice_enabled_=false;
  state.reactive_physical_floor_topic_.clear();state.reactive_known_trunk_enabled_=false;
  reactive_stair::TerrainSnapshot raw;raw.source_id="synthetic_supported_air";raw.frame="world";
  raw.stamp_s=1.;raw.resolution_m=.1;raw.origin_x_m=raw.origin_y_m=-5.05;
  const auto accept=[&]() {
    support.reactive_ground_=support.reactive_terrain_=support.reactive_navigation_ground_=support.reactive_surface_ground_=raw;
    support.reactive_physical_floor_={};support.reactive_parameters_.body_clearance_m=.3;
    support.reactive_decision_=reactive_stair::CollisionDecision(support.reactive_parameters_);
    if(!support.reactive_decision_.acceptTerrain(raw))throw std::runtime_error("Synthetic support rejected");
    map->invalidateRawContributorCache();
  };
  for(int x=0;x<101;++x)for(int y=0;y<101;++y)raw.cells[{x,y}]={{reactive_stair::Support::Flat,0.}};
  accept();support.static_solid_=solid(false);
  auto body=std::make_shared<nav_msgs::msg::Odometry>();body->header.frame_id="world";body->header.stamp=node->now();
  body->pose.pose.position.z=.3;body->pose.pose.orientation.w=1.;
  map->slidingMapFrameCallback(body);map->updateSlidingMap(Eigen::Vector3d(0,0,.3));
  state.reactive_cloud_ready_=true;state.reactive_cloud_stamp_s_=1.;map->reactive_body_stamp_s_=1.;
  std::fill(state.md_.occupancy_buffer_.begin(),state.md_.occupancy_buffer_.end(),state.mp_.clamp_min_log_-1.);
  std::fill(state.md_.occupancy_buffer_inflate_.begin(),state.md_.occupancy_buffer_inflate_.end(),0);
  int failures=0;const auto check=[&](const std::string &label,bool passed) {
    std::cout<<"REPAIR_CHECK "<<label<<"="<<passed<<'\n';failures+=!passed;
  };
  check("supported_unknown_air",map->getInflateOccupancy(Eigen::Vector3d(0,0,.3),0.)==0);
  check("supported_dynamic_height_air",map->getInflateOccupancy(Eigen::Vector3d(0,0,.45),0.)==0);
  // Cleared inflation is unknown evidence, eligible for full supported-air review.
  Eigen::Vector3i index;map->posToIndex(Eigen::Vector3d(.18,0,.3),index);
  state.md_.occupancy_buffer_inflate_[map->toAddress(index)]=1;
  reactive_stair::Verdict typed;
  map->reactiveOccupancy(Eigen::Vector3d(.18,0,.3),nullptr,&typed);
  check("cleared_inflation_supported_air",typed==reactive_stair::Verdict::Free);
  const int address=map->toAddress(index);
  state.md_.occupancy_buffer_[address]=state.mp_.clamp_max_log_;
  state.reactive_nonterrain_hits_.insert({index.x(),index.y(),index.z()});map->invalidateRawContributorCache();
  map->reactiveOccupancy(Eigen::Vector3d(.18,0,.3),nullptr,&typed);
  check("known_inflated_static_contributor_refused",typed==reactive_stair::Verdict::StaticObstacle);
  state.reactive_nonterrain_hits_.clear();map->invalidateRawContributorCache();
  state.md_.occupancy_buffer_[address]=state.mp_.clamp_min_log_-1.;
  Eigen::Vector3i ground_index=index;ground_index.z()-=2;
  const int ga=map->toAddress(ground_index);
  const double saved=state.md_.occupancy_buffer_[ga];
  state.md_.occupancy_buffer_[ga]=state.mp_.clamp_max_log_;
  state.reactive_terrain_hits_.insert({ground_index.x(),ground_index.y(),ground_index.z()});
  map->invalidateRawContributorCache();
  map->reactiveOccupancy(Eigen::Vector3d(.18,0,.3),nullptr,&typed);
  check("inflated_raw_unknown_terrain_contributor",typed==reactive_stair::Verdict::Free);
  state.reactive_terrain_hits_.clear();state.md_.occupancy_buffer_[ga]=saved;map->invalidateRawContributorCache();


  check("cleared_inflation_footprint_supported",map->getInflateOccupancy(Eigen::Vector3d(0,0,.3),0.)==0);
  state.md_.occupancy_buffer_inflate_[map->toAddress(index)]=0;
  state.reactive_cloud_stamp_s_=.1;
  check("stale_refused",map->getInflateOccupancy(Eigen::Vector3d(0,0,.3),0.)!=0);
  state.reactive_cloud_stamp_s_=1.;
  support.static_solid_=solid(true);
  check("source_geometry_not_in_live_air_admission",map->getInflateOccupancy(Eigen::Vector3d(0,.1,.3),0.)==0);
  support.static_solid_=solid(false);
  auto supported=raw;raw.cells.clear();raw.cells[{50,50}]={{reactive_stair::Support::Unsupported,0.}};accept();
  check("unsupported_refused",map->getInflateOccupancy(Eigen::Vector3d(0,0,.3),0.)!=0);
  raw=supported;accept();
  check("unassociated_height_refused",map->getInflateOccupancy(Eigen::Vector3d(0,0,1.),0.)!=0);
  check("outside_map_refused",map->getInflateOccupancy(state.mp_.map_max_boundary_+Eigen::Vector3d::Ones(),0.)!=0);

  // Isolate projection yaw from the unknown-air change using observed free voxels.
  std::fill(state.md_.occupancy_buffer_.begin(),state.md_.occupancy_buffer_.end(),state.mp_.clamp_min_log_);
  raw.cells.clear();for(int x=0;x<101;++x)for(int y=49;y<=51;++y)raw.cells[{x,y}]={{reactive_stair::Support::Flat,0.}};
  accept();AStar astar;astar.initGridMap(map,Eigen::Vector3i(110,80,60));astar.use_upstream_search_plane=true;
  const auto endpoint_result=astar.AstarSearch(.1,Eigen::Vector3d(-1.6,0,.3),Eigen::Vector3d(1.6,.04,.3));
  const auto endpoint_path=astar.getPath();
  check("nearest_endpoint_projection",endpoint_result==ASTAR_RET::SUCCESS&&!endpoint_path.empty()&&std::abs(endpoint_path.back().x()-1.6)<.05);

  raw.cells.clear();for(int x=0;x<101;++x)for(int y=0;y<101;++y) {
    const double xx=-5.+x*.1;const double z=.1*std::max(0,std::min(6,int(std::floor((2.-std::abs(xx))/.3))));
    raw.cells[{x,y}]={{reactive_stair::Support::Flat,z}};
  }
  accept();scan_planner::SCANPlannerManager manager;manager.grid_map_=map;
  manager.bspline_optimizer_rebound_.reset(new scan_planner::BsplineOptimizer);
  manager.bspline_optimizer_rebound_->a_star_.reset(new AStar);
  manager.bspline_optimizer_rebound_->a_star_->initGridMap(map,Eigen::Vector3i(110,80,60));
  manager.bspline_optimizer_rebound_->a_star_->use_upstream_search_plane=true;
  const auto target=manager.findGoalNeighborhoodPath(Eigen::Vector3d(-2.2,0,.3),Eigen::Vector3d(2.2,0,.3),.15);
  bool heights=!target.empty();for(const auto &p:target) {
    reactive_stair::Cell2 cell;heights=heights&&map->supportQueryCell(p.x(),p.y(),cell);
    const auto layer=raw.cells.find(cell);heights=heights&&layer!=raw.cells.end()&&std::abs(p.z()-(layer->second[0].elevation_m+.3))<1e-8;
  }
  check("goal_neighborhood_follows_terrain",heights&&(target.back()-Eigen::Vector3d(2.2,0,.3)).norm()<=.15);

  raw=supported;accept();support.environmental_field_=environment();support.static_solid_=solid(false);
  scan_planner::BsplineOptimizer optimizer;optimizer.setParam(node.get());optimizer.setEnvironment(map);
  optimizer.order_=3;optimizer.bspline_interval_=.2;optimizer.cps_.resize(9);optimizer.cps_.clearance=.1;
  optimizer.lambda1_=.05;optimizer.lambda3_=optimizer.lambda4_=1.;optimizer.max_vel_=optimizer.max_acc_=10.;
  for(int i=0;i<9;++i)optimizer.cps_.points.col(i)=Eigen::Vector3d((i-4)*.025,0.,.3);
  for(int i=0;i<9;++i)optimizer.ref_pts_.push_back(optimizer.cps_.points.col(i));
  double x[9],gradient[9],without,with;std::memcpy(x,optimizer.cps_.points.data()+9,sizeof(x));
  optimizer.lambda_environment_=0.;optimizer.combineCostRefine(x,gradient,without,9);
  Eigen::Map<Eigen::VectorXd> first_gradient(gradient,9);const Eigen::VectorXd base_gradient=first_gradient;
  optimizer.lambda_environment_=1.;optimizer.combineCostRefine(x,gradient,with,9);
  check("refine_excludes_environment",std::abs(with-without)<1e-10&&(first_gradient-base_gradient).norm()<1e-10);
  support.environmental_field_.reset();support.static_solid_=solid(true);
  Eigen::MatrixXd gradient_env;
  check("no_exact_source_optimizer_path",optimizer.calcEnvironmentalCost(optimizer.cps_.points,gradient_env)==0. && gradient_env.norm()==0.);
  for(int i=0;i<64;++i) {
    auto state_heap=std::make_shared<GridMapState>();
    auto parameters=std::make_unique<MappingParameters>();
    if(reinterpret_cast<uintptr_t>(state_heap.get())%alignof(GridMapState) ||
        reinterpret_cast<uintptr_t>(parameters.get())%alignof(MappingParameters))throw std::runtime_error("Unaligned heap owner");
    state_heap->md_.ray_q_=Eigen::Quaterniond::Identity();parameters->lidar_extrinsic_=Eigen::Matrix4d::Identity();
  }
  check("heap_eigen_alignment",true);
  // A blocked quantized endpoint must be allowed to use SCAN's proposal
  // adjustment beyond the former two-cell ring. Every returned edge is checked.
  const auto original_occupancy=state.md_.occupancy_buffer_;
  const auto original_inflation=state.md_.occupancy_buffer_inflate_;
  Eigen::Vector3i lower,upper;map->posToIndex(Eigen::Vector3d(-1.35,-.45,-.05),lower);
  map->posToIndex(Eigen::Vector3d(-.65,.45,.65),upper);
  for(int x=lower.x();x<=upper.x();++x)for(int y=lower.y();y<=upper.y();++y)for(int z=lower.z();z<=upper.z();++z) {
    const Eigen::Vector3i hit(x,y,z);
    const int a=map->toAddress(hit);state.md_.occupancy_buffer_[a]=state.mp_.clamp_max_log_;
    state.md_.occupancy_buffer_inflate_[a]=1;
    state.reactive_nonterrain_hits_.insert({hit.x(),hit.y(),hit.z()});
  }
  map->invalidateRawContributorCache();
  const auto fallback_result=astar.AstarSearch(.1,Eigen::Vector3d(-1,0,.3),Eigen::Vector3d(1,0,.3));
  const auto fallback_path=astar.getPath();bool fallback_edges=!fallback_path.empty();
  for(size_t i=1;i<fallback_path.size();++i)fallback_edges&=map->collisionFreeSegment(fallback_path[i-1],fallback_path[i]);
  std::cout<<"FALLBACK_RESULT status="<<fallback_result<<" terrain="<<astar.terrain_search_<<" points="<<fallback_path.size()<<" edges="<<fallback_edges<<" initial_occ="<<map->getInflateOccupancy(Eigen::Vector3d(-1,0,.3),0.)<<'\n';
  check("upstream_plane_fallback_checked_edges",fallback_result==ASTAR_RET::SUCCESS && !astar.terrain_search_ && fallback_edges);
  state.md_.occupancy_buffer_=original_occupancy;state.md_.occupancy_buffer_inflate_=original_inflation;
  state.reactive_nonterrain_hits_.clear();map->invalidateRawContributorCache();
  AStar thin_pool;thin_pool.initGridMap(map,Eigen::Vector3i(110,80,4));
  check("positive_tolerance_terminal_z_border",thin_pool.AstarSearch(.1,
      Eigen::Vector3d(0,0,.3),Eigen::Vector3d(1,0,.5),false,.25)==ASTAR_RET::INIT_ERR);
  check("positive_tolerance_out_of_pool_refused",thin_pool.AstarSearch(.1,
      Eigen::Vector3d(0,0,.3),Eigen::Vector3d(1,0,10.),false,.25)==ASTAR_RET::INIT_ERR);
  check("pool_interior_start_end",!astar.poolIndexValid({1,1,0},true) &&
      !astar.poolIndexValid({1,1,astar.POOL_SIZE_.z()-1},true));
  std::cout<<"REPAIR {\"failures\":"<<failures<<",\"physics_steps\":0}\n";
  rclcpp::shutdown();return failures?1:0;
}
