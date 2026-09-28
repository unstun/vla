"""Derive oracle_probe.cpp: landing_probe.cpp plus a diagnostic support oracle.

Counterfactual only. After the unchanged replay and before the start state is
taken, every Unknown walkway layer (1.35-1.65 m) whose 0.1 m cell lies in the
landing box x in [-5.3, -3.5], y in [-4.5, -2.3] is relabelled Flat in the
scored terrain, and the collision decision is given the same snapshot. Scans,
occupancy, the route, the committed window, thresholds, the optimizer and all
other support labels are unchanged. It asks one question: if SCAN scored the
walkway's edge ring as supported, would the frontier and the continuation move?
"""
from pathlib import Path
import hashlib, json

here = Path(__file__).resolve().parent
text = (here / "probe_source/src/landing_probe.cpp").read_text()
anchor = "  fsm.setStartStateFromOdomOrCurrentTraj();\n  const Eigen::Vector3d original_start=fsm.start_pt_;\n"
oracle = r'''  // ---- Diagnostic support oracle (counterfactual only) ----
  {
    auto &terrain = map->reactive_terrain_;
    size_t relabelled = 0, walkway = 0;
    for (auto &entry : terrain.cells) {
      const double x0 = terrain.origin_x_m + entry.first.x * terrain.resolution_m;
      const double y0 = terrain.origin_y_m + entry.first.y * terrain.resolution_m;
      if (x0 < -5.3 || x0 > -3.5 || y0 < -4.5 || y0 > -2.3) continue;
      for (auto &surface : entry.second) {
        if (surface.elevation_m < 1.35 || surface.elevation_m > 1.65) continue;
        ++walkway;
        if (surface.support == reactive_stair::Support::Unknown) {
          surface.support = reactive_stair::Support::Flat;
          ++relabelled;
        }
      }
    }
    const bool accepted = map->reactive_decision_.acceptTerrain(terrain);
    std::cout << "[SUPPORT-ORACLE] box=[-5.3,-3.5]x[-4.5,-2.3] walkway_layers=" << walkway
              << " relabelled_unknown_to_flat=" << relabelled << " decision_snapshot_accepted=" << accepted << std::endl;
    if (!accepted) throw std::runtime_error("Oracle terrain rejected");
  }
'''
assert text.count(anchor) == 1
derived = text.replace(anchor, oracle + anchor)
out = here / "oracle_probe_source"
(out / "src").mkdir(parents=True, exist_ok=True)
(out / "src/oracle_probe.cpp").write_text(derived)
(out / "package.xml").write_bytes((here / "probe_source/package.xml").read_bytes())
cmake = (here / "probe_source/CMakeLists.txt").read_text()
assert cmake.count("foreach(target landing_probe)") == 1
(out / "CMakeLists.txt").write_text(cmake.replace("foreach(target landing_probe)", "foreach(target oracle_probe)"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(here / "oracle_probe_derivation.json").write_text(json.dumps({
    "base": {str(p.relative_to(here)): sha(p) for p in [here / "probe_source/src/landing_probe.cpp", here / "probe_source/CMakeLists.txt"]},
    "derived": {str(p.relative_to(here)): sha(p) for p in [out / "src/oracle_probe.cpp", out / "CMakeLists.txt", out / "package.xml"]},
    "change": "Diagnostic support oracle inserted before the start state: Unknown walkway layers (1.35-1.65 m) in x[-5.3,-3.5] y[-4.5,-2.3] relabelled Flat in the scored terrain and the decision snapshot. Counterfactual only; not a proposed implementation.",
}, indent=2) + "\n")
print("ok")
