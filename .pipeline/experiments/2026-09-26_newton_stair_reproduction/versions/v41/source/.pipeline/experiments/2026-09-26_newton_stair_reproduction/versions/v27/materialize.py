"""Preserve v26 and apply only the checked direct-seed simplification."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
OLD = BASE / "runtime/scan58_body_support_v24"
NEW = BASE / "runtime/scan59_seed_shortcut_v27"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

parent = json.loads((HERE.parent / "v26/manifest.json").read_text())
assert not NEW.exists() and not (HERE / "prepared.json").exists()
for name, digest in parent["source_files"].items():
    assert sha(ROOT / name) == digest, name
shutil.copytree(OLD / "src", NEW / "src")
path = NEW / "src/plan_manage/src/planner_manager.cpp"
before = path.read_bytes()
text = before.decode()
anchor = "    // SCAN-Planner 348e8a5 planner_manager.cpp:210-231 (Apache-2.0):"
assert text.count(anchor) == 1
text = text.replace(anchor, '''    // OMPL 1.7.0 eabb4d0 reduceVertices: simplify only after checkMotion.
    // Source/license: references/upstream/2026-09-27_ompl_seed_shortcut.
    // The original native search and every returned edge have already passed.
    // A failed direct connector keeps that original graph path unchanged.
    if (seed_path.size() > 2 &&
        grid_map_->collisionFreeSegment(seed_path.front(), seed_path.back())) {
      RCLCPP_INFO(node_->get_logger(), "verified_direct_seed_shortcut original_nodes=%zu", seed_path.size());
      const Eigen::Vector3d first = seed_path.front(), last = seed_path.back();
      seed_path = {first, last};
    }
''' + anchor)
path.write_bytes(text.encode())
preimage = HERE / "parent_source" / path.relative_to(NEW)
preimage.parent.mkdir(parents=True, exist_ok=True)
preimage.write_bytes(before)
(HERE / "changes.patch").write_bytes("".join(difflib.unified_diff(
    before.decode().splitlines(True), text.splitlines(True),
    fromfile="v26/" + str(path.relative_to(NEW)),
    tofile="v27/" + str(path.relative_to(NEW)))).encode())
native = {str(p.relative_to(NEW)): sha(p) for p in sorted((NEW / "src").rglob("*")) if p.is_file()}
(NEW / "source_sha256.json").write_text(json.dumps(native, indent=2) + "\n")
identity = BASE / "repairs/2026-09-26_generic_occupancy/candidate59_seed_shortcut_v27_identity.json"
identity.write_text(json.dumps({"source_sha256": native, "integration_version": "v27",
    "claim": "Unvalidated OMPL direct-motion seed simplification; original search and complete final guards remain mandatory"}, indent=2) + "\n")
for name in ("building_planner.yaml", "flat_planner.yaml"):
    shutil.copyfile(HERE.parent / "v26" / name, HERE / name)
(HERE / "prepared.json").write_text(json.dumps({"parent": "v26", "status": "unfrozen_candidate",
    "native_build": str(NEW.relative_to(ROOT)),
    "changed_files": [str(path.relative_to(ROOT)), str(identity.relative_to(ROOT))],
    "native_parent": str(OLD.relative_to(ROOT)), "upstream_commit": "eabb4d0f825666e4553a2ec0ecb9c7a5a33637dd",
}, indent=2) + "\n")
print("v27 native candidate prepared; acceptance pending")
