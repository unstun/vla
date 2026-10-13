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
 if(fsm.planner_manager_->local_data_.traj_id_!=0 || fsm.canPreserveReferenceBinding()) throw std::runtime_error("uninitialized source became eligible");
 std::cout << "V54_CLOCK_GUARD_PRETRAJECTORY_PASSED" << std::endl;rclcpp::shutdown();
}
