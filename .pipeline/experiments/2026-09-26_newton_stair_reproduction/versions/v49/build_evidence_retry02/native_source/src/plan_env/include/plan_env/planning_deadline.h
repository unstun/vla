#pragma once
#include <chrono>
#include <exception>

namespace scan_planner {
// Single executor-owned budget. Nested searches and retries never restart it.
class PlanningTimeout final : public std::exception {
 public:
  const char *site;
  explicit PlanningTimeout(const char *where) noexcept : site(where) {}
  const char *what() const noexcept override { return site; }
};
class PlanningDeadline {
 public:
  using Clock = std::chrono::steady_clock;
  explicit PlanningDeadline(Clock::time_point start = Clock::now()) : start_(start) {}
  void check(const char *site) const {
    if (elapsedMs() >= (reserve_ ? 25.0 : 20.0)) throw PlanningTimeout(site);
  }
  void compute() { reserve_ = false; check("compute_budget"); }
  void finalSafety() { check("before_final_safety"); reserve_ = true; check("final_safety_budget"); }
  void recovery() { reserve_ = true; check("recovery_budget"); }
  double elapsedMs() const { return std::chrono::duration<double, std::milli>(Clock::now()-start_).count(); }
 private:
  Clock::time_point start_;
  bool reserve_{false};
};
} // namespace scan_planner
