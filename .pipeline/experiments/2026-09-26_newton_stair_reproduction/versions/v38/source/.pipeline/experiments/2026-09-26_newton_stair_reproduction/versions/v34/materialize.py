"""Preserve v33 and give SCAN's copy of the navigation ground PCT's uninflated floor where it lacks it, except beside drops.

audits/2026-09-29_corridor_entry/RESULT.md replays v32's and v33's corridor-entry stands: four corridor cells of PCT's
pinned navigation ground carry the landing height instead of the floor (v32's blocker), and at the entry the ground
keeps the floor only in a band 0.8-1.0 m wide, with PCT's route 0.04-0.17 m inside its east edge (v33's blocker).
Dr Sun chose the floor fallback in SCAN on 2026-09-29; PLAN.md adds the drop guard.

v34 copies runtime/scan64_input_refresh_v31 (v31's build, run unchanged by v32 and v33) to
runtime/scan65_evidence_floor_v34 and changes three files:
- plan_env/evidence_floor_fill.h (new): addGuardedEvidenceFloor, the pure rule;
- plan_env/grid_map.h: the include, the supportGround declaration and the reactive_navigation_ground_ member;
- plan_env/scan_reactive_grid_methods.inc: supportGround, and its use in the tomogram and surface callbacks.
Edits insert lines only. As in v31, anchors match the file's own line endings, inserted lines take the ending of the
anchor line they follow, and removing the insertions must give back the scan64 bytes exactly.
"""
from pathlib import Path
import difflib
import hashlib
import json
import re
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
OLD = BASE / "runtime/scan64_input_refresh_v31"
NEW = BASE / "runtime/scan65_evidence_floor_v34"
HEADER = "src/plan_env/include/plan_env/grid_map.h"
METHODS = "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc"
FILL = "src/plan_env/include/plan_env/evidence_floor_fill.h"
AUDIT = BASE / "audits/2026-09-29_corridor_entry"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

