#include <plan_env/support_gap_mask.h>
#include <cmath>
#include <iostream>

// Offline diagnostic using the unchanged production mask implementation.
int main(int argc, char **argv) {
  if (argc != 2) return 2;
  reactive_stair::SupportGapMask mask(argv[1], "10479033888964413526", .35);
  double x, y, z, yaw;
  while (std::cin >> x >> y >> z >> yaw) {
    const double dx = .18 * std::cos(yaw), dy = .18 * std::sin(yaw);
    std::cout << mask.blocks(x + dx, y + dy, z - .3) << ' '
              << mask.blocks(x - dx, y - dy, z - .3) << '\n';
  }
}
