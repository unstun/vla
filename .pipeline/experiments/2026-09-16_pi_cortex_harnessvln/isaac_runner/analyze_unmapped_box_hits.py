#!/usr/bin/env python3
"""AC1/AC2 LiDAR AABB hit counts for one unmapped cuboid.

Reads returned stand_probe files (`clouds.jsonl`, `summary.json` or
`unmapped_box_setup.json`) and the frozen `unmapped_box_thresholds.json`.

    analyze_unmapped_box_hits.py RUN [--require ac1|ac2] [--output OUT.json]

RUN is a run package (with returned_artifacts/runner_output) or a
runner_output directory. Counts use raw_points_sensor_frame transformed to
world; planner_points_sensor_frame is ignored.

Claim boundary: LiDAR hit-confirmation only. Not SCAN, not navigation
success, not harness validated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import List, Optional

import unmapped_box as box

HERE = Path(__file__).resolve().parent
DEFAULT_THRESHOLDS = HERE / "unmapped_box_thresholds.json"
# SHA-256 of unmapped_box_thresholds.json frozen before any Isaac run (task A4).
FROZEN_THRESHOLDS_SHA256 = "727d84805067aa4f07191add3d59196bbd9ba1965307a0dcaa8582ba12b44c97"
CLAIM_BOUNDARY = (
    "LiDAR hit-confirmation only. Not SCAN, not navigation success, not harness validated."
)
CLOUD_REQUIRED_KEYS = (
    "sim_time_s", "raw_points_sensor_frame", "sensor_position", "sensor_quaternion_wxyz",
)


class AnalysisError(RuntimeError):
    """A required input is missing or malformed."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_thresholds(path: Path, allow_unfrozen: bool = False) -> dict:
    path = Path(path)
    digest = sha256_file(path)
    frozen = digest == FROZEN_THRESHOLDS_SHA256
    if not frozen and not allow_unfrozen:
        raise AnalysisError(
            "thresholds %s have SHA-256 %s, not the frozen %s" % (
                path, digest, FROZEN_THRESHOLDS_SHA256)
        )
    values = json.loads(path.read_text(encoding="utf-8"))
    return {"path": str(path), "sha256": digest, "frozen": frozen, "values": values}


def resolve_output_dir(run: Path) -> Path:
    run = Path(run)
    for candidate in (run, run / "returned_artifacts/runner_output", run / "artifacts/runner_output"):
        if (candidate / "clouds.jsonl").is_file():
            return candidate
    raise AnalysisError("no clouds.jsonl under %s" % run)


def load_jsonl(path: Path) -> List[dict]:
    rows = []
    with Path(path).open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise AnalysisError("clouds.jsonl line %d is not JSON: %s" % (number, exc))
    if not rows:
        raise AnalysisError("clouds.jsonl is empty: %s" % path)
    return rows


def load_clouds(path: Path) -> List[dict]:
    """Parse clouds.jsonl and refuse rows that cannot be placed on the settle clock."""
    path = Path(path)
    rows = load_jsonl(path)
    for key in CLOUD_REQUIRED_KEYS:
        if any(key not in row for row in rows):
            raise AnalysisError("clouds.jsonl rows lack %s: %s" % (key, path))
    for number, row in enumerate(rows, 1):
        try:
            sim_time = float(row["sim_time_s"])
        except (TypeError, ValueError):
            raise AnalysisError("clouds.jsonl line %d sim_time_s is not a finite number" % number)
        if not math.isfinite(sim_time):
            raise AnalysisError("clouds.jsonl line %d sim_time_s is not a finite number" % number)
        row["sim_time_s"] = sim_time
    return rows


def _finite_xyz(value, name):
    try:
        xyz = tuple(float(item) for item in value)
    except (TypeError, ValueError):
        raise AnalysisError("%s is not three finite metres" % name)
    if len(xyz) != 3 or not all(math.isfinite(item) for item in xyz):
        raise AnalysisError("%s is not three finite metres" % name)
    return xyz


def box_aabb_from_run(out: Path, values: dict) -> dict:
    setup_path = out / "unmapped_box_setup.json"
    summary_path = out / "summary.json"
    identity = None
    if setup_path.is_file():
        identity = json.loads(setup_path.read_text(encoding="utf-8"))
    elif summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        identity = summary.get("unmapped_box")
    if not identity or "center_xyz_m" not in identity:
        raise AnalysisError("unmapped box identity is missing from %s" % out)
    frozen_size = _finite_xyz(values["size_xyz_m"], "frozen size_xyz_m")
    frozen_pad = float(values["aabb_pad_m"])
    frozen_prim = values["prim"]
    size = _finite_xyz(identity.get("size_xyz_m", frozen_size), "size_xyz_m")
    pad = float(identity.get("aabb_pad_m", frozen_pad))
    prim = identity.get("prim", frozen_prim)
    if any(abs(got - want) > 1e-12 for got, want in zip(size, frozen_size)):
        raise AnalysisError("identity size_xyz_m %s differs from frozen %s" % (list(size), list(frozen_size)))
    if abs(pad - frozen_pad) > 1e-12:
        raise AnalysisError("identity aabb_pad_m %s differs from frozen %s" % (pad, frozen_pad))
    if prim != frozen_prim:
        raise AnalysisError("identity prim %r differs from frozen %r" % (prim, frozen_prim))
    center = _finite_xyz(identity["center_xyz_m"], "center_xyz_m")
    aabb = box.expanded_aabb(center, size, pad_m=frozen_pad)
    return {
        "mode": identity.get("mode"),
        "prim": prim,
        "center_xyz_m": list(center),
        "size_xyz_m": list(size),
        "aabb_pad_m": frozen_pad,
        "aabb": aabb,
        "identity": identity,
        "setup_path": setup_path if setup_path.is_file() else None,
        "summary_path": summary_path if summary_path.is_file() else None,
    }


