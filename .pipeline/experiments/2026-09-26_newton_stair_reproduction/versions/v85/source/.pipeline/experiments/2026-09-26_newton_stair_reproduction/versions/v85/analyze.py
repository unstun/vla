"""Check sensor/execution independence during the explicitly injected map stalls."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = json.loads((args.results / "summary.json").read_text())
    rows = {name: [json.loads(line) for line in (args.results / f"{name}.jsonl").read_text().splitlines()]
            for name in ("sensor", "map", "execution")}
    assert summary["sensor_processed"] == summary["mapped"] == 188
    assert [r["scan"] for r in rows["sensor"]] == [r["scan"] for r in rows["map"]] == list(range(188))
    assert summary["state_sha256"] == "da01d77d0e45f6f6a0884df0493dbcac3fae97bd42d13b96fffc44f8ec4a64af"
    assert summary["robot_commands_published"] == summary["physics_steps"] == 0
    stalls = []
    for index in (60, 120):
        begin = rows["map"][index]["begin_s"]
        end = begin + .650
        sensors = [r for r in rows["sensor"] if begin < r["complete_s"] < end]
        ticks = [r for r in rows["execution"] if begin < r["wall_s"] < end]
        unsafe = [r for r in ticks if r["wall_s"] > begin + .300 and r["decision"] == 0]
        assert len(sensors) >= 4 and len(ticks) >= 15 and not unsafe
        stalls.append({"scan": index, "begin_s": begin, "end_s": end,
                       "sensor_callbacks_during_stall": len(sensors),
                       "execution_decisions_during_stall": len(ticks),
                       "allow_decisions_after_map_stale": len(unsafe)})
    decisions = {}
    for row in rows["execution"]:
        key = str(row["decision"])
        decisions[key] = decisions.get(key, 0) + 1
    result = {"checks_passed": True, "native_result": summary, "injected_stalls": stalls,
              "decision_counts": decisions,
              "decision_enum": ["AllowExisting", "NoOwner", "Cancelled", "SensorInvalid", "SensorStale", "HazardPending", "MapRejected", "MapStale"],
              "claim": "Component concurrency, evidence retention and veto semantics only; no moving trajectory, braking, full command identity or robot qualification"}
    for name in ("summary.json", "sensor.jsonl", "map.jsonl", "execution.jsonl"):
        source = args.results / name
        shutil.copyfile(source, args.output / name)
    result["source_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in args.output.iterdir() if p.is_file()}
    (args.output / "verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": True, "stalls": stalls, "native_checks": summary["checks"]}))


if __name__ == "__main__":
    main()
