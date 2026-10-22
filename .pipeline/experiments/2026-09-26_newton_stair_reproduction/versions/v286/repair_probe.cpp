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
  // Inflated evidence cannot be waived, even if no ray traversed this voxel.
  Eigen::Vector3i index;map->posToIndex(Eigen::Vector3d(.18,0,.3),index);
  state.md_.occupancy_buffer_inflate_[map->toAddress(index)]=1;
  check("inflated_unknown_refused",map->getInflateOccupancy(Eigen::Vector3d(0,0,.3),0.)!=0);
  state.md_.occupancy_buffer_inflate_[map->toAddress(index)]=0;
  state.reactive_cloud_stamp_s_=.1;
  check("stale_refused",map->getInflateOccupancy(Eigen::Vector3d(0,0,.3),0.)!=0);
  state.reactive_cloud_stamp_s_=1.;
  support.static_solid_=solid(true);
  check("real_source_collision_refused",map->getInflateOccupancy(Eigen::Vector3d(0,.1,.3),0.)!=0);
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
  const Eigen::MatrixXd q=optimizer.cps_.points;Eigen::MatrixXd g,unused;
  const double near=optimizer.calcEnvironmentalCost(q,g);
  auto plus=q,minus=q;plus(1,4)+=1e-5;minus(1,4)-=1e-5;
  const double numerical=(optimizer.calcEnvironmentalCost(plus,unused)-optimizer.calcEnvironmentalCost(minus,unused))/2e-5;
  const auto source_assessment=support.static_solid_->assess(Eigen::Vector3d(0,0,.3),0.);
  std::cout<<"BUFFER_GRADIENT cost="<<near<<" control_y="<<g(1,4)<<" numerical="<<numerical
    <<" translated_y="<<g.row(1).sum()<<" source_margin="<<source_assessment.margin
    <<" source_gradient="<<source_assessment.gradient.transpose()<<'\n';
  // A single control point also changes yaw. Only a rigid translation has
  // an unambiguous away-from-wall sign; retain the individual derivative test.
  auto translated_plus=q,translated_minus=q;
  translated_plus.row(1).array()+=1e-5;translated_minus.row(1).array()-=1e-5;
  const double translation_numerical=(optimizer.calcEnvironmentalCost(translated_plus,unused)-
      optimizer.calcEnvironmentalCost(translated_minus,unused))/2e-5;
  check("source_buffer_rebound_gradient",near>0.&&g.row(1).sum()>0.&&
      std::abs(numerical-g(1,4))<1e-3&&std::abs(translation_numerical-g.row(1).sum())<1e-3);
  auto far=q;far.row(1).array()-=.15;const double outside=optimizer.calcEnvironmentalCost(far,unused);
  check("source_buffer_zero_outside",outside==0.&&unused.norm()==0.);
  std::cout<<"REPAIR {\"failures\":"<<failures<<",\"physics_steps\":0}\n";
  rclcpp::shutdown();return failures?1:0;
}
