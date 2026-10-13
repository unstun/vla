#include <plan_manage/planning_outcome.h>
#include <cassert>
#include <iostream>
#include <limits>

int main() {
  using namespace scan_planner;
  assert(observationState(false, 5, 4, .25) == ObservationState::Missing);
  assert(observationState(true, 5, 4.75, .25) == ObservationState::Fresh);
  assert(observationState(true, 5, 4.749, .25) == ObservationState::Stale);
  assert(observationState(true, 5, 5.001, .25) == ObservationState::Future);
  assert(observationState(true, 5, 4.99, -1) == ObservationState::Invalid);
  assert(observationState(true, std::numeric_limits<double>::quiet_NaN(), 5, .25)
         == ObservationState::Invalid);
  PlanningOutcome outcome;
  outcome.rejected(FailureStage::Optimizer, "outside_round", ObservationState::Fresh, 1);
  assert(outcome.failures() == 0);
  outcome.begin();
  outcome.rejected(FailureStage::SeedSearch, "astar_rejected", ObservationState::Fresh, 40);
  outcome.rejected(FailureStage::Target, "local_target_selection", ObservationState::Stale, 40);
  outcome.finish(false);
  assert(!outcome.success() && outcome.failures() == 2);
  assert(outcome.first().stage == FailureStage::SeedSearch);
  assert(outcome.first().observation == ObservationState::Fresh);
  assert(outcome.last().observation == ObservationState::Stale);
  std::cout << outcome.json() << '\n';
  outcome.begin();
  outcome.rejected(FailureStage::Optimizer, "optimizer_rejected", ObservationState::Fresh, 41);
  outcome.finish(true);
  assert(outcome.success() && outcome.failures() == 1);
  assert(outcome.counts()[static_cast<std::size_t>(FailureStage::SeedSearch)] == 0);
  assert(outcome.first().map_revision == 41);
  outcome.rejected(FailureStage::Target, "outside_round", ObservationState::Stale, 42);
  assert(outcome.failures() == 1);
  std::cout << outcome.json() << '\n';
  outcome.begin(); outcome.finish(true);
  assert(outcome.success() && outcome.failures() == 0);
  assert(outcome.first().stage == FailureStage::None);
  std::cout << outcome.json() << '\n';
}
