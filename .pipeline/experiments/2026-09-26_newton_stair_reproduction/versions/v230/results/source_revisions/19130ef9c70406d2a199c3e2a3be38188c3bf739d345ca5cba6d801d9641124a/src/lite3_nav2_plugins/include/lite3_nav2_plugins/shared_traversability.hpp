#pragma once
#include <lite3_nav2_interfaces/srv/check_traversability.hpp>
#include <nav_msgs/msg/path.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <rclcpp/rclcpp.hpp>
#include <algorithm>
#include <cmath>
#include <future>
#include <stdexcept>
#include <vector>

namespace lite3_nav2 {
inline double planarYaw(const geometry_msgs::msg::Pose &pose) {
  const auto &q=pose.orientation;
  const double norm=q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w;
  if(!std::isfinite(norm)||std::abs(norm-1.)>1e-3)
    throw std::runtime_error("pct_invalid_planar_reference");
  return std::atan2(2.*(q.w*q.z+q.x*q.y),1.-2.*(q.y*q.y+q.z*q.z));
}

// Check translation AND rotation, including the measured-start connector.
inline std::vector<geometry_msgs::msg::Pose> sampleReference(
    const nav_msgs::msg::Path &path,const geometry_msgs::msg::Pose &start,
    double spacing=0.025,double yaw_spacing=0.05) {
  if(path.poses.empty() || !std::isfinite(spacing)||spacing<=0 ||
      !std::isfinite(yaw_spacing)||yaw_spacing<=0) throw std::runtime_error("pct_invalid_reference_sampling");
  std::vector<geometry_msgs::msg::Pose> samples;
  auto previous=start;
  for(const auto &item:path.poses) {
    const auto &next=item.pose;
    const double dx=next.position.x-previous.position.x,dy=next.position.y-previous.position.y;
    const double dz=next.position.z-previous.position.z;
    const double yaw=planarYaw(previous),delta=std::remainder(planarYaw(next)-yaw,2.*M_PI);
    const double distance=std::sqrt(dx*dx+dy*dy+dz*dz);
    if(!std::isfinite(distance)) throw std::runtime_error("pct_nonfinite_reference");
    const double needed=std::max(distance/spacing,std::abs(delta)/yaw_spacing);
    if(needed>10000 || samples.size()+static_cast<size_t>(std::ceil(needed))+1>10000)
      throw std::runtime_error("pct_reference_sample_budget");
    const size_t count=std::max<size_t>(1,static_cast<size_t>(std::ceil(needed)));
    for(size_t i=0;i<count;++i) {
      const double u=double(i)/count;geometry_msgs::msg::Pose pose;
      pose.position.x=previous.position.x+u*dx;pose.position.y=previous.position.y+u*dy;
      pose.position.z=previous.position.z+u*dz;
      pose.orientation.z=std::sin((yaw+u*delta)/2.);pose.orientation.w=std::cos((yaw+u*delta)/2.);
      samples.push_back(pose);
    }
    previous=next;
  }
  samples.push_back(path.poses.back().pose);
  return samples;
}

class SharedTraversability {
public:
  struct Rejection {geometry_msgs::msg::Pose pose;uint8_t verdict;};
  SharedTraversability(const std::string &name,bool simulation_time,const std::string &odom_topic) {
    rclcpp::NodeOptions options;options.use_global_arguments(false);
    options.parameter_overrides({rclcpp::Parameter("use_sim_time",simulation_time)});
    node_=std::make_shared<rclcpp::Node>(name+"_traversability",options);
    body_sub_=node_->create_subscription<nav_msgs::msg::Odometry>(odom_topic,rclcpp::SensorDataQoS(),
      [this](nav_msgs::msg::Odometry::ConstSharedPtr message) {
        body_.header=message->header;body_.pose=message->pose.pose;have_body_=true;
      });
    client_=node_->create_client<Service>("/scan/check_traversability");executor_.add_node(node_);
  }
  using Service=lite3_nav2_interfaces::srv::CheckTraversability;
  Service::Response::SharedPtr query(const std_msgs::msg::Header &header,
      const geometry_msgs::msg::PoseStamped &start,const std::vector<geometry_msgs::msg::Pose> &poses,uint8_t mode) {
    executor_.spin_some();
    if(!client_->wait_for_service(std::chrono::milliseconds(500)))
      throw std::runtime_error("pct_native_traversability_unavailable");
    auto request=std::make_shared<Service::Request>();request->header=header;
    request->body=have_body_ ? body_ : start;request->poses=poses;request->mode=mode;
    auto future=client_->async_send_request(request);
    const auto status=executor_.spin_until_future_complete(future,std::chrono::milliseconds(1500));
    if(status!=rclcpp::FutureReturnCode::SUCCESS) throw std::runtime_error("pct_native_traversability_timeout");
    const auto reply=future.get();
    if(!reply->ready || reply->verdicts.size()!=poses.size())
      throw std::runtime_error("pct_native_traversability_evidence_unavailable:"+reply->message);
    return reply;
  }
  // A solid verdict for one oriented footprint does not establish all headings.
  // Explicitly check the four undirected headings used by the eight-neighbor graph.
  std::vector<Rejection> graphHeadings(const std_msgs::msg::Header &header,
      const geometry_msgs::msg::PoseStamped &start,const std::vector<Rejection> &rejected) {
    std::vector<geometry_msgs::msg::Pose> probes;
    for(const auto &bad:rejected)if(bad.verdict==7&&probes.size()<800)
      for(int k=0;k<4;++k){auto p=bad.pose;p.orientation.x=p.orientation.y=0.;
        p.orientation.z=std::sin(k*M_PI/8.);p.orientation.w=std::cos(k*M_PI/8.);probes.push_back(p);}
    if(probes.empty())return {};
    const auto reply=query(header,start,probes,Service::Request::STATIC_ONLY);
    std::vector<Rejection> result;
    for(size_t i=0;i<probes.size();++i)if(reply->verdicts[i]!=0)result.push_back({probes[i],reply->verdicts[i]});
    return result;
  }
  std::vector<Rejection> check(const nav_msgs::msg::Path &path,const geometry_msgs::msg::PoseStamped &start) {
    const auto poses=sampleReference(path,start.pose);
    const auto reply=query(path.header,start,poses,Service::Request::STATIC_ONLY);
    std::vector<Rejection> rejected;
    for(size_t i=0;i<reply->verdicts.size();++i)
      if(reply->verdicts[i]!=0) rejected.push_back({poses[i],reply->verdicts[i]});
    return rejected;
  }
private:
  rclcpp::Node::SharedPtr node_;
  rclcpp::executors::SingleThreadedExecutor executor_;
  rclcpp::Client<Service>::SharedPtr client_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr body_sub_;
  geometry_msgs::msg::PoseStamped body_;
  bool have_body_{false};
};
}
