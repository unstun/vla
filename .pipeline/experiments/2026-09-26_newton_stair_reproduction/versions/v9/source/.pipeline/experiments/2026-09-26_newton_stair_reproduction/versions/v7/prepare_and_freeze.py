"""Freeze owned v7 inputs/source; reject repeated freezing."""
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
    if (HERE / "manifest.json").exists():
        raise FileExistsError("v7 already frozen")
    parent = json.loads((HERE.parent / "v6/manifest.json").read_text())
    for name, expected in parent["source_files"].items():
        if sha(ROOT / name) != expected:
            raise ValueError("Parent source changed: " + name)
    native = BASE / "runtime/scan46_cruise_v7"
    for name, expected in json.loads((native / "source_sha256.json").read_text()).items():
        if sha(native / name) != expected:
            raise ValueError("Candidate source changed: " + name)

    fixtures, sources = [], []
    for run_id, label in (("empty_long_root_live08", "flat"), ("v6_building_route02", "building")):
        path = BASE / "runs" / run_id / "artifacts/reactive_observations.jsonl"
        sources.append({"path": str(path.relative_to(ROOT)), "sha256": sha(path)})
        for row in map(json.loads, path.read_text().splitlines()):
            if row["event"] != "bspline":
                continue
            message = row["data"]
            points = [[p[k] for k in ("x", "y", "z")] for p in message["pos_pts"]]
            if max(sum((a - b) ** 2 for a, b in zip(p, points[0])) for p in points) < 1e-8:
                continue
            assert message["order"] == 3
            fixtures.append(f'{label}_{message["traj_id"]} {len(points)} {len(message["knots"])}\n')
            fixtures.extend(" ".join(map(repr, point)) + "\n" for point in points)
            fixtures.append(" ".join(map(repr, message["knots"])) + "\n")
    (HERE / "recorded_curves.txt").write_text("".join(fixtures))
    (HERE / "recorded_curves_provenance.json").write_text(json.dumps(sources, indent=2) + "\n")
    upstream = BASE / "references/2026-09-27_min_cruise"
    shutil.copytree(upstream, HERE / "upstream_reference")

    selected = {ROOT / name for name in parent["source_files"]}
    selected.update(p for p in (native / "src").rglob("*") if p.is_file())
    selected.add(native / "source_sha256.json")
    selected.update(p for p in HERE.iterdir() if p.is_file() and p.name != "native_changes.patch")
    selected.update(p for p in (HERE / "upstream_reference").rglob("*") if p.is_file())
    source_files, changes = {}, []
    snapshot = HERE / "source"
    for path in sorted(selected):
        relative = str(path.relative_to(ROOT))
        source_files[relative] = sha(path)
        dest = snapshot / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
        if relative not in parent["source_files"] or source_files[relative] != parent["source_files"][relative]:
            changes.append(relative)
    manifest = {
        "version": "v7", "parent": "v6", "status": "frozen_unvalidated",
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "change": "Minimum planned cruise speed 0.6 m/s using existing SCAN retiming; boundary ramps/stops exempt",
        "source_files": source_files, "changed_files": changes,
        "native_build": str(native.relative_to(ROOT)), "source_snapshot_prefix": "source/",
        "acceptance_plan": "PLAN.md",
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    changes_text = (HERE / "native_changes.patch").read_text()
    for before, after in (
        (HERE.parent / "v6/building_planner.yaml", HERE / "building_planner.yaml"),
        (BASE / "repairs/2026-09-26_generic_occupancy/geometry_smac_approach_flat.yaml",
         HERE / "flat_planner.yaml"),
    ):
        changes_text += "".join(difflib.unified_diff(
            before.read_text().splitlines(True), after.read_text().splitlines(True),
            fromfile=str(before.relative_to(ROOT)), tofile=str(after.relative_to(ROOT))))
    (HERE / "changes.patch").write_text(changes_text)
    print(json.dumps({"version": "v7", "frozen_files": len(source_files), "changed_files": len(changes)}))


if __name__ == "__main__":
    main()
