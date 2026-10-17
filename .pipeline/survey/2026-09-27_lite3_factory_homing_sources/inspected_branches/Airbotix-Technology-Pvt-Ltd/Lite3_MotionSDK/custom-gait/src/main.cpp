/**
 * @file main.cpp
 * @brief Entry point for the Jueying Lite3 custom gait runner.
 */

#include <iostream>
#include <atomic>
#include <csignal>
#include <chrono>
#include <thread>
#include <cmath>

#include <rclcpp/rclcpp.hpp>
#include "sim_receiver.h"
#include "sim_sender.h"
#include "sim_timer.h"
#include "custom_gait.h"
#include "keyboard_controller.h"

// Global flag for clean shutdown
static std::atomic<bool> g_shutdown{false};

void SignalHandler(int) {
    g_shutdown.store(true);
}

int main(int argc, char** argv) {
    // 1. Initialize ROS2
    rclcpp::init(argc, argv);
    auto node = std::make_shared<rclcpp::Node>("gait_runner");

    // 2. Setup Signal Handler
    std::signal(SIGINT, SignalHandler);

    // 3. Control objects
    SimReceiver   receiver(node);
    SimSender     sender(node);
    SimTimer      timer;
    CustomGait    gait;
    KeyboardController kb;

    timer.TimeInit(1); // 1 kHz
    sender.RobotStateInit();

    // Phase control: Start at StandUp
    enum class Phase { StandUp, Trot };
    Phase phase = Phase::StandUp;

    SimRobotData  robot_data;
    SimRobotCmd   robot_joint_cmd;
    double phase_start_time = timer.GetCurrentTime();
    uint64_t log_tick = 0;

    printf("[INFO] === Lite3 Custom Gait Runner (WASD control) ===\n");

    // Main loop (1 kHz)
    while (!g_shutdown.load() && rclcpp::ok()) {
        // Process ROS2 callbacks
        rclcpp::spin_some(node);

        // Wait for next 1ms tick (mirrors MotionSDK's DRTimer::TimerInterrupt)
        if (timer.TimerInterrupt()) {
            continue; 
        }

        // Get latest simulation data
        if (!receiver.IsDataReady()) {
            static int wait_count = 0;
            if (++wait_count % 1000 == 0) {
                printf("[INFO] Waiting for MuJoCo sim data...\n");
            }
            continue;
        }

        robot_data = receiver.GetState();
        double now_time = timer.GetCurrentTime();
        double elapsed  = timer.GetIntervalTime(phase_start_time);

        // Read keyboard
        float scale = kb.speed_scale();
        float vx = kb.vx() * scale;
        float vy = kb.vy() * scale;
        float wz = kb.wz() * scale;

        // Apply stair mode and manual pitch offset
        gait.SetStairMode(kb.stair_mode());
        gait.SetPitchOffset(kb.pitch_offset());

        switch (phase) {
            case Phase::StandUp: {
                bool done = gait.StandUp(robot_joint_cmd, elapsed, robot_data, 3.0);
                if (done) {
                    printf("[INFO] Phase 1: Trot. Use WASD to control.\n");
                    phase = Phase::Trot;
                    phase_start_time = now_time;
                }
                break;
            }

            case Phase::Trot: {
                bool idle = (std::fabs(vx) < 0.01f &&
                             std::fabs(vy) < 0.01f &&
                             std::fabs(wz) < 0.01f);
                if (idle) {
                    gait.Hold(robot_joint_cmd);
                    phase_start_time = now_time; // Reset so gait starts at phase 0
                } else if (kb.stair_mode()) {
                    gait.Crawl(robot_joint_cmd, elapsed, vx, vy, wz);
                } else {
                    gait.Trot(robot_joint_cmd, elapsed, vx, vy, wz);
                }
                break;
            }
        }

        // Send command back to simulation
        sender.SendCmd(robot_joint_cmd);

        // Status print removed
    }

    // Power off on exit
    printf("\n[INFO] Shutting down. Applying damping...\n");
    gait.JointDamping(robot_joint_cmd);
    sender.SendCmd(robot_joint_cmd);
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    rclcpp::shutdown();
    return 0;
}
