#pragma once
#include <plan_env/evidence_floor_fill.h>

namespace reactive_stair {
// This result explains a rejected selected-surface query; it never grants support.
struct EvidenceFloorDiagnostic {
  bool physical_floor = false;
  bool evidence_candidate = false;
  bool navigation_present = false;
  bool edge_blocked = false;
  double floor_z = std::numeric_limits<double>::quiet_NaN();
  double square_gap_m = std::numeric_limits<double>::infinity();
  double witness_x = std::numeric_limits<double>::quiet_NaN();
  double witness_y = std::numeric_limits<double>::quiet_NaN();
  // 1: measured lower floor; 2: missing layer/column; 3: ambiguous near layers.
  int witness_kind = 0;
};

inline EvidenceFloorDiagnostic diagnoseEvidenceFloor(
    const TerrainSnapshot &navigation, const TerrainSnapshot &evidence,
    const PhysicalFloorSnapshot *physical, double x, double y, double ground_hint,
    double tolerance, double step, double radius, const Cell2 *navigation_cell = nullptr) {
  EvidenceFloorDiagnostic out;
  // Full payloads are validated once by the native snapshot decoder. Rewalking
  // every map cell per collision query would turn diagnostics into O(N^2) work.
  const auto metadata=[](const TerrainSnapshot &t) {
    return !t.source_id.empty() && !t.frame.empty() && !t.cells.empty() &&
        std::isfinite(t.resolution_m) && t.resolution_m>0 &&
        std::isfinite(t.origin_x_m) && std::isfinite(t.origin_y_m);
  };
  if (!physical || !physicalFloorMetadata(*physical) || !metadata(navigation) || !metadata(evidence) ||
      navigation.frame != evidence.frame || physical->frame != evidence.frame ||
      std::abs(navigation.resolution_m-evidence.resolution_m)>1e-9 ||
      std::abs(physical->resolution_m-evidence.resolution_m)>1e-9 ||
      !std::isfinite(x) || !std::isfinite(y) || !std::isfinite(ground_hint) ||
      !std::isfinite(tolerance) || tolerance<0 || !std::isfinite(step) || step<=0 ||
      !std::isfinite(radius) || radius<0 || radius>2) return out;
  Cell2 pc;
  if (!physicalFloorIndex(*physical,x,y,pc)) return out;
  const auto floors=physical->cells.find(pc);
  if (floors==physical->cells.end()) return out;
  const int layer=nearestPhysicalFloor(floors->second,ground_hint,tolerance);
  if (layer<0) return out;
  out.physical_floor=true;out.floor_z=floors->second[layer].elevation_m;

  Cell2 target;
  if (navigation_cell) target=*navigation_cell;
  else if (!evidenceFillIndex(x,navigation.origin_x_m,navigation.resolution_m,target.x) ||
      !evidenceFillIndex(y,navigation.origin_y_m,navigation.resolution_m,target.y)) return out;
  const auto original=navigation.cells.find(target);
  if (original!=navigation.cells.end()) for (const auto &surface:original->second)
    if (std::abs(surface.elevation_m-out.floor_z)<=tolerance) out.navigation_present=true;
  if (out.navigation_present) return out;

  // Locate the evidence cell(s) which the production fill maps into this exact
  // navigation cell. Different grid origins must not move the association.
  const double r=evidence.resolution_m;
  int ex,ey;
  if (!evidenceFillIndex(navigation.origin_x_m+(target.x+.5)*r,evidence.origin_x_m,r,ex) ||
      !evidenceFillIndex(navigation.origin_y_m+(target.y+.5)*r,evidence.origin_y_m,r,ey)) return out;
  for (int dx=-1;dx<=1;++dx) for(int dy=-1;dy<=1;++dy) {
    const Cell2 candidate{ex+dx,ey+dy};
    const auto found=evidence.cells.find(candidate);if(found==evidence.cells.end())continue;
    int nx,ny;
    if (!evidenceFillIndex(evidence.origin_x_m+(candidate.x+.5)*r,navigation.origin_x_m,r,nx) ||
        !evidenceFillIndex(evidence.origin_y_m+(candidate.y+.5)*r,navigation.origin_y_m,r,ny) ||
        nx!=target.x || ny!=target.y) continue;
    for (const auto &surface:found->second) {
      if (std::abs(surface.elevation_m-out.floor_z)>1e-5) continue;
      out.evidence_candidate=true;
      const int reach=static_cast<int>(std::ceil(radius/r))+1;
      for(int gx=-reach;gx<=reach;++gx)for(int gy=-reach;gy<=reach;++gy) {
        const double sx=std::max(0,std::abs(gx)-1)*r,sy=std::max(0,std::abs(gy)-1)*r;
        const double gap=std::hypot(sx,sy);
        if(sx*sx+sy*sy>radius*radius+1e-12)continue;
        const Cell2 witness{candidate.x+gx,candidate.y+gy};
        if(!physicalFloorDrop(*physical,evidence,witness,surface.elevation_m,step))continue;
        out.edge_blocked=true;
        if(gap>=out.square_gap_m)continue;
        out.square_gap_m=gap;
        out.witness_x=evidence.origin_x_m+(witness.x+.5)*r;
        out.witness_y=evidence.origin_y_m+(witness.y+.5)*r;
        Cell2 wi;out.witness_kind=2;
        if(physicalFloorIndex(*physical,out.witness_x,out.witness_y,wi)) {
          const auto ws=physical->cells.find(wi);
          if(ws!=physical->cells.end()) for(const auto &f:ws->second) {
            if(std::abs(f.elevation_m-surface.elevation_m)<=step) {out.witness_kind=3;break;}
            if(f.elevation_m<surface.elevation_m-step)out.witness_kind=1;
          }
        }
      }
    }
  }
  return out;
}
} // namespace reactive_stair
