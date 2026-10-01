"""Freeze the cache component before execution; do not promote acceptance."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
NATIVE = HERE.parents[1] / "runtime/scan68_raw_contributor_cache_v39"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not (HERE / "manifest.json").exists()
    parent_path = HERE.parent / "v38/manifest.json"
    parent = json.loads(parent_path.read_text())
    selected = dict(parent["source_files"])
    for name, digest in selected.items():
        assert sha(ROOT / name) == digest, name
        assert sha(HERE.parent / "v38/source" / name) == digest, name
    for directory in (HERE, NATIVE / "src"):
        for path in directory.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                selected[str(path.relative_to(ROOT))] = sha(path)
    selected[str((NATIVE / "source_sha256.json").relative_to(ROOT))] = sha(NATIVE / "source_sha256.json")
    for name, digest in selected.items():
        destination = HERE / "source" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, destination)
        assert sha(destination) == digest
    manifest = {"version": "v39", "parent": "v38", "native_source_parent": "v36",
                "parent_manifest_sha256": sha(parent_path), "status": "frozen_unvalidated_cache_component",
                "source_files": dict(sorted(selected.items())), "physics_run": False,
                "full_stack_integrated": False, "navigation_validated": False}
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"version": "v39", "frozen_files": len(selected), "validated": False}))


if __name__ == "__main__":
    main()
