// v34 fill contract, header part (versions/v34/PLAN.md, K2).
// The same source is compiled against the plan_env headers of scan64 (red) and
// scan65 (green). Red has no fill header and passes every input through
// unchanged. The program applies the tree's rule to the synthetic cases and to
// the pinned Building grounds, and writes every output layer for check.py to
// compare with oracle.py.
#include <plan_env/eth_step_score_adaptation.h>
#if __has_include(<plan_env/evidence_floor_fill.h>)
#include <plan_env/evidence_floor_fill.h>
#define VLA_HAS_FILL 1
#else
#define VLA_HAS_FILL 0
#endif

#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace reactive_stair;

struct Fill {
  TerrainSnapshot ground;
  size_t added = 0, rejected = 0;
  bool used = false;
};

Fill fillWith(const TerrainSnapshot &navigation, const TerrainSnapshot *evidence) {
  Fill out;
#if VLA_HAS_FILL
  EvidenceFloorFill summary;
  out.ground = addGuardedEvidenceFloor(navigation, evidence, 0.12, 0.26, 0.35, &summary);
  out.added = summary.added;
  out.rejected = summary.drop_rejected;
  out.used = summary.evidence_used;
#else
  (void)evidence;
  out.ground = navigation;
#endif
  return out;
}

TerrainSnapshot snapshot(const std::string &id) {
  TerrainSnapshot value;
  value.source_id = id;
  value.frame = "world";
  value.stamp_s = 1.0;
  value.resolution_m = 0.1;
  return value;
}

TerrainSnapshot decode(const std::string &path) {
  // Repeats GridMap::decodeReactiveGround with the planner defaults:
  // 0.1 m cells, 0.03 m z offset, cost limit 20, layers in file order.
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

void writeLayers(std::ostream &out, const std::string &name, const TerrainSnapshot &terrain) {
  for (const auto &entry : terrain.cells)
    for (size_t layer = 0; layer < entry.second.size(); ++layer)
      out << name << "," << entry.first.x << "," << entry.first.y << "," << layer << "," << entry.second[layer].elevation_m << "\n";
}

int main(int argc, char **argv) {
  if (argc != 5) {
    std::cerr << "usage: fill_contract cases.txt navigation.f32 evidence.f32 out_dir\n";
    return 2;
  }
  const std::string out_dir = argv[4];
  std::ofstream cases_out(out_dir + "/cases_layers.csv");
  cases_out << std::setprecision(17) << "case,ix,iy,layer,elevation\n";
  std::ofstream cases_summary(out_dir + "/cases_summary.csv");
  cases_summary << "case,added,rejected,evidence_used,input_layers,output_layers\n";
  std::ifstream cases(argv[1]);
  std::string line, name, mode;
  TerrainSnapshot nav, evidence;
  size_t case_count = 0;
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
      const Fill result = fillWith(nav, mode == "none" ? nullptr : &evidence);
      size_t in_layers = 0, out_layers = 0;
      for (const auto &entry : nav.cells) in_layers += entry.second.size();
      for (const auto &entry : result.ground.cells) out_layers += entry.second.size();
      writeLayers(cases_out, name, result.ground);
      cases_summary << name << "," << result.added << "," << result.rejected << "," << result.used << ","
                    << in_layers << "," << out_layers << "\n";
      ++case_count;
    }
  }
  const TerrainSnapshot navigation = decode(argv[2]);
  const TerrainSnapshot surface = decode(argv[3]);
  // Wall time of one full-map fill (best of three) in the tree under test.
  Fill map_fill;
  double best_ms = std::numeric_limits<double>::infinity();
  for (int repeat = 0; repeat < 3; ++repeat) {
    const auto start = std::chrono::steady_clock::now();
    map_fill = fillWith(navigation, &surface);
    best_ms = std::min(best_ms, std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count());
  }
  // The added layers are the ones after a cell's navigation layers (the rule appends; it never removes or reorders).
  std::ofstream added_out(out_dir + "/map_added.csv");
  added_out << std::setprecision(17) << "ix,iy,layer,elevation\n";
  size_t kept_violations = 0, navigation_layers = 0;
  for (const auto &entry : map_fill.ground.cells) {
    const auto original = navigation.cells.find(entry.first);
    const size_t kept = original == navigation.cells.end() ? 0 : original->second.size();
    for (size_t layer = 0; layer < entry.second.size(); ++layer) {
      if (layer < kept) {
        if (entry.second[layer].elevation_m != original->second[layer].elevation_m ||
            entry.second[layer].support != original->second[layer].support) ++kept_violations;
      } else {
        added_out << entry.first.x << "," << entry.first.y << "," << layer << "," << entry.second[layer].elevation_m << "\n";
      }
    }
  }
  for (const auto &entry : navigation.cells) {
    navigation_layers += entry.second.size();
    if (!map_fill.ground.cells.count(entry.first)) ++kept_violations;
  }
  // Step-score labels of the added layers (v30's rule with the same evidence), for the record.
  const StepScoreResult scored = precomputeEthStyleStepScores(map_fill.ground, StepScoreParameters{}, &surface);
  std::map<int, size_t> added_labels;
  for (const auto &entry : scored.support.cells) {
    const auto original = navigation.cells.find(entry.first);
    const size_t kept = original == navigation.cells.end() ? 0 : original->second.size();
    for (size_t layer = kept; layer < entry.second.size(); ++layer) ++added_labels[static_cast<int>(entry.second[layer].support)];
  }
  std::ofstream summary(out_dir + "/fill.json");
  summary << std::setprecision(17) << "{\"fill_available\":" << (VLA_HAS_FILL ? "true" : "false")
          << ",\"cases\":" << case_count << ",\"map_navigation_layers\":" << navigation_layers
          << ",\"map_navigation_cells\":" << navigation.cells.size() << ",\"map_evidence_cells\":" << surface.cells.size()
          << ",\"map_added\":" << map_fill.added << ",\"map_rejected\":" << map_fill.rejected
          << ",\"map_evidence_used\":" << (map_fill.used ? "true" : "false")
          << ",\"map_output_cells\":" << map_fill.ground.cells.size() << ",\"navigation_layers_changed\":" << kept_violations
          << ",\"fill_ms_best_of_3\":" << best_ms << ",\"added_step_labels\":{";
  bool first = true;
  for (const auto &entry : added_labels) {
    summary << (first ? "" : ",") << "\"" << entry.first << "\":" << entry.second;
    first = false;
  }
  summary << "},\"navigation_origin\":[" << navigation.origin_x_m << "," << navigation.origin_y_m << "]"
          << ",\"evidence_origin\":[" << surface.origin_x_m << "," << surface.origin_y_m << "]}\n";
  std::cout << "[FILL-CONTRACT] cases=" << case_count << " added=" << map_fill.added << " rejected=" << map_fill.rejected
            << " fill=" << VLA_HAS_FILL << std::endl;
  return 0;
}
