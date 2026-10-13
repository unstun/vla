#include "../v84/recording.h"
#include <plan_manage/scan_replan_fsm.h>
#include <tf2/utils.h>
#include <scan_planner_msgs/msg/p2_b_execution_safety.hpp>

int main(int argc,char **argv)
{
  rclcpp::init(argc,argv);
  const fs::path input=std::getenv("V87_INPUT");
  const auto scans=read_scans(input);
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  set_clock(*node,1000000000LL);
  scan_planner::SCANReplanFSM fsm; fsm.init(node.get());
  fsm.exec_timer_->cancel(); fsm.safety_timer_->cancel();
  auto &map=*fsm.planner_manager_->grid_map_;
  map.occ_timer_->cancel(); map.vis_timer_->cancel();
  if(map.async_mapping_) throw std::runtime_error("Producer fixture requires synchronous input application");
  for(const auto &entry:std::vector<std::pair<std::string,int>>{
      {"navigation.f32",0},{"surface.f32",1},{"physical_floor.f32",2}}) {
    auto message=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/entry.first,true));
    message->header.stamp=rclcpp::Time(1000000000LL,RCL_ROS_TIME);
    if(entry.second==0) map.reactiveTomogramCallback(message);
    if(entry.second==1) map.reactiveSurfaceGroundCallback(message);
    if(entry.second==2) map.reactivePhysicalFloorCallback(message);
  }
  Eigen::Vector3d center;
  bool found=false;
  RecordedScan chosen=scans.front();
  for(const auto &scan:scans) {
    apply_scan(map,*node,scan); fsm.odometryCallback(scan.body);
    const auto &p=scan.body->pose.pose.position; center=Eigen::Vector3d(p.x,p.y,p.z);
    if(map.getInflateOccupancy(center,tf2::getYaw(scan.body->pose.pose.orientation))==0) {
      found=true; chosen=scan; break;
    }
  }
  if(!found) throw std::runtime_error("No recorded measured-body position passed the native collision entry");
  auto receiver=std::make_shared<rclcpp::Node>("native_safety_receiver");
  scan_planner_msgs::msg::P2BExecutionSafety::ConstSharedPtr received;
  auto subscription=receiver->create_subscription<scan_planner_msgs::msg::P2BExecutionSafety>(
    "/planning/execution_safety",10,
    [&](scan_planner_msgs::msg::P2BExecutionSafety::ConstSharedPtr message) { received=message; });
  const auto wait=[&](const std::function<bool()> &condition) {
    const auto until=std::chrono::steady_clock::now()+std::chrono::seconds(2);
    while(std::chrono::steady_clock::now()<until) {
      rclcpp::spin_some(receiver);
      if(condition()) return;
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    throw std::runtime_error("Native safety message timed out");
  };
  wait([&] { return fsm.nav2_safety_pub_->get_subscription_count()>0; });
  fsm.have_p2b_identity_=true;
  fsm.active_p2b_identity_={"native_producer",1,"request","goal","route","command",1,"map",1};
  fsm.exec_state_=scan_planner::SCANReplanFSM::EXEC_TRAJ;
  auto &trajectory=fsm.planner_manager_->local_data_;
  Eigen::MatrixXd points(3,4);
  for(int i=0;i<4;++i) points.col(i)=center;
  trajectory.position_traj_=scan_planner::UniformBspline(points,3,1.0);
  trajectory.velocity_traj_=trajectory.position_traj_.getDerivative();
  trajectory.acceleration_traj_=trajectory.velocity_traj_.getDerivative();
  trajectory.start_time_=node->now(); trajectory.duration_=trajectory.position_traj_.getTimeSum();
  trajectory.traj_id_=23;
  fsm.checkCollisionCallback();
  wait([&] { return bool(received); });
  if(!received->clear || received->binding.traj_id!=23 || received->binding.command_id!="command" ||
      received->binding.consumer!="native_safety" || received->binding.map_revision!=1 ||
      std::abs(received->observation_stamp_s-chosen.stamp*1e-9)>1e-8)
    throw std::runtime_error("Native full-curve clear evidence or identity/stamp mismatch");
  received.reset();
  trajectory.start_time_=node->now()+rclcpp::Duration::from_seconds(1.0);
  fsm.checkCollisionCallback();
  wait([&] { return bool(received); });
  if(received->clear) throw std::runtime_error("Future native trajectory incorrectly received a safety grant");
  std::cout<<"V87_NATIVE_SAFETY {\"passed\":true,\"fixture\":\"constant curve at a recorded native-clear body pose\","
    <<"\"clear_identity_and_original_stamp\":true,\"future_curve_rejected\":true,\"commands\":0}"<<std::endl;
  rclcpp::shutdown();
}
