#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <nav2_core/global_planner.hpp>
#include <nav2_core/exceptions.hpp>
#include <pluginlib/class_list_macros.hpp>
#include <mutex>
#include <atomic>
#include <lite3_nav2_plugins/blocked_feedback.hpp>
#include <lite3_nav2_plugins/shared_traversability.hpp>
#include <lite3_nav2_plugins/route_policy.hpp>
#include <lite3_nav2_interfaces/srv/route_session.hpp>
#include <nav_msgs/msg/odometry.hpp>

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
  RoutePolicy policy_;
  BlockedFeedback feedback_;
  std::atomic<uint64_t> session_epoch_{0};
  std::unique_ptr<SharedTraversability> traversability_;
  rclcpp::Service<lite3_nav2_interfaces::srv::RouteSession>::SharedPtr session_service_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr body_sub_;
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
    const auto environmental_path=parameter(name+".environmental_path",std::string(""));
    if(!environmental_path.empty()) planner_->setEnvironmentalField(
      std::make_shared<reactive_stair::EnvironmentalField>(environmental_path,
        parameter(name+".environmental_fnv64",std::string(""))));
    const auto support_path=parameter(name+".static_support_path",std::string(""));
    if(!support_path.empty()) {
      if(environmental_path.empty())throw std::runtime_error("Physical support mode requires shared ENV225");
      auto support=std::make_shared<reactive_stair::StaticSupportField>(support_path,
        parameter(name+".static_support_fnv64",std::string("")));
      if(support->radius()!=.35||support->offset()!=.18)throw std::runtime_error("Native support shape mismatch");
      planner_->setStaticSupport(support);
    }
    const auto solid_path=parameter(name+".static_solid_path",std::string(""));
    const auto solid_fnv=parameter(name+".static_solid_fnv64",std::string(""));
    if(!support_path.empty()&&solid_path.empty())throw std::runtime_error("Physical support mode requires pinned static solids");
    if(solid_path.empty()!=solid_fnv.empty())throw std::runtime_error("Static solid path and identity must be paired");
    if(!solid_path.empty())planner_->setStaticSolid(std::make_shared<reactive_stair::StaticSolidField>(solid_path,solid_fnv));
    path_pub_=parent_->create_publisher<nav_msgs::msg::Path>("/pct_planned_path",10);
    if(parameter(name+".shared_traversability",false))
      traversability_=std::make_unique<SharedTraversability>(parent_->get_name(),
        parameter("use_sim_time",false),parameter(name+".odom_topic",std::string("/quad_0/body_pose")));
    session_service_=parent_->create_service<lite3_nav2_interfaces::srv::RouteSession>(
      "/lite3_nav2/route_session",[this](std::shared_ptr<lite3_nav2_interfaces::srv::RouteSession::Request> request,
             std::shared_ptr<lite3_nav2_interfaces::srv::RouteSession::Response> response) {
        try {
          if(request->operation==request->BEGIN) {
            if(!valid(request->goal)) throw std::runtime_error("Invalid route-session goal");
            policy_.begin(request->session_id,request->goal,request->infer_heading);
          } else if(request->operation==request->END) policy_.end(request->session_id);
          else throw std::runtime_error("Invalid route-session operation");
          ++session_epoch_;response->accepted=true;
        } catch(const std::exception &error) {response->accepted=false;response->message=error.what();}
      });
    body_sub_=parent_->create_subscription<nav_msgs::msg::Odometry>(
      parameter(name+".odom_topic",std::string("/quad_0/body_pose")),rclcpp::SensorDataQoS(),
      [this](nav_msgs::msg::Odometry::ConstSharedPtr body) {
        geometry_msgs::msg::PoseStamped pose;pose.header=body->header;pose.pose=body->pose.pose;policy_.measured(pose);
      });
  }
  void activate() override {
    std::lock_guard<std::mutex> lock(mutex_);active_=true;path_pub_->on_activate();
  }
  void deactivate() override {
    std::lock_guard<std::mutex> lock(mutex_);active_=false;if(path_pub_) path_pub_->on_deactivate();
  }
  void cleanup() override {
    std::lock_guard<std::mutex> lock(mutex_);active_=false;
    session_service_.reset();body_sub_.reset();traversability_.reset();planner_.reset();path_pub_.reset();parent_.reset();
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
      const auto epoch=session_epoch_.load();
      const auto context=policy_.context();
      const std::string session=context ? context->id+"/"+std::to_string(epoch) : "";
      const auto same_session=[&] {
        const auto current=policy_.context();
        if(session_epoch_.load()!=epoch || bool(current)!=bool(context) ||
            (current&&current->id!=context->id))throw std::runtime_error("mission_changed_during_feedback");
      };
      const auto refresh=[&](const nav_msgs::msg::Path &reference) {
        feedback_.bind(session,BlockedFeedback::Clock::now());
        if(traversability_ && context) {
          const auto poses=localFeedbackSamples(reference,start,feedback_.witnesses());
          if(!poses.empty()) {
            try {
              const auto reply=traversability_->query(reference.header,start,poses,
                SharedTraversability::Service::Request::STATIC_AND_LIVE);
              same_session();
              const auto before=feedback_.constraints().size();
              feedback_.observe(poses,*reply,parent_->now().nanoseconds(),BlockedFeedback::Clock::now());
              const auto count=feedback_.constraints().size();
              if(count!=before)RCLCPP_INFO(parent_->get_logger(),"pct_live_feedback session=%s epoch=%lu revision=%lu observation_ns=%ld witnesses=%zu->%zu",
                context->id.c_str(),static_cast<unsigned long>(epoch),static_cast<unsigned long>(reply->map_revision),
                static_cast<long>(rclcpp::Time(reply->observation.stamp).nanoseconds()),before,count);
            } catch(const std::exception &error) {
              same_session(); // Optional live evidence cannot replace required static checking.
              RCLCPP_DEBUG(parent_->get_logger(),"pct_live_feedback_unavailable: %s",error.what());
            }
          }
        }
        same_session();feedback_.bind(session,BlockedFeedback::Clock::now());
        planner_->setFeedbackConstraints(feedback_.constraints());
      };
      refresh(context ? context->cached : nav_msgs::msg::Path{});
      planner_->clearRepairConstraints();
      for(unsigned attempt=0;attempt<3;++attempt) {
        nav_msgs::msg::Path path;
        try {
          path=policy_.plan(start,goal,[this]{return parent_->now();},
            [&]{return planner_->plan(xyz(start),xyz(goal),attempt<2);});
        } catch(const PCTOptimizationFailure &error) {
          RCLCPP_WARN(parent_->get_logger(),"pct_optimizer_rejected attempt=%u reason=%s",attempt,error.what());
          if(attempt==2)throw;
          continue; // Reuse the original two smooth/one graph attempt budget.
        }
        refresh(path); // Also catches observations arriving during the solve and cached returns.
        auto rejected=traversability_ ? traversability_->check(path,start) :
          std::vector<SharedTraversability::Rejection>();
        if(traversability_&&!rejected.empty()) {
          const auto headings=traversability_->graphHeadings(path.header,start,rejected);
          rejected.insert(rejected.end(),headings.begin(),headings.end());
        }
        if(traversability_)for(const auto &pose:sampleReference(path,start.pose))
          if(planner_->rejectedAt({pose.position.x,pose.position.y,pose.position.z},planarYaw(pose),true))
            rejected.push_back({pose,7u});
        same_session();
        if(rejected.empty()) {path_pub_->publish(path);return path;}
        policy_.rejectCached(path);
        RCLCPP_WARN(parent_->get_logger(),"pct_shared_rejected attempt=%u poses=%zu",attempt,rejected.size());
        std::vector<PCTRoutePlanner::RejectedPose> constraints;
        for(const auto &bad:rejected) constraints.push_back({
          Eigen::Vector3d(bad.pose.position.x,bad.pose.position.y,bad.pose.position.z),planarYaw(bad.pose),
          false}); // A rejected oriented body pose does not prove every heading blocked.
        planner_->addRepairConstraints(constraints);
      }
      throw std::runtime_error("pct_shared_traversability_no_route");
    } catch (const std::exception &error) {
      throw nav2_core::PlannerException(std::string("Native PCT: ")+error.what());
    }
  }
};
}  // namespace lite3_nav2
PLUGINLIB_EXPORT_CLASS(lite3_nav2::PCTPlanner, nav2_core::GlobalPlanner)
