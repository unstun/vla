// Copyright (c) 2019 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// Adapted from Navigation2 0.4.7, commit a947ab5656e46ae3aa1afdf95e1706a16e478974.
// Retain its two-child control/stop semantics; renew retries only from fresh,
// previously unvisited physical space. No path acceptance or actuation here.
#pragma once
#include <behaviortree_cpp_v3/control_node.h>
#include <rclcpp/rclcpp.hpp>
#include <tf2_ros/buffer.h>
#include <array>
#include <vector>
#include <cmath>
namespace lite3_nav2 {
class MeasuredProgressRecovery : public BT::ControlNode {
public:
 MeasuredProgressRecovery(const std::string&,const BT::NodeConfiguration&);
 static BT::PortsList providedPorts(){return {
  BT::InputPort<int>("number_of_retries",6,"Retries without new measured space"),
  BT::InputPort<std::string>("global_frame",std::string("world"),"Fixed global frame"),
  BT::InputPort<std::string>("robot_base_frame",std::string("base_link"),"Measured robot frame")};}
private:
 unsigned current_child_idx_,number_of_retries_,retry_count_;
 rclcpp::Node::SharedPtr node_;
 std::shared_ptr<tf2_ros::Buffer> tf_;
 std::string global_frame_,base_frame_;
 std::vector<std::array<double,3>> anchors_;
 double last_stamp_{0.0};
 void updateMeasuredProgress(){
  geometry_msgs::msg::TransformStamped pose;
  try {pose=tf_->lookupTransform(global_frame_,base_frame_,tf2::TimePointZero);}
  catch(const tf2::TransformException&){return;}
  const double stamp=rclcpp::Time(pose.header.stamp).seconds(),now=node_->now().seconds();
  if(stamp<=0.0 || stamp<=last_stamp_ || now<stamp || now-stamp>0.1)return;
  const auto &p=pose.transform.translation;
  const std::array<double,3> point{p.x,p.y,p.z};
  for(double x:point)if(!std::isfinite(x))return;
  last_stamp_=stamp;
  if(anchors_.empty()){anchors_.push_back(point);return;}
  if(anchors_.size()>=256)return; // Fixed memory and replenishment bound.
  for(const auto &a:anchors_){
   const double d2=std::pow(point[0]-a[0],2)+std::pow(point[1]-a[1],2)+std::pow(point[2]-a[2],2);
   if(d2<4.0)return; // At least2m from every prior checkpoint; loops do not renew.
  }
  anchors_.push_back(point);
  if(retry_count_>0)RCLCPP_INFO(node_->get_logger(),
   "V170_RECOVERY_BUDGET_RENEW used=%u checkpoints=%zu xyz=[%.6f,%.6f,%.6f] source_s=%.9f",
   retry_count_,anchors_.size(),point[0],point[1],point[2],stamp);
  retry_count_=0;
 }
 BT::NodeStatus tick() override;
 void halt() override;
};
inline MeasuredProgressRecovery::MeasuredProgressRecovery(
  const std::string & name,
  const BT::NodeConfiguration & conf)
: BT::ControlNode::ControlNode(name, conf),
  current_child_idx_(0),
  number_of_retries_(1),
  retry_count_(0)
{
  getInput("number_of_retries", number_of_retries_);
  node_=config().blackboard->get<rclcpp::Node::SharedPtr>("node");
  tf_=config().blackboard->get<std::shared_ptr<tf2_ros::Buffer>>("tf_buffer");
  if(!getInput("global_frame",global_frame_) || !getInput("robot_base_frame",base_frame_) || global_frame_.empty() || base_frame_.empty())throw BT::BehaviorTreeException("Measured progress requires explicit frames");

}

inline BT::NodeStatus MeasuredProgressRecovery::tick()
{
  const unsigned children_count = children_nodes_.size();

  if (children_count != 2) {
    throw BT::BehaviorTreeException("Recovery Node '" + name() + "' must only have 2 children.");
  }

  if(current_child_idx_==0) updateMeasuredProgress();
  setStatus(BT::NodeStatus::RUNNING);

  while (current_child_idx_ < children_count && retry_count_ <= number_of_retries_) {
    TreeNode * child_node = children_nodes_[current_child_idx_];
    const BT::NodeStatus child_status = child_node->executeTick();

    if (current_child_idx_ == 0) {
      switch (child_status) {
        case BT::NodeStatus::SUCCESS:
          {
            retry_count_ = 0;
            halt();
            return BT::NodeStatus::SUCCESS;
          }

        case BT::NodeStatus::FAILURE:
          {
            // tick second child
            if (retry_count_ < number_of_retries_) {
              current_child_idx_++;
              break;
            } else {
              ControlNode::haltChildren();
              return BT::NodeStatus::FAILURE;
            }
          }

        case BT::NodeStatus::RUNNING:
          {
            return BT::NodeStatus::RUNNING;
          }

        default:
          {
            halt();
            return BT::NodeStatus::FAILURE;
          }
      }  // end switch

    } else if (current_child_idx_ == 1) {
      switch (child_status) {
        case BT::NodeStatus::SUCCESS:
          {
            retry_count_++;
            current_child_idx_--;
            ControlNode::haltChildren();
          }
          break;

        case BT::NodeStatus::FAILURE:
          {
            current_child_idx_--;
            retry_count_ = 0;
            halt();
            return BT::NodeStatus::FAILURE;
          }

        case BT::NodeStatus::RUNNING:
          {
            return BT::NodeStatus::RUNNING;
          }

        default:
          {
            halt();
            return BT::NodeStatus::FAILURE;
          }
      }  // end switch
    }
  }  // end while loop
  retry_count_ = 0;
  halt();
  return BT::NodeStatus::FAILURE;
}

inline void MeasuredProgressRecovery::halt()
{
  ControlNode::halt();
  current_child_idx_ = 0;
  retry_count_ = 0;
  anchors_.clear();last_stamp_=0.0;
}

}
