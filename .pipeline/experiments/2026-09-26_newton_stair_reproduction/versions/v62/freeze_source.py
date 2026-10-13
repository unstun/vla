"""Freeze the Mac-tested source, explicitly without full qualification/physics."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
NATIVE = BASE / "runtime/scan81_retry_epoch_v62"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (HERE / "manifest.json").exists(), "Frozen versions are immutable"
    parent_path = HERE.parent / "v59/manifest.json"
    parent = json.loads(parent_path.read_text())
    prepared = json.loads((HERE / "candidate_source.json").read_text())
    qualification = json.loads((HERE / "component_qualification.json").read_text())
    result = json.loads((HERE / "mac_tests/attempt02/result.json").read_text())
    assert qualification["mac_suite_passed"] and not qualification["component_passed"]
    assert result["passed"] and result["owned_container_absent"]
    assert not qualification["physics_run"] and not qualification["full_scene_30hz_validated"]
    selected = dict(prepared["source_files"])
    locations = dict(prepared["snapshot_locations"])
    assert all(sha(ROOT / name) == h and sha(ROOT / locations[name]) == h
               for name, h in selected.items())
    own = [HERE / name for name in ("PLAN.md", "freeze_source.py", "mac_validate.py",
        "mac_inside.sh", "changes.patch", "preparation.json", "candidate_source.json",
        "component_qualification.json")]
    own.extend(p for p in (HERE / "contract").iterdir() if p.is_file())
    own.append(NATIVE / "source_sha256.json")
    for path in own:
        name = str(path.relative_to(ROOT))
        digest = sha(path)
        previous = str((HERE.parent / "v59" / path.relative_to(HERE)).relative_to(ROOT)) if path.is_relative_to(HERE) else ""
        if parent["source_files"].get(previous) == digest:
            location = parent["snapshot_locations"][previous]
        else:
            destination = HERE / "source" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            assert not destination.exists() or sha(destination) == digest
            if not destination.exists():
                shutil.copyfile(path, destination)
            location = str(destination.relative_to(ROOT))
        selected[name] = digest
        locations[name] = location
        assert sha(ROOT / location) == digest
    manifest = {
        "version": "v62", "parent": "v59", "native_source_parent": "v59",
        "status": "frozen_mac_checks_passed_full_qualification_pending",
        "parent_manifest_sha256": sha(parent_path),
        "source_files": dict(sorted(selected.items())),
        "snapshot_locations": dict(sorted(locations.items())),
        "native_source_sha256": prepared["native_source_sha256"],
        "mac_build_install_sha256": json.loads((HERE / "mac_tests/attempt02/install_sha256.json").read_text()),
        "mac_component_subset_passed": True, "component_passed": False,
        "physics_run": False, "full_stack_integrated": False,
        "navigation_validated": False, "full_scene_30hz_validated": False,
        "claim_boundary": "Frozen source with successful Mac checks; full recorded-corner/native/physics qualification is pending",
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"version": "v62", "frozen_files": len(selected),
        "full_qualification": False, "navigation_validated": False}))


if __name__ == "__main__":
    main()
