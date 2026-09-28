#ifndef VLA_ASTAR_GRID_COORDINATES_H
#define VLA_ASTAR_GRID_COORDINATES_H
#include <cmath>
namespace reactive_stair {
inline int nearestGridOffset(double cells) {
  return static_cast<int>(std::floor(cells + 0.5));
}
inline double startAlignedSearchCenter(double start, double end, double step) {
  return start + step * nearestGridOffset((end - start) / (2.0 * step));
}
}  // namespace reactive_stair
#endif
