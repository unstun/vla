// v30 support contract, header part (versions/v30/PLAN.md step 2).
// The same source is compiled against the plan_env headers of v29 (red) and
// v30 (green). It scores the synthetic cases and the pinned Building grounds,
// and writes every label for check.py to compare with oracle.py.
#include <plan_env/eth_step_score_adaptation.h>

#include <chrono>
#include <cmath>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using namespace reactive_stair;

// v30 has an evidence overload; v29 does not. Both trees compile this call.
template <class T>
auto scoreWith(const T &input, const T *evidence, int)
    -> decltype(precomputeEthStyleStepScores(input, StepScoreParameters{}, evidence)) {
  return precomputeEthStyleStepScores(input, StepScoreParameters{}, evidence);
}
template <class T>
StepScoreResult scoreWith(const T &input, const T *, long) { return precomputeEthStyleStepScores(input); }
template <class T>
constexpr auto overloadProbe(int) -> decltype(precomputeEthStyleStepScores(std::declval<const T &>(), StepScoreParameters{},
                                                                         std::declval<const T *>()), true) { return true; }
template <class T>
constexpr bool overloadProbe(long) { return false; }

TerrainSnapshot snapshot(const std::string &id) {
  TerrainSnapshot value;
  value.source_id = id;
  value.frame = "world";
  value.stamp_s = 1.0;
  value.resolution_m = 0.1;
  return value;
}

void write(std::ostream &out, const std::string &name, const StepScoreResult &result) {
  for (const auto &entry : result.support.cells) {
    const auto &scores = result.scores.at(entry.first);
    for (size_t layer = 0; layer < entry.second.size(); ++layer)
      out << name << "," << entry.first.x << "," << entry.first.y << "," << layer << ","
          << entry.second[layer].elevation_m << "," << static_cast<int>(entry.second[layer].support) << ","
          << scores[layer].known << "," << scores[layer].first_pass_height_m << "\n";
  }
}

TerrainSnapshot decode(const std::string &path) {
  // Repeats GridMap::decodeReactiveGround with the planner defaults:
  // 0.1 m cells, 0.03 m z offset, cost limit 20.
  std::ifstream stream(path, std::ios::binary);
  stream.seekg(0, std::ios::end);
  const auto bytes = static_cast<size_t>(stream.tellg());
  stream.seekg(0);
  std::vector<float> values(bytes / sizeof(float));
  stream.read(reinterpret_cast<char *>(values.data()), static_cast<std::streamsize>(bytes));
  if (!stream || bytes == 0 || bytes % 16) throw std::runtime_error("bad ground file " + path);
  const auto usable = [&](size_t i) {
    return std::isfinite(values[4 * i]) && std::isfinite(values[4 * i + 1]) && std::isfinite(values[4 * i + 2]) &&
           std::isfinite(values[4 * i + 3]) && values[4 * i + 3] <= 20.0;
  };
  double min_x = std::numeric_limits<double>::infinity(), min_y = min_x;
  for (size_t i = 0; i < values.size() / 4; ++i)
    if (usable(i)) { min_x = std::min(min_x, double(values[4 * i])); min_y = std::min(min_y, double(values[4 * i + 1])); }
  TerrainSnapshot terrain = snapshot(path);
  terrain.origin_x_m = min_x - 0.05;
  terrain.origin_y_m = min_y - 0.05;
  for (size_t i = 0; i < values.size() / 4; ++i) {
    if (!usable(i)) continue;
    const double ix = std::floor((values[4 * i] - terrain.origin_x_m) / 0.1);
    const double iy = std::floor((values[4 * i + 1] - terrain.origin_y_m) / 0.1);
    terrain.cells[{static_cast<int>(ix), static_cast<int>(iy)}].push_back({Support::Stair, values[4 * i + 2] - 0.03});
  }
  return terrain;
}

