#include "seed_polyline_sampling.h"
#include "collision_segment.h"
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <string>

using Eigen::Vector3d;
using reactive_stair::sampleSeedPolyline;
void require(bool ok, const char* message) { if (!ok) throw std::runtime_error(message); }
bool equal(const Vector3d& a, const Vector3d& b) { return (a.array() == b.array()).all(); }
double distanceFromSegment(const Vector3d& p, const Vector3d& a, const Vector3d& b) {
  const Vector3d delta = b - a;
  const double u = std::max(0.0, std::min(1.0, (p - a).dot(delta) / delta.squaredNorm()));
  return (p - a - u * delta).norm();
}
void verify(const reactive_stair::SeedSamplingResult& r, const std::vector<Vector3d>& raw,
            double spacing, double duration, size_t budget) {
  require(r.ready(), "sampling failed");
  require(r.points.size() <= budget && r.points.size() > 1, "output budget violated");
  require(equal(r.points.front(), raw.front()) && equal(r.points.back(), raw.back()), "endpoint changed");
  require(std::abs((r.points.size() - 1) * r.interval_s - duration) < 1e-12, "total duration changed");
  require(r.parent_edges.size() + 1 == r.points.size(), "missing parent attribution");
  for (size_t i = 1; i < r.points.size(); ++i) {
    const size_t parent = r.parent_edges[i - 1];
    require(parent + 1 < raw.size() && !equal(raw[parent], raw[parent + 1]), "parent refers to duplicate/wrong raw edge");
    require(distanceFromSegment(r.points[i - 1], raw[parent], raw[parent + 1]) < 1e-10 &&
            distanceFromSegment(r.points[i], raw[parent], raw[parent + 1]) < 1e-10, "subedge crosses an original corner");
    require((r.points[i] - r.points[i - 1]).norm() <= spacing + 1e-12, "spacing exceeded");
  }
  size_t cursor = 0;
  for (const auto& vertex : raw) {
    while (cursor < r.points.size() && !equal(r.points[cursor], vertex)) ++cursor;
    require(cursor < r.points.size(), "input vertex lost or reordered");
  }
  require(r.vertex_indices.size() == r.source_vertex_indices.size(), "vertex mapping absent");
  for (size_t i = 0; i < r.vertex_indices.size(); ++i)
    require(equal(r.points[r.vertex_indices[i]], raw[r.source_vertex_indices[i]]), "vertex mapping changed coordinates");
}

void corner() {
  const std::vector<Vector3d> raw{{0, 0, 0}, {1, 0, 0}, {1, 1, 0}};
  const auto r = sampleSeedPolyline(raw, .1, 4.0, 128);
  verify(r, raw, .1, 4.0, 128);
  auto occupied = [](const Vector3d& p, double) {
    return !((std::abs(p.y()) < .04 && p.x() >= 0 && p.x() <= 1) ||
             (std::abs(p.x() - 1) < .04 && p.y() >= 0 && p.y() <= 1));
  };
  require(!reactive_stair::collisionFreeSegment(raw.front(), raw.back(), .1, 0.0, occupied), "corner-cut control did not fail");
  for (size_t i = 1; i < r.points.size(); ++i)
    require(reactive_stair::collisionFreeSegment(r.points[i - 1], r.points[i], .1, 0.0, occupied), "corner-preserving chain blocked");
}

void duplicates_and_short_edge() {
  const std::vector<Vector3d> raw{{0,0,0},{0,0,0},{1e-8,0,0},{1e-8,0,0},{1e-8,.2,0},{1,.2,0}};
  const auto r = sampleSeedPolyline(raw, .1, 3.0, 128);
  verify(r, raw, .1, 3.0, 128);
  require(r.exact_duplicates_removed == 2, "duplicates not tracked");
  require(r.parent_edges.front() == 1, "duplicate collapse lost raw edge mapping");
  require(equal(r.points[r.vertex_indices[1]], raw[2]), "nonzero short edge removed");
}

