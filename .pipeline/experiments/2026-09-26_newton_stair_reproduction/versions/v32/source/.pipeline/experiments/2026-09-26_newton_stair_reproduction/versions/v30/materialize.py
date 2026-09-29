"""Preserve v29 and let the pinned surface evidence decide walkway-edge drops in the step score.

v29_historical_full01 stalled on the upper landing. From saved inputs,
audits/2026-09-28_v29_landing_stall/RESULT.md shows the cause:
- the PCT route runs on the walkway's outer ring of navigation cells;
- SCAN's ETH-style step score marks that ring Unknown support, because the
  neighbouring cells exist only for other floors' surfaces;
- the frontier therefore cannot pass 8.6446 s.
Dr Sun chose option 1 on 2026-09-28.

v30 changes one rule and nothing else. A present navigation neighbour with no
layer within the step capability still makes the layer Unknown (a possible
drop), unless the pinned surface evidence (/pct_ground_surface) has an
unambiguous surface within the step capability at that XY. In that case the
neighbour is measured ground, as ETH treats a measured cell:
- pass 1 includes its evidence height;
- pass 2 skips it, because it has no score.
Only navigation cells are ever scored. Evidence never adds a supported cell.

The GridMap passes the evidence to the step score and rescores the accepted
navigation ground whenever new evidence arrives, so delivery order does not
matter. Unusable evidence (none, wrong frame or wrong resolution) scores
exactly as v29 did.
"""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
OLD = BASE / "runtime/scan61_sensor_column_v29"
NEW = BASE / "runtime/scan62_support_evidence_v30"
STEP = "src/plan_env/include/plan_env/eth_step_score_adaptation.h"
GRID = "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc"
AUDIT = BASE / "audits/2026-09-28_v29_landing_stall"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

