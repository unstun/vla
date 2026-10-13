"""Copy the original PCT/backend/bridge modules without changing their logic."""
import hashlib
import json
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parents[1]
PROJECT = BASE.parents[2]
OLD = PROJECT / ".pipeline/experiments/2026-09-23_scan_reactive_stair/runtime_integration/runs/walk_scan28_height030_right_v1"
PCT = PROJECT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/pct_runtime"
OUT = BASE / "runtime_sources"


def main():
    OUT.mkdir(exist_ok=False)
    records = []
    for group in ("backend_adapter", "backend_ros", "navigation_service", "bridge"):
        source = OLD / group
        for path in sorted(source.rglob("*.py")):
            if "tests" in path.parts or "qualification" in path.parts or "checks" in path.parts:
                continue
            destination = OUT / group / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            records.append((path, destination))
    for group in ("python", "lib"):
        source = PCT / group
        for path in sorted(source.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            destination = OUT / "pct_runtime" / group / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, destination)
            records.append((path, destination))
    destination = BASE / "inputs/static_background"
    destination.mkdir()
    for name in ("building2_9.pcd", "identity.json"):
        source = OLD / "inputs/static_background" / name
        shutil.copyfile(source, destination / name)
        records.append((source, destination / name))
    manifest = [{"source": str(s), "path": str(d.relative_to(BASE)), "bytes": d.stat().st_size,
                 "sha256": hashlib.sha256(d.read_bytes()).hexdigest()} for s, d in records]
    (BASE / "setup/runtime_sources.json").write_text(json.dumps({"records": manifest,
        "scope": "Original algorithm/service source and recorded native PCT libraries, no policy changes"}, indent=2) + "\n")
    print(json.dumps({"files": len(records), "bytes": sum(r["bytes"] for r in manifest)}))


if __name__ == "__main__":
    main()
