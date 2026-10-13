"""Validate complete native admission evidence and return only compact results."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exposure(events, horizon):
    completed = [row for row in events if row["event"] == "complete"]
    maximum = stale = 0.0
    for i, row in enumerate(completed):
        end = completed[i + 1]["complete_s"] if i + 1 < len(completed) else horizon
        maximum = max(maximum, end - row["source_s"])
        stale += max(0.0, end - max(row["complete_s"], row["source_s"] + .250))
    return {"held_map_age_max_s": maximum, "held_map_stale_duration_s": stale,
            "no_completed_map_initial_duration_s": completed[0]["complete_s"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    paths = [args.results / f"{schedule}_{mode}" for schedule in ("nominal", "blackout")
             for mode in ("fifo", "timer", "latest")]
    summaries = {p.name: json.loads((p / "summary.json").read_text()) for p in paths}
    reference = summaries["nominal_fifo"]
    assert reference["state_sha256"] == "da01d77d0e45f6f6a0884df0493dbcac3fae97bd42d13b96fffc44f8ec4a64af"
    occupied = np.fromfile(paths[0] / "occupancy.bin", dtype=np.uint8)
    inflated = np.fromfile(paths[0] / "inflation.bin", dtype=np.uint8)
    assert len(occupied) == len(inflated) == 4_000_000
    horizon = max(row["virtual_end_s"] for row in summaries.values())
    comparisons = []
    for path in paths:
        summary = summaries[path.name]
        events = [json.loads(line) for line in (path / "events.jsonl").read_text().splitlines()]
        assert len(events) == 188 and sorted(row["scan"] for row in events) == list(range(188))
        assert sum(row["event"] == "complete" for row in events) == summary["processed"]
        assert sum(row["event"] == "skip" for row in events) == summary["skipped"]
        assert summary["origin"] == reference["origin"]
        candidate = np.fromfile(path / "occupancy.bin", dtype=np.uint8)
        candidate_inflated = np.fromfile(path / "inflation.bin", dtype=np.uint8)
        assert candidate.shape == occupied.shape and candidate_inflated.shape == inflated.shape
        row = dict(summary, run=path.name, **exposure(events, horizon))
        row.update(
            equal_original_full_state=summary["state_sha256"] == reference["state_sha256"],
            occupancy_categories_changed=int(np.count_nonzero(candidate != occupied)),
            reference_occupied_no_longer_occupied=int(np.count_nonzero((occupied == 2) & (candidate != 2))),
            reference_inflated_no_longer_inflated=int(np.count_nonzero((inflated != 0) & (candidate_inflated == 0))),
            sources={name: {"sha256": sha(path / name), "bytes": (path / name).stat().st_size}
                     for name in ("summary.json", "events.jsonl", "occupancy.bin", "inflation.bin")},
        )
        comparisons.append(row)
        compact = args.output / path.name
        compact.mkdir()
        for name in ("summary.json", "events.jsonl"):
            shutil.copyfile(path / name, compact / name)
    result = {"checks_passed": True, "recorded_scans": 188, "runs": comparisons,
              "map_threshold_s": .250, "common_virtual_horizon_s": horizon,
              "claim": "Native same-input admission replay; held-age includes blackouts; not physics or upstream mapper performance"}
    (args.output / "comparison.json").write_text(json.dumps(result, indent=2) + "\n")
    for row in comparisons:
        print(row["run"], "processed", row["processed"], "skipped", row["skipped"],
              "occupied_lost", row["reference_occupied_no_longer_occupied"],
              "held_age_max_ms", round(row["held_map_age_max_s"] * 1000, 3))


if __name__ == "__main__":
    main()
