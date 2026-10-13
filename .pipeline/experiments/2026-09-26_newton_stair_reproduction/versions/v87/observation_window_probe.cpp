#include <plan_env/grid_map.h>
#include <plan_env/observation_window.h>
#include <nav2_costmap_2d/observation_buffer.hpp>
#include <nav2_util/lifecycle_node.hpp>
#include <rcl/time.h>
#include <tf2_ros/transform_listener.h>
#include <sensor_msgs/point_cloud2_iterator.hpp>
#include <algorithm>
#include <iostream>
#include <stdexcept>

static void require(bool condition,const std::string &message)
{
  if (!condition) throw std::runtime_error(message);
}
static void clockAt(rclcpp::Clock::SharedPtr clock,int64_t ns)
{
  require(rcl_enable_ros_time_override(clock->get_clock_handle())==RCL_RET_OK,"enable clock");
  require(rcl_set_ros_time_override(clock->get_clock_handle(),ns)==RCL_RET_OK,"set clock");
}
static sensor_msgs::msg::PointCloud2::SharedPtr cloudAt(int64_t ns,float marker)
{
  auto m=std::make_shared<sensor_msgs::msg::PointCloud2>();
  m->header.frame_id="world"; m->header.stamp=rclcpp::Time(ns,RCL_ROS_TIME);
  sensor_msgs::PointCloud2Modifier modifier(*m); modifier.setPointCloud2FieldsByString(1,"xyz"); modifier.resize(1);
  sensor_msgs::PointCloud2Iterator<float> x(*m,"x"),y(*m,"y"),z(*m,"z");
  *x=marker; *y=0; *z=0.5;
  return m;
}
int main(int argc,char **argv)
{
  rclcpp::init(argc,argv);
  auto original=std::make_shared<nav2_util::LifecycleNode>("nav2_buffer_oracle");
  auto adapted=std::make_shared<rclcpp::Node>("scan_buffer_probe");
  tf2_ros::Buffer tf(original->get_clock());
  tf2_ros::TransformListener listener(tf);
  int checks=0;
  for(double retention:{0.0,0.5}) {
    clockAt(original->get_clock(),1000000000LL); clockAt(adapted->get_clock(),1000000000LL);
    nav2_costmap_2d::ObservationBuffer buffer(original,"cloud",retention,0.1,-10,10,100,100,tf,"world","world",0.1);
    GridMap map;
    map.node_=adapted.get(); map.async_mapping_=std::make_shared<GridMap::AsyncMapping>();
    auto context=map.async_mapping_;
    context->nav2_window=true; context->observation_policy.persistence_s=retention;
    for(int i=0;i<13;++i) {
      const int64_t ns=1000000000LL+100000000LL*i;
      clockAt(original->get_clock(),ns); clockAt(adapted->get_clock(),ns);
      auto message=cloudAt(ns,static_cast<float>(i));
      buffer.bufferCloud(*message);
      map.enqueueMapping({1,ns,nullptr,message});
      std::vector<nav2_costmap_2d::Observation> expected;
      buffer.getObservations(expected);
      std::vector<int64_t> actual_stamps,expected_stamps;
      for(const auto &input:context->queue) if(input.kind==1) actual_stamps.push_back(input.stamp_ns);
      for(const auto &item:expected) expected_stamps.push_back(rclcpp::Time(item.cloud_->header.stamp).nanoseconds());
      std::sort(expected_stamps.begin(),expected_stamps.end());
      require(expected_stamps==actual_stamps,"Foxy ObservationBuffer admission mismatch"); ++checks;
      require(!context->failed,"Unexpected queue failure");
    }
    const size_t expected=retention==0 ? 1 : 6;
    require(context->queue.size()==expected,"Retention boundary count"); ++checks;
    if(retention==0) require(context->replaced_clouds==12,"Latest-only drop accounting");
    else require(context->expired_clouds==7,"Window expiry accounting");
    ++checks;
    const auto last=context->queue.back();
    map.enqueueMapping(last);
    require(context->failed,"Repeated source stamp must fail closed"); ++checks;
  }
  {
    GridMap map; map.node_=adapted.get(); map.async_mapping_=std::make_shared<GridMap::AsyncMapping>();
    auto context=map.async_mapping_; context->nav2_window=true;
    context->observation_policy.persistence_s=100; context->observation_policy.maximum_clouds=2;
    for(int i=0;i<10;++i) {
      const int64_t ns=1000000000LL+100000000LL*i;
      clockAt(adapted->get_clock(),ns); map.enqueueMapping({1,ns,nullptr,cloudAt(ns,i)});
    }
    require(context->queue.size()==2 && context->capacity_drops==8,"Hard capacity bound"); ++checks;
  }
  for(double hz:{0.0,-1.0,101.0}) {
    scan_observation_window::Policy policy; policy.update_hz=hz;
    bool rejected=false; try { policy.validate(); } catch(const std::invalid_argument &) { rejected=true; }
    require(rejected,"Invalid update rate accepted"); ++checks;
  }
  scan_observation_window::Policy p; p.persistence_s=-0.1;
  bool rejected=false; try { p.validate(); } catch(const std::invalid_argument &) { rejected=true; }
  require(rejected,"Negative persistence accepted"); ++checks;
  std::cout << "{\"passed\":true,\"checks\":" << checks
            << ",\"oracle\":\"actual Foxy ObservationBuffer\",\"robot_commands\":0}" << std::endl;
  rclcpp::shutdown();
}
