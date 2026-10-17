#ifndef P2B_REACTIVE_STAIR_COLLISION_H
#define P2B_REACTIVE_STAIR_COLLISION_H

// Local experiment contract. This header has no ROS dependency and is not
// connected to scan_05's GridMap until the three input producers are verified.
#include <cmath>
#include <limits>
#include <map>
#include <set>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

namespace reactive_stair {

struct Cell2 {
  int x;
  int y;
  bool operator<(const Cell2 &other) const { return std::tie(x, y) < std::tie(other.x, other.y); }
};

struct Cell3 {
  int x;
  int y;
  int z;
  bool operator<(const Cell3 &other) const {
    return std::tie(x, y, z) < std::tie(other.x, other.y, other.z);
  }
};

enum class Support { Unknown, Flat, Stair, Unsupported };
enum class Occupancy { Unknown, Free, Occupied };
enum class Verdict {
  Free,
  InvalidQuery,
  OutOfMap,
  MissingInput,
  StaleInput,
  Person,
  UnknownObstacle,
  StaticObstacle,
  UnknownSupport,
  UnsupportedTerrain,
  WrongHeight,
};

struct SurfaceCell {
  Support support = Support::Unknown;
  double elevation_m = 0.0;  // World-frame ground elevation, including tread interiors.
};

struct TerrainSnapshot {
  std::string source_id;
  std::string frame;
  double stamp_s = 0.0;
  double resolution_m = 0.0;
  double origin_x_m = 0.0;
  double origin_y_m = 0.0;
  // Several ground elevations may share an XY cell in a layered tomogram.
  std::map<Cell2, std::vector<SurfaceCell>> cells;
};

struct Track {
  std::string id;
  double stamp_s = 0.0;
  double x_m = 0.0;
  double y_m = 0.0;
  double radius_m = 0.0;
};

// Each accepted batch is a complete current observation, including an empty
// clearing batch. A stale or invalid batch blocks all queries; no motion model.
struct TrackSnapshot {
  std::string source_id;
  std::string frame;
  double stamp_s = 0.0;
  bool complete = false;
  std::vector<Track> tracks;
};

struct Query {
  std::string frame;
  double stamp_s = 0.0;
  double x_m = 0.0;
  double y_m = 0.0;
  double z_m = 0.0;
  bool in_map = false;
};

// Occupancy must come from a source that excludes positively classified
// terrain. Unclassified raw hits belong in this layer as Occupied.
struct NonTerrainVoxel {
  Occupancy occupancy = Occupancy::Unknown;
  std::string source_id;
  std::string frame;
  double stamp_s = 0.0;
};

struct Parameters {
  double track_max_age_s = 0.25;
  double terrain_max_age_s = 0.5;
  double obstacle_max_age_s = 0.25;
  double robot_radius_m = 0.25;
  double body_clearance_m = 0.4;
  double body_height_tolerance_m = 0.12;
};

inline bool fresh(double now, double stamp, double max_age) {
  return std::isfinite(now) && std::isfinite(stamp) && std::isfinite(max_age) &&
         max_age >= 0.0 && now >= stamp && now - stamp <= max_age;
}

inline bool valid(const TerrainSnapshot &value) {
  if (value.source_id.empty() || value.frame.empty() || !std::isfinite(value.stamp_s) ||
      !std::isfinite(value.resolution_m) || value.resolution_m <= 0.0 ||
      !std::isfinite(value.origin_x_m) || !std::isfinite(value.origin_y_m) ||
      value.cells.empty())
    return false;
  for (const auto &entry : value.cells) {
    if (entry.second.empty()) return false;
    for (const SurfaceCell &surface : entry.second)
      if (!std::isfinite(surface.elevation_m)) return false;
  }
  return true;
}

inline bool valid(const TrackSnapshot &value) {
  if (!value.complete || value.source_id.empty() || value.frame.empty() ||
      !std::isfinite(value.stamp_s)) return false;
  std::set<std::string> ids;
  for (const Track &track : value.tracks) {
    if (track.id.empty() || !ids.insert(track.id).second || !std::isfinite(track.stamp_s) ||
        track.stamp_s > value.stamp_s || !std::isfinite(track.x_m) ||
        !std::isfinite(track.y_m) || !std::isfinite(track.radius_m) || track.radius_m < 0.0)
      return false;
  }
  return true;
}

class CollisionDecision {
 public:
  explicit CollisionDecision(Parameters parameters) : p_(parameters) {}

