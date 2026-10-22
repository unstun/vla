#include "v84/recording.h"
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <plan_env/static_solid.h>
#include <unistd.h>
#include "src/plan_manage/include/plan_manage/measured_seed.h"

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  unsigned feedback_pass=0,feedback_total=0;
  for(int i=0;i<4;++i) {
    const double angle=i*M_PI/2.;
    Eigen::Matrix3d rotation=Eigen::AngleAxisd(angle,Eigen::Vector3d::UnitZ()).toRotationMatrix();
    const Eigen::Vector3d origin(.37*i,-.29*i,.3);
    if(!scan_planner::measuredSeedAgrees(origin,angle,origin+rotation*Eigen::Vector3d(.02,0,0),angle,.1,.18))
      throw std::runtime_error("Ordinary measured warm seed lost");
    if(scan_planner::measuredSeedAgrees(origin,angle,origin+rotation*Eigen::Vector3d(.334,-.128,.019),angle+.543,.1,.18))
      throw std::runtime_error("Recorded tracking displacement accepted as warm state");
    if(scan_planner::measuredSeedAgrees(origin,angle,origin,angle+.6,.1,.18))
      throw std::runtime_error("Yaw envelope displacement ignored");
  }
  for(int rotation=0;rotation<4;++rotation) {
    const double shiftx=.37*rotation,shifty=-.29*rotation,yaw=rotation*M_PI/2;
    const std::string stem="/tmp/v283_endpoint_"+std::to_string(getpid());
    const std::string bundle=stem+".pct",support_file=stem+".support";
    constexpr int n=41;
    {std::ofstream out(bundle,std::ios::binary);out.write("PCTMAP01",8);
     const uint32_t dims[]={1,n,n};out.write(reinterpret_cast<const char*>(dims),sizeof(dims));
     const double meta[]={.1,shiftx,shifty,.5,.5};out.write(reinterpret_cast<const char*>(meta),sizeof(meta));
     for(int c=0;c<6;++c)for(int i=0;i<n*n;++i) {const double value=c==2?3.:0.;out.write(reinterpret_cast<const char*>(&value),8);}
     for(int i=0;i<n*n;++i)out.put(1);}
    std::ostringstream text;text<<std::setprecision(17)<<"SUPPORT247 .1 "<<shiftx-2.05<<' '<<shifty-2.05
      <<" 1 "<<shiftx-2.05<<' '<<shifty-2.05<<" .3 .12 .35 .18 synthetic world "<<n*n<<" \"\" none\n";
    for(int x=0;x<n;++x)for(int y=0;y<n;++y)text<<x<<' '<<y<<" 0 1 1\n";
    const auto bytes=text.str();uint64_t fnv=14695981039346656037ULL;
    for(unsigned char c:bytes){fnv^=c;fnv*=1099511628211ULL;}
    {std::ofstream out(support_file);out<<bytes;}
    lite3_nav2::PCTRoutePlanner planner(bundle,.3);
    planner.setStaticSupport(std::make_shared<reactive_stair::StaticSupportField>(support_file,std::to_string(fnv)));
    const Eigen::Vector3d axis(std::cos(yaw),std::sin(yaw),0.),center(shiftx,shifty,.3);
    const Eigen::Vector3d start=center-.6*axis,goal=center+.6*axis;
    for(const auto &hints:std::vector<std::vector<lite3_nav2::PCTRoutePlanner::RejectedPose>>{
      {{start,yaw,false}},{{goal,yaw,false}},{{start+.05*axis,yaw,false},{goal-.05*axis,yaw,false}}}) {
      ++feedback_total;planner.setFeedbackConstraints(hints);
      try {const auto path=planner.plan(start,goal,false,yaw,yaw);feedback_pass+=path.size()>1;}
      catch(const std::exception &e){std::cout<<"ENDPOINT_REJECTION "<<e.what()<<'\n';}
    }
    planner.setFeedbackConstraints({{center,yaw,false}});
    if(!planner.rejectedAt(center,yaw,true))throw std::runtime_error("Interior hint lost");
    bool invalid_refused=false;
    try {planner.plan(center+Eigen::Vector3d(8,0,0),goal,false,yaw,yaw);}
    catch(const std::exception &){invalid_refused=true;}
    if(!invalid_refused)throw std::runtime_error("Invalid static endpoint admitted");
    std::remove(bundle.c_str());std::remove(support_file.c_str());
  }

  rclcpp::NodeOptions options;options.parameter_overrides({rclcpp::Parameter("grid_map.asynchronous_mapping",false),
      rclcpp::Parameter("grid_map.static_solid_path",std::string(std::getenv("RAW_FIELD"))),
      rclcpp::Parameter("grid_map.static_solid_fnv64",std::string(std::getenv("RAW_FNV")))});
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node",options);GridMap map;
  initialize_map(map,*node,"/work/fixtures/building");
  const Eigen::Vector3d witness(8.0657835006713867,7.4972043037414551,4.8370351791381836);
  const double witness_yaw=-.11866584275379298;
  auto pose=std::make_shared<nav_msgs::msg::Odometry>();pose->header.frame_id="world";pose->header.stamp=node->now();
  pose->pose.pose.position.x=witness.x();pose->pose.pose.position.y=witness.y();pose->pose.pose.position.z=witness.z();
  pose->pose.pose.orientation.z=std::sin(witness_yaw/2);pose->pose.pose.orientation.w=std::cos(witness_yaw/2);
  map.slidingMapFrameCallback(pose);
  map.updateSlidingMap(witness);
  auto &state=map.mutableMapState();
  state.reactive_cloud_ready_=true;state.reactive_cloud_stamp_s_=node->now().seconds();
  std::fill(state.md_.occupancy_buffer_.begin(),state.md_.occupancy_buffer_.end(),state.mp_.clamp_min_log_);
  std::fill(state.md_.occupancy_buffer_inflate_.begin(),state.md_.occupancy_buffer_inflate_.end(),0);
  map.reactive_body_stamp_s_=node->now().seconds();
  map.reactive_body_quaternion_=Eigen::Quaterniond(std::cos(witness_yaw/2),0,0,std::sin(witness_yaw/2));
  // Diagnostic-only scene witness, deliberately absent from the live obstacle
  // buffers. This does not modify production geometry or manufacture a run.
  const auto source=map.supportState().static_solid_->assess(witness,witness_yaw);
  const bool local_reject=map.getInflateOccupancy(witness,witness_yaw)!=0;
  std::cout<<"CONTRACT {\"feedback_pass\":"<<feedback_pass<<",\"feedback_total\":"<<feedback_total
    <<",\"source_wall_margin\":"<<source.margin<<",\"local_wall_rejected\":"<<local_reject
    <<",\"live_verdict\":"<<int(map.liveTraversability(witness,witness_yaw))<<"}\n";
  rclcpp::shutdown();
  return feedback_pass==feedback_total && source.margin<0 && local_reject?0:1;
}
