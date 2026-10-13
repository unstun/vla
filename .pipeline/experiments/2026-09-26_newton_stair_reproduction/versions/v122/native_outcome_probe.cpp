#include <plan_manage/planner_manager.h>
#include <rcl/time.h>
#include <iostream>
#include <stdexcept>
#include <algorithm>
#include <chrono>
#include <vector>

void require(bool condition, const char *message) {
  if (!condition) throw std::runtime_error(message);
}
int main(int argc, char **argv) {
  using namespace scan_planner;
  rclcpp::init(argc, argv);
  rclcpp::Node node("scan_planner_node");
  auto handle = node.get_clock()->get_clock_handle();
  require(rcl_enable_ros_time_override(handle) == RCL_RET_OK, "clock enable");
  require(rcl_set_ros_time_override(handle, 10000000000LL) == RCL_RET_OK, "clock set");
  SCANPlannerManager manager;
  manager.initPlanModules(&node);
  auto &outcome = manager.planning_outcome_;
  const Eigen::Vector3d zero = Eigen::Vector3d::Zero();
  rclcpp::Time future(20000000000LL, RCL_ROS_TIME);
  outcome.begin();
  const bool future_accepted = manager.reboundReplan(zero, zero, zero,
      Eigen::Vector3d(1, 0, 0), zero, true, false, &future);
  outcome.finish(future_accepted);
  require(!future_accepted && outcome.last().stage == FailureStage::Epoch, "native epoch branch");
  require(outcome.last().observation == ObservationState::Missing, "missing observation context");
  std::cout << "V122_PROBE " << outcome.json() << std::endl;

  outcome.begin();
  const bool stationary_accepted = manager.reboundReplan(zero, zero, zero, zero, zero, true, false);
  outcome.finish(stationary_accepted);
  require(!stationary_accepted && outcome.last().stage == FailureStage::SeedGeometry,
          "native no-translation branch");
  std::cout << "V122_PROBE " << outcome.json() << std::endl;

  Eigen::Vector3d lower, upper;
  require(manager.grid_map_->bodyCenterBounds(lower, upper), "valid map bounds");
  const Eigen::Vector3d start = 0.5 * (lower + upper);
  const Eigen::Vector3d goal = start + Eigen::Vector3d(0.3, 0, 0);
  require(manager.hasLocalTranslation(start, goal), "test has actual translation");
  outcome.begin();
  const bool unknown_accepted = manager.reboundReplan(start, zero, zero, goal, zero, true, false);
  outcome.finish(unknown_accepted);
  require(!unknown_accepted && outcome.first().stage == FailureStage::SeedSearch,
          "native unknown-map A-star rejection");
  std::cout << "V122_PROBE " << outcome.json() << std::endl;
  // Measure the actual structured logger, including context capture, separately
  // from search time. This is a local component overhead check, not a deadline.
  std::vector<double> overhead;
  double sum = 0;
  for (int i = 0; i < 1000; ++i) {
    const auto begin = std::chrono::steady_clock::now();
    outcome.begin();
    manager.planningRejected(FailureStage::SeedSearch, "overhead_probe");
    manager.finishPlanningOutcome(false);
    const double us = std::chrono::duration<double, std::micro>(
        std::chrono::steady_clock::now() - begin).count();
    overhead.push_back(us); sum += us;
  }
  std::sort(overhead.begin(), overhead.end());
  std::cout << "V122_OVERHEAD {\"samples\":1000,\"mean_us\":" << sum / 1000
            << ",\"p95_us\":" << overhead[950] << "}" << std::endl;
  require(sum / 1000 < 200 && overhead[950] < 500, "diagnostic logging overhead");
  rclcpp::shutdown();
}
