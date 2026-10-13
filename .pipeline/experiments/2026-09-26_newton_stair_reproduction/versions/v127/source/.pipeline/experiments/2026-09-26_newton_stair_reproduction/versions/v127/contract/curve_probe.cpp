#include "records.h"
#include "v84/recording.h"
#include <cstring>
#include <cstdint>
#include <plan_manage/scan_replan_fsm.h>
#include <bspline_opt/full_trajectory_collision.h>
#ifdef VALIDATOR_CANDIDATE
#include <plan_manage/trajectory_validation.h>
#endif

int main(int argc,char **argv) {
  std::srand(0);
  rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  set_clock(*node,1000000000LL);
  node->declare_parameter<bool>("grid_map.asynchronous_mapping",false);
  node->set_parameter(rclcpp::Parameter("grid_map.asynchronous_mapping",false));
  scan_planner::SCANReplanFSM fsm;fsm.init(node.get());
  fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();
  auto &manager=*fsm.planner_manager_;auto map=manager.grid_map_;
  map->occ_timer_->cancel();map->vis_timer_->cancel();
  if(map->async_mapping_)throw std::runtime_error("Probe expects ordered recorded-map initialization");
  const fs::path input=std::getenv("V114_INPUT");
  auto nav=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"navigation.f32",true));
  auto surface=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"surface.f32",true));
  auto floor=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"physical_floor.f32",true));
  nav->header.stamp=surface->header.stamp=floor->header.stamp=node->now();
  map->reactiveTomogramCallback(nav);map->reactiveSurfaceGroundCallback(surface);map->reactivePhysicalFloorCallback(floor);
  std::ifstream listing(input/"scans.txt");int index;int64_t stamp,later;std::string body,sensor,cloud,later_body;
  nav_msgs::msg::Odometry::SharedPtr last;
  while(listing>>index>>stamp>>body>>sensor>>cloud>>later>>later_body) {
    RecordedScan scan{index,stamp,std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/body)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sensor)),
      std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cloud,false))};
    scan.body->header.stamp=scan.sensor->header.stamp=scan.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    apply_scan(*map,*node,scan);last=scan.body;
  }
  fsm.odometryCallback(last);fsm.have_p2b_identity_=true;fsm.active_p2b_identity_.run_id="publication-proof";
  fsm.active_p2b_identity_.command_id="verified-command";fsm.active_p2b_identity_.generation=1;
  const auto start=fsm.odom_pos_;const Eigen::Vector3d end(start.x()+.25,start.y()-.6,3.34),zero=Eigen::Vector3d::Zero();
  const auto checked_clock=node->now();const double observation=map->observationStamp();
#ifdef DIAGNOSTIC_CANDIDATE
  manager.planning_outcome_.begin();
#endif
  const bool success=manager.reboundReplan(start,zero,zero,end,zero,true,false);
#ifdef DIAGNOSTIC_CANDIDATE
  manager.finishPlanningOutcome(success);