FILL_TEXT = """#ifndef P2B_EVIDENCE_FLOOR_FILL_H
#define P2B_EVIDENCE_FLOOR_FILL_H

// v34 (Dr Sun, 2026-09-29; audits/2026-09-29_corridor_entry). SCAN's footprint
// support reads PCT's navigation ground, which PCT trims by its obstacle-distance
// inflation. The surface evidence is PCT's uninflated selection of the same
// ground. Where the navigation cell containing an evidence cell's centre has no
// layer within tolerance_m of an evidence layer, the returned ground gains that
// layer, unless a drop lies within guard_radius_m: an evidence cell whose square
// comes within guard_radius_m of the candidate's square, with no surface within
// step_m of the layer and either no surface at all or one more than step_m below
// it. A cell with only higher surfaces is solid (a wall under an upper floor);
// LiDAR occupancy still decides obstacles. Navigation layers are never changed or
// removed. Unusable evidence adds nothing, as it scores exactly as without
// evidence in the step score (v30).
#include <plan_env/reactive_collision.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <vector>

namespace reactive_stair {

struct EvidenceFloorFill {
  bool evidence_used = false;
  std::size_t added = 0;          // evidence layers added to the navigation ground
  std::size_t drop_rejected = 0;  // candidates rejected because a drop lies within the guard
};

inline bool evidenceFillIndex(double coordinate, double origin, double resolution, int &index) {
  const double value = std::floor((coordinate - origin) / resolution);
  if (!std::isfinite(value) || value < std::numeric_limits<int>::min() ||
      value > std::numeric_limits<int>::max()) return false;
  index = static_cast<int>(value);
  return true;
}

inline TerrainSnapshot addGuardedEvidenceFloor(const TerrainSnapshot &navigation,
                                               const TerrainSnapshot *evidence,
                                               double tolerance_m, double step_m,
                                               double guard_radius_m,
                                               EvidenceFloorFill *summary = nullptr) {
  TerrainSnapshot out = navigation;
  EvidenceFloorFill fill;
  const bool usable = evidence != nullptr && valid(navigation) && valid(*evidence) &&
      evidence->frame == navigation.frame &&
      std::abs(evidence->resolution_m - navigation.resolution_m) <= 1e-9 &&
      std::isfinite(tolerance_m) && tolerance_m >= 0.0 &&
      std::isfinite(step_m) && step_m > 0.0 &&
      std::isfinite(guard_radius_m) && guard_radius_m >= 0.0;
  if (!usable) {
    if (summary) *summary = fill;
    return out;
  }
  fill.evidence_used = true;
  const double resolution = navigation.resolution_m;
  // Evidence cells whose squares come within guard_radius_m of the candidate cell's square.
  std::vector<Cell2> guard;
  const int reach = static_cast<int>(std::ceil(guard_radius_m / resolution)) + 1;
  for (int dx = -reach; dx <= reach; ++dx)
    for (int dy = -reach; dy <= reach; ++dy) {
      const double gap_x = std::max(0, std::abs(dx) - 1) * resolution;
      const double gap_y = std::max(0, std::abs(dy) - 1) * resolution;
      if (gap_x * gap_x + gap_y * gap_y <= guard_radius_m * guard_radius_m + 1e-12)
        guard.push_back({dx, dy});
    }
  // A drop: no surface within step_m of the level, and no surface at all or one below it.
  const auto drop = [&](const Cell2 &cell, double level) {
    const auto found = evidence->cells.find(cell);
    if (found == evidence->cells.end()) return true;
    bool lower = false;
    for (const SurfaceCell &surface : found->second) {
      if (std::abs(surface.elevation_m - level) <= step_m) return false;
      if (surface.elevation_m < level - step_m) lower = true;
    }
    return lower;
  };
  for (const auto &entry : evidence->cells) {
    int ix = 0, iy = 0;
    if (!evidenceFillIndex(evidence->origin_x_m + (entry.first.x + 0.5) * resolution,
                           navigation.origin_x_m, resolution, ix) ||
        !evidenceFillIndex(evidence->origin_y_m + (entry.first.y + 0.5) * resolution,
                           navigation.origin_y_m, resolution, iy)) continue;
    const Cell2 target{ix, iy};
    for (const SurfaceCell &candidate : entry.second) {
      const double level = candidate.elevation_m;
      const auto present = out.cells.find(target);
      if (present != out.cells.end() &&
          std::any_of(present->second.begin(), present->second.end(), [&](const SurfaceCell &surface) {
            return std::abs(surface.elevation_m - level) <= tolerance_m;
          })) continue;
      bool rejected = false;
      for (const Cell2 &offset : guard)
        if (drop({entry.first.x + offset.x, entry.first.y + offset.y}, level)) {
          rejected = true;
          break;
        }
      if (rejected) {
        ++fill.drop_rejected;
        continue;
      }
      // The decoder's default status; the step score labels it with the other layers.
      out.cells[target].push_back({Support::Stair, level});
      ++fill.added;
    }
  }
  if (summary) *summary = fill;
  return out;
}

}  // namespace reactive_stair

#endif
"""

# Each edit inserts lines between two adjacent anchors (either may be empty); see v31/materialize.py.
HEADER_EDITS = [
    ("""#include <plan_env/eth_step_score_adaptation.h>
""", """#include <plan_env/evidence_floor_fill.h>
""", """#include <set>
"""),
    ("""  reactive_stair::TerrainSnapshot decodeReactiveGround(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) const;
""", """  // v34: the navigation ground plus the guarded evidence floor (evidence_floor_fill.h).
  reactive_stair::TerrainSnapshot supportGround(const reactive_stair::TerrainSnapshot &navigation);
""", """  void reactiveSurfaceGroundCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg);
"""),
    ("""  reactive_stair::TerrainSnapshot reactive_ground_; // Unscored positive ground evidence.
""", """  // v34: the navigation ground as decoded. New evidence is always applied to it,
  // never to reactive_ground_, which holds the augmented copy.
  reactive_stair::TerrainSnapshot reactive_navigation_ground_;
""", """  // Explicit raw-return classification evidence; scored navigation support stays separate.
"""),
]

