"""Prepare the next native candidate without changing its frozen parent."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

H = Path(__file__).resolve().parent
B = H.parents[1]
R = B.parents[2]
N = B / "runtime/scan56_dense_ground_v23"
P = B / "runtime/scan55_surface_ground_v21"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not N.exists() and not (H / "prepared.json").exists()
    parent = json.loads((H.parent / "v22/manifest.json").read_text())
    for name, digest in parent["source_files"].items():
        assert sha(R / name) == digest, name
    N.mkdir()
    shutil.copytree(P / "src", N / "src")
    before = {}
    p = N / "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc"
    before[p] = p.read_bytes()
    source = before[p].decode()
    begin = source.index("bool GridMap::reactiveTerrainReturn")
    end = source.index("\nint GridMap::reactiveOccupancy", begin)
    source = source[:begin] + '''bool GridMap::reactiveTerrainReturn(const Eigen::Vector3d &point) const {
  if (!reactiveSurfaceGroundReady()) return false;
  // A configured source replaces the classification evidence, not navigation support.
  const auto &evidence = reactive_surface_ground_topic_.empty()
      ? reactive_ground_ : reactive_surface_ground_;
  return reactive_stair::selectedGroundReturn(evidence,
      point.x(), point.y(), point.z(), reactive_terrain_band_m_);
}
''' + source[end:]
    p.write_bytes(source.encode())
    p = N / "src/plan_env/include/plan_env/grid_map.h"
    before[p] = p.read_bytes()
    old = b"// Broader floor evidence never authorizes risers or changes scored support."
    assert before[p].count(old) == 1
    p.write_bytes(before[p].replace(old, b"// Explicit raw-return classification evidence; scored navigation support stays separate."))
    for p, raw in before.items():
        target = H / "parent_source" / p.relative_to(N)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    (H / "changes.patch").write_text("".join(
        "".join(difflib.unified_diff(raw.decode().splitlines(True),
            p.read_text().splitlines(True), fromfile="v22/" + str(p.relative_to(N)),
            tofile="v23/" + str(p.relative_to(N)))) for p, raw in before.items()))
    native = {str(p.relative_to(N)): sha(p) for p in sorted((N / "src").rglob("*")) if p.is_file()}
    (N / "source_sha256.json").write_text(json.dumps(native, indent=2) + "\n")
    identity = B / "repairs/2026-09-26_generic_occupancy/candidate56_dense_ground_v23_identity.json"
    identity.write_text(json.dumps({"source_sha256": native,
        "integration_version": "v23", "claim": "Unvalidated candidate: apply existing floor/riser rule to the explicit qualified classification source; original scored navigation support unchanged."}, indent=2) + "\n")
    for name in ("building_planner.yaml", "flat_planner.yaml"):
        shutil.copyfile(H.parent / "v22" / name, H / name)
    (H / "prepared.json").write_text(json.dumps({
        "parent": "v22", "status": "unfrozen_candidate",
        "native_build": str(N.relative_to(R)),
        "changed_files": [str(p.relative_to(R)) for p in before] + [str(identity.relative_to(R))]
    }, indent=2) + "\n")
    print("v23 source prepared; build, freeze and validation pending")


if __name__ == "__main__":
    main()