void budgets() {
  const std::vector<Vector3d> raw{{0,0,0},{1,0,0}};
  const auto exact = sampleSeedPolyline(raw, .125, 2.0, 9);
  verify(exact, raw, .125, 2.0, 9);
  require(exact.points.size() == 9, "geometric exact budget count changed");
  const auto insufficient = sampleSeedPolyline(raw, .125, 2.0, 8);
  require(insufficient.status == reactive_stair::SeedSamplingStatus::BudgetExceeded && insufficient.points.empty(), "geometric shortage accepted");
  const std::vector<Vector3d> tiny{{0,0,0},{.5,0,0},{.500000001,.001,0},{1,0,0}};
  const auto capped = sampleSeedPolyline(tiny, .2, 2.0, 16);
  verify(capped, tiny, .2, 2.0, 16);
  require(capped.temporal_budget_capped && capped.points.size() == 16, "temporal cap not reported");
  require(capped.max_vertex_time_error_s > 0, "approximate timing incorrectly claimed exact");
}

void invalid() {
  const std::vector<Vector3d> raw{{0,0,0},{1,0,0}};
  for (double value : {0.0, -1.0, std::numeric_limits<double>::quiet_NaN()}) {
    require(!sampleSeedPolyline(raw, value, 2.0).ready(), "invalid spacing accepted");
    require(!sampleSeedPolyline(raw, .1, value).ready(), "invalid duration accepted");
  }
  require(!sampleSeedPolyline({{0,0,0},{std::numeric_limits<double>::infinity(),0,0}}, .1, 2.0).ready(), "nonfinite point accepted");
  require(sampleSeedPolyline({{0,0,0},{0,0,0}}, .1, 2.0).status == reactive_stair::SeedSamplingStatus::DegeneratePath, "all-duplicate path accepted");
}

void real_seed(const char* filename) {
  std::ifstream input(filename);
  require(input.good(), "captured seed absent");
  std::vector<Vector3d> raw;
  std::string line;
  while (std::getline(input, line)) {
    std::replace(line.begin(), line.end(), ',', ' ');
    std::istringstream row(line); double x, y, z;
    require(bool(row >> x >> y >> z), "invalid captured row"); raw.emplace_back(x,y,z);
  }
  require(raw.size() == 76, "wrong recorded seed");
  const auto r = sampleSeedPolyline(raw, .025, 5.52, 512);
  verify(r, raw, .025, 5.52, 512);
  size_t fallback = 0, changed_fallback = 0;
  for (size_t i = 1; i < r.points.size(); ++i) {
    const bool child = (r.points[i] - r.points[i - 1]).head<2>().squaredNorm() < 1e-4;
    const size_t parent = r.parent_edges[i - 1];
    const bool original = (raw[parent + 1] - raw[parent]).head<2>().squaredNorm() < 1e-4;
    fallback += child; changed_fallback += child != original;
  }
  std::cout.precision(17);
  std::cout << "METRICS points=" << r.points.size() << " interval=" << r.interval_s
            << " time_error=" << r.max_vertex_time_error_s << " capped=" << r.temporal_budget_capped
            << " fallback=" << fallback << " changed_fallback=" << changed_fallback << '\n';
  require(fallback > 0 && changed_fallback > 0, "fixture did not expose required actual-heading recheck");
  const auto again = sampleSeedPolyline(raw, .025, 5.52, 512);
  require(again.intervals_per_edge == r.intervals_per_edge, "quota distribution is not deterministic");
}

int main(int argc, char** argv) {
  try {
    require(argc == 2, "captured CSV path required");
    corner(); std::cout << "PASS corner\n";
    duplicates_and_short_edge(); std::cout << "PASS duplicates_and_short_edge\n";
    budgets(); std::cout << "PASS budgets\n";
    invalid(); std::cout << "PASS invalid\n";
    real_seed(argv[1]); std::cout << "PASS real_seed\n";
    return 0;
  } catch (const std::exception& error) { std::cerr << "FAIL " << error.what() << '\n'; return 1; }
}