STEP_EDITS = [
    ("""      critical_height_m <= 0.0 || critical_cell_number <= 0)
    return std::numeric_limits<double>::quiet_NaN();
  const double effective_step = std::min(
      maximum_step_m,
      static_cast<double>(critical_cells) / critical_cell_number * maximum_step_m);
  return effective_step < critical_height_m ?
      1.0 - effective_step / critical_height_m : 0.0;
}

inline StepScoreResult precomputeEthStyleStepScores(
    const TerrainSnapshot &input, const StepScoreParameters &parameters = {}) {
""", """      critical_height_m <= 0.0 || critical_cell_number <= 0)
    return std::numeric_limits<double>::quiet_NaN();
  const double effective_step = std::min(
      maximum_step_m,
      static_cast<double>(critical_cells) / critical_cell_number * maximum_step_m);
  return effective_step < critical_height_m ?
      1.0 - effective_step / critical_height_m : 0.0;
}

// Surface evidence (the pinned /pct_ground_surface cells) only decides whether
// a present navigation neighbour that lacks this level is a possible drop. If
// the evidence cell under that neighbour's centre has an unambiguous surface
// within the step capability, the neighbour is measured ground at that height.
// Evidence never adds or scores a navigation cell.
inline bool evidenceSurfaceHeight(const TerrainSnapshot *evidence, const TerrainSnapshot &input,
                                  const Cell2 &cell, double elevation_m,
                                  double maximum_layer_distance_m, double &height_m) {
  if (!evidence) return false;
  const double x = input.origin_x_m + (static_cast<double>(cell.x) + 0.5) * input.resolution_m;
  const double y = input.origin_y_m + (static_cast<double>(cell.y) + 0.5) * input.resolution_m;
  const double ix = std::floor((x - evidence->origin_x_m) / evidence->resolution_m);
  const double iy = std::floor((y - evidence->origin_y_m) / evidence->resolution_m);
  if (!std::isfinite(ix) || !std::isfinite(iy) ||
      ix < std::numeric_limits<int>::min() || ix > std::numeric_limits<int>::max() ||
      iy < std::numeric_limits<int>::min() || iy > std::numeric_limits<int>::max()) return false;
  const auto found = evidence->cells.find({static_cast<int>(ix), static_cast<int>(iy)});
  if (found == evidence->cells.end()) return false;
  const int nearest = nearestSurface(found->second, elevation_m, maximum_layer_distance_m);
  if (nearest < 0) return false;
  height_m = found->second[nearest].elevation_m;
  return true;
}

inline StepScoreResult precomputeEthStyleStepScores(
    const TerrainSnapshot &input, const StepScoreParameters &parameters = {},
    const TerrainSnapshot *evidence = nullptr) {
"""),
    ("""    return result;
  }

  // ETH pass 1: maximum minus minimum elevation in the first circle.
  // ETH skips missing neighbors. A present multilevel neighbor still needs
  // an unambiguous nearby surface; do not join different building floors.
""", """    return result;
  }
  // Unusable evidence scores exactly as without evidence.
  const TerrainSnapshot *usable_evidence =
      evidence && valid(*evidence) && evidence->frame == input.frame &&
      std::abs(evidence->resolution_m - input.resolution_m) <= 1e-9 ? evidence : nullptr;

  // ETH pass 1: maximum minus minimum elevation in the first circle.
  // ETH skips missing neighbors. A present multilevel neighbor still needs
  // an unambiguous nearby surface; do not join different building floors.
  // Without one, the neighbour is a possible drop unless the surface evidence
  // shows ground at this level there; that evidence height then counts.
"""),
    ("""        const int nearest = nearestSurface(cell->second, surface.elevation_m, parameters.critical_height_m);
        if (nearest < 0) { complete = false; break; }
        const double height = cell->second[nearest].elevation_m;
        minimum = std::min(minimum, height);
""", """        const int nearest = nearestSurface(cell->second, surface.elevation_m, parameters.critical_height_m);
        double height = 0.0;
        if (nearest >= 0) {
          height = cell->second[nearest].elevation_m;
        } else if (!evidenceSurfaceHeight(usable_evidence, input, neighbor, surface.elevation_m,
                                          parameters.critical_height_m, height)) {
          complete = false;
          break;
        }
        minimum = std::min(minimum, height);
"""),
    ("""        const int nearest = nearestSurface(cell->second, original[layer].elevation_m, parameters.critical_height_m);
        if (nearest < 0) { complete = false; break; }
        const auto &neighbor_score = result.scores.at(neighbor)[nearest];
""", """        const int nearest = nearestSurface(cell->second, original[layer].elevation_m, parameters.critical_height_m);
        if (nearest < 0) {
          // Measured evidence ground has no score; ETH skips missing scores.
          double evidence_height = 0.0;
          if (evidenceSurfaceHeight(usable_evidence, input, neighbor, original[layer].elevation_m,
                                    parameters.critical_height_m, evidence_height)) continue;
          complete = false;
          break;
        }
        const auto &neighbor_score = result.scores.at(neighbor)[nearest];
"""),
]
GRID_EDITS = [
    ("""  reactive_stair::StepScoreResult scored =
      reactive_stair::precomputeEthStyleStepScores(terrain);
  if (reactive_decision_.acceptTerrain(scored.support)) {
""", """  // The surface evidence decides whether a neighbour without this level is a drop.
  reactive_stair::StepScoreResult scored =
      reactive_stair::precomputeEthStyleStepScores(terrain, {}, &reactive_surface_ground_);
  if (reactive_decision_.acceptTerrain(scored.support)) {
"""),
    ("""  reactive_surface_ground_ = decodeReactiveGround(msg);
  // A changed source must not retain positive labels from an older source.
  // Historical nonterrain evidence remains conservative and is not cleared.
  reactive_terrain_hits_.clear();
  reactive_cloud_ready_ = false;
  reactive_pending_cloud_ = false;
}
""", """  reactive_surface_ground_ = decodeReactiveGround(msg);
  // A changed source must not retain positive labels from an older source.
  // Historical nonterrain evidence remains conservative and is not cleared.
  reactive_terrain_hits_.clear();
  reactive_cloud_ready_ = false;
  reactive_pending_cloud_ = false;
  // The step score consults this evidence, so rescore the accepted navigation
  // ground. Unusable evidence scores exactly as without evidence.
  if (!reactive_ground_.cells.empty()) {
    reactive_stair::StepScoreResult scored = reactive_stair::precomputeEthStyleStepScores(
        reactive_ground_, {}, &reactive_surface_ground_);
    if (reactive_decision_.acceptTerrain(scored.support)) {
      reactive_terrain_ = scored.support;
      reactive_step_result_ = std::move(scored);
    }
  }
}
"""),
]

