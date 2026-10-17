/**
 * @file sim_sender.h
 * @brief Sends joint commands from your gait code to MuJoCo sim over /JOINTS_CMD.
 *        Drop-in replacement for MotionSDK's Sender when running in simulation.
 *
 * Usage:
 *   SimSender sender(node);
 *   sender.SendCmd(robot_cmd);   // call every 1ms (or at your control rate)
 */

#pragma once

#include "sim_robot_types.h"

#include <rclcpp/rclcpp.hpp>
#include <drdds/msg/joints_data_cmd.hpp>
#include <drdds/msg/joints_data_cmd_value.hpp>
#include <drdds/msg/joint_data_cmd.hpp>
#include <drdds/msg/meta_type.hpp>

#include <chrono>
#include <cstring>
#include <array>

class SimSender {
public:
    explicit SimSender(rclcpp::Node::SharedPtr node)
        : node_(node)
    {
        pub_ = node_->create_publisher<drdds::msg::JointsDataCmd>(
            "/JOINTS_CMD",
            rclcpp::QoS(rclcpp::KeepLast(1)).reliable());

        RCLCPP_INFO(node_->get_logger(), "[SimSender] Publishing to /JOINTS_CMD");
    }

    /**
     * @brief Send a joint command to the MuJoCo simulation.
     *        Call this at your control frequency (e.g., every 1 ms).
     *
     * @param cmd  12-joint command: position, velocity, torque, kp, kd per joint
     */
    void SendCmd(const SimRobotCmd& cmd) {
        drdds::msg::JointsDataCmd msg;

        // Fill header timestamp
        auto now = node_->get_clock()->now();
        msg.header.stamp.sec    = static_cast<int32_t>(now.seconds());
        msg.header.stamp.nanosec = static_cast<uint32_t>(now.nanoseconds() % 1'000'000'000ULL);
        msg.header.frame_id = 0;

        // joints_data is std::array<JointDataCmd,16> — fixed size, no resize needed
        for (int i = 0; i < 12; ++i) {
            auto& jc = msg.data.joints_data[i];
            jc.position = cmd.joint_cmd[i].position;
            jc.velocity = cmd.joint_cmd[i].velocity;
            jc.torque   = cmd.joint_cmd[i].torque;
            jc.kp       = cmd.joint_cmd[i].kp;
            jc.kd       = cmd.joint_cmd[i].kd;
        }
        // Dummy entries (indices 12–15) left at zero

        pub_->publish(msg);
    }

    /**
     * @brief Zero all joints and apply light damping — call once at startup.
     */
    void RobotStateInit() {
        SimRobotCmd zero_cmd{};
        for (int i = 0; i < 12; ++i) {
            zero_cmd.joint_cmd[i].position = 0.f;
            zero_cmd.joint_cmd[i].velocity = 0.f;
            zero_cmd.joint_cmd[i].torque   = 0.f;
            zero_cmd.joint_cmd[i].kp       = 0.f;
            zero_cmd.joint_cmd[i].kd       = 1.f; // light damping
        }
        // Publish several times to ensure sim receives it
        for (int i = 0; i < 20; ++i) {
            SendCmd(zero_cmd);
            rclcpp::spin_some(node_);
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
        }
        RCLCPP_INFO(node_->get_logger(), "[SimSender] RobotStateInit done — damping applied.");
    }

private:
    rclcpp::Node::SharedPtr                                        node_;
    rclcpp::Publisher<drdds::msg::JointsDataCmd>::SharedPtr        pub_;
};
