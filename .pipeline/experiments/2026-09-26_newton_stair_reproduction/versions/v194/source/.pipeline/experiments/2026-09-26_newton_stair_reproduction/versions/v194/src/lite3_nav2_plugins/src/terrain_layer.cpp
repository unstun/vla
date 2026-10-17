#include <cmath>
#include <mutex>
#include <nav2_costmap_2d/costmap_layer.hpp>
#include <nav_msgs/msg/occupancy_grid.hpp>
#include <pluginlib/class_list_macros.hpp>

namespace lite3_nav2 {
class TerrainLayer : public nav2_costmap_2d::CostmapLayer {
  std::mutex mutex_;
  nav_msgs::msg::OccupancyGrid::ConstSharedPtr latest_;
  rclcpp::Subscription<nav_msgs::msg::OccupancyGrid>::SharedPtr subscription_;
  std::string frame_, base_;
  bool fresh(const nav_msgs::msg::OccupancyGrid &grid) const {
    const auto age = (node_->now() - rclcpp::Time(grid.header.stamp)).seconds();
    return grid.header.stamp.sec >= 0 && age >= 0.0 && age <= 0.25;
  }
public:
  void onInitialize() override {
    frame_ = layered_costmap_->getGlobalFrameID();
    declareParameter("topic", rclcpp::ParameterValue("/nav2_scan/terrain_slice"));
    declareParameter("base_frame", rclcpp::ParameterValue("base_link"));
    base_ = node_->get_parameter(name_ + ".base_frame").as_string();
    subscription_ = node_->create_subscription<nav_msgs::msg::OccupancyGrid>(
      node_->get_parameter(name_ + ".topic").as_string(), rclcpp::QoS(1),
      [this](nav_msgs::msg::OccupancyGrid::ConstSharedPtr grid) {
        const auto &info = grid->info;
        const auto &q = info.origin.orientation;
        const uint64_t cells = uint64_t(info.width) * info.height;
        if (grid->header.frame_id != frame_ || cells == 0 || cells > 1000000 ||
            cells != grid->data.size() || !std::isfinite(info.resolution) || info.resolution <= 0 ||
            !std::isfinite(info.origin.position.x) || !std::isfinite(info.origin.position.y) ||
            !std::isfinite(info.origin.position.z) || q.x != 0 || q.y != 0 || q.z != 0 || q.w != 1 ||
            !fresh(*grid)) return;
        for (const auto value : grid->data) if (value < -1 || value > 100) return;
        std::lock_guard<std::mutex> lock(mutex_);
        if (latest_ && rclcpp::Time(grid->header.stamp) <= rclcpp::Time(latest_->header.stamp)) return;
        latest_ = grid;
      });
    current_ = false;
    enabled_ = true;
  }
  void reset() override { current_ = false; } // Clear-costmap does not erase 3D evidence.
  void updateBounds(double x, double y, double, double *min_x, double *min_y,
    double *max_x, double *max_y) override {
    *min_x = std::min(*min_x, x - 3.0); *min_y = std::min(*min_y, y - 3.0);
    *max_x = std::max(*max_x, x + 3.0); *max_y = std::max(*max_y, y + 3.0);
    current_ = false;
    std::lock_guard<std::mutex> lock(mutex_);
    if (!latest_ || !fresh(*latest_)) return;
    try {
      const auto transform = tf_->lookupTransform(frame_, base_, tf2::TimePointZero);
      current_ = std::abs(transform.transform.translation.z - latest_->info.origin.position.z) <= 0.20;
    } catch (const tf2::TransformException &) { return; }
  }
  void updateCosts(nav2_costmap_2d::Costmap2D &master, int min_i, int min_j,
    int max_i, int max_j) override {
    nav_msgs::msg::OccupancyGrid::ConstSharedPtr grid;
    { std::lock_guard<std::mutex> lock(mutex_); grid = latest_; }
    if (!current_ || !grid || !fresh(*grid)) { current_ = false; return; }
    for (int y = min_j; y < max_j; ++y) for (int x = min_i; x < max_i; ++x) {
      double wx, wy; master.mapToWorld(x, y, wx, wy);
      const int gx = std::floor((wx - grid->info.origin.position.x) / grid->info.resolution);
      const int gy = std::floor((wy - grid->info.origin.position.y) / grid->info.resolution);
      if (gx < 0 || gy < 0 || gx >= int(grid->info.width) || gy >= int(grid->info.height)) continue;
      const int value = grid->data[gy * grid->info.width + gx];
      if (value < 0) continue;
      const unsigned char cost = value >= 50 ? nav2_costmap_2d::LETHAL_OBSTACLE : nav2_costmap_2d::FREE_SPACE;
      const auto previous = master.getCost(x, y);
      if (previous == nav2_costmap_2d::NO_INFORMATION || cost > previous) master.setCost(x, y, cost);
    }
  }
};
}
PLUGINLIB_EXPORT_CLASS(lite3_nav2::TerrainLayer, nav2_costmap_2d::Layer)
