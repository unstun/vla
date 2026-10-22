// Export utility derived from frozen v247; no planner modifications.
// Evaluation only: installed PCT plugin/service and cold SCAN FSM, no planner source.
#include "v84/recording.h"
#include "v232/tools/raw_reference.h"
#include <plan_manage/scan_replan_fsm.h>
#include <bspline_opt/full_trajectory_collision.h>
#include <lite3_nav2_plugins/shared_traversability.hpp>
#include <lite3_nav2_interfaces/srv/route_session.hpp>
#include <nav2_core/global_planner.hpp>
#include <pluginlib/class_loader.hpp>
#include <atomic>
#include <cstring>
#include <plan_env/static_support.h>
#include <random>

double seconds(std::chrono::steady_clock::time_point t) {
  return std::chrono::duration<double>(std::chrono::steady_clock::now()-t).count();
}
reactive_stair::Verdict oldStatic(GridMap &map,Eigen::Vector3d pos,double yaw) {
  using reactive_stair::Verdict;
  if (!map.mapperHealthy() || !map.reactiveSurfaceGroundReady()) return Verdict::MissingInput;
  Verdict verdict=Verdict::Free;
  const auto test=[&](const std::array<double,3> &p) {
    const Eigen::Vector3d point(p[0],p[1],p[2]);
    if (map.mapState().mp_.support_gap_mask_ && map.mapState().mp_.support_gap_mask_->blocks(
        point.x(),point.y(),point.z()-map.supportState().reactive_parameters_.body_clearance_m)) {
      verdict=Verdict::SupportGap;return 1;
    }
    reactive_stair::Query query;
    query.frame=map.mapState().mp_.frame_id_;query.stamp_s=map.queryNow().seconds();query.in_map=true;
    query.x_m=point.x();query.y_m=point.y();query.z_m=point.z();
    reactive_stair::NonTerrainVoxel unused;
    verdict=map.footprintSupportVerdict(pos,unused,query,true);
    if (verdict==Verdict::Free) {
      reactive_stair::Cell2 cell;
      verdict=map.supportQueryCell(query.x_m,query.y_m,cell) ?
          map.supportState().reactive_decision_.supportVerdict(query,&cell) : Verdict::InvalidQuery;
    }
    return verdict==Verdict::Free ? 0 : 1;
  };
  if (reactive_stair::twoCylinderQuery({{pos.x(),pos.y(),pos.z()}},yaw,
      map.mapState().mp_.double_cylinder_offset_,test)!=0 && verdict==Verdict::Free)
    return Verdict::InvalidQuery;
  return verdict;
}

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  const fs::path input=std::getenv("CASE_INPUT"),out=std::getenv("PROBE_OUTPUT"),terrain=std::getenv("REPLAY_INPUT");
  fs::create_directories(out);
  std::ofstream metrics(out/"metrics.txt");metrics<<std::setprecision(17);
  const auto began=std::chrono::steady_clock::now();
  rclcpp::NodeOptions options;options.parameter_overrides({rclcpp::Parameter("grid_map.asynchronous_mapping",false)});
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node",options);set_clock(*node,1000000000LL);
  scan_planner::SCANReplanFSM fsm;
  int rounds=0,successes=0,published=0,emergencies=0;
  scan_planner_msgs::msg::Bspline publication;
  scan_planner::SCANReplanFSM::DirectIO direct;
  direct.planning_result=[&](bool success,int64_t){++rounds;successes+=success;};
  direct.spline=[&](const scan_planner_msgs::msg::Bspline &message) {
    if(message.emergency_stop)++emergencies;else {++published;publication=message;}
  };
  fsm.init(node.get(),nullptr,direct);auto map=fsm.nav2Map();
  fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();map->occ_timer_->cancel();map->vis_timer_->cancel();
  for(auto name:{"navigation","surface","physical_floor"}) {
    auto cloud=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(terrain/(std::string(name)+".f32"),true));
    cloud->header.stamp=node->now();
    if(std::string(name)=="navigation")map->reactiveTomogramCallback(cloud);
    else if(std::string(name)=="surface")map->reactiveSurfaceGroundCallback(cloud);
    else map->reactivePhysicalFloorCallback(cloud);
  }
  if(!map->reactiveSurfaceGroundReady()||!map->hasEnvironmentalField())throw std::runtime_error("Terrain/ENV not ready");
  auto field=std::make_shared<reactive_stair::EnvironmentalField>(std::getenv("ENVIRONMENT_INPUT"),std::getenv("ENVIRONMENT_FNV"));
  metrics<<"initialization_s="<<seconds(began)<<'\n';
  const auto &state=map->supportState();const auto &mp=map->mapState();
  const auto &raw=state.reactive_ground_, &scored=state.reactive_terrain_;
  const auto path=out/"native.support";
  std::ofstream file(path);file<<std::setprecision(17);
  size_t count=0;for(const auto &entry:raw.cells)count+=entry.second.size();
  const auto gap_path=node->get_parameter("grid_map.support_gap_path").as_string();
  const auto gap_fnv=node->get_parameter("grid_map.support_gap_fnv64").as_string();
  file<<"SUPPORT247 "<<raw.resolution_m<<' '<<raw.origin_x_m<<' '<<raw.origin_y_m<<' '
    <<mp.support_lattice_enabled_<<' '<<mp.support_lattice_origin_x_m_<<' '<<mp.support_lattice_origin_y_m_<<' '
    <<state.reactive_parameters_.body_clearance_m<<' '<<state.reactive_parameters_.body_height_tolerance_m<<' '
    <<mp.mp_.double_cylinder_radius_<<' '<<mp.mp_.double_cylinder_offset_<<' '<<raw.source_id<<' '<<raw.frame<<' '<<count<<' '
    <<std::quoted(gap_path)<<' '<<(gap_fnv.empty()?"none":gap_fnv)<<'\n';
  for(const auto &entry:raw.cells) {
    const auto &other=scored.cells.at(entry.first);if(other.size()!=entry.second.size())throw std::runtime_error("Native support layer mismatch");
    for(size_t i=0;i<other.size();++i)file<<entry.first.x<<' '<<entry.first.y<<' '<<entry.second[i].elevation_m<<' '
      <<int(entry.second[i].support)<<' '<<int(other[i].support)<<'\n';
  }
  file.close();
  std::cout<<"SUPPORT_EXPORT_COMPLETE "<<path<<std::endl;
  rclcpp::shutdown();return 0;
}
