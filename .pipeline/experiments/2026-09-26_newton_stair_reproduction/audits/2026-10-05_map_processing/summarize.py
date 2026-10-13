"""Summarize measured map hot paths while preserving the live/replay boundary."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import statistics

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
VERSION = BASE / "versions/v78"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument("--temporary-root", type=Path, required=True)
args = parser.parse_args()
raw = args.temporary_root / "results"
evidence = VERSION / "profiles/attempt02"
original = json.loads((HERE / "original_flow.json").read_text())
manifest = json.loads((VERSION / "manifest.json").read_text())
for name, expected in manifest["source_files"].items():
    assert sha(ROOT / name) == expected
    assert sha(ROOT / manifest["snapshot_locations"][name]) == expected
assert sha(BASE / "versions/v76/manifest.json") == manifest["parent_manifest_sha256"]
rows_by_run = {}
run_summaries = []
digests = set()
counts = []
selected = []
for repetition in (1, 2, 3):
    for arm in ("baseline", "instrumented"):
        name = f"{arm}_{repetition}"
        rows = [json.loads(line) for line in (raw / (name + ".jsonl")).read_text().splitlines()]
        assert len(rows) == 188 and [r["scan"] for r in rows] == list(range(188))
        assert all(b["stamp_ns"] > a["stamp_ns"] for a, b in zip(rows, rows[1:]))
        line = re.search(r"V78_MAP_REPLAY_COMPLETE scans=(\d+) state_sha256=([a-f0-9]{64}) voxels=200 200 100 inflation_offsets=(\d+) terrain_cells=(\d+)", (raw / (name + ".log")).read_text())
        assert line and int(line[1]) == 188 and int(line[3]) == 2755 and int(line[4]) == 29345
        digests.add(line[2])
        tail = [r for r in rows if 181 <= r["scan"] <= 187]
        assert [r["stamp_ns"] for r in tail] == original["selected_scan_stamps_ns"]
        assert sum(r["points"] for r in tail) == original["points_in_seven_scans"]
        result = {"run": name, "state_sha256": line[2], "scans": len(rows),
            "seven_cloud_wall_ms": sum(r["cloud_ms"] for r in tail),
            "seven_pose_wall_ms": sum(r["pose_ms"] for r in tail),
            "seven_total_wall_ms": sum(r["cloud_ms"] + r["pose_ms"] for r in tail),
            "seven_total_thread_cpu_ms": sum(r["cloud_cpu_ms"] + r["pose_cpu_ms"] for r in tail),
            "source_jsonl_sha256": sha(raw / (name + ".jsonl")),
            "source_log_sha256": sha(raw / (name + ".log"))}
        if arm == "instrumented":
            result["stage_totals"] = {key: {field: sum(r["instrumentation"]["stages"][key][field] for r in tail) for field in ("wall_ms", "cpu_ms")} for key in tail[0]["instrumentation"]["stages"]}
            result["operation_counts"] = {key: sum(r["instrumentation"]["counts"][key] for r in tail) for key in tail[0]["instrumentation"]["counts"]}
            counts.append(result["operation_counts"])
        run_summaries.append(result)
        selected.extend(dict(run=name, **r) for r in tail)
        rows_by_run[name] = rows
        shutil.copyfile(raw / (name + ".log"), evidence / (name + ".log"))
assert len(digests) == 1 and counts[0] == counts[1] == counts[2]
assert counts[0]["occupancy_transitions"] + counts[0]["cleared_occupied"] == counts[0]["inflation_calls"]
assert counts[0]["inflation_offset_visits"] == 2755 * counts[0]["inflation_calls"]
(evidence / "selected_scan_profiles.jsonl").write_text("".join(json.dumps(r) + "\n" for r in selected))
baseline = [r["seven_total_wall_ms"] for r in run_summaries if r["run"].startswith("baseline")]
summary = {"passed": True, "stage": "experiment + analysis", "version": "v78",
    "native_parent": "v63", "parent": "v76", "source_files_and_snapshots_verified": len(manifest["source_files"]),
    "manifest_sha256": sha(VERSION / "manifest.json"), "runs": run_summaries,
    "six_final_buffer_history_digests_identical": True, "final_state_sha256": next(iter(digests)),
    "state_digest_scope": "Occupancy/inflation/hit/miss/ray-flag buffers, map origin, ray counter and terrain/nonterrain/history sets; not full planner or dynamics state.",
    "original_input_wall_ms": original["input_wall_ms"], "original_input_thread_cpu_ms": original["input_thread_cpu_ms"],
    "baseline_replay_total_ms": {"minimum": min(baseline), "median": statistics.median(baseline), "maximum": max(baseline)},
    "operation_counts": counts[0], "representative_stages": next(r for r in run_summaries if r["run"] == "instrumented_2")["stage_totals"],
    "original_977ms_exactly_reproduced": False, "causal_live_speedup_validated": False,
    "claim_boundary": "Measured original seven-scan synchronous work; isolated native replay localizes voxel fusion/inflation and sliding reset cost. Original native DDS batching/map history, active planner/cache context and concurrent live load are not reconstructed; the live multiplier is unresolved.",
    "physics_executed": False, "gpu_job_started": False, "production_fix": False,
    "current_reference": "v48", "analyzer_sha256": sha(Path(__file__))}
(HERE / "profile_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
(evidence / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: summary[k] for k in ("passed", "final_state_sha256", "baseline_replay_total_ms", "operation_counts", "representative_stages", "original_977ms_exactly_reproduced")}, indent=2))
