// Actual DDS queue -> unchanged input drain/callbacks -> prefix collision predicate.
#include <plan_manage/scan_replan_fsm.h>
#include <rcl/time.h>
#include <rclcpp/serialization.hpp>
#include <fstream>
#include <cstring>
#include <thread>
#include <iostream>
using namespace scan_planner;
template<class T> T decode(const std::vector<char>&bytes) {
 rclcpp::SerializedMessage data(bytes.size());auto &r=data.get_rcl_serialized_message();std::memcpy(r.buffer,bytes.data(),bytes.size());r.buffer_length=bytes.size();T m;rclcpp::Serialization<T>().deserialize_message(&data,&m);return m;
}
sensor_msgs::msg::PointCloud2 ground(const char *path) {
 std::ifstream f(path,std::ios::binary);sensor_msgs::msg::PointCloud2 m;m.data=std::vector<uint8_t>(std::istreambuf_iterator<char>(f),{});if(m.data.empty())throw std::runtime_error("ground missing");m.header.frame_id="world";m.header.stamp.sec=1;m.point_step=16;m.height=1;m.width=m.data.size()/16;m.row_step=m.data.size();
 for(int i=0;i<4;++i){sensor_msgs::msg::PointField p;p.name=std::vector<std::string>{"x","y","z","intensity"}[i];p.offset=4*i;p.datatype=p.FLOAT32;p.count=1;m.fields.push_back(p);}return m;
}
template<class T> auto recovery(T &fsm,const Eigen::Vector3d &p,double yaw,int)->decltype(fsm.recoveryTargetOccupancy(p,yaw)){return fsm.recoveryTargetOccupancy(p,yaw);}
template<class T> int recovery(T &fsm,const Eigen::Vector3d &p,double yaw,long){return fsm.planner_manager_->grid_map_->getInflateOccupancy(p,yaw);}
int main(int argc,char **argv) {
 rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");SCANReplanFSM fsm;fsm.init(node.get());fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();auto map=fsm.planner_manager_->grid_map_;map->occ_timer_->cancel();map->vis_timer_->cancel();
 auto clock=[&](int64_t ns){auto *h=node->get_clock()->get_clock_handle();if(rcl_enable_ros_time_override(h)!=RCL_RET_OK||rcl_set_ros_time_override(h,ns)!=RCL_RET_OK)throw std::runtime_error("clock");};clock(1000000000);
 map->reactiveTomogramCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/versions/v36/tests/attempt09/v33_stand/converted_inputs/ground.f32")));
 map->reactiveSurfaceGroundCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32")));
 nav_msgs::msg::Odometry body,sensor;sensor_msgs::msg::PointCloud2 cloud;std::ifstream stream("/archive/audits/2026-10-02_v52_corner_43s/attempt05/replay/events.bin",std::ios::binary);
 while(true){uint8_t type;int64_t ns;uint32_t size;if(!stream.read(reinterpret_cast<char*>(&type),1))throw std::runtime_error("missing marker");stream.read(reinterpret_cast<char*>(&ns),8);stream.read(reinterpret_cast<char*>(&size),4);std::vector<char> bytes(size);stream.read(bytes.data(),size);clock(ns);
  if(type==0){body=decode<nav_msgs::msg::Odometry>(bytes);auto p=std::make_shared<nav_msgs::msg::Odometry>(body);map->slidingMapFrameCallback(p);fsm.odometryCallback(p);}
  else if(type==1){sensor=decode<nav_msgs::msg::Odometry>(bytes);map->sensorPoseCallback(std::make_shared<nav_msgs::msg::Odometry>(sensor));}
  else if(type==2){cloud=decode<sensor_msgs::msg::PointCloud2>(bytes);map->cloudCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(cloud));}
  else if(type==3)fsm.p2bRouteCallback(std::make_shared<scan_planner_msgs::msg::P2BRoute>(decode<scan_planner_msgs::msg::P2BRoute>(bytes)));
  else if(type==5){uint32_t id;std::memcpy(&id,bytes.data(),4);if(id==3)break;}
 }
 int checks=0;auto check=[&](bool ok,const char *name){if(!ok)throw std::runtime_error(name);std::cout<<"V54_FRESHNESS_CHECK "<<name<<" PASS"<<std::endl;++checks;};
 clock(42578227997LL);auto target=fsm.planner_manager_->global_data_.getPosition(.875);
 fsm.start_pt_=Eigen::Vector3d(7.250016972066203,-4.3335893190743935,1.8554786405589827);
 fsm.start_vel_=Eigen::Vector3d(.5034277877043865,.0953803380132511,-.0033831344807125937);
 fsm.start_acc_=Eigen::Vector3d(-.4657690875621696,.24832199879925335,.018786398748487337);
 const auto pva_p=fsm.start_pt_,pva_v=fsm.start_vel_,pva_a=fsm.start_acc_;const double yaw=std::atan2(target.y()-pva_p.y(),target.x()-pva_p.x());
 check(map->reactive_parameters_.obstacle_max_age_s==.25,"original_cloud_limit");
 check(map->getInflateOccupancy(target,yaw)!=0,"stale_before_queued_recovery");
 auto pubnode=std::make_shared<rclcpp::Node>("v54_queued_input_fixture");
 auto bp=pubnode->create_publisher<nav_msgs::msg::Odometry>(fsm.odom_sub_->get_topic_name(),100);
 auto sp=pubnode->create_publisher<nav_msgs::msg::Odometry>(map->lidar_pose_sub_->get_topic_name(),rclcpp::SensorDataQoS());
 auto cp=pubnode->create_publisher<sensor_msgs::msg::PointCloud2>(map->cloud_sub_->get_topic_name(),rclcpp::SensorDataQoS());
 for(int i=0;i<100 && (bp->get_subscription_count()<2||sp->get_subscription_count()<1||cp->get_subscription_count()<1);++i)std::this_thread::sleep_for(std::chrono::milliseconds(10));
 check(bp->get_subscription_count()>=2 && sp->get_subscription_count()>=1 && cp->get_subscription_count()>=1,"real_dds_subscriptions_discovered");
 // Controlled fixture stamp changes, with unchanged recorded geometry; this is not a live-history reconstruction.
 auto queue=[&](int64_t ns){body.header.stamp=sensor.header.stamp=cloud.header.stamp=rclcpp::Time(ns,RCL_ROS_TIME);bp->publish(body);sp->publish(sensor);cp->publish(cloud);std::this_thread::sleep_for(std::chrono::milliseconds(50));};
 queue(42578227997LL);
 const int result=recovery(fsm,target,yaw,0);
 std::cout<<"V54_QUEUED_RESULT occupied="<<result<<" cloud_age="<<node->now().seconds()-map->reactive_cloud_stamp_s_<<std::endl;
 if(std::getenv("V54_PARENT_RED")){check(result!=0 && node->now().seconds()-map->reactive_cloud_stamp_s_>.25,"parent_skips_queued_input_and_rejects");std::cout<<"V54_PARENT_RED_REPRODUCED"<<std::endl;rclcpp::shutdown();return 0;}
 check(result==0 && node->now().seconds()-map->reactive_cloud_stamp_s_<1e-9,"queued_fresh_cloud_admitted_after_actual_boundary");
 check((fsm.start_pt_.array()==pva_p.array()).all()&&(fsm.start_vel_.array()==pva_v.array()).all()&&(fsm.start_acc_.array()==pva_a.array()).all(),"drain_preserves_start_pva");
 clock(42900000000LL);check(recovery(fsm,target,yaw,0)!=0,"no_new_input_keeps_stale_rejection");
 queue(42500000000LL);check(recovery(fsm,target,yaw,0)!=0,"old_queued_input_stays_stale");
 queue(43100000000LL);check(recovery(fsm,target,yaw,0)!=0,"future_input_rejected");
 queue(42900000000LL);check(recovery(fsm,target,yaw,0)==0,"new_current_input_recovers_without_threshold_change");
 std::cout<<"V54_FRESHNESS_PASSED checks="<<checks<<std::endl;rclcpp::shutdown();
}