int main(int argc, char **argv) {
  if (argc != 5) {
    std::cerr << "usage: step_contract cases.txt navigation.f32 evidence.f32 out_dir\n";
    return 2;
  }
  const std::string out_dir = argv[4];
  std::ofstream cases_out(out_dir + "/cases_labels.csv");
  cases_out << std::setprecision(17) << "case,ix,iy,layer,elevation,support,known,first_pass\n";
  std::ifstream cases(argv[1]);
  std::string line, name, mode;
  TerrainSnapshot nav, evidence;
  size_t case_count = 0, cell_set_violations = 0;
  while (std::getline(cases, line)) {
    std::istringstream in(line);
    std::string tag;
    in >> tag;
    if (tag == "case") {
      in >> name;
      nav = snapshot("nav:" + name);
      evidence = snapshot("evidence:" + name);
    } else if (tag == "evidence_mode") {
      in >> mode;
    } else if (tag == "evidence_origin") {
      in >> evidence.origin_x_m >> evidence.origin_y_m;
    } else if (tag == "N" || tag == "E") {
      int x, y;
      double z;
      in >> x >> y >> z;
      (tag == "N" ? nav : evidence).cells[{x, y}].push_back({Support::Stair, z});
    } else if (tag == "end") {
      if (mode == "frame_map") evidence.frame = "map";
      if (mode == "resolution_0.2") evidence.resolution_m = 0.2;
      if (mode == "empty") evidence.cells.clear();
      if (mode == "nan") evidence.cells[{0, 0}].push_back({Support::Stair, std::numeric_limits<double>::quiet_NaN()});
      const StepScoreResult result = scoreWith(nav, mode == "none" ? nullptr : &evidence, 0);
      // Evidence must never add or remove a scored cell or layer.
      if (result.support.cells.size() != nav.cells.size()) ++cell_set_violations;
      for (const auto &entry : nav.cells) {
        const auto found = result.support.cells.find(entry.first);
        if (found == result.support.cells.end() || found->second.size() != entry.second.size()) ++cell_set_violations;
      }
      write(cases_out, name, result);
      ++case_count;
    }
  }
  const TerrainSnapshot navigation = decode(argv[2]);
  const TerrainSnapshot surface = decode(argv[3]);
  // Wall time of one full-map scoring (best of three) in the tree under test.
  const auto timed = [&](const TerrainSnapshot *evidence_ptr, double &best_ms) {
    StepScoreResult out;
    best_ms = std::numeric_limits<double>::infinity();
    for (int repeat = 0; repeat < 3; ++repeat) {
      const auto start = std::chrono::steady_clock::now();
      out = scoreWith(navigation, evidence_ptr, 0);
      best_ms = std::min(best_ms, std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count());
    }
    return out;
  };
  double ms_with = 0.0, ms_without = 0.0;
  const StepScoreResult map_result = timed(&surface, ms_with);
  timed(nullptr, ms_without);
  std::ofstream map_out(out_dir + "/map_labels.csv");
  map_out << std::setprecision(17) << "case,ix,iy,layer,elevation,support,known,first_pass\n";
  write(map_out, "map", map_result);
  size_t layers = 0;
  for (const auto &entry : navigation.cells) layers += entry.second.size();
  std::ofstream summary(out_dir + "/step.json");
  summary << std::setprecision(17) << "{\"evidence_overload\":" << (overloadProbe<TerrainSnapshot>(0) ? "true" : "false")
          << ",\"cases\":" << case_count << ",\"cell_set_violations\":" << cell_set_violations
          << ",\"map_cells\":" << navigation.cells.size() << ",\"map_layers\":" << layers
          << ",\"evidence_cells\":" << surface.cells.size()
          << ",\"scoring_ms_with_evidence_best_of_3\":" << ms_with
          << ",\"scoring_ms_without_evidence_best_of_3\":" << ms_without
          << ",\"navigation_origin\":[" << navigation.origin_x_m << "," << navigation.origin_y_m << "]"
          << ",\"evidence_origin\":[" << surface.origin_x_m << "," << surface.origin_y_m << "]}\n";
  std::cout << "[STEP-CONTRACT] cases=" << case_count << " map_layers=" << layers
            << " overload=" << overloadProbe<TerrainSnapshot>(0) << std::endl;
  return 0;
}
