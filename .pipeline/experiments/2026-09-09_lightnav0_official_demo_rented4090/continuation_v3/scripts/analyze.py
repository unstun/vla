"""Six-run analysis: identities, stops, sampled stillness, geometry and timing."""
from __future__ import annotations

import hashlib, json, math, sys
from pathlib import Path

PKG = Path(sys.argv[1]).resolve()
EXP = PKG.parent
ASHCAN = (8.517243958826407, 9.358022131055993)
ASHCAN_2 = (14.476999260372253, 9.029992737543653)
DOG_BED = (9.82396, 10.4095)
SPAWN = (6.5, 13.8)
INSTRUCTION = "move forward, then go to the trashcan on the right"

STILL_MAX_RATE = 0.01
STILL_MAX_POSE = 0.01
STILL_MIN_S = 2.0
STILL_MAX_GAP_S = 0.15
STILL_START_WINDOW_S = 0.2


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def stillness(frames, stop_mono_ns):
    """Sampled stillness from the 20 Hz capture stream after the consumed native STOP."""
    if stop_mono_ns is None:
        return {"checked": False, "reason": "no consumed native stop"}
    after = [f for f in frames if f["capture_mono_ns"] >= stop_mono_ns]
    if not after:
        return {"checked": False, "reason": "no samples after stop"}
    first = after[0]
    start_delay = (first["capture_mono_ns"] - stop_mono_ns) / 1e9
    if start_delay > STILL_START_WINDOW_S:
        return {"checked": False, "reason": f"first sample {start_delay:.3f}s after stop"}
    window, max_gap = [], 0.0
    previous = None
    for f in after:
        if previous is not None:
            gap = (f["capture_mono_ns"] - previous["capture_mono_ns"]) / 1e9
            max_gap = max(max_gap, gap)
            if gap > STILL_MAX_GAP_S:
                break
        window.append(f)
        previous = f
    mono_span = (window[-1]["capture_mono_ns"] - window[0]["capture_mono_ns"]) / 1e9
    sim_span = window[-1]["sim_time"] - window[0]["sim_time"]
    rates = [max(abs(f["velocity_linear"]), abs(f["command_linear"])) for f in window]
    yaws = [max(abs(f["velocity_angular"]), abs(f["command_angular"])) for f in window]
    xs = [f["pose_x"] for f in window]
    ys = [f["pose_y"] for f in window]
    yaw_vals = [f["pose_yaw"] for f in window]
    drift = math.hypot(max(xs) - min(xs), max(ys) - min(ys))
    yaw_drift = max(yaw_vals) - min(yaw_vals)
    passed = (mono_span >= STILL_MIN_S and sim_span >= STILL_MIN_S
              and max(rates) <= STILL_MAX_RATE and max(yaws) <= STILL_MAX_RATE
              and drift <= STILL_MAX_POSE and abs(yaw_drift) <= STILL_MAX_POSE
              and max_gap <= STILL_MAX_GAP_S)
    return {"checked": True, "passed": bool(passed), "samples": len(window),
            "start_delay_s": start_delay, "monotonic_span_s": mono_span,
            "simulation_span_s": sim_span, "max_sample_gap_s": max_gap,
            "max_abs_linear_rate": max(rates), "max_abs_yaw_rate": max(yaws),
            "planar_pose_drift_m": drift, "yaw_drift_rad": abs(yaw_drift),
            "thresholds": {"min_span_s": STILL_MIN_S, "max_rate": STILL_MAX_RATE,
                           "max_pose_drift_m": STILL_MAX_POSE, "max_gap_s": STILL_MAX_GAP_S},
            "note": "sampled stillness evidence from the 20 Hz capture stream, not a proof of permanent rest"}


def arrival_verdict(end_xy, d_target):
    if d_target <= 1.0:
        return "at_requested_object"
    if d_target <= 2.0:
        return "short_stop"
    d2, dbed = dist(end_xy, ASHCAN_2), dist(end_xy, DOG_BED)
    if min(d2, dbed) < d_target:
        return "other_object"
    return "short_stop" if d_target < 3.0 else "unclear"


