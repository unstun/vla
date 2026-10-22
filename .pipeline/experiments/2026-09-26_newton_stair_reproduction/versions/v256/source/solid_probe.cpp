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
  rclcpp::NodeOptions options;options.parameter_overrides({rclcpp::Parameter("grid_map.asynchronous_mapping",false),
    rclcpp::Parameter("grid_map.static_solid_path",std::string(std::getenv("RAW_FIELD"))),
    rclcpp::Parameter("grid_map.static_solid_fnv64",std::string(std::getenv("RAW_FNV")))});
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

  reactive_stair::StaticSupportField support("/work/fixtures/building/native.support","1404261889151999461");
  reactive_stair::StaticSolidField solid(std::getenv("RAW_FIELD"),std::getenv("RAW_FNV"));
  void *legacy=makePointField("/task/environment_score_v224/fixtures/building/environment03.env","4316416882194453309",false);
  std::ofstream samples(out/"poses.csv");samples<<std::setprecision(17)<<"x,y,z,yaw,native_solid_margin,legacy_raw_solid_margin\n";
  std::mt19937 random(256);std::uniform_real_distribution<double> u(-.049,.049),angle(-M_PI,M_PI);
  size_t checked=0,admission_mismatch=0,solid_refusals=0;
  const auto &raw=map->supportState().reactive_ground_;
  for(const auto &entry:raw.cells) {
    if(random()%10)continue;
    for(const auto &surface:entry.second) {
      Eigen::Vector3d p(raw.origin_x_m+(entry.first.x+.5)*raw.resolution_m+u(random),
        raw.origin_y_m+(entry.first.y+.5)*raw.resolution_m+u(random),surface.elevation_m+.3+u(random));
      const double yaw=angle(random);const auto exact=solid.assess(p,yaw);
      double old[4];pointAssessment(legacy,p.x(),p.y(),p.z(),yaw,old);
      samples<<p.x()<<','<<p.y()<<','<<p.z()<<','<<yaw<<','<<exact.margin<<','<<old[1]<<'\n';
      auto expected=support.assess(p.x(),p.y(),p.z(),yaw);
      if(expected==reactive_stair::Verdict::Free&&exact.collision()){expected=reactive_stair::Verdict::StaticObstacle;++solid_refusals;}
      const auto actual=map->staticTraversability(p,yaw);
      admission_mismatch+=(expected==reactive_stair::Verdict::Free)!=(actual==reactive_stair::Verdict::Free);++checked;
    }
  }
  const Eigen::Vector3d b08(-6.0453147888183594,-3.1868112087249756,4.833031196594238);
  const auto witness=solid.assess(b08,-2.872806690561133);
  metrics<<"solid_queries="<<checked
    <<"\nstatic_admission_mismatch="<<admission_mismatch<<"\nnew_solid_refusals="<<solid_refusals
    <<"\nb08_margin="<<witness.margin<<"\nb08_verdict="<<int(map->staticTraversability(b08,-2.872806690561133))
    <<"\nb08_all_headings_blocked="<<solid.impossibleAt(b08)<<"\nquery_wall_s="<<seconds(began)<<'\n';
  freePointField(legacy);rclcpp::shutdown();return admission_mismatch||witness.margin>=0.?1:0;
}
