"""Extract saved G07 inputs only; preserve publication order, source stamps and hashes.

Adapted from the v238 prepare_replay.py export format. No planner or physics runs.
Raw arrays remain on gpu5070ti; metadata.json and frame metadata are compact receipts.
"""
import argparse
import bisect
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile

import numpy as np


TARGETS = (100.096618652, 101.106063843, 102.110511780)
EXPECTED_MAPPED = (884, 894, 904)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def numbers(values):
    return " ".join(format(float(value), ".17g") for value in values)


def stamp(data):
    value = data["header"]["stamp"]
    return value["sec"] * 10**9 + value["nanosec"]


def pose_values(data, twist=False):
    p, q = data["pose"]["pose"]["position"], data["pose"]["pose"]["orientation"]
    result = [*[p[key] for key in ("x", "y", "z")], *[q[key] for key in ("x", "y", "z", "w")]]
    if twist:
        t = data["twist"]["twist"]
        result += [*[t["linear"][key] for key in ("x", "y", "z")],
                   *[t["angular"][key] for key in ("x", "y", "z")]]
    return result


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=Path, default=Path("/data/sun/vla_mppi_20261009/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction"))
    parser.add_argument("--capture", type=Path, default=Path("/data/sun/vla_mppi_20261009/trials/v248_G07_attempt01/runs/v248_G07_attempt01"))
    parser.add_argument("--output", type=Path, default=Path("/data/sun/vla_mppi_20261009/generic_mechanisms_v249/g07_input"))
    args = parser.parse_args()
    sys.path.insert(0, str(args.experiment / "versions/v196"))
    from analyze_remote import Capture

    capture = Capture(args.capture)
    receipt = capture.json("raw_capture_manifest.json")
    archive_path = args.capture / "raw_capture.zip"
    # Hash the whole archive once, before accepting any retained member.
    archive_hash = hashlib.sha256()
    with archive_path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 2**20), b""):
            archive_hash.update(block)
    assert archive_hash.hexdigest() == receipt["archive_sha256"]
    assert archive_path.stat().st_size == receipt["archive_bytes"]
    events = capture.rows("artifacts/reactive_observations.jsonl")
    logs = capture.read("nav2.log").splitlines()
    audits = capture.rows("bridge_scan_audit.jsonl")
    sensors = capture.json("sensor_manifest.json")
    sensors_by_stamp = {item["stamp_ns"]: item for item in sensors}
    assert len(sensors_by_stamp) == len(sensors)
    published = [item for item in audits if item["outcome"] == "published_sequentially"]
    assert all(a["timestamp_ns"] < b["timestamp_ns"] for a, b in zip(published, published[1:]))
    frames = []
    snapshots = []
    generation = None
    for line_number, line in enumerate(logs, 1):
        found = re.search(r"V82_MAP_SNAPSHOT revision=(\d+) clouds=(\d+) cloud_stamp=([0-9.]+)", line)
        if found:
            snapshots.append(dict(revision=int(found[1]), applied_clouds=int(found[2]),
                                  source_s=float(found[3]), log_line=line_number))
        found = re.search(r"V132_REFERENCE_ADMISSION generation=(\d+) accepted=1", line)
        if found:
            generation = int(found[1])
        found = re.search(r"nominal_replan .*ros_s=([0-9.]+)", line)
        if found and any(abs(float(found[1]) - target) < 1e-10 for target in TARGETS):
            frames.append(dict(query_s=float(found[1]), query_ns=round(float(found[1])*1e9),
                               snapshot=dict(snapshots[-1]), route_generation=generation,
                               nominal_replan_log_line=line_number))
    assert tuple(frame["query_s"] for frame in frames) == TARGETS
    assert tuple(frame["snapshot"]["applied_clouds"] for frame in frames) == EXPECTED_MAPPED
    # Log timestamps are rounded to 9 decimals; match each to the exact source stamp.
    for frame in frames:
        nearest = min(published, key=lambda row: abs(row["timestamp_ns"]*1e-9-frame["snapshot"]["source_s"]))
        assert abs(nearest["timestamp_ns"]*1e-9-frame["snapshot"]["source_s"]) < 1.1e-9
        frame["cutoff_ns"] = nearest["timestamp_ns"]
    scans = [item for item in published if item["timestamp_ns"] <= frames[-1]["cutoff_ns"]]
    assert len(scans) == 910, (len(scans), "Never trim the published prefix to match mapper counters")
    args.output.mkdir(parents=True, exist_ok=False)
    scan_records = []
    with zipfile.ZipFile(archive_path) as archive:
        for index, audit in enumerate(scans):
            source_ns = audit["timestamp_ns"]
            source = sensors_by_stamp[source_ns]
            source_path = args.capture / source["file"]
            raw = source_path.read_bytes() if source_path.is_file() else archive.read(source["file"])
            assert sha(raw) == source["sha256"], source["file"]
            member = receipt["members"].get(source["file"])
            if member:
                assert len(raw) == member["bytes"] and sha(raw) == member["sha256"]
            with np.load(io.BytesIO(raw), allow_pickle=False) as data:
                points = np.asarray(data["sensor_points"], dtype="<f4")
            assert points.ndim == 2 and points.shape[1] == 3
            assert len(points) == audit["planning_point_count"] == audit["raw_point_count"]
            assert np.isfinite(points).all()
            cloud_name = f"cloud_{index:05d}.f32"
            cloud_raw = points.tobytes()
            (args.output / cloud_name).write_bytes(cloud_raw)
            pose = source["body_sensor"]
            for optical, role in ((False, "body"), (True, "sensor")):
                w, x, y, z = pose["sensor_quaternion" if optical else "quaternion"]
                values = [*pose["sensor_position" if optical else "position"], x, y, z, w]
                if not optical:
                    values += [*pose["linear_world"], *pose["angular_world"]]
                (args.output / f"{role}_{index:05d}.txt").write_text(numbers(values)+"\n")
            scan_records.append(dict(index=index, scan_id=audit["scan_id"], source_ns=source_ns,
                                     source_file=source["file"], source_npz_sha256=sha(raw),
                                     points=len(points), cloud_file=cloud_name, cloud_sha256=sha(cloud_raw),
                                     body_file=f"body_{index:05d}.txt", sensor_file=f"sensor_{index:05d}.txt"))
    (args.output / "scans.txt").write_text("".join(
        f"{item['index']} {item['source_ns']} {item['body_file']} {item['sensor_file']} {item['cloud_file']}\n"
        for item in scan_records))
    save(args.output / "scan_inventory.json", scan_records)

    bodies = [event for event in events if event["event"] == "body_pose_observer"]
    routes = [event for event in events if event["event"] == "pct_route"]
    curves = [event for event in events if event["event"] == "bspline"]
    source_to_index = {item["source_ns"]: item["index"] for item in scan_records}
    # Preserve the complete observer input order, including intermediate body poses.
    with (args.output / "input_events.jsonl").open("w") as stream:
        for event_index, event in enumerate(events):
            if event.get("clock_ns") is None or event["clock_ns"] > frames[-1]["query_ns"]:
                continue
            if event["event"] not in ("body_pose_observer", "lidar_pose", "cloud"):
                continue
            source_ns = event["data"]["stamp_ns"] if event["event"] == "cloud" else stamp(event["data"])
            if event["event"] != "body_pose_observer" and source_ns not in source_to_index:
                continue
            stream.write(json.dumps(dict(observer_sequence=event_index, **event), allow_nan=False)+"\n")
    (args.output / "body_events.txt").write_text("".join(
        f"{index} {event['clock_ns']} {event['wall_monotonic_ns']} {stamp(event['data'])} "+numbers(pose_values(event["data"], True))+"\n"
        for index, event in enumerate(bodies) if event.get("clock_ns") is not None and event["clock_ns"] <= frames[-1]["query_ns"]))
    for index, frame in enumerate(frames):
        query_ns = frame["query_ns"]
        body = next(event for event in reversed(bodies)
                    if event["clock_ns"] <= query_ns and stamp(event["data"]) <= query_ns)
        route = next(event for event in reversed(routes) if event["clock_ns"] <= query_ns)
        curve = next(event for event in reversed(curves) if event["clock_ns"] <= query_ns)
        tag = f"{index:04d}"
        (args.output / f"query_{tag}.txt").write_text(numbers(pose_values(body["data"], True))+"\n")
        save(args.output / f"route_{tag}.json", route)
        route_positions = [[pose["pose"]["position"][key] for key in ("x", "y", "z")] for pose in route["data"]["poses"]]
        assert len(route_positions) == 401
        (args.output / f"route_{tag}.txt").write_text("\n".join(numbers(point) for point in route_positions)+"\n")
        d = curve["data"]
        origin = d["start_time"]["sec"] + d["start_time"]["nanosec"]*1e-9
        duration = d["knots"][len(d["pos_pts"])] - d["knots"][d["order"]]
        controls = [[point[key] for key in ("x", "y", "z")] for point in d["pos_pts"]]
        (args.output / f"curve_{tag}.txt").write_text(numbers([origin, len(controls), len(d["knots"])])+"\n"+
            "\n".join(numbers(point) for point in controls)+"\n"+numbers(d["knots"])+"\n")
        prefix = [item for item in scan_records if item["source_ns"] <= frame["cutoff_ns"]]
        observers = {}
        for kind in ("cloud", "lidar_pose"):
            matching = [event for event in events if event["event"] == kind and
                        (event["data"]["stamp_ns"] if kind == "cloud" else stamp(event["data"])) <= frame["cutoff_ns"]]
            observers[kind] = len(matching)
        frame.update(index=index, body_source_ns=stamp(body["data"]), body=body,
                     route_observer_clock_ns=route["clock_ns"], route_header_ns=stamp(route["data"]),
                     route_file=f"route_{tag}.json", route_points=len(route_positions),
                     curve=curve, curve_origin_s=origin, curve_duration_s=duration,
                     curve_expired=query_ns*1e-9-origin >= duration,
                     original_start_branch="measured_odometry" if query_ns*1e-9-origin >= duration else "depends_on_original_fail_count",
                     published_prefix_count=len(prefix), observer_prefix_counts=observers,
                     published_minus_mapper_count=len(prefix)-frame["snapshot"]["applied_clouds"],
                     body_age_s=(query_ns-stamp(body["data"]))*1e-9,
                     cloud_age_s=(query_ns-frame["cutoff_ns"])*1e-9)
        save(args.output / f"frame_{tag}.json", frame)
    (args.output / "frames.txt").write_text("".join(
        f"{frame['index']} {frame['query_ns']} {frame['body_source_ns']} {frame['cutoff_ns']}\n" for frame in frames))
    terrain = Path("/data/sun/vla_mppi_20261009/physical_traversability_v247/native/fixtures/building")
    terrain_manifest = json.loads((terrain / "terrain247.json").read_text())
    terrain_files = {}
    for role in ("navigation", "surface", "physical_floor"):
        entry = terrain_manifest["clouds"][role]
        raw = (terrain / entry["file"]).read_bytes()
        assert sha(raw) == entry["sha256"]
        (args.output / f"{role}.f32").write_bytes(raw)
        terrain_files[role] = dict(source=str(terrain/entry["file"]), sha256=sha(raw), bytes=len(raw))
    for name in ("nav2_params.scan.yaml", "nav2_params.yaml", "backend_config.json", "inputs/stair_scenario.json"):
        (args.output / name.replace("/", "__")).write_text(capture.read(name))
    rejections = [dict(log_line=index, text=line) for index, line in enumerate(logs, 1) if "pct_shared_rejected" in line]
    global_boundary = dict(original_rejection_log=rejections, final_refused_count=2,
        original_refused_pose_coordinates_recorded=False, original_candidate_path_recorded=False,
        scope="Only admitted published routes are retained. Original rejected candidate/service requests and internal repair/cache state are absent; regenerated two-pose results require their own provenance and cannot be named the original coordinates.")
    save(args.output / "global_recoverability.json", global_boundary)
    metadata = dict(schema="g07_saved_input_prefix_v1", source_run=str(args.capture), remote_output=str(args.output),
        archive_sha256=receipt["archive_sha256"], archive_bytes=receipt["archive_bytes"], adapter_sha256=sha(Path(__file__).read_bytes()),
        frames=[{key: value for key, value in frame.items() if key not in ("body", "curve")} for frame in frames],
        scans=len(scan_records), first_source_ns=scan_records[0]["source_ns"], last_source_ns=scan_records[-1]["source_ns"],
        total_points=sum(item["points"] for item in scan_records), all_npz_hashes_verified=True,
        publication_order_preserved=True, source_stamps_rebased=False, physics_steps=0,
        actual_mapper_consumption_sequence_available=False, exact_snapshot_memory_available=False,
        input_scope="Full original published prefix, exact observer body/twist and per-frame route/curve. Mapper counter is six below published/observer counts; no scans were deleted to force parity. Async consumption/drop/batching is not recovered.",
        global_recoverability=global_boundary, terrain=terrain_files, sources=capture.sources)
    save(args.output / "metadata.json", metadata)
    print(json.dumps({key: metadata[key] for key in ("remote_output", "scans", "total_points", "all_npz_hashes_verified", "physics_steps")}))


if __name__ == "__main__":
    main()
