#pragma once
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <lite3_nav2_plugins/shared_traversability.hpp>
#include <chrono>
#include <string>

namespace lite3_nav2 {
// Mission-scoped planning hints. They never grant native execution clearance.
class BlockedFeedback {
public:
  using Clock=std::chrono::steady_clock;
  struct Entry {PCTRoutePlanner::RejectedPose pose;int64_t observation;uint64_t revision;Clock::time_point admitted;};
  void bind(const std::string &session,Clock::time_point now) {
    if(session.empty()||session!=session_){entries_.clear();source_.clear();session_=session;}
    entries_.erase(std::remove_if(entries_.begin(),entries_.end(),[&](const auto &e){return now-e.admitted>=std::chrono::seconds(2);}),entries_.end());
  }
  void observe(const std::vector<geometry_msgs::msg::Pose> &poses,
      const SharedTraversability::Service::Response &reply,int64_t now_ns,Clock::time_point wall_now) {
    if(session_.empty()||!reply.ready||reply.source_identity.empty()||reply.verdicts.size()!=poses.size()||
        reply.observation.frame_id!="world"||reply.observation.stamp.sec<0||reply.observation.stamp.nanosec>=1000000000u)return;
    const int64_t stamp=int64_t(reply.observation.stamp.sec)*1000000000LL+reply.observation.stamp.nanosec;
    // Match the native obstacle-age bound; a stale response cannot add or clear.
    if(stamp<=0||stamp>now_ns||now_ns-stamp>250000000LL)return;
    if(source_!=reply.source_identity){entries_.clear();source_=reply.source_identity;}
    for(size_t i=0;i<poses.size();++i) {
      const auto &p=poses[i];const Eigen::Vector3d xyz(p.position.x,p.position.y,p.position.z);
      const double yaw=planarYaw(p);
      auto match=[&](const auto &e){return (e.pose.position-xyz).head(2).norm()<=.05&&
        std::abs(e.pose.position.z()-xyz.z())<.26&&std::abs(std::remainder(e.pose.yaw-yaw,M_PI))<.15;};
      if(reply.verdicts[i]==0) {
        entries_.erase(std::remove_if(entries_.begin(),entries_.end(),[&](const auto &e){
          return (e.pose.position-xyz).norm()<1e-6&&std::abs(std::remainder(e.pose.yaw-yaw,M_PI))<1e-6&&
            stamp>e.observation&&reply.map_revision>=e.revision;}),entries_.end());
      } else if(reply.verdicts[i]==7 && xyz.allFinite()) {
        const auto found=std::find_if(entries_.begin(),entries_.end(),match);
        if(found!=entries_.end()) {
          if(stamp>found->observation&&reply.map_revision>=found->revision) {
            found->observation=stamp;found->revision=reply.map_revision;found->admitted=wall_now;
          } // Keep the exact witness location; deduplication must not walk across a region.
        } else if(entries_.size()<128) entries_.push_back({{xyz,yaw,false},stamp,reply.map_revision,wall_now});
      }
    }
  }
  std::vector<PCTRoutePlanner::RejectedPose> constraints() const {
    std::vector<PCTRoutePlanner::RejectedPose> result;for(const auto &e:entries_)result.push_back(e.pose);return result;
  }
  std::vector<geometry_msgs::msg::Pose> witnesses() const {
    std::vector<geometry_msgs::msg::Pose> result;
    for(const auto &e:entries_) {
      geometry_msgs::msg::Pose p;p.position.x=e.pose.position.x();p.position.y=e.pose.position.y();p.position.z=e.pose.position.z();
      p.orientation.z=std::sin(e.pose.yaw*.5);p.orientation.w=std::cos(e.pose.yaw*.5);result.push_back(p);
    }
    return result;
  }
private:
  std::string session_,source_;std::vector<Entry> entries_;
};

// Follow the existing reference forward from its nearest 3-D point. Do not
// manufacture a connector from the measured body to the old reference start.
inline std::vector<geometry_msgs::msg::Pose> localFeedbackSamples(const nav_msgs::msg::Path &path,
    const geometry_msgs::msg::PoseStamped &start,const std::vector<geometry_msgs::msg::Pose> &witnesses) {
  auto result=witnesses;
  if(path.poses.empty())return result;
  const auto samples=sampleReference(path,path.poses.front().pose);
  const Eigen::Vector3d body(start.pose.position.x,start.pose.position.y,start.pose.position.z);
  size_t closest=0;double best=1e100;
  for(size_t i=0;i<samples.size();++i) {
    const auto &p=samples[i].position;const double distance=(Eigen::Vector3d(p.x,p.y,p.z)-body).squaredNorm();
    if(distance<best){best=distance;closest=i;}
  }
  for(size_t i=closest;i<samples.size()&&result.size()<384;++i) {
    const auto &p=samples[i].position;
    if((Eigen::Vector3d(p.x,p.y,p.z)-body).norm()>3.)break;
    result.push_back(samples[i]);
  }
  return result;
}
} // namespace lite3_nav2
