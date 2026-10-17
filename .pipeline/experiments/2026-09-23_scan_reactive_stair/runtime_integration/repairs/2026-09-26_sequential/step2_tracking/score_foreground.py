"""Host-only scoring. Actor truth is loaded only after inference has finished."""
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
RI = HERE.parents[2]
SOURCE = "sensor_lidar_static_background_cluster_v3"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ns(stamp):
    return stamp["sec"] * 1_000_000_000 + stamp["nanosec"]


def normalized_ros(msg):
    return {"stamp_ns": ns(msg["header"]["stamp"]), "frame": msg["header"]["frame_id"],
            "source_id": msg["source_id"], "complete": msg["complete"],
            "tracks": [{"id": t["id"], "stamp_ns": ns(t["observed_at"]),
                        "center": [t["center"][v] for v in ("x", "y", "z")], "radius_m": t["radius_m"]}
                       for t in msg["tracks"]]}


def same_snapshot(a, b):
    if any(a[k] != b[k] for k in ("stamp_ns", "frame", "source_id", "complete")) or len(a["tracks"]) != len(b["tracks"]):
        return False
    for ta, tb in zip(a["tracks"], b["tracks"]):
        if ta["id"] != tb["id"] or ta["stamp_ns"] != tb["stamp_ns"] or \
           abs(ta["radius_m"] - tb["radius_m"]) > 1e-6 or math.dist(ta["center"], tb["center"]) > 1e-6:
            return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    out = args.run / "review.json"
    if out.exists():
        raise FileExistsError(out)
    numeric = json.loads((args.run / "results/numeric/result.json").read_text())
    transport = json.loads((args.run / "results/ros/result.json").read_text())
    local = json.loads((HERE / "local_wrapper_v1/result.json").read_text())
    execution = json.loads((args.run / "execution_result.json").read_text())
    report = {"passed": False, "runs": [], "python": numeric["python"], "numpy": numeric["numpy"],
              "scipy": numeric["scipy"], "numeric_ros_complete": numeric["completed"] and transport["completed"],
              "returned_hashes_match": execution["returned_hashes_match"],
              "input_manifest_matches": numeric["input_manifest_sha256"] == transport["input_manifest_sha256"] == local["input_manifest_sha256"],
              "files_sha256": {p: sha(args.run / p) for p in ("results/numeric/result.json", "results/ros/result.json", "execution_result.json")},
              "scorer_sha256": sha(Path(__file__)),
              "claim": "Frozen-runtime tracking component and recorded-input ROS integration only; not live navigation or stair avoidance acceptance."}
    for nr, rr, lr in zip(numeric["runs"], transport["runs"], local["runs"]):
        assert nr["name"] == rr["name"] == lr["name"]
        truthpath = RI / "runs" / nr["name"] / "returned_artifacts/runner_output/official_human_truth.jsonl"
        truth = [json.loads(v) for v in truthpath.open()]
        by_stamp = {}
        for r in rr["received"]:
            v = normalized_ros(r["data"])
            by_stamp.setdefault(v["stamp_ns"], []).append((v, r["arrival_wall"]))
        sent = {r["stamp_ns"]: r for r in rr["sent"]}
        evaluation, latency = [], []
        for f, lf in zip(nr["frames"], lr["frames"]):
            s = f["snapshot"]
            actor = min(truth, key=lambda t: abs(t["sim_time_s"] - f["sim_time_s"]))["actor_truth"]["ground_xyz_m"]
            near = sum(math.dist(t["center"][:2], actor[:2]) < .65 for t in s["tracks"])
            matches = [arrival for received, arrival in by_stamp.get(s["stamp_ns"], []) if same_snapshot(s, received)]
            if matches:
                latency.append(min(matches) - sent[s["stamp_ns"]]["publish_wall"])
            evaluation.append({"scan_id": f["scan_id"], "sim_time_s": f["sim_time_s"],
                               "complete": s["complete"], "tracks": len(s["tracks"]), "near_actor": near,
                               "ros_matches_numeric": bool(matches), "local_matches_foxy": same_snapshot(s, lf["snapshot"])})
        summary = {"name": nr["name"], "frames": len(evaluation),
                   "complete_actor_frames": sum(f["complete"] and f["near_actor"] > 0 for f in evaluation),
                   "first_complete_actor_time_s": next((f["sim_time_s"] for f in evaluation if f["complete"] and f["near_actor"]), None),
                   "pre_motion_track_frames": sum(f["sim_time_s"] < 10 and f["tracks"] > 0 for f in evaluation),
                   "outside_actor_track_frames": sum(f["tracks"] > f["near_actor"] for f in evaluation),
                   "ros_matching_frames": sum(f["ros_matches_numeric"] for f in evaluation),
                   "local_matching_frames": sum(f["local_matches_foxy"] for f in evaluation),
                   "track_ids": sorted({t["id"] for f in nr["frames"] for t in f["snapshot"]["tracks"]}),
                   "source_ids": sorted({f["snapshot"]["source_id"] for f in nr["frames"]}),
                   "max_numeric_frame_s": nr["max_frame_wall_s"], "max_ros_receive_latency_s": max(latency) if latency else None,
                   "wrong_schema_incomplete_seen": rr["wrong_schema_incomplete_seen"],
                   "truth_sha256": sha(truthpath), "mismatched_frames": [f for f in evaluation if not f["ros_matches_numeric"] or not f["local_matches_foxy"]]}
        summary["passed"] = (summary["frames"] == summary["ros_matching_frames"] == summary["local_matching_frames"] and
                             summary["complete_actor_frames"] == 189 and summary["track_ids"] == ["cluster-1"] and
                             summary["source_ids"] == [SOURCE] and summary["pre_motion_track_frames"] == 0 and
                             summary["outside_actor_track_frames"] == 0 and summary["wrong_schema_incomplete_seen"] and
                             summary["max_ros_receive_latency_s"] < .25)
        report["runs"].append(summary)
    report["passed"] = (report["numeric_ros_complete"] and report["returned_hashes_match"] and
                        report["input_manifest_matches"] and len(report["runs"]) == 2 and all(r["passed"] for r in report["runs"]))
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
