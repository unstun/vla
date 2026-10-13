#include <plan_env/grid_map.h>
#include <rcl/time.h>
#include <openssl/sha.h>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include "map_meter.h"
namespace fs=std::filesystem;
#include "recorded_readers.h"
#include "map_digest.h"

struct Outcome {std::string digest;uint64_t reduced,maximum_queue;double batch_ms;};
int main(int argc,char **argv) {
  const fs::path input(std::getenv("V82_INPUT"));
  rclcpp::init(argc,argv);
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  if(!node->has_parameter("grid_map.drop_backlogged_lidar"))node->declare_parameter<bool>("grid_map.drop_backlogged_lidar",false);
  const auto clock=[&](int64_t ns) {
    auto handle=node->get_clock()->get_clock_handle();
    if(rcl_enable_ros_time_override(handle)!=RCL_RET_OK || rcl_set_ros_time_override(handle,ns)!=RCL_RET_OK)
      throw std::runtime_error("Clock override failed");
  };
  auto nav=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"navigation.f32",true));
  auto surface=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"surface.f32",true));
  auto physical=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"physical_floor.f32",true));
  nav->header.stamp=surface->header.stamp=physical->header.stamp=rclcpp::Time(1000000000LL,RCL_ROS_TIME);
  const auto run=[&](bool enabled,const std::string &test,int frames,int seed,int initial_generation) {
    clock(1000000000);
    node->set_parameter(rclcpp::Parameter("grid_map.drop_backlogged_lidar",enabled));
    GridMap map;map.initMap(node.get());map.occ_timer_->cancel();map.vis_timer_->cancel();
    map.reactiveTomogramCallback(nav);map.reactiveSurfaceGroundCallback(surface);map.reactivePhysicalFloorCallback(physical);
    map.mutableMapState().md_.raycast_num_=static_cast<char>(initial_generation);
    map.startAsyncMapping();
    auto pose=std::make_shared<nav_msgs::msg::Odometry>();pose->header.frame_id="world";
    pose->pose.pose.position.z=.6;pose->pose.pose.orientation.w=1.0;
    auto cloud=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"cloud_00000.f32",false));
    cloud->width=1;cloud->height=1;cloud->row_step=12;cloud->data.resize(12);
    const float xyz[]={.8f,0,2.0f};std::memcpy(cloud->data.data(),xyz,sizeof(xyz));
    int64_t stamp=10000000000LL;
    const auto wait=[&](int64_t target) {
      const auto limit=std::chrono::steady_clock::now()+std::chrono::seconds(5);
      while(true) {
        map.adoptMappingSnapshot();
        if(!map.mapperHealthy())throw std::runtime_error("Backlog test mapper failed");
        if(std::abs(map.mapState().reactive_cloud_stamp_s_-double(target)*1e-9)<1e-8)break;
        if(std::chrono::steady_clock::now()>limit)throw std::runtime_error("Backlog snapshot not completed");
        std::this_thread::sleep_for(std::chrono::microseconds(200));
      }
    };
    for(int i=0;i<seed;++i) {
      clock(stamp);pose->header.stamp=cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
      map.slidingMapFrameCallback(std::make_shared<nav_msgs::msg::Odometry>(*pose));
      map.sensorPoseCallback(std::make_shared<nav_msgs::msg::Odometry>(*pose));
      map.cloudCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(*cloud));wait(stamp);stamp+=1000000;
    }
    const auto final_stamp=stamp+(frames-1)*1000000LL;
    clock(final_stamp);
    auto final_body=std::make_shared<nav_msgs::msg::Odometry>(*pose);
    final_body->header.stamp=rclcpp::Time(final_stamp,RCL_ROS_TIME);
    map.slidingMapFrameCallback(final_body);
    std::vector<GridMap::MappingInput> batch;
    int64_t missing_stamp=0;
    for(int i=0;i<frames;++i) {
      const auto ns=stamp+i*1000000LL;
      auto body=std::make_shared<nav_msgs::msg::Odometry>(*pose);
      auto sensor=std::make_shared<nav_msgs::msg::Odometry>(*pose);
      auto frame=std::make_shared<sensor_msgs::msg::PointCloud2>(*cloud);
      body->header.stamp=sensor->header.stamp=frame->header.stamp=rclcpp::Time(ns,RCL_ROS_TIME);
      if(test=="changed_pose")sensor->pose.pose.position.x=.001;
      if(test=="changed_body")body->pose.pose.position.x=.001;
      if(test=="changed_obstacle" && i==frames-1) {
        const float changed[]={1.8f,0,2.0f};std::memcpy(frame->data.data(),changed,sizeof(changed));
      }
      batch.push_back({2,ns,body,nullptr});
      if(test!="unpaired" || i!=frames-1)batch.push_back({0,ns,sensor,nullptr});
      else missing_stamp=ns;
      if(test=="support_change" && i==0)batch.push_back({5,ns,nullptr,physical});
      batch.push_back({1,ns,nullptr,frame});
    }
    const auto began=std::chrono::steady_clock::now();
    {
      std::lock_guard<std::mutex> lock(map.async_mapping_->queue_mutex);
      for(auto &packet:batch)map.async_mapping_->queue.push_back(std::move(packet));
    }
    map.async_mapping_->wake.notify_one();
    if(missing_stamp) {
      std::this_thread::sleep_for(std::chrono::milliseconds(50));
      auto exact=std::make_shared<nav_msgs::msg::Odometry>(*pose);exact->header.stamp=rclcpp::Time(missing_stamp,RCL_ROS_TIME);
      map.sensorPoseCallback(exact);
    }
    wait(final_stamp);
    const auto elapsed=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-began).count();
    auto snapshot=map.async_mapping_->latest;
    std::ostringstream metadata;
    metadata<<std::setprecision(17)<<map.mapState().reactive_cloud_stamp_s_<<":"<<map.mapState().reactive_cloud_ready_;
    Outcome result{map_digest(map)+metadata.str(),snapshot->reduced_clouds,snapshot->maximum_queued_clouds,elapsed};
    map.stopAsyncMapping();
    return result;
  };
  int checks=0;
  for(const auto &test:std::vector<std::string>{"single","duplicate","unsaturated","changed_pose","changed_body","changed_obstacle","support_change","unpaired","ray_wrap","full_generation"}) {
    const int frames=test=="single"?1:(test=="full_generation"?256:4);
    const int seed=test=="unsaturated"?1:8;
    const int generation=test=="ray_wrap"?125:0;
    const auto before=run(false,test,frames,seed,generation);
    const auto after=run(true,test,frames,seed,generation);
    if(before.digest!=after.digest)throw std::runtime_error("Map/history/metadata mismatch: "+test);
    ++checks;
    const auto expected=(test=="duplicate" || test=="ray_wrap")?uint64_t(frames-1):0;
    if(after.reduced!=expected)throw std::runtime_error("Unexpected frame reduction: "+test+" got="+std::to_string(after.reduced));
    ++checks;
    std::cout<<"V82_BACKLOG_CHECK test="<<test<<" reduced="<<after.reduced<<" max_queue="<<after.maximum_queue
      <<" baseline_ms="<<before.batch_ms<<" candidate_ms="<<after.batch_ms<<" PASS"<<std::endl;
  }
  std::cout<<"V82_BACKLOG_CONTRACT_PASS checks="<<checks<<std::endl;
  rclcpp::shutdown();
}
