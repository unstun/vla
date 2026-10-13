#include "recording.h"

// An explicit negative, not a claim that this obstacle occurred in the capture.
int main(int argc, char **argv) {
  try {
    const fs::path input(std::getenv("V84_INPUT"));
    const auto scans = read_scans(input);
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("scan_planner_node");
    GridMap reference, latest;
    initialize_map(reference, *node, input); initialize_map(latest, *node, input);
    const auto base = scans.front();
    auto point_scan = [&](int index, Eigen::Vector3d point) {
      RecordedScan s{index, base.stamp + index * 1000000LL,
        std::make_shared<nav_msgs::msg::Odometry>(*base.body),
        std::make_shared<nav_msgs::msg::Odometry>(*base.sensor),
        std::make_shared<sensor_msgs::msg::PointCloud2>(*base.cloud)};
      s.body->header.stamp = s.sensor->header.stamp = s.cloud->header.stamp = rclcpp::Time(s.stamp, RCL_ROS_TIME);
      s.cloud->width = s.cloud->height = 1; s.cloud->row_step = s.cloud->point_step;
      s.cloud->data.resize(s.cloud->point_step);
      const float xyz[] = {float(point.x()),float(point.y()),float(point.z())};
      std::memcpy(s.cloud->data.data(),xyz,sizeof(xyz)); return s;
    };
    set_clock(*node, base.stamp);
    reference.sensorPoseCallback(base.sensor);
    const Eigen::Vector3d local_obstacle(1.2,0,1.0), local_other(0,1.2,1.0);
    const Eigen::Vector3d world = reference.mapState().md_.ray_pos_ + reference.mapState().md_.ray_q_ * local_obstacle;
    if (reference.reactiveTerrainReturn(world)) throw std::runtime_error("Fixture point incorrectly on a classified terrain surface");
    Eigen::Vector3i id; reference.posToIndex(world,id);
    for(int i=1;i<=8;++i) apply_scan(reference,*node,point_scan(i,local_obstacle));
    const bool observed = reference.getOccupancy(world) == 1;
    const auto last = point_scan(9,local_other);
    apply_scan(reference,*node,last); apply_scan(latest,*node,last);
    const bool reference_retains = reference.getOccupancy(world) == 1;
    const bool latest_retains = latest.getOccupancy(world) == 1;
    if (!observed || !reference_retains || latest_retains)
      throw std::runtime_error("Native transient negative did not distinguish admission policies");
    std::cout << "V84_TRANSIENT_RESULT {\"offered\":9,\"fifo_processed\":9,\"latest_processed\":1,"
              << "\"fifo_obstacle_occupied\":true,\"latest_obstacle_occupied\":false,"
              << "\"synthetic_negative\":true,\"plain_latest_only_acceptable\":false}\n";
    rclcpp::shutdown(); return 0;
  } catch(const std::exception &e) {
    std::cerr << "V84_TRANSIENT_FAILED " << e.what() << '\n';
    if(rclcpp::ok()) rclcpp::shutdown(); return 1;
  }
}
