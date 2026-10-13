"""Freeze diagnostic sources after compile qualification and before replay."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
NATIVE = BASE / "runtime/scan82_optimizer_failure_v63"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument("--temporary-root", type=Path, required=True)
parser.add_argument("--evidence", type=Path, required=True)
args = parser.parse_args()
assert not (HERE / "manifest.json").exists()
build = json.loads((args.temporary_root / "results/build_receipt.json").read_text())
assert build["passed"] and build["native_source_unchanged"]
native = json.loads((NATIVE / "source_sha256.json").read_text())
assert build["native_source_sha256"] == native
assert all(sha(NATIVE / path) == value for path, value in native.items())
parent = json.loads((BASE / "versions/v76/manifest.json").read_text())
sources = {str((NATIVE / p).relative_to(ROOT)): h for p, h in native.items()}
snapshots = {}
for path, value in sources.items():
    snapshot = ROOT / parent["snapshot_locations"][path]
    assert sha(snapshot) == value
    snapshots[path] = str(snapshot.relative_to(ROOT))
owned = [p for p in HERE.iterdir() if p.is_file()]
owned += [BASE / "versions/v76/building_planner.yaml"]
for name in ("instrumented_grid_map.cpp", "instrumentation.patch", "recorded_readers.h"):
    target = args.evidence / ("executed_" + name)
    shutil.copyfile(args.temporary_root / "generated" / name, target)
    owned.append(target)
for path in owned:
    relative = str(path.relative_to(ROOT))
    copy = HERE / "source" / relative
    copy.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, copy)
    sources[relative] = sha(path)
    snapshots[relative] = str(copy.relative_to(ROOT))
manifest = {"version": "v78", "parent": "v76", "parent_manifest_sha256": sha(BASE / "versions/v76/manifest.json"),
    "status": "frozen_diagnostic_map_profile_only", "native_source_parent": "v63",
    "source_files": sources, "snapshot_locations": snapshots,
    "native_source_sha256": native, "build_receipt_sha256": sha(args.temporary_root / "results/build_receipt.json"),
    "instrumented_translation_unit_sha256": build["instrumented_translation_unit_sha256"],
    "physics_run": False, "navigation_validated": False, "full_scene_30hz_validated": False,
    "claim_boundary": "Observation-only recorded map replay; exact native callback math and paired support, not historical DDS queue or full planner-state reconstruction. No production planner/stop/safety changes."}
(HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
shutil.copyfile(args.temporary_root / "results/build_receipt.json", args.evidence / "build_receipt.json")
print(json.dumps({"version": "v78", "source_files": len(sources), "manifest_sha256": sha(HERE / "manifest.json")}))
