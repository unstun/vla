// Evaluate the exact native support header against the delivered PCT payload.
#include <plan_env/eth_step_score_adaptation.h>
#include <array>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc, char **argv) {
  if (argc != 2) throw std::runtime_error("expected float32 XYZI ground payload");
  std::ifstream input(argv[1], std::ios::binary);
  if (!input) throw std::runtime_error("input not found");
  std::vector<std::array<float, 4>> points;
  std::array<float, 4> point;
  double min_x = 1e9, min_y = 1e9;
  while (input.read(reinterpret_cast<char *>(point.data()), sizeof(point))) {
    points.push_back(point);
    min_x = std::min(min_x, static_cast<double>(point[0]));
    min_y = std::min(min_y, static_cast<double>(point[1]));
  }
  reactive_stair::TerrainSnapshot terrain;
  terrain.source_id = "actual_pct_payload"; terrain.frame = "world"; terrain.stamp_s = 1.0;
  terrain.resolution_m = 0.1; terrain.origin_x_m = min_x - 0.05; terrain.origin_y_m = min_y - 0.05;
  for (const auto &p : points) {
    const int x = std::floor((p[0] - terrain.origin_x_m) / terrain.resolution_m);
    const int y = std::floor((p[1] - terrain.origin_y_m) / terrain.resolution_m);
    terrain.cells[{x, y}].push_back({reactive_stair::Support::Stair, p[2] - 0.03});
  }
  const auto result = reactive_stair::precomputeEthStyleStepScores(terrain);
  std::cout << std::setprecision(10) << "x,y,z,support,known,first_height,score,critical_cells\n";
  for (const auto &cell : result.support.cells) {
    const double x = terrain.origin_x_m + (cell.first.x + 0.5) * 0.1;
    const double y = terrain.origin_y_m + (cell.first.y + 0.5) * 0.1;
    if (x < -5.9 || x > -4.8 || y < 0.0 || y > 7.5) continue;
    for (size_t i = 0; i < cell.second.size(); ++i) {
      const auto &p = cell.second[i];
      const auto &s = result.scores.at(cell.first)[i];
      if (p.elevation_m < -0.2 || p.elevation_m > 2.0) continue;
      std::cout << x << ',' << y << ',' << p.elevation_m << ',' << static_cast<int>(p.support) << ','
                << s.known << ',' << s.first_pass_height_m << ',' << s.score << ',' << s.critical_cells << '\n';
    }
  }
}
