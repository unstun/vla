// Existing initial Foxy port of upstream occupancy mapping, without local gates.
#include <plan_env/grid_map.h>
#include <rcl/time.h>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
namespace fs=std::filesystem;
#include "v81/recorded_readers.h"

void clock_at(rclcpp::Node &node,int64_t stamp) {
  auto h=node.get_clock()->get_clock_handle();
  if(rcl_enable_ros_time_override(h)!=RCL_RET_OK||rcl_set_ros_time_override(h,stamp)!=RCL_RET_OK)throw std::runtime_error("Clock error");
}
struct Scan {int64_t stamp;std::string body,sensor,cloud;};
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  if(std::getenv("AUTHOR_GEOMETRY")) {
    for(const auto &v:std::vector<std::pair<std::string,double>>{{"grid_map.double_cylinder_radius",.25},{"grid_map.obstacles_inflation_z_up",.1},{"grid_map.obstacles_inflation_z_down",.1}}) {
      node->declare_parameter<double>(v.first,v.second);node->set_parameter(rclcpp::Parameter(v.first,v.second));
    }
  }
  clock_at(*node,1000000000LL);GridMap map;map.initMap(node.get());map.occ_timer_->cancel();map.vis_timer_->cancel();
  const fs::path input=std::getenv("REPLAY_INPUT"),output=std::getenv("REPLAY_OUTPUT");fs::create_directories(output);
  std::ifstream list(input/"scans.txt");int id;Scan s;std::vector<Scan> scans;
  while(list>>id>>s.stamp>>s.body>>s.sensor>>s.cloud)scans.push_back(s);
  std::ifstream frames(input/"frames.txt");int frame;int64_t query_ns,body_ns,cutoff;std::string bodyfile,queryfile;size_t applied=0;
  while(frames>>frame>>query_ns>>body_ns>>cutoff>>bodyfile>>queryfile) {
    while(applied<scans.size()&&scans[applied].stamp<=cutoff) {
      const auto &s=scans[applied];clock_at(*node,s.stamp);
      auto body=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/s.body));
      auto sensor=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/s.sensor));
      auto cloud=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/s.cloud,false));
      body->header.stamp=sensor->header.stamp=cloud->header.stamp=rclcpp::Time(s.stamp,RCL_ROS_TIME);
      map.slidingMapFrameCallback(body);map.sensorPoseCallback(sensor);map.cloudCallback(cloud);map.updateOccupancyCallback();++applied;
    }
    if(!applied||scans[applied-1].stamp!=cutoff)throw std::runtime_error("Prefix differs");
    clock_at(*node,query_ns);auto body=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/bodyfile));body->header.stamp=rclcpp::Time(body_ns,RCL_ROS_TIME);map.slidingMapFrameCallback(body);
    std::ifstream points(input/queryfile);std::ofstream csv(output/("frame_"+std::to_string(frame)+".csv"));csv<<"id,kind,x,y,z,yaw,blocked\n"<<std::setprecision(17);
    int id,kind;double x,y,z,yaw;int count=0,blocked=0;
    while(points>>id>>kind>>x>>y>>z>>yaw) {
      int result=map.getInflateOccupancy(Eigen::Vector3d(x,y,z),yaw);
      csv<<id<<','<<kind<<','<<x<<','<<y<<','<<z<<','<<yaw<<','<<result<<'\n';++count;blocked+=result!=0;
    }
    std::cout<<"ORIGINAL_FRAME "<<frame<<" scans="<<applied<<" queries="<<count<<" blocked="<<blocked<<std::endl;
  }
  rclcpp::shutdown();return 0;
}