#endif
  if(!success)throw std::runtime_error("Actual native fixture did not produce a validated trajectory");
  const auto controls = manager.local_data_.position_traj_.getControlPoint();
  const auto knots = manager.local_data_.position_traj_.getKnot();
  auto bits = [](double value) { uint64_t result; std::memcpy(&result, &value, sizeof(result)); return result; };
  std::ostringstream curve_record;
  curve_record << "{\"rows\":" << controls.rows() << ",\"cols\":" << controls.cols() << ",\"control_bits\":[";
  for (int i=0;i<controls.size();++i) { if(i)curve_record<<","; curve_record<<bits(controls.data()[i]); }
  curve_record << "],\"knot_bits\":[";
  for (int i=0;i<knots.size();++i) { if(i)curve_record<<","; curve_record<<bits(knots[i]); }
  curve_record << "],\"duration_bits\":" << bits(manager.local_data_.duration_) << "}" ;
  writeTestRecord("MPPI_CURVE",curve_record.str());
  const auto before_validation_digest=map_digest(*map);
  int collision_cases=0,clear_cases=0,blocked_cases=0;
  auto inspect=[&](const std::string &name,scan_planner::UniformBspline curve,double phase,int expected) {
#ifdef VALIDATOR_CANDIDATE
    const auto report=scan_planner::NativeTrajectoryValidator::collision(curve,*map,phase);
#else
    const auto report=reactive_stair::checkFullCubicTrajectory(
        curve,phase,map->getResolution(),GridMap::collision_heading_lookahead_s,
        [&map](const Eigen::Vector3d &p,const Eigen::Vector3d &ahead,const Eigen::Vector3d &v) {
          return map->collisionTrajectoryYaw(p,ahead,v);
        },[&map](const Eigen::Vector3d &p,double yaw){return map->getInflateOccupancy(p,yaw)!=0;});
#endif
    if(expected>=0 && int(report.clear())!=expected)throw std::runtime_error("collision expectation: "+name);
    ++collision_cases;if(report.clear())++clear_cases;else ++blocked_cases;
    std::ostringstream collision_record;
    collision_record<<"{\"case\":\""<<name<<"\",\"status\":"<<int(report.status)
      <<",\"first_time_bits\":"<<bits(report.first_time_s)<<",\"duration_bits\":"<<bits(report.duration_s)
      <<",\"samples\":"<<report.samples<<"}";
    writeTestRecord("V127_COLLISION",collision_record.str());
  };
  auto accepted_curve=manager.local_data_.position_traj_;
  inspect("whole",accepted_curve,0.,1);
  inspect("remaining",accepted_curve,accepted_curve.getTimeSum()*.5,1);
  inspect("negative_time",accepted_curve,-.01,0);
  inspect("nonfinite_time",accepted_curve,std::numeric_limits<double>::quiet_NaN(),0);
  inspect("endpoint",accepted_curve,accepted_curve.getTimeSum(),1);
  auto outside=controls;outside.row(0).array()+=1000.;
  inspect("outside_map",scan_planner::UniformBspline(outside,3,1.),0.,0);
  auto invalid=controls;invalid(0,0)=std::numeric_limits<double>::quiet_NaN();
  inspect("nonfinite_controls",scan_planner::UniformBspline(invalid,3,1.),0.,0);
  scan_planner::UniformBspline empty;inspect("empty_curve",empty,0.,0);
  for(double dx:{-.2,0.,.2})for(double dy:{-.2,0.,.2})for(double dz:{-.15,0.,.15}) {
    auto translated=controls;
    for(int i=0;i<translated.cols();++i)translated.col(i)+=Eigen::Vector3d(dx,dy,dz);
    scan_planner::UniformBspline varied(translated,3,1.);varied.setKnot(knots);
    inspect("offset_"+std::to_string(dx)+"_"+std::to_string(dy)+"_"+std::to_string(dz),varied,0.,-1);
  }
  if(clear_cases==0 || blocked_cases==0 || map_digest(*map)!=before_validation_digest)
    throw std::runtime_error("real-map validation coverage or immutability");
  const auto certificate=manager.publication_check_;
  if(!certificate.clear || certificate.traj_id!=manager.local_data_.traj_id_ ||
     certificate.checked_at!=checked_clock || certificate.observation_stamp_s!=observation)
    throw std::runtime_error("Actual final validation evidence was not bound to the exact trajectory");
  auto reader=std::make_shared<rclcpp::Node>("publication_proof_reader");
  scan_planner_msgs::msg::P2BExecutionSafety::ConstSharedPtr received;
  auto sub=reader->create_subscription<scan_planner_msgs::msg::P2BExecutionSafety>("/planning/execution_safety",10,
    [&](scan_planner_msgs::msg::P2BExecutionSafety::ConstSharedPtr p){received=p;});
  for(int i=0;i<100 && fsm.nav2_safety_pub_->get_subscription_count()==0;++i)std::this_thread::sleep_for(std::chrono::milliseconds(5));
  set_clock(*node,checked_clock.nanoseconds()+20000000LL);
  fsm.publishExecutionSafety(certificate.traj_id,certificate.checked_at,certificate.observation_stamp_s,certificate.map_revision,true);
  for(int i=0;i<100 && !received;++i){rclcpp::spin_some(reader);std::this_thread::sleep_for(std::chrono::milliseconds(2));}
  if(!received || !received->clear || received->binding.traj_id!=certificate.traj_id ||
     received->binding.command_id!="verified-command" || rclcpp::Time(received->stamp)!=certificate.checked_at ||
     received->observation_stamp_s!=observation)throw std::runtime_error("Published proof changed the source times/identity");
  manager.publication_lease_.reset();set_clock(*node,checked_clock.nanoseconds()+300000000LL);
#ifdef DIAGNOSTIC_CANDIDATE
  manager.planning_outcome_.begin();
#endif
  const bool stale_success=manager.reboundReplan(start,zero,zero,end,zero,true,false);
#ifdef DIAGNOSTIC_CANDIDATE
  manager.finishPlanningOutcome(stale_success);
#endif
  if(stale_success || manager.publication_check_.clear)throw std::runtime_error("Rejected solve retained a publishable proof");
  std::cout<<"V114_PUBLICATION_PROOF_PASS actual_final_check exact_trajectory original_check_and_map_times stale_solve_invalidates"<<std::endl;
  rclcpp::shutdown();
}
