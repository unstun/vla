#include "../v84/recording.h"
#include <atomic>

int main(int argc,char **argv)
{
  rclcpp::init(argc,argv);
  const fs::path input=std::getenv("V91_INPUT"),output=std::getenv("V91_OUTPUT");
  const std::string mode=std::getenv("V91_MODE");
  if(mode!="fifo" && mode!="latest" && mode!="window") throw std::runtime_error("Unknown arm");
  const int stall_ms=std::getenv("V91_STALL_MS") ? std::stoi(std::getenv("V91_STALL_MS")) : 0;
  const double update_hz=std::getenv("V91_UPDATE_HZ") ? std::stod(std::getenv("V91_UPDATE_HZ")) : 5.0;
  if (stall_ms<0 || stall_ms>2000 || !std::isfinite(update_hz) || update_hz<=0 || update_hz>100)
    throw std::runtime_error("Invalid replay parameters");
  auto scans=read_scans(input);
  rclcpp::Node node("scan_planner_node");
  GridMap map; initialize_map(map,node,input);
  node.declare_parameter("grid_map.mapping_admission",mode=="fifo" ? "fifo" : "nav2_observation_window");
  node.declare_parameter("grid_map.map_update_frequency",update_hz);
  node.declare_parameter("grid_map.observation_persistence",mode=="latest" ? 0.0 : 0.5);
  node.declare_parameter("grid_map.maximum_buffered_clouds",64);
  map.startAsyncMapping();
  auto context=map.async_mapping_;
  fs::create_directories(output);
  std::ofstream trace(output/"ingress.jsonl");
  std::vector<std::thread> stalls;
  double max_ingress_ms=0.0, max_observed_age_s=0.0;
  uint64_t stale_observations=0, unavailable_snapshots=0;
  std::shared_ptr<const GridMap::MappingSnapshot> observed;
  uint64_t max_buffered_clouds=0;
  for(const auto &scan:scans) {
    if(stall_ms>0 && (scan.index==60 || scan.index==120)) {
      auto acquired=std::make_shared<std::atomic<bool>>(false);
      stalls.emplace_back([context,acquired,stall_ms] {
        std::unique_lock<std::mutex> lease(context->publication_mutex);
        *acquired=true;
        std::this_thread::sleep_for(std::chrono::milliseconds(stall_ms));
      });
      while(!*acquired) std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    const auto start=std::chrono::steady_clock::now();
    set_clock(node,scan.stamp);
    map.slidingMapFrameCallback(scan.body); map.sensorPoseCallback(scan.sensor); map.cloudCallback(scan.cloud);
    const double elapsed=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
    max_ingress_ms=std::max(max_ingress_ms,elapsed);
    uint64_t buffered=0;
    {
      std::lock_guard<std::mutex> lock(context->queue_mutex);
      for(const auto &pending:context->queue) if(pending.kind==1) ++buffered;
    }
    max_buffered_clouds=std::max(max_buffered_clouds,buffered);
    bool snapshot_available=false;
    {
      std::unique_lock<std::mutex> lock(context->publication_mutex,std::try_to_lock);
      snapshot_available=lock.owns_lock();
      if (snapshot_available) observed=context->latest;
      else ++unavailable_snapshots;
    }
    double observed_age_s=-1.0;
    if (observed && observed->state->reactive_cloud_stamp_s_>0) {
      observed_age_s=scan.stamp*1e-9-observed->state->reactive_cloud_stamp_s_;
      max_observed_age_s=std::max(max_observed_age_s,observed_age_s);
      if (observed_age_s>0.25) ++stale_observations;
    }
    trace<<"{\"index\":"<<scan.index<<",\"stamp_ns\":"<<scan.stamp
         <<",\"ingress_ms\":"<<elapsed<<",\"pending_clouds\":"<<buffered
         <<",\"observed_map_age_s\":"<<observed_age_s<<",\"snapshot_available\":"<<(snapshot_available ? "true" : "false")<<"}\n";
    if(context->failed) throw std::runtime_error("Native map worker failed");
    std::this_thread::sleep_until(start+std::chrono::milliseconds(100));
  }
  for(auto &stall:stalls) stall.join();
  const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(30);
  std::shared_ptr<const GridMap::MappingSnapshot> final;
  while(std::chrono::steady_clock::now()<deadline) {
    {
      std::lock_guard<std::mutex> lock(context->publication_mutex);
      final=context->latest;
    }
    const uint64_t dropped=context->expired_clouds+context->replaced_clouds+context->capacity_drops;
    if(final && final->applied_clouds+dropped==scans.size()) break;
    if(context->failed) throw std::runtime_error("Map failed while draining");
    std::this_thread::sleep_for(std::chrono::milliseconds(20));
  }
  const uint64_t expired=context->expired_clouds,replaced=context->replaced_clouds,capacity=context->capacity_drops;
  if(!final || final->applied_clouds+expired+replaced+capacity!=188) throw std::runtime_error("Incomplete observation accounting");
  map.adoptMappingSnapshot();
  const std::string digest=map_digest(map);
  const auto &state=map.mapState();
  std::ofstream occupancy(output/"occupancy.bin",std::ios::binary);
  occupancy.write(reinterpret_cast<const char *>(state.md_.occupancy_buffer_.data()),
                  state.md_.occupancy_buffer_.size()*sizeof(state.md_.occupancy_buffer_[0]));
  occupancy.close();
  std::ofstream summary(output/"summary.json");
  summary<<std::setprecision(17)<<"{\"mode\":\""<<mode<<"\",\"input_frames\":188,\"applied_frames\":"<<final->applied_clouds
    <<",\"expired\":"<<expired<<",\"replaced\":"<<replaced<<",\"capacity_drops\":"<<capacity
    <<",\"max_ingress_ms\":"<<max_ingress_ms<<",\"max_buffered_clouds\":"<<max_buffered_clouds
    <<",\"final_source_stamp_s\":"<<state.reactive_cloud_stamp_s_
    <<",\"observer_max_map_age_s\":"<<max_observed_age_s<<",\"observer_stale_samples\":"<<stale_observations
    <<",\"observer_snapshot_unavailable\":"<<unavailable_snapshots
    <<",\"occupancy_threshold\":"<<state.mp_.min_occupancy_log_
    <<",\"map_sha256\":\""<<digest<<"\",\"injected_stall_ms\":"<<stall_ms
    <<",\"map_update_hz\":"<<update_hz<<",\"physics\":false,\"robot_commands\":0}\n";
  map.stopAsyncMapping();
  std::cout<<"V91_NATIVE_REPLAY_DONE "<<mode<<" applied="<<final->applied_clouds<<std::endl;
  rclcpp::shutdown();
}
