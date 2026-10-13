#pragma once
#include <array>
#include <chrono>
#include <ctime>
#include <sstream>

namespace map_meter {
enum Stage { Decode, Projection, Traversal, Fusion, Slide, SlideMask, SlideReset, Count };
enum Counter { Points, KeptPoints, TerrainCalls, Rays, UniqueRays, RaySteps,
               FusedVoxels, OccupancyCalls, OccupancyTransitions, InflationCalls,
               InflationOffsetVisits, SlideCalls, RealSlides, ClearedVoxels,
               ClearedOccupied, CounterCount };
struct Reading { double wall_ms = 0, cpu_ms = 0; };
struct Meter {
  std::array<Reading, Count> stages{};
  std::array<unsigned long long, CounterCount> counts{};
};
inline thread_local Meter meter;
inline double cpu_ms() {
  timespec ts{};
  return clock_gettime(CLOCK_THREAD_CPUTIME_ID, &ts) == 0
      ? ts.tv_sec * 1000.0 + ts.tv_nsec * 1e-6 : 0;
}
struct Scope {
  Stage stage;
  std::chrono::steady_clock::time_point started = std::chrono::steady_clock::now();
  double cpu = cpu_ms();
  bool active = true;
  explicit Scope(Stage value) : stage(value) {}
  void finish() {
    if (!active) return;
    meter.stages[stage].wall_ms += std::chrono::duration<double, std::milli>(
        std::chrono::steady_clock::now() - started).count();
    meter.stages[stage].cpu_ms += cpu_ms() - cpu;
    active = false;
  }
  ~Scope() { finish(); }
};
inline std::string difference(const Meter &before) {
  const char *stages[Count] = {"decode", "projection_and_terrain", "ray_traversal",
      "occupancy_fusion", "sliding", "slide_mask", "slide_reset"};
  const char *counts[CounterCount] = {"points", "kept_points", "terrain_calls",
      "rays", "unique_rays", "ray_steps", "fused_voxels", "occupancy_calls",
      "occupancy_transitions", "inflation_calls", "inflation_offset_visits",
      "slide_calls", "real_slides", "cleared_voxels", "cleared_occupied"};
  std::ostringstream out;
  out.precision(15);
  out << "{\"stages\":{";
  for (int i = 0; i < Count; ++i) {
    if (i) out << ',';
    out << '"' << stages[i] << "\":{\"wall_ms\":"
        << meter.stages[i].wall_ms - before.stages[i].wall_ms << ",\"cpu_ms\":"
        << meter.stages[i].cpu_ms - before.stages[i].cpu_ms << '}';
  }
  out << "},\"counts\":{";
  for (int i = 0; i < CounterCount; ++i) {
    if (i) out << ',';
    out << '"' << counts[i] << "\":" << meter.counts[i] - before.counts[i];
  }
  out << "}}";
  return out.str();
}
}  // namespace map_meter
