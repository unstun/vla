#include <plan_env/astar_grid_coordinates.h>
#include <cassert>
#include <cmath>
#include <iostream>
using namespace reactive_stair;

int main() {
  // Casting the signed offset plus 0.5 truncates toward zero; -1.2 used to
  // become 0 instead of -1. A negative-side point could move over half a cell.
  assert(static_cast<int>(-1.2 + 0.5) == 0);
  assert(nearestGridOffset(-1.2) == -1);
  for (int i = -10000; i <= 10000; ++i) {
    double cells = i / 100.0;
    assert(std::abs(nearestGridOffset(cells) - cells) <= 0.500000000001);
  }
  for (double start : {-5.4205, 5.998, 0.35454}) {
    for (double end : {-5.38, 2.29, 1.03}) {
      const double center = startAlignedSearchCenter(start, end, 0.05);
      const double restored = center + nearestGridOffset((start - center) / 0.05) * 0.05;
      assert(std::abs(start - restored) < 1e-12);
    }
  }
  std::cout << "signed rounding stays within half a cell; the measured start lies exactly on the search lattice\n";
}