def count_scan(row: dict, aabb: dict) -> dict:
    if "raw_points_sensor_frame" not in row:
        raise AnalysisError("clouds.jsonl row lacks raw_points_sensor_frame")
    if "sensor_position" not in row or "sensor_quaternion_wxyz" not in row:
        raise AnalysisError("clouds.jsonl row lacks sensor pose")
    world = box.sensor_points_to_world(
        row["raw_points_sensor_frame"], row["sensor_position"], row["sensor_quaternion_wxyz"])
    count = box.aabb_hit_count(world, aabb)
    return {
        "scan_id": row.get("scan_id"),
        "sim_time_s": row["sim_time_s"],
        "raw_point_count": len(row["raw_points_sensor_frame"]),
        "aabb_count": count,
    }


def evaluate(scans: List[dict], values: dict) -> dict:
    settle = float(values["settle_s"])
    after = [row for row in scans if row["sim_time_s"] >= settle]
    if not after:
        raise AnalysisError("no clouds.jsonl scans at or after settle_s %g" % settle)
    counts = [row["aabb_count"] for row in after]
    median = float(statistics.median(counts))
    ac1 = all(count == values["ac1_spawn"]["after_settle_every_scan_aabb_count"] for count in counts)
    ac2_every = all(count >= values["ac2_lidar"]["after_settle_every_scan_min_aabb_count"] for count in counts)
    ac2_median = median >= values["ac2_lidar"]["after_settle_median_min_aabb_count"]
    ac2 = ac2_every and ac2_median
    return {
        "settle_s": settle,
        "scan_count_total": len(scans),
        "scan_count_after_settle": len(after),
        "aabb_counts_after_settle": counts,
        "median_aabb_count_after_settle": median,
        "min_aabb_count_after_settle": min(counts),
        "max_aabb_count_after_settle": max(counts),
        "ac1": {"passed": ac1, "rule": values["ac1_spawn"]},
        "ac2": {
            "passed": ac2,
            "every_scan_min": ac2_every,
            "median_min": ac2_median,
            "rule": values["ac2_lidar"],
        },
        "scans": after,
    }


def analyze_run(run: Path, thresholds: dict) -> dict:
    out = resolve_output_dir(run)
    clouds = out / "clouds.jsonl"
    rows = load_clouds(clouds)
    contract = box_aabb_from_run(out, thresholds["values"])
    scans = [count_scan(row, contract["aabb"]) for row in rows]
    verdict = evaluate(scans, thresholds["values"])
    inputs = {"clouds": {"path": str(clouds), "sha256": sha256_file(clouds)}}
    for name, path in (("unmapped_box_setup", contract["setup_path"]),
                       ("summary", contract["summary_path"])):
        if path is not None:
            inputs[name] = {"path": str(path), "sha256": sha256_file(path)}
    return {
        "run": str(run),
        "output_dir": str(out),
        "thresholds": {"path": thresholds["path"], "sha256": thresholds["sha256"],
                       "frozen": thresholds["frozen"]},
        "box": {key: contract[key] for key in ("mode", "prim", "center_xyz_m", "size_xyz_m", "aabb_pad_m")},
        "aabb": {
            "min_xyz_m": list(contract["aabb"]["min_xyz_m"]),
            "max_xyz_m": list(contract["aabb"]["max_xyz_m"]),
        },
        "inputs": inputs,
        "claim_boundary": CLAIM_BOUNDARY,
        **verdict,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--allow-unfrozen-thresholds", action="store_true", default=False)
    parser.add_argument("--require", choices=("ac1", "ac2"), default=None)
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    thresholds = load_thresholds(args.thresholds, allow_unfrozen=args.allow_unfrozen_thresholds)
    report = analyze_run(args.run, thresholds)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "run": report["run"],
        "mode": report["box"]["mode"],
        "ac1": report["ac1"]["passed"],
        "ac2": report["ac2"]["passed"],
        "median_aabb_count_after_settle": report["median_aabb_count_after_settle"],
        "scan_count_after_settle": report["scan_count_after_settle"],
        "thresholds_sha256": report["thresholds"]["sha256"],
        "claim_boundary": CLAIM_BOUNDARY,
    }, indent=2, sort_keys=True))
    if args.require == "ac1" and not report["ac1"]["passed"]:
        return 1
    if args.require == "ac2" and not report["ac2"]["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
