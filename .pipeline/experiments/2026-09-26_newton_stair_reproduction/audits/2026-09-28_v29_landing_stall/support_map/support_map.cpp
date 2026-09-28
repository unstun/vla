// Dump SCAN's scored PCT support in a box, using the v29 native header-only
// step score (plan_env/eth_step_score_adaptation.h) on the pinned navigation
// ground. The decode repeats GridMap::decodeReactiveGround with the defaults
// that building_planner.yaml does not override: 0.1 m cells, 0.03 m z offset,
// cost limit 20. Usage: support_map ground.f32 out.csv xmin xmax ymin ymax
#include <plan_env/eth_step_score_adaptation.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <vector>

int main(int argc, char **argv) {
  if (argc != 7) return 2;
  std::ifstream stream(argv[1], std::ios::binary);
  std::vector<float> values;
  stream.seekg(0, std::ios::end);
  const auto bytes = static_cast<size_t>(stream.tellg());
  stream.seekg(0);
  values.assign(bytes / sizeof(float), 0.0f);
  stream.read(reinterpret_cast<char *>(values.data()), static_cast<std::streamsize>(bytes));
  if (!stream || bytes % 16) return 3;
  const double resolution = 0.1, z_offset = 0.03, cost_limit = 20.0;
  double min_x = std::numeric_limits<double>::infinity(), min_y = min_x;
  const size_t count = values.size() / 4;
  const auto usable = [&](size_t i) {
    const float x = values[4 * i], y = values[4 * i + 1], z = values[4 * i + 2], c = values[4 * i + 3];
    return std::isfinite(x) && std::isfinite(y) && std::isfinite(z) && std::isfinite(c) && c <= cost_limit;
  };
  for (size_t i = 0; i < count; ++i) {
    if (!usable(i)) continue;
    min_x = std::min(min_x, static_cast<double>(values[4 * i]));
    min_y = std::min(min_y, static_cast<double>(values[4 * i + 1]));
  }
  reactive_stair::TerrainSnapshot terrain;
  terrain.source_id = "support_map";
  terrain.frame = "world";
  terrain.stamp_s = 1.0;
  terrain.resolution_m = resolution;
  terrain.origin_x_m = min_x - resolution / 2.0;
  terrain.origin_y_m = min_y - resolution / 2.0;
  for (size_t i = 0; i < count; ++i) {
    if (!usable(i)) continue;
    const double ix = std::floor((values[4 * i] - terrain.origin_x_m) / resolution);
    const double iy = std::floor((values[4 * i + 1] - terrain.origin_y_m) / resolution);
    terrain.cells[{static_cast<int>(ix), static_cast<int>(iy)}].push_back(
        {reactive_stair::Support::Stair, values[4 * i + 2] - z_offset});
  }
  const auto scored = reactive_stair::precomputeEthStyleStepScores(terrain);
  const double xmin = std::atof(argv[3]), xmax = std::atof(argv[4]), ymin = std::atof(argv[5]), ymax = std::atof(argv[6]);
  std::ofstream out(argv[2]);
  out << std::setprecision(12) << "ix,iy,x0,y0,layer,elevation,support,known,first_pass_height,score\n";
  for (const auto &entry : scored.support.cells) {
    const double x0 = terrain.origin_x_m + entry.first.x * resolution;
    const double y0 = terrain.origin_y_m + entry.first.y * resolution;
    if (x0 + resolution < xmin || x0 > xmax || y0 + resolution < ymin || y0 > ymax) continue;
    const auto &scores = scored.scores.at(entry.first);
    for (size_t layer = 0; layer < entry.second.size(); ++layer)
      out << entry.first.x << "," << entry.first.y << "," << x0 << "," << y0 << "," << layer << ","
          << entry.second[layer].elevation_m << "," << static_cast<int>(entry.second[layer].support) << ","
          << scores[layer].known << "," << scores[layer].first_pass_height_m << "," << scores[layer].score << "\n";
  }
  std::cout << "origin " << std::setprecision(12) << terrain.origin_x_m << " " << terrain.origin_y_m
            << " cells " << terrain.cells.size() << std::endl;
  return 0;
}
