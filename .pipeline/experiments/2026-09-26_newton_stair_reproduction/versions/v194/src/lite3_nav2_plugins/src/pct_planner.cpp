#include <cmath>
#include <nav2_core/global_planner.hpp>
#include <nav2_core/exceptions.hpp>
#include <lite3_nav2_interfaces/srv/plan_route.hpp>
#include <pluginlib/class_list_macros.hpp>

namespace lite3_nav2 {
class PCTPlanner : public nav2_core::GlobalPlanner {
  using Service = lite3_nav2_interfaces::srv::PlanRoute;
  rclcpp::Node::SharedPtr node_;
  rclcpp::Client<Service>::SharedPtr client_;
  rclcpp::executors::SingleThreadedExecutor executor_;
  std::string frame_;
  bool active_{false};
public:
  void configure(rclcpp_lifecycle::LifecycleNode::SharedPtr parent, std::string name,
    std::shared_ptr<tf2_ros::Buffer>, std::shared_ptr<nav2_costmap_2d::Costmap2DROS> map) override {
    frame_ = map->getGlobalFrameID();
    const auto key = name + ".service";
    if (!parent->has_parameter(key)) parent->declare_parameter(key, "/lite3_nav2/plan_route");
    rclcpp::NodeOptions options;
    options.use_global_arguments(false);
    options.parameter_overrides({rclcpp::Parameter("use_sim_time", parent->get_parameter("use_sim_time").as_bool())});
    node_ = std::make_shared<rclcpp::Node>("pct_nav2_planner_client", options);
    client_ = node_->create_client<Service>(parent->get_parameter(key).as_string());
    executor_.add_node(node_);
  }
  void activate() override { active_ = true; }
  void deactivate() override { active_ = false; }
  void cleanup() override {
    active_ = false;
    if (node_) executor_.remove_node(node_);
    client_.reset(); node_.reset();
  }
  nav_msgs::msg::Path createPlan(const geometry_msgs::msg::PoseStamped &start,
    const geometry_msgs::msg::PoseStamped &goal) override {
    if (!active_ || start.header.frame_id != frame_ || goal.header.frame_id != frame_)
      throw nav2_core::PlannerException("Inactive PCT planner or frame mismatch");
    if (!client_->wait_for_service(std::chrono::milliseconds(200)))
      throw nav2_core::PlannerException("PCT mission service unavailable");
    auto request = std::make_shared<Service::Request>();
    request->start = start; request->goal = goal;
    auto future = client_->async_send_request(request);
    if (executor_.spin_until_future_complete(future, std::chrono::seconds(6)) != rclcpp::FutureReturnCode::SUCCESS)
      throw nav2_core::PlannerException("PCT mission service timeout");
    const auto response = future.get();
    const auto &path = response->path;
    if (!response->accepted || path.header.frame_id != frame_ || path.poses.size() < 2)
      throw nav2_core::PlannerException("PCT rejected route: " + response->message);
    for (const auto &p : path.poses) {
      const auto &q = p.pose.orientation;
      const double norm = q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w;
      if (p.header.frame_id != frame_ || !std::isfinite(p.pose.position.x) ||
          !std::isfinite(p.pose.position.y) || !std::isfinite(p.pose.position.z) ||
          !std::isfinite(norm) || std::abs(norm-1.0)>1e-6)
        throw nav2_core::PlannerException("Invalid native PCT pose");
    }
    return path;
  }
};
}
PLUGINLIB_EXPORT_CLASS(lite3_nav2::PCTPlanner, nav2_core::GlobalPlanner)
