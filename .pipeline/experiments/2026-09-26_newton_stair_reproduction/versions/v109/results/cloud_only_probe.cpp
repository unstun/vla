#include "../v84/recording.h"

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  const fs::path input=std::getenv("V109_INPUT"),output=std::getenv("V109_OUTPUT");
  const double rate=std::stod(std::getenv("V109_RATE"));
  std::ifstream listing(input/"scans.txt"),delays("/task/scan-delays.txt");
  std::vector<RecordedScan> scans;std::vector<int64_t> delivery;
  int index;int64_t stamp,later_stamp,delay;std::string body,sensor,cloud,later_body;
  while(listing>>index>>stamp>>body>>sensor>>cloud>>later_stamp>>later_body) {
    if(!(delays>>delay))throw std::runtime_error("Missing recorded sensor delivery delay");
    RecordedScan scan{index,stamp,std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/body)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sensor)),
      std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cloud,false))};
    scan.body->header.stamp=scan.sensor->header.stamp=scan.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    scans.push_back(scan);delivery.push_back(stamp+delay);
  }
  if(scans.size()!=20)throw std::runtime_error("Expected verified20-scan prefix");
  rclcpp::Node node("scan_planner_node");GridMap map;initialize_map(map,node,input);
  node.declare_parameter("grid_map.mapping_admission","nav2_observation_window");
  node.declare_parameter("grid_map.map_update_frequency",rate);
  node.declare_parameter("grid_map.observation_persistence",0.5);
  node.declare_parameter("grid_map.maximum_buffered_clouds",64);
  set_clock(node,scans.front().stamp);map.startAsyncMapping();auto context=map.async_mapping_;
  const auto begin=std::chrono::steady_clock::now();
  fs::create_directories(output);std::ofstream trace(output/"ages.jsonl");
  size_t sent=0,samples=0,stale=0;double maximum=0;
  const int64_t end=delivery.back()+150000000LL;
  while(true) {
    const auto elapsed=std::chrono::steady_clock::now()-begin;
    const int64_t now=scans.front().stamp+std::chrono::duration_cast<std::chrono::nanoseconds>(elapsed).count();
    if(now>end)break;
    set_clock(node,now);
    while(sent<scans.size() && now>=delivery[sent]) {
      const auto &s=scans[sent++];map.slidingMapFrameCallback(s.body);map.sensorPoseCallback(s.sensor);map.cloudCallback(s.cloud);
    }
    map.adoptMappingSnapshot();const double source=map.observationStamp();
    if(source>0) {
      const double age=node.now().seconds()-source;maximum=std::max(maximum,age);++samples;
      if(age>0.25)++stale;
      trace<<std::setprecision(17)<<"{\"now\":"<<node.now().seconds()<<",\"map_source\":"<<source<<",\"age\":"<<age<<"}\n";
    }
    if(context->failed)throw std::runtime_error(context->error);
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
  map.stopAsyncMapping(); // Drained well within the final150ms in both measured arms.
  const auto final=context->latest;
  if(final->applied_clouds!=20 || context->expired_clouds || context->replaced_clouds || context->capacity_drops)
    throw std::runtime_error("Replay lost source observations");
  std::ofstream result(output/"summary.json");
  result<<std::setprecision(17)<<"{\"update_hz\":"<<rate<<",\"applied\":"<<final->applied_clouds
    <<",\"max_sampled_map_age_s\":"<<maximum<<",\"samples\":"<<samples<<",\"stale_samples\":"<<stale
    <<",\"map_sha256\":\""<<map_digest(map)<<"\",\"physics\":false,\"source\":\"original20 scans and recorded sensor publication delays\"}\n";
  rclcpp::shutdown();
}
