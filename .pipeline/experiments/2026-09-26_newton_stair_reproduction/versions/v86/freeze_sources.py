"""Freeze/verify the scoped Foxy component sources; not a Newton deployment pin."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parents[1]
ROOT = EXPERIMENT.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected(version):
    directory = EXPERIMENT / "versions" / version
    roots = ([EXPERIMENT / "runtime/scan_nav2_foxy_v86/src", directory / "nav2_controller"]
             if version == "v86" else [directory / "plan_env"])
    paths = []
    for root in roots:
        paths.extend(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    paths.extend(p for p in directory.iterdir() if p.is_file() and
                 (p.suffix in (".py", ".sh", ".cpp", ".h", ".yaml", ".patch") or p.name == "CMakeLists.txt"))
    if version == "v87":
        paths.extend(EXPERIMENT / "versions" / name for name in (
            "v84/recording.h", "v81/recorded_readers.h", "v81/map_digest.h", "v81/sync_planner.yaml"))
    return sorted(set(paths))


def verify(version):
    directory = EXPERIMENT / "versions" / version
    manifest = json.loads((directory / "manifest.json").read_text())
    for name, expected in manifest["source_files"].items():
        if digest(ROOT / name) != expected or digest(ROOT / manifest["snapshot_locations"][name]) != expected:
            raise ValueError("Frozen source/snapshot mismatch: " + name)
    parent = EXPERIMENT / "versions" / manifest["parent"] / "manifest.json"
    if digest(parent) != manifest["parent_manifest_sha256"]:
        raise ValueError("Parent manifest changed")
    if digest(directory / "quality.json") != manifest["quality_sha256"]:
        raise ValueError("Frozen qualification record changed")
    print(json.dumps({"version": version, "source_snapshot_pairs": len(manifest["source_files"]), "passed": True}))


def freeze(version):
    directory = EXPERIMENT / "versions" / version
    target = directory / "manifest.json"
    if target.exists():
        raise ValueError("Never overwrite a frozen version")
    parent = "v85" if version == "v86" else "v86"
    files, snapshots = {}, {}
    if version == "v87":
        prior = json.loads((EXPERIMENT / "versions/v86/manifest.json").read_text())
        files.update(prior["source_files"])
        snapshots.update(prior["snapshot_locations"])
    for source in selected(version):
        relative = source.relative_to(ROOT)
        copy = directory / "source" / relative
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, copy)
        files[str(relative)] = digest(source)
        snapshots[str(relative)] = str(copy.relative_to(ROOT))
    manifest = {
        "version": version, "parent": parent,
        "parent_manifest_sha256": digest(EXPERIMENT / "versions" / parent / "manifest.json"),
        "native_source_parent": "v82",
        "scope": "Foxy ARM64 SCAN/Nav2 component workspace, not a complete Newton or robot deployment",
        "status": "frozen_component_checked_navigation_not_accepted",
        "nav2_commit": "a947ab5656e46ae3aa1afdf95e1706a16e478974",
        "source_files": files, "snapshot_locations": snapshots,
        "quality_sha256": digest(directory / "quality.json"),
        "materialization": {
            "base": ".pipeline/experiments/2026-09-26_newton_stair_reproduction/runtime/scan_nav2_foxy_v86/src",
            "nav2_controller": ".pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v86/nav2_controller",
            "plan_env_override": None if version == "v86" else
              ".pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v87/plan_env",
        },
    }
    target.write_text(json.dumps(manifest, indent=2) + "\n")
    verify(version)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["freeze", "verify"])
    parser.add_argument("version", choices=["v86", "v87"])
    args = parser.parse_args()
    (freeze if args.action == "freeze" else verify)(args.version)