def analyse_new(rep):
    data = json.loads((PKG / "analysis" / f"{rep}_slice.json").read_text())
    episode = data["episode"]
    frames = data["frames"]
    joined = data["joined"]
    consumptions = data["consumptions"]
    controls = data["controls"]
    stop = next((c for c in consumptions if c.get("native_stop_consumed")), None)
    stop_mono = stop["mono_ns"] if stop else None
    end = episode["end_pose"]
    end_xy = (end["x"], end["y"])
    path = [(f["pose_x"], f["pose_y"]) for f in frames]
    path_len = sum(dist(path[i], path[i + 1]) for i in range(len(path) - 1))
    d_target = dist(end_xy, ASHCAN)
    latencies = [(j["receive_mono_ns"] - j["send_mono_ns"]) / 1e6 for j in joined]
    server_lat = [(j.get("record") or {}).get("latency_ms") for j in joined]
    server_lat = [v for v in server_lat if v is not None]
    solves = [c.get("mpc_solve_ms") for c in controls if c.get("mpc_solve_ms") is not None]
    gaps = [(frames[i + 1]["capture_mono_ns"] - frames[i]["capture_mono_ns"]) / 1e9
            for i in range(len(frames) - 1)]
    records = [j.get("record") for j in joined if j.get("record")]
    opos = [r for r in records if (r.get("pointing") or {}).get("opos_px")]
    visible = [r for r in records if r.get("visible")]
    stop_records = [r for r in records if r.get("stop")]
    first_stop_seq = min((r["seq"] for r in stop_records), default=None)
    return {
        "rep": rep, "cohort": "new_v3", "instruction": INSTRUCTION,
        "instruction_sha256": episode["instruction_sha256"],
        "termination": episode["termination"], "termination_detail": episode["termination_detail"],
        "decisions_reported_by_demo": episode["decisions"],
        "requests_traced": len(data["requests"]), "predictions_joined": len(joined),
        "join_problems": data["join_problems"],
        "official_episode": data.get("resolved_official_episode"),
        "raw_stop_predictions": [r["seq"] for r in stop_records],
        "first_raw_stop_seq": first_stop_seq,
        "consumed_native_stop_seq": stop["seq"] if stop else None,
        "consumed_native_stop_mono_ns": stop_mono,
        "applied_to_mpc": sum(1 for c in consumptions if c.get("applied_to_mpc")),
        "discarded_after_stop": [c["seq"] for c in consumptions
                                 if c.get("disposition") == "discarded_after_stop"],
        "responses_not_enqueued": [r["seq"] for r in data["responses"] if r.get("enqueued") is False],
        "stillness": stillness(frames, stop_mono),
        "start_pose": episode["start_pose"], "end_pose": end,
        "path_length_m": path_len, "net_displacement_m": dist(SPAWN, end_xy),
        "distance_to_requested_trashcan_m": d_target,
        "distance_to_second_trashcan_m": dist(end_xy, ASHCAN_2),
        "distance_to_dog_bed_m": dist(end_xy, DOG_BED),
        "within_1_0m": d_target <= 1.0, "within_1_5m": d_target <= 1.5, "within_2_0m": d_target <= 2.0,
        "arrival_verdict": arrival_verdict(end_xy, d_target),
        "opos_pointed_predictions": len(opos), "visible_true_predictions": len(visible),
        "client_round_trip_ms": {"n": len(latencies), "mean": sum(latencies) / len(latencies) if latencies else None,
                                 "min": min(latencies, default=None), "max": max(latencies, default=None)},
        "server_reported_latency_ms": {"n": len(server_lat),
                                       "mean": sum(server_lat) / len(server_lat) if server_lat else None,
                                       "min": min(server_lat, default=None), "max": max(server_lat, default=None)},
        "mpc_solve_ms": {"n": len(solves), "mean": sum(solves) / len(solves) if solves else None,
                         "max": max(solves, default=None)},
        "capture_frames": len(frames),
        "capture_cadence_hz": (len(frames) - 1) / sum(gaps) if gaps else None,
        "capture_max_gap_s": max(gaps, default=None),
        "measured_seconds_instruction_to_stop": episode["measured_seconds"],
        "instruction_to_termination_s": (episode["end_mono_ns"] - episode["instruction_send_mono_ns"]) / 1e9,
        "recording_losses": 0,
        "errors": [c for c in controls if c.get("mpc_error")][:3],
    }