METHOD_EDITS = [
    ("""  return terrain;
}

""", """reactive_stair::TerrainSnapshot GridMap::supportGround(const reactive_stair::TerrainSnapshot &navigation) {
  // v34: PCT's navigation ground is inflated; the surface evidence is its
  // uninflated selection. Add the evidence floor that the navigation ground lacks,
  // except beside drops (audits/2026-09-29_corridor_entry, versions/v34/PLAN.md).
  reactive_stair::EvidenceFloorFill fill;
  auto ground = reactive_stair::addGuardedEvidenceFloor(navigation, &reactive_surface_ground_,
      reactive_parameters_.body_height_tolerance_m, reactive_stair::StepScoreParameters{}.critical_height_m,
      mp_.double_cylinder_radius_, &fill);
  size_t layers = 0;
  for (const auto &entry : navigation.cells) layers += entry.second.size();
  RCLCPP_INFO(node_->get_logger(),
      "evidence_floor_fill evidence_used=%d navigation_layers=%zu added=%zu drop_rejected=%zu",
      fill.evidence_used ? 1 : 0, layers, fill.added, fill.drop_rejected);
  return ground;
}

""", """void GridMap::reactiveTomogramCallback(sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) {
"""),
    ("""  auto terrain = decodeReactiveGround(msg);
""", """  // v34: keep the navigation ground as decoded, and give SCAN's copy the guarded
  // evidence floor. An invalid ground passes unchanged.
  reactive_navigation_ground_ = terrain;
  terrain = supportGround(terrain);
""", """  if (terrain.cells.empty()) {
"""),
    ("""  // ground. Unusable evidence scores exactly as without evidence.
""", """  // v34: re-augment the navigation ground as decoded with this evidence, so the
  // result does not depend on which message arrived first.
  if (!reactive_ground_.cells.empty()) reactive_ground_ = supportGround(reactive_navigation_ground_);
""", """  if (!reactive_ground_.cells.empty()) {
"""),
]

EDITS = ((HEADER, HEADER_EDITS), (METHODS, METHOD_EDITS))


def anchor_pattern(text):
    """A byte-exact pattern for text whose line endings may be LF or CRLF in the file."""
    return r"\r?\n".join(re.escape(part) for part in text.split("\n"))


def apply_edits(before, edits):
    """Insert every edit into `before` (bytes as surrogate-escaped str); return the text and insertions."""
    after, inserted = before, []
    for anchor_before, lines, anchor_after in edits:
        matches = list(re.finditer(anchor_pattern(anchor_before + anchor_after), after))
        assert len(matches) == 1, (anchor_before[:60], anchor_after[:60], len(matches))
        match = matches[0]
        split = match.start() + len(re.match(anchor_pattern(anchor_before), after[match.start():]).group(0))
        # The line ending of the anchor line the insertion follows, else of the one it precedes.
        if anchor_before:
            eol = "\r\n" if after[:split].endswith("\r\n") else "\n"
        else:
            first = re.match(r"[^\n]*\n", after[split:]).group(0)
            eol = "\r\n" if first.endswith("\r\n") else "\n"
        assert lines.endswith("\n")
        text = lines.replace("\n", eol)
        after = after[:split] + text + after[split:]
        inserted.append((split, text))
    return after, inserted


def without(after, inserted):
    """Remove the insertions again (latest first); must give back the parent bytes."""
    offsets, text = [], after
    for split, piece in inserted:
        offsets = [(s + len(piece) if s >= split else s, p) for s, p in offsets] + [(split, piece)]
    for split, piece in sorted(offsets, reverse=True):
        assert text[split:split + len(piece)] == piece
        text = text[:split] + text[split + len(piece):]
    return text


parent = json.loads((HERE.parent / "v33/manifest.json").read_text())
assert not NEW.exists() and not (HERE / "prepared.json").exists()
for name, digest in parent["source_files"].items():
    assert sha(ROOT / name) == digest, name
native = json.loads((OLD / "source_sha256.json").read_text())
for name, digest in native.items():
    assert sha(OLD / name) == digest, name
