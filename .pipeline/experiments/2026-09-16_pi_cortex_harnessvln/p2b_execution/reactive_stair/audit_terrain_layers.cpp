// Compile against an exact captured native header. No Python reimplementation.
#include <plan_env/eth_step_score_adaptation.h>
#include <array>
#include <fstream>
#include <iomanip>
#include <iostream>

using namespace reactive_stair;

int main(int argc, char **argv) {
  if (argc != 2) return 2;
  std::ifstream input(argv[1], std::ios::binary);
  std::vector<std::array<float, 4>> points;
  std::array<float, 4> p;
  double min_x = INFINITY, min_y = INFINITY;
  while (input.read(reinterpret_cast<char *>(p.data()), sizeof(p))) {
    if (!std::all_of(p.begin(), p.end(), [](float v) { return std::isfinite(v); }) || p[3] > 20.) continue;
    min_x = std::min(min_x, static_cast<double>(p[0]));
    min_y = std::min(min_y, static_cast<double>(p[1]));
    points.push_back(p);
  }
  if (points.empty() || !input.eof()) return 3;
  TerrainSnapshot t;
  t.source_id = "actual_selected_pct_payload";
  t.frame = "world";
  t.stamp_s = 1.;
  t.resolution_m = .1;
  t.origin_x_m = min_x - .05;
  t.origin_y_m = min_y - .05;
  for (auto point : points)
    t.cells[{static_cast<int>(std::floor((point[0] - t.origin_x_m) / .1)),
             static_cast<int>(std::floor((point[1] - t.origin_y_m) / .1))}].push_back({Support::Stair, point[2] - .03});
  const auto result = precomputeEthStyleStepScores(t);
  std::cout << "ix,iy,layer,x,y,z,support,first_pass,known,score\n" << std::setprecision(17);
  for (const auto &entry : result.support.cells)
    for (size_t i = 0; i < entry.second.size(); ++i) {
      const auto &s = entry.second[i];
      const auto &score = result.scores.at(entry.first)[i];
      std::cout << entry.first.x << ',' << entry.first.y << ',' << i << ','
                << t.origin_x_m + (entry.first.x + .5) * .1 << ','
                << t.origin_y_m + (entry.first.y + .5) * .1 << ','
                << s.elevation_m << ',' << static_cast<int>(s.support) << ','
                << score.first_pass_height_m << ',' << score.known << ',' << score.score << '\n';
    }
}
