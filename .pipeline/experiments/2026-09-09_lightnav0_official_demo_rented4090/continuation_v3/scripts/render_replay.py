"""Offline state replay: slice runs, join predictions, render the overhead view.

No stepping, no policy, no control. mj_setState + mj_forward only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v3_join import join_predictions
from v3_render import make_overhead_renderer
from v3_timeline import build_timeline

REPS = ("rep_04", "rep_05", "rep_06")
FPS = 20


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", required=True)
    ap.add_argument("--runs", required=True)
    ap.add_argument("--records", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ffmpeg", required=True)
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=768)
    args = ap.parse_args()

    capture = Path(args.capture)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    frames = load_jsonl(capture / "frames_index.jsonl")
    traces = load_jsonl(capture / "traces.jsonl")
    by_stamp = {f["stamp_ns"]: f for f in frames}

    requests = [t for t in traces if t["trace"] == "request"]
    responses = [t for t in traces if t["trace"] == "response"]
    consumptions = [t for t in traces if t["trace"] == "consumption"]
    controls = [t for t in traces if t["trace"] == "control"]
    lifecycle = [t for t in traces if t["trace"] == "lifecycle"]
    geometry = next((t for t in traces if t["trace"] == "camera_geometry"), None)

    # official model records: connection dirs, images hashed for the exact join
    record_root = Path(args.records)
    record_runs = sorted([p for p in record_root.iterdir() if p.is_dir()])
    official = {}
    for run_dir in record_runs:
        for conn in sorted(run_dir.iterdir()):
            for episode in sorted(conn.glob("episode_*")):
                actions_file = episode / "actions.json"
                if not actions_file.exists():
                    continue
                entries = json.loads(actions_file.read_text())
                for entry in entries:
                    image = episode / f"image_{entry['step']:06d}.jpg"
                    entry["image_path"] = str(image)
                    entry["image_sha256"] = sha256_file(image) if image.exists() else None
                official[f"{run_dir.name}/{conn.name}/{episode.name}"] = entries

    import mujoco
    from vln_mujoco.robots.turtlebot import build_model

    model = build_model()
    probe = mujoco.MjData(model)
    mujoco.mj_forward(model, probe)
    targets = {}
    for name in ("ashcan", "dog_bed"):
        pass
    body_positions = {}
    for bid in range(model.nbody):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, bid) or ""
        body_positions[name] = [float(v) for v in probe.xpos[bid]]

    # Per-run slices from the harness monotonic boundaries.
    runs = {}
    for rep in REPS:
        episode = json.loads((Path(args.runs) / rep / "episode.json").read_text())
        t0 = episode["instruction_send_mono_ns"]
        t1 = episode["end_mono_ns"]
        run_frames = [f for f in frames if t0 <= f["capture_mono_ns"] <= t1]
        run_requests = [r for r in requests if t0 <= r["send_mono_ns"] <= t1]
        conn_ids = sorted({r["connection_id"] for r in run_requests})
        joined_all, problems_all = [], []
        for conn in conn_ids:
            for key, entries in official.items():
                joined, problems = join_predictions(run_frames, run_requests, responses, entries, conn)
                if joined:
                    for item in joined:
                        item["official_key"] = key
                    joined_all.extend(joined)
                    problems_all.extend(problems)
                    break
            else:
                joined, problems = join_predictions(run_frames, run_requests, responses, [], conn)
                joined_all.extend(joined)
                problems_all.extend(problems)
        runs[rep] = {
            "episode": episode,
            "frames": run_frames,
            "requests": run_requests,
            "responses": [r for r in responses if t0 <= r["receive_mono_ns"] <= t1],
            "consumptions": [c for c in consumptions if t0 <= c["mono_ns"] <= t1],
            "controls": [c for c in controls if t0 <= c["mono_ns"] <= t1],
            "lifecycle": [c for c in lifecycle if t0 <= c["mono_ns"] <= t1],
            "connection_ids": conn_ids,
            "joined": sorted(joined_all, key=lambda j: j["seq"]),
            "join_problems": problems_all,
        }

    # One common fixed view covering every new run plus both objects.
    xs, ys = [], []
    for rep in REPS:
        xs += [f["pose_x"] for f in runs[rep]["frames"]]
        ys += [f["pose_y"] for f in runs[rep]["frames"]]
    for name in ("ashcan", "dog_bed"):
        pass
    for point in (body_positions.get("ashcan"), body_positions.get("dog_bed")):
        if point:
            xs.append(point[0]); ys.append(point[1])
    margin = 1.2
    xmin, xmax = min(xs) - margin, max(xs) + margin
    ymin, ymax = min(ys) - margin, max(ys) + margin
    aspect = args.width / args.height
    span_y = max(ymax - ymin, (xmax - xmin) / aspect) * 1.12
    lookat = ((xmin + xmax) / 2.0, (ymin + ymax) / 2.0, 0.0)
    view = {"lookat": list(lookat), "vertical_span_m": span_y,
            "horizontal_span_m": span_y * aspect, "width": args.width, "height": args.height,
            "x_range": [lookat[0] - span_y * aspect / 2, lookat[0] + span_y * aspect / 2],
            "y_range": [lookat[1] - span_y / 2, lookat[1] + span_y / 2],
            "common_for_all_new_runs": True}

    renderer, camera, hidden = make_overhead_renderer(
        model, width=args.width, height=args.height, vertical_span_m=span_y, lookat=lookat)
    projection = {k: np.asarray(getattr(renderer.scene.camera[0], k)).tolist()
                  for k in ("pos", "forward", "up", "frustum_width", "frustum_bottom",
                            "frustum_top", "frustum_near", "frustum_far", "orthographic")}
    assert int(projection["orthographic"]) == 1

    states = np.memmap(capture / "states.f64", dtype=np.uint8, mode="r")
    replay_data = mujoco.MjData(model)
    signature = mujoco.mjtState.mjSTATE_INTEGRATION
    meta = {}

    for rep in REPS:
        info = runs[rep]
        episode = info["episode"]
        t0, t1 = episode["instruction_send_mono_ns"], episode["end_mono_ns"]
        timeline = build_timeline(t0, t1, info["frames"], [
            {"receive_mono_ns": j["receive_mono_ns"], **j} for j in info["joined"]], fps=FPS)
        target = out / f"topdown_raw_{rep}.mp4"
        proc = subprocess.Popen(
            [args.ffmpeg, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{args.width}x{args.height}", "-r", str(FPS), "-i", "-",
             "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "14",
             "-pix_fmt", "yuv444p", str(target)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        rendered = 0
        last_frame_id = None
        for entry in timeline:
            frame = entry["frame"]
            if frame is None:
                proc.stdin.write(np.zeros((args.height, args.width, 3), np.uint8).tobytes())
                rendered += 1
                continue
            if frame["frame_id"] != last_frame_id:
                offset = frame["state_offset"]
                nbytes = frame["state_bytes"]
                buf = np.frombuffer(bytes(states[offset:offset + nbytes]), dtype=np.float64)
                mujoco.mj_setState(model, replay_data, buf, signature)
                mujoco.mj_forward(model, replay_data)
                renderer.update_scene(replay_data, camera=camera)
                image = renderer.render()
                last_frame_id = frame["frame_id"]
            proc.stdin.write(np.ascontiguousarray(image).tobytes())
            rendered += 1
        proc.stdin.close()
        proc.wait()
        meta[rep] = {
            "presentation_frames": len(timeline),
            "rendered_frames": rendered,
            "unique_states_rendered": len({e["frame_id"] for e in timeline if e["frame"]}),
            "raw_video": str(target),
            "raw_video_sha256": sha256_file(target),
            "fps": FPS,
            "source_span_ns": t1 - t0,
            "label": "state_replay",
        }
        # Export the per-run join and slice for local analysis and composition.
        payload = {
            "rep": rep,
            "episode": episode,
            "connection_ids": info["connection_ids"],
            "frames": info["frames"],
            "requests": info["requests"],
            "responses": [{k: v for k, v in r.items() if k != "raw_response"} for r in info["responses"]],
            "raw_responses": {str(r["seq"]): r.get("raw_response") for r in info["responses"]},
            "consumptions": info["consumptions"],
            "controls": info["controls"],
            "lifecycle": info["lifecycle"],
            "join_problems": info["join_problems"],
            "joined": [{k: v for k, v in j.items() if k not in ("frame", "response")} for j in info["joined"]],
            "timeline_len": len(timeline),
        }
        (out / f"{rep}_slice.json").write_text(json.dumps(payload, indent=2) + "\n")

    renderer.close()
    (out / "replay_meta.json").write_text(json.dumps({
        "view": view, "projection": projection, "hidden_offline_ceiling_geoms": hidden,
        "mujoco": mujoco.__version__, "state_signature": int(signature),
        "state_size": int(mujoco.mj_stateSize(model, signature)),
        "body_positions": {k: v for k, v in body_positions.items()
                           if any(token in k.lower() for token in
                                  ("ashcan", "dog", "bed", "trash", "garbage", "base_link"))},
        "all_body_names": [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, bid) or ""
                           for bid in range(model.nbody)],
        "camera_geometry_trace": geometry,
        "runs": meta,
        "official_record_keys": list(official),
        "simulation_steps": 0,
        "new_vla_inference": False,
    }, indent=2) + "\n")
    print(json.dumps({"runs": {k: {"presentation_frames": v["presentation_frames"],
                                   "unique_states": v["unique_states_rendered"]}
                               for k, v in meta.items()},
                      "view": view}, indent=2))


if __name__ == "__main__":
    main()
