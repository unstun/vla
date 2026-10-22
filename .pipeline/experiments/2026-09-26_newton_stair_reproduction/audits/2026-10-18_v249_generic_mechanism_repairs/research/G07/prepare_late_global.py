"""Extract exact saved late G07 body observations and canonical goal only."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


def ns(data):
    value = data["header"]["stamp"]
    return value["sec"] * 10**9 + value["nanosec"]


def values(pose):
    p, q = pose["position"], pose["orientation"]
    return [*[p[k] for k in ("x", "y", "z")], *[q[k] for k in ("x", "y", "z", "w")]]


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("/data/sun/vla_mppi_20261009/generic_mechanisms_v249/g07_late_global"))
    args = parser.parse_args()
    experiment = Path("/data/sun/vla_mppi_20261009/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction")
    capture_root = Path("/data/sun/vla_mppi_20261009/trials/v248_G07_attempt01/runs/v248_G07_attempt01")
    sys.path.insert(0, str(experiment / "versions/v196"))
    from analyze_remote import Capture
    capture = Capture(capture_root)
    events = capture.rows("artifacts/reactive_observations.jsonl")
    bodies = [(index, event) for index, event in enumerate(events) if event["event"] == "body_pose_observer"]
    selected = [(index, event) for index, event in bodies if 104000000000 <= ns(event["data"]) <= 105700000000]
    controls = [(index, event) for index, event in bodies if 103800000000 <= ns(event["data"]) < 104000000000]
    assert selected and controls
    assert all(ns(a[1]["data"]) < ns(b[1]["data"]) for a, b in zip(selected, selected[1:]))
    routes = [event for event in events if event["event"] == "pct_route"]
    canonical = routes[0]["data"]["poses"][-1]["pose"]
    assert all(route["data"]["poses"][-1]["pose"] == canonical for route in routes)
    args.output.mkdir(parents=True, exist_ok=False)
    def write_rows(filename, rows):
        with (args.output / filename).open("w") as stream:
            for row_index, (observer_index, event) in enumerate(rows):
                data = event["data"]
                pose = values(data["pose"]["pose"])
                assert abs(sum(v*v for v in pose[3:7])-1.0) < 1e-5
                stream.write(f"{row_index} {ns(data)} {event['clock_ns']} {event['wall_monotonic_ns']} " +
                             " ".join(format(v, ".17g") for v in pose) + "\n")
        save(args.output / filename.replace(".txt", ".json"), [dict(observer_sequence=index, **event) for index, event in rows])
    write_rows("starts.txt", selected)
    write_rows("pre104_controls.txt", controls)
    (args.output / "goal_canonical.txt").write_text(" ".join(format(v, ".17g") for v in values(canonical)) + "\n")
    save(args.output / "goal_canonical.json", dict(pose=canonical, first_route_observer_ns=routes[0]["clock_ns"],
         first_route_header_ns=ns(routes[0]["data"]), published_routes_verified=len(routes), terminal_pose_identical=True))
    lines = capture.read("nav2.log").splitlines()
    evidence = []
    for index, line in enumerate(lines, 1):
        if index >= 87232 and any(token in line for token in (
                "Planner loop missed", "wait completed successfully", "pct_optimizer_rejected", "pct_shared_rejected", "pct_shared_traversability_no_route")):
            evidence.append(dict(log_line=index, text=line))
    save(args.output / "log_timing.json", dict(evidence=evidence,
         final_graph_attempt2_start_epoch_s_lower_exclusive="1792318669.374664892",
         final_graph_attempt2_start_epoch_s_upper_exclusive="1792318669.844112799",
         bound_basis="Sequential attempt loop: attempt1 rejection precedes attempt2 solve and the final shared rejection follows it.",
         final_create_plan_entry_epoch_s=None,
         create_plan_entry_limit="No timestamped createPlan entry or original request.start is recorded. Recovery wait completed at1792318668.146897116 and attempt0 rejected at1792318668.774810218; this is scheduling context, not a recorded exact entry interval. Untimestamped printf output is buffered and cannot supply a tighter start time.",
         fixed_start_semantics="The same const createPlan(start,goal) arguments are reused for all three attempts; request.body in the later shared service is a separately acquired latest body observation."))
    files = {path.name: dict(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
             for path in args.output.iterdir() if path.is_file()}
    save(args.output / "metadata.json", dict(source_run=str(capture_root),
         source_archive_sha256=json.loads((capture_root/"raw_capture_manifest.json").read_text())["archive_sha256"],
         adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         starts=len(selected), pre104_controls=len(controls),
         columns=["index", "body_source_ns", "observer_clock_ns", "observer_wall_monotonic_ns", "x", "y", "z", "qx", "qy", "qz", "qw"],
         first_source_ns=ns(selected[0][1]["data"]), last_source_ns=ns(selected[-1][1]["data"]),
         source_stamps_rebased=False, resampled=False, physics_steps=0, planner_calls=0,
         claim="Saved body observations for candidate-start reconstruction. Original planner request.start and shared request.body were not recorded; no row is asserted to be either original request.",
         files=files, sources=capture.sources))
    print(json.dumps(dict(output=str(args.output), starts=len(selected), pre104_controls=len(controls), files=files)))


if __name__ == "__main__":
    main()