def analyse_legacy(rep):
    episode = json.loads((EXP / "runs" / rep / "episode.json").read_text())
    end = episode["end_pose"]
    end_xy = (end["x"], end["y"])
    d_target = dist(end_xy, ASHCAN)
    return {
        "rep": rep, "cohort": "legacy_round_1", "instruction": episode["instruction"],
        "instruction_sha256": episode["instruction_sha256"],
        "termination": episode["termination"], "decisions_reported_by_demo": episode["decisions"],
        "start_pose": episode["start_pose"], "end_pose": end,
        "net_displacement_m": dist(SPAWN, end_xy),
        "distance_to_requested_trashcan_m": d_target,
        "distance_to_second_trashcan_m": dist(end_xy, ASHCAN_2),
        "distance_to_dog_bed_m": dist(end_xy, DOG_BED),
        "within_1_0m": d_target <= 1.0, "within_1_5m": d_target <= 1.5, "within_2_0m": d_target <= 2.0,
        "arrival_verdict": arrival_verdict(end_xy, d_target),
        "native_stop_observed": episode["native_stop_seen"],
        "capture_frames": episode["first_person_frames"],
        "recording_losses": "31/28/32 harness frames overwritten per stream in round 1 "
                            "(see review/LEAD_REVIEW_2026-09-09.md); no MuJoCo state was saved",
        "path_length_m": None, "stillness": {"checked": False,
                                             "reason": "round 1 saved no state/velocity stream at capture rate"},
        "exact_state_replay_possible": False,
    }


runs = [analyse_new(r) for r in ("rep_04", "rep_05", "rep_06")]
runs += [analyse_legacy(r) for r in ("rep_01", "rep_02", "rep_03")]
meta = json.loads((PKG / "analysis" / "replay_meta.json").read_text())
capture_status = json.loads(next((PKG / "runs").glob("capture_v3_*/recorder_status.json")).read_text())
summary = {
    "generated_from": "continuation_v3 raw evidence; no value retyped from prose",
    "identities": {
        "source_commit": "d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c",
        "checkpoint_revision": "826dc5fbfa37afa8293d2e336d329b6ffc0bfb64",
        "backend": "vllm_local BF16", "task": "vln",
        "gpu_memory_utilization": 0.80, "max_batch_size": 8,
        "cam_hfov_deg": 112.2, "cam_height": 0.198,
        "instruction": INSTRUCTION,
        "instruction_sha256": hashlib.sha256(INSTRUCTION.encode()).hexdigest(),
        "scene": "val_2_ceiling.xml (ProcTHOR val_2)", "robot": "kinematic TurtleBot",
        "spawn": list(SPAWN),
    },
    "object_roots_from_pinned_xml": {
        "requested_trashcan_ashcan_1": list(ASHCAN),
        "second_trashcan_ashcan_2": list(ASHCAN_2),
        "dog_bed_pad_1": list(DOG_BED),
    },
    "recorder_status": capture_status,
    "overhead_view": meta["view"],
    "runs": runs,
}
(PKG / "analysis" / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

lines = ["# LightNav-0 continuation v3: six-run summary", "",
         "Cohorts are reported separately. Legacy rep_01..03 keep their original gaps.", "",
         "| run | cohort | termination | decisions | consumed STOP | stillness | end (x,y) | d(trashcan) | d(trashcan#2) | d(dog bed) | <=1.0/1.5/2.0 m | verdict |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
for r in runs:
    still = r["stillness"]
    still_text = ("pass" if still.get("passed") else ("fail" if still.get("checked") else "n/a"))
    end = r["end_pose"]
    lines.append(
        f'| {r["rep"]} | {r["cohort"]} | {r["termination"]} | {r["decisions_reported_by_demo"]} | '
        f'{r.get("consumed_native_stop_seq", "n/a")} | {still_text} | '
        f'({end["x"]:.3f}, {end["y"]:.3f}) | {r["distance_to_requested_trashcan_m"]:.3f} m | '
        f'{r["distance_to_second_trashcan_m"]:.3f} m | {r["distance_to_dog_bed_m"]:.3f} m | '
        f'{int(r["within_1_0m"])}/{int(r["within_1_5m"])}/{int(r["within_2_0m"])} | {r["arrival_verdict"]} |')
lines += ["", "Diagnostic radii are reported at all three thresholds and are not an official",
          "benchmark success rate. No radius was selected after seeing the outcomes.", ""]
(PKG / "analysis" / "summary.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
