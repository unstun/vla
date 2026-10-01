#ifndef LOCAL_HOTSPOT_PROFILE_H
#define LOCAL_HOTSPOT_PROFILE_H
#include <array>
#include <chrono>
#include <cstdint>

namespace local_profile {
struct Record { std::uint64_t calls{0}; std::uint64_t elapsed_ns{0}; };
extern bool active;
extern std::array<Record, 12> records;
void start();
void stop();
void report();
class Scope {
  std::size_t index_;
  bool active_;
  std::chrono::steady_clock::time_point started_;
 public:
  explicit Scope(std::size_t index) : index_(index), active_(active) {
    if (active_) started_ = std::chrono::steady_clock::now();
  }
  ~Scope() {
    if (!active_) return;
    records[index_].calls++;
    records[index_].elapsed_ns += std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::steady_clock::now() - started_).count();
  }
};
}
#endif
