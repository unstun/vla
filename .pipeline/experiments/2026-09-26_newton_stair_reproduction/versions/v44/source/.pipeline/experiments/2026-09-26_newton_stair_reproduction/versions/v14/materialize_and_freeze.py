"""Freeze consumer-scoped admission matching; native planner is unchanged."""
from datetime import datetime, timezone
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parent = json.loads((HERE.parent / "v13/manifest.json").read_text())
    if (HERE / "manifest.json").exists():
        raise FileExistsError("v14 is frozen")
    for name, digest in parent["source_files"].items():
        if sha(ROOT / name) != digest:
            raise ValueError("Parent changed: " + name)
    receiver = BASE / "runtime_sources/backend_ros/p2b_backend_ros/node.py"
    receipt = BASE / "setup/runtime_sources.json"
    for path in [receiver, receipt]:
        dest = HERE / "parent_source" / path.relative_to(BASE)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    before = receiver.read_text()
    old = '(admission.consumer in consumers or admission.status == "rejected")'
    if before.count(old) != 1:
        raise ValueError("Pinned admission matching anchor changed")
    after = before.replace(old, "admission.consumer in consumers")
    receiver.write_text(after)
    (HERE / "changes.patch").write_text("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True),
        fromfile="v13/runtime_sources/backend_ros/p2b_backend_ros/node.py",
        tofile="v14/runtime_sources/backend_ros/p2b_backend_ros/node.py")))
    record = json.loads(receipt.read_text())
    matches = [r for r in record["records"] if r["path"] == str(receiver.relative_to(BASE))]
    if len(matches) != 1 or matches[0]["sha256"] != sha(HERE / "parent_source" / receiver.relative_to(BASE)):
        raise ValueError("Receiver receipt mismatch")
    row = matches[0]
    row["sha256"] = sha(receiver)
    row["bytes"] = receiver.stat().st_size
    row["local_modification"] = "v11 fault propagation; v14 consumer-scoped replies; preimages and patches in versions/v11 and versions/v14"
    receipt.write_text(json.dumps(record, indent=2) + "\n")
    for name in ["building_planner.yaml", "flat_planner.yaml"]:
        shutil.copyfile(HERE.parent / "v13" / name, HERE / name)
    selected = {ROOT / name for name in parent["source_files"]}
    selected.update(p for p in HERE.iterdir() if p.is_file())
    selected.update(p for p in (HERE / "parent_source").rglob("*") if p.is_file())
    records = {}
    for path in sorted(selected):
        name = str(path.relative_to(ROOT))
        records[name] = sha(path)
        dest = HERE / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    (HERE / "manifest.json").write_text(json.dumps({
        "version": "v14", "parent": "v13", "status": "frozen_unvalidated",
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "change": "Match admission replies only from the requested consumer",
        "source_files": records,
        "changed_files": [str(p.relative_to(ROOT)) for p in [receiver, receipt]],
        "native_build": parent["native_build"], "source_snapshot_prefix": "source/",
        "acceptance_plan": "PLAN.md",
    }, indent=2) + "\n")
    print(json.dumps({"version": "v14", "files": len(records)}))


if __name__ == "__main__":
    main()
