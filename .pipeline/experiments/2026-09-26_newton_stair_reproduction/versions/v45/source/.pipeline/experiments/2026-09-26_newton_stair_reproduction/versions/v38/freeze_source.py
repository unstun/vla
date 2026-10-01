"""Freeze the isolated solver-graph implementation before bounded comparisons."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (HERE / "manifest.json").exists()
    parent_path = HERE.parent / "v37/manifest.json"
    parent = json.loads(parent_path.read_text())
    selected = dict(parent["source_files"])
    for name, digest in selected.items():
        assert sha(ROOT / name) == digest, name
        assert sha(HERE.parent / "v37/source" / name) == digest, name
    for path in HERE.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            selected[str(path.relative_to(ROOT))] = sha(path)
    for name, digest in selected.items():
        destination = HERE / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
        assert sha(destination) == digest
    manifest = {"version": "v38", "parent": "v37", "parent_manifest_sha256": sha(parent_path),
                "status": "frozen_unvalidated_solver_graph_component", "source_files": dict(sorted(selected.items())),
                "configuration": json.loads((HERE / "device_contract.json").read_text()),
                "physics_run": False, "full_stack_integrated": False, "navigation_validated": False}
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"version": "v38", "frozen_files": len(selected), "validated": False}))


if __name__ == "__main__":
    main()
