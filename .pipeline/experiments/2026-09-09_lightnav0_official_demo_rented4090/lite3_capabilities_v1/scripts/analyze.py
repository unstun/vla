"""Measure frozen capability cases from raw captures, contacts and model records."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from metrics import displacement


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pkg", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    args.pkg = args.pkg.resolve()
    args.run = args.run.resolve()
    suite = json.loads((args.pkg / "cases/suite.json").read_text())
    output = args.pkg / "analysis"
    output.mkdir(exist_ok=True)
    captures = {}
    for scene in ("clear", "blocked"):
        cap = args.run / f"capture_{scene}"
        frames, traces = rows(cap / "frames_index.jsonl"), rows(cap / "traces.jsonl")
        status = json.loads((cap / "recorder_status.json").read_text())
        problems = []
        for frame in frames:
            for camera in ("front", "third"):
                if hashlib.sha256((cap / frame[camera+"_file"]).read_bytes()).hexdigest() != frame[camera+"_sha256"]:
                    problems.append([frame["frame_id"], camera])
        counts = [len(frames), len(list((cap / "frames/front").glob("*.jpg"))),
                  len(list((cap / "frames/third").glob("*.jpg"))), status["written_frames"]]
        counts.append((cap / "states.f64").stat().st_size // status["state_size_bytes"])
        if len(set(counts)) != 1:
            problems.append(["count_mismatch", counts])
        if any(status[k] for k in ("queue_drops", "write_failures", "duplicate_names", "malformed_rows")):
            problems.append(["recording_loss", status])
        captures[scene] = {"frames": frames, "traces": traces, "status": status,
                           "problems": problems, "root": str(cap)}
    official = {}
    for actions_path in sorted((args.run / "records").rglob("actions.json")):
        for record in json.loads(actions_path.read_text()):
            image = actions_path.parent / f"image_{record['step']:06d}.jpg"
            image_hash = hashlib.sha256(image.read_bytes()).hexdigest()
            record["image_path"] = str(image.resolve())
            key = record["seq"], image_hash, record["instruction"]
            official.setdefault(key, []).append(record)
    results = []
    for case in suite["cases"]:
        episode_file = args.run / "cases" / case["id"] / "episode.json"
        if not episode_file.exists():
            results.append({"id": case["id"], "termination": "not_executed"})
            continue
        episode = json.loads(episode_file.read_text())
        t0, t1 = episode["instruction_send_mono_ns"], episode["end_mono_ns"]
        cap = captures[case["scene"]]
        samples = [f for f in cap["frames"] if t0 <= f["capture_mono_ns"] <= t1]
        traces = [t for t in cap["traces"] if t0 <= t["mono_ns"] <= t1]
        stop = next((t for t in traces if t.get("native_stop_consumed")), None)
        requests = [t for t in traces if t["trace"] == "request"]
        responses = {(t["connection_id"], t["seq"]): t for t in cap["traces"] if t["trace"] == "response"}
        frame_by_stamp = {f["stamp_ns"]: f for f in cap["frames"]}
        joined, problems = [], list(cap["problems"])
        for request in requests:
            candidates = official.get((request["seq"], request["jpeg_sha256"], case["instruction"]), [])
            response = responses.get((request["connection_id"], request["seq"]))
            frame = frame_by_stamp.get(request["stamp_ns"])
            if len(candidates) != 1 or response is None or frame is None:
                problems.append(["missing_or_ambiguous_join", request["seq"], len(candidates)])
                continue
            if request["instruction_sha256"] != case["instruction_sha256"] or frame["front_sha256"] != request["jpeg_sha256"]:
                problems.append(["request_identity_mismatch", request["seq"]])
                continue
            record = candidates[0]
            wire = json.loads(response["raw_response"])["data"]
            if any(wire[k] != record[k] for k in ("raw_text", "stop", "pointing")) or wire["actions"]["actions"] != record["waypoints"]:
                problems.append(["wire_record_mismatch", request["seq"]])
                continue
            joined.append({"seq": request["seq"], "record": record, "enqueued": response["enqueued"],
                           "receive_mono_ns": response["receive_mono_ns"],
                           "capture_mono_ns": frame["capture_mono_ns"]})
        first_pose = episode["start_pose"]
        start = first_pose["x"], first_pose["y"], first_pose["yaw"]
        final = samples[-1]
        terminal = final["pose_x"], final["pose_y"], final["pose_yaw"]
        movement = displacement(start, terminal)
        target = suite["target_xy"]
        path = sum(math.dist((a["pose_x"],a["pose_y"]), (b["pose_x"],b["pose_y"]))
                   for a,b in zip(samples,samples[1:]))
        last_two = [f for f in samples if f["capture_mono_ns"] >= t1-2_000_000_000]
        contacts = max(f["backend"]["obstacle_contact_steps"] for f in samples)
        boundary = max(f["backend"]["boundary_contact_steps"] for f in samples)
        crossed = max(f["pose_x"] for f in samples) > suite["obstacle_xy"][0]+suite["obstacle_half_extents"][0]+0.35
        reached = math.dist(terminal[:2], target) <= suite["goal_radius_m"]
        distance_error = movement["forward_m"]-case["requested_distance_m"] if "requested_distance_m" in case else None
        distance_pass = (stop is not None and abs(distance_error) <= suite["distance_tolerance_m"]
                         and abs(movement["lateral_m"]) <= suite["lateral_tolerance_m"]
                         and abs(math.degrees(movement["yaw_error_rad"])) <= suite["heading_tolerance_deg"]
                         ) if distance_error is not None else None
        stop_move = None
        if stop:
            pose = stop["sim_snapshot"]["pose"]
            stop_move = displacement(start, (pose["x"],pose["y"],pose["yaw"]))
        result = {
            "id": case["id"], "language": case["language"], "category": case["category"],
            "scene": case["scene"], "instruction": case["instruction"], "requested_m": case.get("requested_distance_m"),
            "termination": episode["termination"], "decisions": episode["decisions"],
            "consumed_stop_seq": stop["seq"] if stop else None, "start_pose": list(start),
            "terminal_pose": list(terminal), **movement, "sampled_path_length_m": path,
            "distance_error_m": distance_error, "distance_diagnostic_pass": distance_pass,
            "movement_at_consumed_stop": stop_move,
            "target_distance_m": math.dist(terminal[:2],target), "within_goal_radius": reached,
            "goal_stop_pass": (reached and stop is not None) if case["category"] == "obstacle_avoidance" else None,
            "obstacle_contact_physics_steps": contacts, "boundary_contact_physics_steps": boundary,
            "maximum_obstacle_force_N": max(f["backend"]["maximum_obstacle_force_N"] for f in samples),
            "passed_obstacle_x": crossed if case["scene"] == "blocked" else None,
            "cleared_box_without_contact": crossed and contacts == 0 if case["scene"] == "blocked" else None,
            "maximum_lateral_detour_m": max(abs(displacement(start,(f["pose_x"],f["pose_y"],f["pose_yaw"]))["lateral_m"]) for f in samples),
            "minimum_base_height_m": min(f["pose_z"] for f in samples),
            "maximum_tilt_rad": max(f["backend"]["tilt_rad"] for f in samples),
            "last_two_seconds_max_abs_forward_mps": max(abs(f["velocity_linear"]) for f in last_two),
            "last_two_seconds_max_abs_yaw_rps": max(abs(f["velocity_angular"]) for f in last_two),
            "requests": len(requests), "joined": len(joined), "join_problems": problems,
            "source_wall_seconds": (t1-t0)/1e9, "capture_samples": len(samples),
        }
        results.append(result)
        before = [f for f in cap["frames"] if f["capture_mono_ns"]<t0][-1:]
        (output / f"{case['id']}_slice.json").write_text(json.dumps({
            "case": case, "episode": episode, "result": result, "frames": before+samples,
            "capture_root": cap["root"], "joined": joined, "stop": stop,
        },ensure_ascii=False,indent=2)+"\n")
    summary = {"suite": suite, "results": results,
               "capture_checks": {s:{"problems":v["problems"],"status":v["status"]} for s,v in captures.items()}}
    (output / "summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
    fields = ["id","instruction","termination","consumed_stop_seq","requested_m","forward_m","lateral_m",
              "distance_error_m","distance_diagnostic_pass","target_distance_m","obstacle_contact_physics_steps",
              "cleared_box_without_contact","goal_stop_pass"]
    with (output / "summary.csv").open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)
    print(json.dumps([{k:r.get(k) for k in fields if k!='instruction'} for r in results],indent=2))


if __name__ == "__main__":
    main()
