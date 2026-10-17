#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <nav2_core/global_planner.hpp>
#include <nav2_core/exceptions.hpp>
#include <pluginlib/class_list_macros.hpp>
#include <mutex>

namespace lite3_nav2
{
class PCTPlanner : public nav2_core::GlobalPlanner
{
  std::mutex mutex_;
  rclcpp_lifecycle::LifecycleNode::SharedPtr parent_;
  rclcpp_lifecycle::LifecyclePublisher<nav_msgs::msg::Path>::SharedPtr path_pub_;
  std::unique_ptr<PCTRoutePlanner> planner_;
  std::string frame_;
  bool active_{false};
  template<class T> T parameter(const std::string &name,const T &fallback) {
    if (!parent_->has_parameter(name)) parent_->declare_parameter<T>(name,fallback);
    return parent_->get_parameter(name).get_value<T>();
  }
  bool valid(const geometry_msgs::msg::PoseStamped &p) const {
    const auto &q=p.pose.orientation;
    const double norm=q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w;
    return p.header.frame_id==frame_ && std::isfinite(p.pose.position.x) &&
      std::isfinite(p.pose.position.y) && std::isfinite(p.pose.position.z) &&
      std::isfinite(norm) && std::abs(norm-1.0)<=1e-6;
  }
public:
  void configure(rclcpp_lifecycle::LifecycleNode::SharedPtr parent,std::string name,
      std::shared_ptr<tf2_ros::Buffer>,std::shared_ptr<nav2_costmap_2d::Costmap2DROS> map) override {
    std::lock_guard<std::mutex> lock(mutex_);
    parent_=parent;
    frame_=map ? map->getGlobalFrameID() : parameter(name+".global_frame",std::string("world"));
    const auto bundle=parameter(name+".map_bundle",std::string(""));
    planner_=std::make_unique<PCTRoutePlanner>(bundle,
      parameter(name+".reference_height",0.35),parameter(name+".use_quintic",true),
      parameter(name+".max_heading_rate",10.0));
    path_pub_=parent_->create_publisher<nav_msgs::msg::Path>("/pct_planned_path",10);
  }
  void activate() override {
    std::lock_guard<std::mutex> lock(mutex_);active_=true;path_pub_->on_activate();
  }
  void deactivate() override {
    std::lock_guard<std::mutex> lock(mutex_);active_=false;if(path_pub_) path_pub_->on_deactivate();
  }
  void cleanup() override {
    std::lock_guard<std::mutex> lock(mutex_);active_=false;
    planner_.reset();path_pub_.reset();parent_.reset();
  }
  nav_msgs::msg::Path createPlan(const geometry_msgs::msg::PoseStamped &start,
      const geometry_msgs::msg::PoseStamped &goal) override {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!active_ || !planner_ || !valid(start) || !valid(goal))
      throw nav2_core::PlannerException("Inactive PCT planner or invalid world pose");
    try {
      const auto xyz=[](const geometry_msgs::msg::PoseStamped &p) {
        return Eigen::Vector3d(p.pose.position.x,p.pose.position.y,p.pose.position.z);
      };
      const auto points=planner_->plan(xyz(start),xyz(goal));
      // Nav2 owns the requested target. A rejected request never replays a cache.
      if ((points[points.size()-2]-xyz(goal)).norm()>2.0)
        throw std::runtime_error("pct_goal_connector_disconnected");
      nav_msgs::msg::Path path;path.header.frame_id=frame_;path.header.stamp=parent_->now();
      double yaw=0.0;
      for(size_t i=0;i<points.size();++i) {
        if (i+1<points.size()) {
          const auto delta=points[i+1]-points[i];
          if (std::hypot(delta.x(),delta.y())>1e-12) yaw=std::atan2(delta.y(),delta.x());
        }
        geometry_msgs::msg::PoseStamped p;p.header=path.header;
        p.pose.position.x=points[i].x();p.pose.position.y=points[i].y();p.pose.position.z=points[i].z();
        p.pose.orientation.z=std::sin(yaw/2.0);p.pose.orientation.w=std::cos(yaw/2.0);
        path.poses.push_back(p);
      }
      path.poses.back().pose=goal.pose;
      path_pub_->publish(path);
      return path;
    } catch (const std::exception &error) {
      throw nav2_core::PlannerException(std::string("Native PCT: ")+error.what());
    }
  }
};
}  // namespace lite3_nav2
PLUGINLIB_EXPORT_CLASS(lite3_nav2::PCTPlanner, nav2_core::GlobalPlanner)
