#pragma once
#include <cmath>
#include <algorithm>
#include <functional>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>
#include <Eigen/Core>
#include <nav_msgs/msg/path.hpp>
#include <rclcpp/time.hpp>

namespace lite3_nav2
{
// Navigation-owned task state. Solver calls never hold the context mutex.
class RoutePolicy
{
public:
  struct Context {
    std::string id;
    geometry_msgs::msg::PoseStamped requested;
    bool infer_heading{false};
    std::optional<geometry_msgs::msg::Pose> canonical;
    nav_msgs::msg::Path cached;
    std::string refresh_status{"initial"};
    uint64_t retained_count{0};
  };
  using Solver=std::function<std::vector<Eigen::Vector3d>()>;
  using Clock=std::function<rclcpp::Time()>;
  void begin(const std::string &id,const geometry_msgs::msg::PoseStamped &goal,bool infer) {
    if(id.empty()) throw std::runtime_error("Empty route session");
    std::lock_guard<std::mutex> lock(mutex_);
    if(context_ && context_->id==id) {
      if(context_->requested.pose!=goal.pose || context_->requested.header.frame_id!=goal.header.frame_id ||
          context_->infer_heading!=infer) throw std::runtime_error("Route session reused with a different goal");
      return;
    }
    ++generation_;context_.emplace();context_->id=id;context_->requested=goal;context_->infer_heading=infer;
  }
  void end(const std::string &id) {
    std::lock_guard<std::mutex> lock(mutex_);
    if(context_ && context_->id==id) {++generation_;context_.reset();}
  }
  std::optional<Context> context() const {std::lock_guard<std::mutex> lock(mutex_);return context_;}
  void rejectCached(const nav_msgs::msg::Path &route) {
    std::lock_guard<std::mutex> lock(mutex_);
    if(!context_ || context_->cached.poses.size()!=route.poses.size())return;
    for(size_t i=0;i<route.poses.size();++i)
      if(context_->cached.poses[i].pose!=route.poses[i].pose)return;
    context_->cached=nav_msgs::msg::Path();
  }
  void measured(const geometry_msgs::msg::PoseStamped &body) {
    std::lock_guard<std::mutex> lock(mutex_);measured_=body;
  }
  // Static mission continuation: the admitted reference survives moving-start
  // height/yaw fluctuations. Only remove a prefix; never re-search or re-score.
  std::optional<nav_msgs::msg::Path> retainedStatic(const geometry_msgs::msg::PoseStamped &start,
      const geometry_msgs::msg::PoseStamped &goal) {
    std::lock_guard<std::mutex> lock(mutex_);
    if(!context_ || context_->cached.poses.size()<2)return {};
    if(goal.header.frame_id!=context_->requested.header.frame_id ||
        (goal.pose!=context_->requested.pose && (!context_->canonical || goal.pose!=*context_->canonical)))
      throw std::runtime_error("mission_changed_during_planning");
    auto &poses=context_->cached.poses;
    const auto distance=[&](const auto &pose) {
      const auto &a=pose.pose.position,&b=start.pose.position;
      return (a.x-b.x)*(a.x-b.x)+(a.y-b.y)*(a.y-b.y)+(a.z-b.z)*(a.z-b.z);
    };
    const auto nearest=std::min_element(poses.begin(),poses.end(),[&](const auto &a,const auto &b){return distance(a)<distance(b);});
    poses.erase(poses.begin(),std::min(nearest,poses.end()-2));
    // Preserve the original reference epoch: local owners must not treat reuse
    // as a new curve or lose warm-start continuity.
    context_->refresh_status="static_reference_retained";++context_->retained_count;
    return context_->cached;
  }
  nav_msgs::msg::Path plan(const geometry_msgs::msg::PoseStamped &start,
      const geometry_msgs::msg::PoseStamped &goal,const Clock &now,const Solver &solve,
      const std::function<std::vector<double>()> &heading_provider={}) {
    Context saved;bool managed=false;uint64_t generation;
    {
      std::lock_guard<std::mutex> lock(mutex_);generation=generation_;
      if(context_) {
        managed=true;saved=*context_;
        if(!matches(goal,saved.requested.pose) && (!saved.canonical || !matches(goal,*saved.canonical)))
          throw std::runtime_error("mission_changed_during_planning");
        if(!saved.cached.poses.empty() && (near(start,*saved.canonical) ||
            (measured_ && measured_->header.frame_id==goal.header.frame_id && near(*measured_,*saved.canonical))))
          return retain(now,"terminal_approach");
      }
    }
    try {
      const auto points=solve();
      const auto headings=heading_provider?heading_provider():std::vector<double>{};
      if(!headings.empty()&&(headings.size()!=points.size()||std::any_of(headings.begin(),headings.end(),[](double h){return !std::isfinite(h);})))throw std::runtime_error("pct_invalid_route_headings");
      if(points.size()<2) throw std::runtime_error("pct_height_count_mismatch_or_empty_route");
      for(const auto &p:points) if(!p.allFinite()) throw std::runtime_error("pct_nonfinite_route");
      nav_msgs::msg::Path path;path.header.frame_id=goal.header.frame_id;path.header.stamp=now();
      double yaw=0;
      for(size_t i=0;i<points.size();++i) {
        if(i+1<points.size()) {const auto d=points[i+1]-points[i];if(std::hypot(d.x(),d.y())>1e-12) yaw=std::atan2(d.y(),d.x());}
        geometry_msgs::msg::PoseStamped pose;pose.header=path.header;
        pose.pose.position.x=points[i].x();pose.pose.position.y=points[i].y();pose.pose.position.z=points[i].z();
        setYaw(pose.pose,headings.empty()?yaw:headings[i]);path.poses.push_back(pose);
      }
      auto canonical=goal.pose;
      if(managed) {
        if(saved.canonical) canonical=*saved.canonical;
        else {
          canonical=path.poses.back().pose;
          if(saved.infer_heading) {
            bool found=!headings.empty();
            for(size_t i=points.size()-1;!found&&i>0;--i) {
              const auto d=points[i]-points[i-1];
              if(std::hypot(d.x(),d.y())>1e-6) {setYaw(canonical,std::atan2(d.y(),d.x()));found=true;break;}
            }
            if(!found) throw std::runtime_error("pct_no_terminal_heading");
          } else canonical.orientation=saved.requested.pose.orientation;
        }
      }
      const auto &last=canonical.position;const auto &previous=points[points.size()-2];
      if((previous-Eigen::Vector3d(last.x,last.y,last.z)).norm()>2.)
        throw std::runtime_error("pct_canonical_goal_disconnected");
      if(!headings.empty()) {
        const auto &q=canonical.orientation;
        const double yaw=std::atan2(2.*(q.w*q.z+q.x*q.y),1.-2.*(q.y*q.y+q.z*q.z));
        if(std::abs(std::remainder(headings.back()-yaw,2*M_PI))>1e-6)
          throw std::runtime_error("pct_canonical_heading_not_planned");
      }
      path.poses.back().pose=canonical;
      std::lock_guard<std::mutex> lock(mutex_);checkGeneration(generation);
      if(managed) {context_->canonical=canonical;context_->cached=path;context_->refresh_status="planned";}
      return path;
    } catch(const std::exception &error) {
      std::lock_guard<std::mutex> lock(mutex_);checkGeneration(generation);
      const std::string reason=error.what();
      if(managed && !context_->cached.poses.empty() && (reason=="pct_no_route" ||
          reason=="pct_height_count_mismatch_or_empty_route" || reason=="pct_canonical_goal_disconnected"))
        return retain(now,reason);
      throw;
    }
  }
private:
  static void setYaw(geometry_msgs::msg::Pose &pose,double yaw) {
    pose.orientation.x=pose.orientation.y=0;pose.orientation.z=std::sin(yaw/2);pose.orientation.w=std::cos(yaw/2);
  }
  static bool matches(const geometry_msgs::msg::PoseStamped &goal,const geometry_msgs::msg::Pose &target) {
    const auto &a=goal.pose.position,&b=target.position;
    return std::abs(a.x-b.x)<=1e-6 && std::abs(a.y-b.y)<=1e-6 && std::abs(a.z-b.z)<=1e-6;
  }
  static bool near(const geometry_msgs::msg::PoseStamped &pose,const geometry_msgs::msg::Pose &goal) {
    const auto &a=pose.pose.position,&b=goal.position;
    return std::isfinite(a.x)&&std::isfinite(a.y)&&std::isfinite(a.z)&&
      std::hypot(a.x-b.x,a.y-b.y)<=1.0 && std::abs(a.z-b.z)<=0.35;
  }
  void checkGeneration(uint64_t generation) const {
    if(generation!=generation_) throw std::runtime_error("mission_changed_during_planning");
  }
  nav_msgs::msg::Path retain(const Clock &now,const std::string &reason) {
    auto path=context_->cached;path.header.stamp=now();for(auto &p:path.poses)p.header=path.header;
    context_->refresh_status=reason;++context_->retained_count;return path;
  }
  mutable std::mutex mutex_;
  uint64_t generation_{0};
  std::optional<Context> context_;
  std::optional<geometry_msgs::msg::PoseStamped> measured_;
};
} // namespace lite3_nav2
