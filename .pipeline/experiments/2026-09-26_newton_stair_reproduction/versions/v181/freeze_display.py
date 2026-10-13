import hashlib
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify():
    data = json.loads((HERE / "manifest.json").read_text())
    for name, value in data["files"].items():
        if digest(ROOT / name) != value["sha256"] or digest(ROOT / value["snapshot"]) != value["sha256"]:
            raise ValueError("Frozen renderer changed: " + name)
    return data


if __name__ == "__main__":
    if sys.argv[1:] == ["verify"]:
        print("DISPLAY_SOURCE_PASS", len(verify()["files"]))
    elif sys.argv[1:] == ["freeze"] and not (HERE / "manifest.json").exists():
        paths = list(HERE.glob("*.py")) + [HERE / "PLAN.md"] + list((BASE / "versions/v51").glob("*.py"))
        records = {}
        for p in paths:
            name = str(p.relative_to(ROOT)); target = HERE / "source" / name
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(p, target)
            records[name] = dict(sha256=digest(p), snapshot=str(target.relative_to(ROOT)))
        (HERE / "manifest.json").write_text(json.dumps(dict(version="v181", physics_parent="v179",
            physics_manifest_sha256=digest(BASE / "versions/v179/manifest.json"), files=records), indent=2) + "\n")
        print("DISPLAY_FROZEN", len(verify()["files"]))
    else:
        raise ValueError("freeze once or verify")