  bool acceptTerrain(const TerrainSnapshot &value) {
    terrain_ready_ = valid(value);
    if (terrain_ready_) terrain_ = value;
    return terrain_ready_;
  }

  bool acceptTracks(const TrackSnapshot &value) {
    tracks_ready_ = valid(value);
    if (tracks_ready_) tracks_ = value;
    return tracks_ready_;
  }

  Verdict decide(const Query &query, const NonTerrainVoxel &obstacle) const {
    if (query.frame.empty() || !std::isfinite(query.stamp_s) ||
        !std::isfinite(query.x_m) || !std::isfinite(query.y_m) ||
        !std::isfinite(query.z_m) || !std::isfinite(p_.robot_radius_m) ||
        p_.robot_radius_m < 0.0 || !std::isfinite(p_.body_clearance_m) ||
        !std::isfinite(p_.body_height_tolerance_m) || p_.body_height_tolerance_m < 0.0)
      return Verdict::InvalidQuery;
    if (!query.in_map) return Verdict::OutOfMap;
    if (!terrain_ready_ || !tracks_ready_ || obstacle.source_id.empty()) return Verdict::MissingInput;
    if (query.frame != terrain_.frame || query.frame != tracks_.frame || query.frame != obstacle.frame)
      return Verdict::MissingInput;
    if (!fresh(query.stamp_s, tracks_.stamp_s, p_.track_max_age_s) ||
        !fresh(query.stamp_s, terrain_.stamp_s, p_.terrain_max_age_s) ||
        !fresh(query.stamp_s, obstacle.stamp_s, p_.obstacle_max_age_s))
      return Verdict::StaleInput;
    for (const Track &track : tracks_.tracks) {
      if (!fresh(query.stamp_s, track.stamp_s, p_.track_max_age_s))
        return Verdict::StaleInput;
      const double radius = p_.robot_radius_m + track.radius_m;
      const double dx = query.x_m - track.x_m;
      const double dy = query.y_m - track.y_m;
      if (dx * dx + dy * dy <= radius * radius) return Verdict::Person;
    }
    if (obstacle.occupancy == Occupancy::Unknown) return Verdict::UnknownObstacle;
    if (obstacle.occupancy == Occupancy::Occupied) return Verdict::StaticObstacle;
    const double ix = std::floor((query.x_m - terrain_.origin_x_m) / terrain_.resolution_m);
    const double iy = std::floor((query.y_m - terrain_.origin_y_m) / terrain_.resolution_m);
    if (!std::isfinite(ix) || !std::isfinite(iy) ||
        ix < std::numeric_limits<int>::min() || ix > std::numeric_limits<int>::max() ||
        iy < std::numeric_limits<int>::min() || iy > std::numeric_limits<int>::max())
      return Verdict::InvalidQuery;
    const Cell2 cell{static_cast<int>(ix), static_cast<int>(iy)};
    const auto found = terrain_.cells.find(cell);
    if (found == terrain_.cells.end()) return Verdict::UnknownSupport;
    bool supported_here = false;
    bool unknown_here = false;
    for (const SurfaceCell &surface : found->second) {
      if (std::abs(query.z_m - surface.elevation_m - p_.body_clearance_m) >
          p_.body_height_tolerance_m) continue;
      if (surface.support == Support::Unsupported) return Verdict::UnsupportedTerrain;
      if (surface.support == Support::Unknown) unknown_here = true;
      if (surface.support == Support::Flat || surface.support == Support::Stair)
        supported_here = true;
    }
    if (unknown_here) return Verdict::UnknownSupport;
    return supported_here ? Verdict::Free : Verdict::WrongHeight;
  }

 private:
  Parameters p_;
  TerrainSnapshot terrain_;
  TrackSnapshot tracks_;
  bool terrain_ready_ = false;
  bool tracks_ready_ = false;
};

}  // namespace reactive_stair

#endif