assert FILL not in native
diagnosis = {str(p.relative_to(ROOT)): sha(p) for p in
             [AUDIT / "RESULT.md", AUDIT / "summary.json", AUDIT / "route_support_margin.json",
              AUDIT / "grounds/grounds.json", AUDIT / "probe_derivation.json"] +
             sorted(AUDIT.glob("v3[23]_stand/result_*.json"))}

shutil.copytree(OLD / "src", NEW / "src")
changes, preimages, line_endings = [], {}, {}
for relative, edits in EDITS:
    path = NEW / relative
    raw = path.read_bytes()
    before = raw.decode("utf-8", "surrogateescape")
    after, inserted = apply_edits(before, edits)
    assert without(after, inserted) == before, relative
    new_raw = after.encode("utf-8", "surrogateescape")
    added_cr = sum(piece.count("\r") for _, piece in inserted)
    assert new_raw.count(b"\r") == raw.count(b"\r") + added_cr, relative
    path.write_bytes(new_raw)
    preimages[relative] = raw
    line_endings[relative] = {"parent_crlf_lines": raw.count(b"\r\n"), "parent_lines": raw.count(b"\n"),
                              "inserted": ["CRLF" if piece.endswith("\r\n") else "LF" for _, piece in inserted]}
    changes.append("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                fromfile="v33/" + relative, tofile="v34/" + relative)))
(NEW / FILL).write_text(FILL_TEXT)
changes.append("".join(difflib.unified_diff([], FILL_TEXT.splitlines(True), fromfile="/dev/null", tofile="v34/" + FILL)))
for relative, raw in preimages.items():
    preimage = HERE / "parent_source" / relative
    preimage.parent.mkdir(parents=True, exist_ok=True)
    preimage.write_bytes(raw)
    assert sha(preimage) == native[relative], relative
(HERE / "changes.patch").write_bytes("".join(changes).encode("utf-8", "surrogateescape"))

manifest = {str(p.relative_to(NEW)): sha(p) for p in sorted((NEW / "src").rglob("*")) if p.is_file()}
assert set(manifest) == set(native) | {FILL}
assert {name for name in manifest if manifest.get(name) != native.get(name)} == {HEADER, METHODS, FILL}
(NEW / "source_sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
identity = BASE / "repairs/2026-09-26_generic_occupancy/candidate65_evidence_floor_v34_identity.json"
assert not identity.exists()
identity.write_text(json.dumps({
    "source_sha256": manifest, "integration_version": "v34",
    "parent": {"native_build": str(OLD.relative_to(ROOT)), **{relative: native[relative] for relative, _ in EDITS}},
    "added_file": FILL, "line_endings": line_endings, "diagnosis": diagnosis,
    "claim": "Unvalidated: when SCAN accepts its ground inputs, its copy of PCT's navigation ground gains each surface-"
             "evidence layer that the navigation cell containing the evidence cell's centre lacks within 0.12 m "
             "(body_height_tolerance), unless an evidence cell within 0.35 m (double_cylinder_radius, square to "
             "square) of the candidate has no surface within 0.26 m (the step capability) of the layer and either no "
             "surface or one more than 0.26 m below it. New evidence re-augments the navigation ground as decoded. "
             "Step score, support query, decision, thresholds, occupancy and planner unchanged"},
    indent=2) + "\n")
for name in ("building_planner.yaml", "flat_planner.yaml"):
    shutil.copyfile(HERE.parent / "v33" / name, HERE / name)
    assert (HERE / name).read_bytes() == (HERE.parent / "v33" / name).read_bytes(), name
(HERE / "prepared.json").write_text(json.dumps({
    "parent": "v33", "status": "unfrozen_candidate", "native_build": str(NEW.relative_to(ROOT)),
    "changed_files": [str((NEW / relative).relative_to(ROOT)) for relative in (HEADER, METHODS, FILL)] +
                     [str(identity.relative_to(ROOT))],
    "native_parent": str(OLD.relative_to(ROOT)),
    "diagnosis": str(AUDIT.relative_to(ROOT))}, indent=2) + "\n")
print(json.dumps({"v34": "native candidate scan65 prepared; acceptance pending", "line_endings": line_endings}))
