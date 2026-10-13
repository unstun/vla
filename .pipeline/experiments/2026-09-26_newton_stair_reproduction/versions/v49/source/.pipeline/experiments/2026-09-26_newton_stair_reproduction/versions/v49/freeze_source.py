"""Freeze qualified v49 Candidate 3 before full-stack measurement."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
NATIVE = HERE.parents[1] / "runtime/scan72_solve_budget_v49"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (HERE / "manifest.json").exists()
    parent_path = HERE.parent / "v48/manifest.json"
    parent = json.loads(parent_path.read_text())
    selected = dict(parent["source_files"])
    for name, digest in selected.items():
        assert sha(ROOT / name) == digest, name
        assert sha(HERE.parent / "v48/source" / name) == digest, name
    qualification = json.loads((HERE / "component_qualification.json").read_text())
    assert qualification["cache_geometry_and_contract_passed"] and qualification["warm_contract_passed"] and qualification["deadline_contract_passed"]
    owned = [p for p in HERE.iterdir() if p.is_file()]
    owned += [p for p in (HERE / "contract").rglob("*") if p.is_file()]
    owned += [p for p in (HERE / "parent_source").rglob("*") if p.is_file()]
    owned += [p for p in (HERE / "backend_ros").rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    owned += [p for p in (NATIVE / "src").rglob("*") if p.is_file()]
    for path in owned:
        if path.is_file() and "__pycache__" not in path.parts:
            selected[str(path.relative_to(ROOT))] = sha(path)
    for filename in ("source_sha256.json", "install_sha256.json", "build_result.json"):
        selected[str((NATIVE / filename).relative_to(ROOT))] = sha(NATIVE / filename)
    for name, digest in selected.items():
        destination = HERE / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
        assert sha(destination) == digest
    manifest = {"version": "v49", "parent": "v48", "native_source_parent": "v48",
                "parent_manifest_sha256": sha(parent_path), "status": "frozen_candidate_3_components_passed",
                "source_files": dict(sorted(selected.items())),
                "native_source_sha256": json.loads((NATIVE / "source_sha256.json").read_text()),
                "native_install_sha256": json.loads((NATIVE / "install_sha256.json").read_text()), "physics_run": False,
                "full_stack_integrated": False, "navigation_validated": False}
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"version": "v49", "frozen_files": len(selected), "validated": False}))


if __name__ == "__main__":
    main()