parent = json.loads((HERE.parent / "v29/manifest.json").read_text())
assert not NEW.exists() and not (HERE / "prepared.json").exists()
for name, digest in parent["source_files"].items():
    assert sha(ROOT / name) == digest, name
native = json.loads((OLD / "source_sha256.json").read_text())
for name, digest in native.items():
    assert sha(OLD / name) == digest, name
diagnosis = {str(p.relative_to(ROOT)): sha(p) for p in [AUDIT / "RESULT.md", AUDIT / "support_map/evidence_fallback_estimate.json",
                                                         AUDIT / "support_map/validation.json", AUDIT / "landing_oracle/result.json",
                                                         AUDIT / "onset_oracle/result.json"]}

shutil.copytree(OLD / "src", NEW / "src")
changes, preimages = [], {}
for relative, edits in ((STEP, STEP_EDITS), (GRID, GRID_EDITS)):
    path = NEW / relative
    before = path.read_text()
    after = before
    for old, new in edits:
        assert after.count(old) == 1, (relative, old[:60])
        after = after.replace(old, new)
    path.write_text(after)
    preimages[relative] = before
    changes.append("".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                fromfile="v29/" + relative, tofile="v30/" + relative)))
for relative, before in preimages.items():
    preimage = HERE / "parent_source" / relative
    preimage.parent.mkdir(parents=True, exist_ok=True)
    preimage.write_text(before)
(HERE / "changes.patch").write_text("".join(changes))

manifest = {str(p.relative_to(NEW)): sha(p) for p in sorted((NEW / "src").rglob("*")) if p.is_file()}
assert set(manifest) == set(native)
assert {name for name in manifest if manifest[name] != native[name]} == {STEP, GRID}
(NEW / "source_sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
identity = BASE / "repairs/2026-09-26_generic_occupancy/candidate62_support_evidence_v30_identity.json"
identity.write_text(json.dumps({
    "source_sha256": manifest, "integration_version": "v30",
    "parent": {"native_build": str(OLD.relative_to(ROOT)), "step_sha256": native[STEP], "grid_sha256": native[GRID]},
    "diagnosis": diagnosis,
    "claim": "Unvalidated: in the ETH-style step score, a present navigation neighbour without this level is a possible drop "
             "only if the pinned surface evidence also lacks an unambiguous surface within the step capability there; "
             "evidence heights enter pass 1, evidence-only neighbours are skipped in pass 2, evidence never adds a scored "
             "cell, and unusable evidence scores as v29. All planner gates unchanged"},
    indent=2) + "\n")
for name in ("building_planner.yaml", "flat_planner.yaml"):
    shutil.copyfile(HERE.parent / "v29" / name, HERE / name)
(HERE / "prepared.json").write_text(json.dumps({
    "parent": "v29", "status": "unfrozen_candidate", "native_build": str(NEW.relative_to(ROOT)),
    "changed_files": [str((NEW / STEP).relative_to(ROOT)), str((NEW / GRID).relative_to(ROOT)),
                      str(identity.relative_to(ROOT))],
    "native_parent": str(OLD.relative_to(ROOT))}, indent=2) + "\n")
print(json.dumps({"v30": "native candidate prepared; acceptance pending", "changed": [STEP, GRID]}))
