"""Freeze verified v26 sources while keeping later results outside the snapshot."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
parent = json.loads((HERE.parent / "v25/manifest.json").read_text())
prepared = json.loads((HERE / "prepared.json").read_text())
native = ROOT / prepared["native_build"]
assert not (HERE / "manifest.json").exists()
assert json.loads((HERE / "native_chain/result.json").read_text())["passed"]
changed = set(prepared["changed_files"])
for name, digest in parent["source_files"].items():
    if name not in changed:
        assert sha(ROOT / name) == digest, name
for name, digest in json.loads((native / "source_sha256.json").read_text()).items():
    assert sha(native / name) == digest, name
assert json.loads((native / "build_result.json").read_text())["passed"]
for name in ("build_result.json", "install_sha256.json"):
    shutil.copyfile(native / name, HERE / name)
selected = {ROOT / name for name in parent["source_files"]} | {ROOT / name for name in changed}
selected.update(path for path in HERE.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
records = {}
for path in sorted(selected):
    name = str(path.relative_to(ROOT))
    records[name] = sha(path)
    destination = HERE / "source" / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, destination)
(HERE / "manifest.json").write_text(json.dumps({
    "version": "v26", "parent": "v25", "status": "frozen_unvalidated",
    "frozen_utc": datetime.now(timezone.utc).isoformat(),
    "change": "Preserve explicit null at map.pct_layer through ROS and adapter config loading",
    "source_files": records, "changed_files": sorted(changed),
    "native_build": prepared["native_build"], "source_snapshot_prefix": "source/",
    "acceptance_plan": "PLAN.md", "freeze_boundary": "After loader and native IPC chain regressions, before physical execution",
}, indent=2) + "\n")
print(json.dumps({"version": "v26", "source_files": len(records)}))
