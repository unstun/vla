#pragma once
#include <array>
#include <chrono>
#include <ctime>
#include <iomanip>
#include <sstream>
namespace reactive_stair {
// Observation only: no deadlines, cancellation, eligibility or stop decisions.
struct PlanningProfile {
  enum Stage { Target, GoalSearch, GoalProof, Inputs, Cloud, SlidingMap, Seed,
               WarmSeed, Optimizer, Refine, FinalCheck, Count };
  struct Reading { double wall_ms{0}, cpu_ms{0}; unsigned long calls{0}; };
  using Snapshot = std::array<Reading, Count>;
  Snapshot values{};
  static double cpuMs() {
    timespec ts{};
    return clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts) == 0
        ? ts.tv_sec * 1000.0 + ts.tv_nsec * 1e-6 : 0.0;
  }
  struct Scope {
    PlanningProfile &owner; Stage stage;
    std::chrono::steady_clock::time_point wall;
    double cpu; bool running{true};
    Scope(PlanningProfile &p, Stage s) : owner(p), stage(s),
        wall(std::chrono::steady_clock::now()), cpu(cpuMs()) {}
    void finish() {
      if (!running) return;
      auto &r=owner.values[stage];
      r.wall_ms+=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-wall).count();
      r.cpu_ms+=cpuMs()-cpu; ++r.calls; running=false;
    }
    ~Scope() { finish(); }
    Scope(const Scope&)=delete; Scope& operator=(const Scope&)=delete;
  };
  std::string since(const Snapshot &before) const {
    static const char *names[Count]={"target","goal_search","goal_proof","inputs",
      "cloud","sliding_map","seed","warm_seed","optimizer","refine","final_check"};
    std::ostringstream out; out<<std::setprecision(9)<<"{";
    for (int i=0;i<Count;++i) {
      if(i)out<<",";
      out<<"\""<<names[i]<<"\":{\"wall_ms\":"<<values[i].wall_ms-before[i].wall_ms
         <<",\"cpu_ms\":"<<values[i].cpu_ms-before[i].cpu_ms
         <<",\"calls\":"<<values[i].calls-before[i].calls<<"}";
    }
    out<<"}";return out.str();
  }
};
} // namespace reactive_stair
