"""Bind standalone probes to inherited source and a new immutable harness."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify():
    data = json.loads((HERE / "manifest.json").read_text())
    for name, record in data["files"].items():
        if sha(ROOT / name) != record["sha256"] or sha(ROOT / record["snapshot"]) != record["sha256"]:
            raise ValueError("Frozen input differs: " + name)
    return data


def main():
    if sys.argv[1:] == ["verify"]:
        print("SOURCE_IDENTITY_PASS", len(verify()["files"]))
        return
    if sys.argv[1:] != ["freeze"] or (HERE / "manifest.json").exists():
        raise ValueError("Expected freeze once, or verify")
    parent = json.loads((BASE / "versions/v177/manifest.json").read_text())
    directories = [BASE / "scripts", BASE / "versions/v40/physics", BASE / "runtime_sources/bridge",
                   BASE.parent / "2026-09-26_newton_macos_policy/scripts",
                   BASE.parent / "2026-09-26_newton_macos_policy/references",
                   BASE.parent / "2026-09-27_lite3_factory_runtime_audit"]
    paths = set(HERE.glob("*.py")) | {HERE / "PLAN.md"}
    for directory in directories:
        paths.update(p for p in directory.rglob("*.py") if "source" not in p.parts and "runtime" not in p.parts)
    paths.add(BASE.parent / "2026-09-16_pi_cortex_harnessvln/isaac_runner/stance_hold.py")
    files = {}
    for path in sorted(paths):
        name = str(path.relative_to(ROOT)); digest = sha(path)
        old = parent.get("source_files", {}).get(name)
        if old is not None and old != digest:
            raise ValueError("Inherited v177 source differs: " + name)
        target = HERE / "source" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        files[name] = dict(sha256=digest, snapshot=str(target.relative_to(ROOT)))
    (HERE / "manifest.json").write_text(json.dumps(dict(version=HERE.name, parent="v179", inherited_physics_parent="v177",
        parent_manifest_sha256=sha(BASE / "versions/v177/manifest.json"), files=files,
        change="same v179 protocol, only walking command amplitudes changed to0.6/0.8/1.0mps"), indent=2) + "\n")
    print("FROZEN", len(verify()["files"]))


if __name__ == "__main__":
    main()
