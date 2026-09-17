#!/usr/bin/env python3
"""Render a synchronized walk-review MP4 for one continuous two-goal run.

Layout (1280x720): the runner's third-person camera scaled to 853x480 (top
left) with a banner, a top-down map (top right, 427x480) and a time strip
(bottom, 1280x240). Every drawn value comes from recorded files:

- video frame i <-> the camera_frames.jsonl row with frame_index i (sim_time_s);
- robot state <-> the metrics.jsonl row with the same control step (0.02 s
  records; nothing is interpolated);
- events and phases <-> pilot_journal.json driver events and backend terminal
  records. Wall/backend monotonic times are mapped to simulation time with the
  rule of p2b_execution/review_two_goal.py: the last metrics row whose
  state_sample_monotonic_ns is not later than the event.

The script only reads a run and never drives a simulator. Run packages are
immutable, so --output is required and must point outside them unless the
package owner asked for the file.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

FRAME_W, FRAME_H = 1280, 720
CAM_W, CAM_H = 853, 480
STRIP_H = FRAME_H - CAM_H
DEFAULT_GOAL_TOLERANCE_M = 0.25
# Same freshness bound as review_two_goal.py raw_state_fresh (0 <= lag <= 0.25 s).
MAX_EVENT_STATE_LAG_S = 0.25
SIZE_TARGET_BYTES = 2_000_000
SIZE_TARGET_EPISODE_S = 17.0
ENCODERS = ("libx264", "h264_nvenc", "h264_videotoolbox")

# Driver request ids and expected terminal statuses: pilot_driver_source() in
# run_two_goal_pilot.py and review_two_goal.py (wanted list).
REQUEST_SUFFIXES = {
    "a1": "-goal-a-attempt-1",
    "a2": "-goal-a-attempt-2",
    "b": "-goal-b",
}
EXPECTED_STATUS = {"a1": "cancelled", "a2": "arrived", "b": "arrived"}
REQUEST_LABEL = {"a1": "A attempt 1", "a2": "A attempt 2", "b": "B"}

# (key, marker label, phase text) for events every passing run must record.
EXPECTED_EVENTS = [
    ("goal_a_sent", "goal A", "walking to A"),
    ("cancel_sent", "cancel", "cancel sent, stopping"),
    ("cancel_confirmed", "cancelled", "cancel confirmed, stopping"),
    ("still_confirmed", "still", "still confirmed"),
    ("goal_a_resent", "resubmit A", "resubmitted A, walking to A"),
    ("arrived_a", "arrived A", "arrived A"),
    ("goal_b_sent", "goal B", "walking to B"),
    ("arrived_b", "arrived B", "arrived B"),
]
EXPECTED_KEYS = [key for key, _, _ in EXPECTED_EVENTS]
INITIAL_PHASE = "standing, no goal sent"


class InputError(RuntimeError):
    """A recorded input is missing or inconsistent; nothing is rendered."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path) -> dict:
    path = Path(path)
    return {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def locate_inputs(run: Path, artifacts: Path, video: Optional[Path]) -> Dict[str, Optional[Path]]:
    paths = {
        "video": Path(video) if video else artifacts / "runner_output/third_person_master.mp4",
        "camera_frames": artifacts / "runner_output/camera_frames.jsonl",
        "metrics": artifacts / "runner_output/metrics.jsonl",
        "run_clock": artifacts / "runner_output/run_clock.json",
        "pilot_journal": artifacts / "pilot_journal.json",
    }
    missing = ["%s (%s)" % (name, path) for name, path in paths.items() if not path.is_file()]
    if missing:
        hint = " The original video may be remote-only; pass --video." if not paths["video"].is_file() else ""
        raise InputError("missing inputs: " + ", ".join(missing) + "." + hint)
    optional = {
        "summary": artifacts / "runner_output/summary.json",
        "pilot": run / "inputs/pilot.json",
        "run_request": run / "run_request.json",
    }
    for name, path in optional.items():
        paths[name] = path if path.is_file() else None
    return paths


def load_camera_rows(path: Path) -> List[dict]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise InputError("camera_frames.jsonl is empty")
    indices = [row.get("frame_index") for row in rows]
    if indices != list(range(len(rows))):
        raise InputError("camera_frames.jsonl frame_index is not contiguous from 0")
    times = [float(row["sim_time_s"]) for row in rows]
    if any(b <= a for a, b in zip(times, times[1:])):
        raise InputError("camera_frames.jsonl sim_time_s is not strictly increasing")
    return rows


def load_state_rows(path: Path) -> List[dict]:
    """Keep only the metrics fields the review draws, one line at a time."""
    keep = ("step", "sim_time_s", "state_sample_monotonic_ns", "base_xyz", "base_rpy_rad",
            "horizontal_speed_mps", "command_horizontal_norm_mps", "admitted_command", "raw_command",
            "nonfoot_force_max_n")
    rows = []
    with Path(path).open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            missing = [key for key in keep if key not in row]
            if missing:
                raise InputError("metrics.jsonl row lacks " + ", ".join(missing))
            rows.append({key: row[key] for key in keep})
    if not rows:
        raise InputError("metrics.jsonl is empty")
    return rows


def align_frames(video_frames: int, camera_rows: int) -> Tuple[int, str]:
    """Pair video frame i with camera row i; tolerate one unpaired trailing item."""
    diff = video_frames - camera_rows
    if diff == 0:
        return camera_rows, "equal: video frame i is paired with camera_frames frame_index i"
    if diff == 1:
        return camera_rows, ("video_plus_one: the video has one more frame than camera_frames.jsonl; frames are "
                             "paired by index and the trailing video frame, which has no pose row, is not rendered")
    if diff == -1:
        return video_frames, ("camera_plus_one: camera_frames.jsonl has one more row than the video; frames are "
                              "paired by index and the last camera row, which has no video frame, is not rendered")
    raise InputError(
        "frame count mismatch: the video has %d frames and camera_frames.jsonl has %d rows "
        "(difference %+d exceeds the 1-frame tolerance)" % (video_frames, camera_rows, diff)
    )


class StateIndex:
    def __init__(self, rows: List[dict]):
        self.rows = rows
        self.sim = [float(r["sim_time_s"]) for r in rows]
        self.mono = [int(r["state_sample_monotonic_ns"]) for r in rows]
        if any(b <= a for a, b in zip(self.sim, self.sim[1:])):
            raise InputError("metrics.jsonl sim_time_s is not strictly increasing")
        if any(b < a for a, b in zip(self.mono, self.mono[1:])):
            raise InputError("metrics.jsonl state_sample_monotonic_ns decreases")
        self.by_step = {int(r["step"]): i for i, r in enumerate(rows)}

    def row_for_frame(self, frame: dict) -> Tuple[int, str]:
        t = float(frame["sim_time_s"])
        idx = self.by_step.get(int(frame.get("step", -1)))
        if idx is not None and abs(self.sim[idx] - t) <= 1e-6:
            return idx, "same_step"
        idx = bisect.bisect_right(self.sim, t + 1e-9) - 1
        if idx < 0:
            raise InputError("camera frame at sim %.3f s precedes the first metrics row" % t)
        return idx, "last_row_not_after_frame"

    def sim_at_monotonic(self, monotonic_ns: int) -> dict:
        """review_two_goal.py rule: last row with state_sample_monotonic_ns <= event."""
        idx = bisect.bisect_right(self.mono, int(monotonic_ns)) - 1
        if idx < 0:
            return {"sim_time_s": None, "placement": "before_first_state_row"}
        lag = (int(monotonic_ns) - self.mono[idx]) / 1e9
        record = {"sim_time_s": self.sim[idx], "state_row": idx, "state_row_lag_s": lag, "placement": "timeline"}
        if lag > MAX_EVENT_STATE_LAG_S:
            record["placement"] = "after_recorded_state"
        return record


def resolve_run_id(run: Path, paths: dict, journal: dict) -> Tuple[str, str]:
    if paths.get("run_request"):
        run_id, source = load_json(paths["run_request"])["run_id"], "run_request.json run_id"
    else:
        run_id, source = run.name, "run directory name (remote_worker.py passes run_root.name as the run id)"
    for event in journal.get("events", []):
        snapshot = event.get("snapshot") if event.get("event") in {"initial_snapshot", "initial_cancel_reference_snapshot"} else None
        if snapshot and snapshot.get("run_id") not in (None, run_id):
            raise InputError("run id %r differs from the journal's initial snapshot run id %r" % (run_id, snapshot.get("run_id")))
    return run_id, source


def resolve_goals(journal: dict, pilot: Optional[dict]) -> Dict[str, dict]:
    goals: Dict[str, dict] = {}
    if pilot:
        for goal in pilot.get("goals", []):
            goals[goal["goal_id"]] = {"ground_xyz_m": [float(v) for v in goal["ground_xyz_m"]],
                                      "source": "inputs/pilot.json goals"}
    for event in journal.get("events", []):
        if event.get("event") != "post_goal":
            continue
        payload = event.get("payload") or {}
        goal_id, target = payload.get("goal_id"), payload.get("target_ground_xyz")
        if goal_id is None or target is None:
            continue
        target = [float(v) for v in target]
        known = goals.get(goal_id)
        if known is None:
            goals[goal_id] = {"ground_xyz_m": target, "source": "pilot_journal.json post_goal payload target_ground_xyz"}
        elif max(abs(a - b) for a, b in zip(known["ground_xyz_m"], target)) > 1e-9:
            raise InputError("goal %s differs between inputs/pilot.json and the journal request %s" % (goal_id, payload.get("request_id")))
        else:
            known["source"] += " (matches pilot_journal.json post_goal payload)"
    for goal_id in ("goal-a", "goal-b"):
        if goal_id not in goals:
            raise InputError("goal %s position is not recorded in inputs/pilot.json or the journal" % goal_id)
    return goals


def extract_journal(journal: dict, run_id: str, state: StateIndex) -> dict:
    """Collect events, positions and plans with review_two_goal.py field names."""
    request_ids = {key: run_id + suffix for key, suffix in REQUEST_SUFFIXES.items()}
    key_by_request = {value: key for key, value in request_ids.items()}
    terminals: Dict[Tuple[str, str], dict] = {}
    plans: Dict[str, dict] = {}
    events: List[dict] = []
    points: Dict[str, dict] = {}
    order = 0

    def add(key, label, source, monotonic_ns=None, sim_time_s=None, **extra):
        nonlocal order
        order += 1
        record = {"key": key, "label": label, "source": source, "journal_order": order}
        if monotonic_ns is not None:
            record["monotonic_ns"] = int(monotonic_ns)
            record.update(state.sim_at_monotonic(monotonic_ns))
        else:
            record.update({"sim_time_s": sim_time_s, "placement": "timeline", "time_source": "recorded sim_time_s"})
        record.update(extra)
        events.append(record)
        return record

    for event in journal.get("events", []):
        name = event.get("event")
        state_record = event.get("state") or {}
        for terminal in state_record.get("terminal_results", []):
            terminals.setdefault((terminal.get("request_id"), terminal.get("status")), terminal)
        for plan in (state_record.get("pct") or {}).get("plan_history", []):
            plans.setdefault(plan.get("request_id", str(len(plans))), plan)
        if name in {"initial_snapshot", "initial_cancel_reference_snapshot"} and "start" not in points:
            points["start"] = {"xyz": event["snapshot"]["measured"]["base_xyz"],
                               "source": "pilot_journal.json %s snapshot.measured.base_xyz" % name}
        elif name == "post_goal":
            payload = event.get("payload") or {}
            key = key_by_request.get(payload.get("request_id"))
            accepted = (event.get("response") or {}).get("ok") is True
            if key is None:
                continue
            ev_key = {"a1": "goal_a_sent", "a2": "goal_a_resent", "b": "goal_b_sent"}[key]
            label = {"a1": "goal A", "a2": "resubmit A", "b": "goal B"}[key]
            add(ev_key, label if accepted else label + " rejected", "pilot_journal.json post_goal wall_monotonic_ns",
                monotonic_ns=event["wall_monotonic_ns"], accepted=accepted, request_id=payload.get("request_id"))
        elif name == "post_cancel":
            trigger = event["trigger_snapshot"]
            points["cancel"] = {"xyz": trigger["measured"]["base_xyz"],
                                "source": "pilot_journal.json post_cancel trigger_snapshot.measured.base_xyz"}
            add("cancel_sent", "cancel", "pilot_journal.json post_cancel wall_monotonic_ns",
                monotonic_ns=event["wall_monotonic_ns"], snapshot_sim_time_s=trigger.get("sim_time_s"),
                cancel_displacement_m=event.get("cancel_displacement_m"),
                accepted=(event.get("response") or {}).get("ok") is True)
        elif name == "post_stop_proof":
            snapshot = event["snapshot"]
            points["stop"] = {"xyz": snapshot["measured"]["base_xyz"],
                              "source": "pilot_journal.json post_stop_proof snapshot.measured.base_xyz"}
            add("still_dwell_start", "dwell", "pilot_journal.json post_stop_proof dwell_start_sim_s",
                sim_time_s=float(event["dwell_start_sim_s"]))
            add("still_confirmed", "still", "pilot_journal.json post_stop_proof wall_monotonic_ns",
                monotonic_ns=event["wall_monotonic_ns"], snapshot_sim_time_s=snapshot.get("sim_time_s"),
                dwell_sim_s=float(snapshot["sim_time_s"]) - float(event["dwell_start_sim_s"]))
        elif name == "driver_error":
            add("driver_error", "driver error", "pilot_journal.json driver_error wall_monotonic_ns",
                monotonic_ns=event["wall_monotonic_ns"], error=str(event.get("error", ""))[:300])

    for (request_id, status), terminal in terminals.items():
        key = key_by_request.get(request_id)
        if key is None:
            continue
        source = "pilot_journal.json state.terminal_results monotonic_s (backend)"
        mono = int(round(float(terminal["monotonic_s"]) * 1e9))
        if status == EXPECTED_STATUS[key]:
            ev_key = {"a1": "cancel_confirmed", "a2": "arrived_a", "b": "arrived_b"}[key]
            label = {"a1": "cancelled", "a2": "arrived A", "b": "arrived B"}[key]
            add(ev_key, label, source, monotonic_ns=mono, request_id=request_id, cause=terminal.get("cause"))
        else:
            add("terminal_" + status, "%s %s" % (REQUEST_LABEL[key], status), source, monotonic_ns=mono,
                request_id=request_id, cause=terminal.get("cause"), unexpected_status=True)

    plan_records = []
    for request_id, plan in plans.items():
        if not plan.get("ok") or not plan.get("waypoints_m") or "started_monotonic_s" not in plan:
            continue
        timing = state.sim_at_monotonic(int(round(float(plan["started_monotonic_s"]) * 1e9)))
        plan_records.append({"request_id": request_id, "waypoints_xy": [p[:2] for p in plan["waypoints_m"]],
                             "sim_time_s": timing["sim_time_s"], "placement": timing["placement"]})

    events.sort(key=lambda e: (e["sim_time_s"] if e["sim_time_s"] is not None else math.inf, e["journal_order"]))
    present = {e["key"] for e in events}
    missing = [key for key in EXPECTED_KEYS if key not in present]
    for event in events:
        event["phase"] = phase_text(event, events)
    return {"request_ids": request_ids, "events": events, "missing": missing, "points": points, "plans": plan_records}


def phase_text(event: dict, events: List[dict]) -> str:
    key = event["key"]
    if key == "cancel_confirmed":
        dwell_before = any(e["key"] == "still_dwell_start" and e["sim_time_s"] is not None
                           and event["sim_time_s"] is not None and e["sim_time_s"] <= event["sim_time_s"] for e in events)
        return "cancel confirmed, confirming stillness" if dwell_before else "cancel confirmed, stopping"
    if key == "still_dwell_start":
        return "stopped, confirming stillness (dwell)"
    if key == "driver_error":
        return "driver error"
    if event.get("unexpected_status"):
        cause = event.get("cause")
        return event["label"] + (": " + str(cause) if cause else "")
    if event.get("accepted") is False:
        return event["label"]
    for expected_key, _, text in EXPECTED_EVENTS:
        if expected_key == key:
            return text
    return event["label"]


def timeline_events(events: List[dict]) -> List[dict]:
    return [e for e in events if e["placement"] == "timeline" and e["sim_time_s"] is not None]


def phase_at(events: List[dict], t: float) -> Tuple[str, List[dict]]:
    """Phase is the text of the latest timeline event at or before t."""
    done = [e for e in timeline_events(events) if e["sim_time_s"] <= t + 1e-9]
    return (done[-1]["phase"] if done else INITIAL_PHASE), done


def run_capture(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)


def probe_video(ffprobe: str, path: Path) -> dict:
    proc = run_capture([ffprobe, "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                        "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,nb_read_packets,duration",
                        "-of", "json", str(path)])
    if proc.returncode != 0:
        raise InputError("ffprobe failed on %s: %s" % (path, proc.stderr.strip()[-500:]))
    streams = json.loads(proc.stdout).get("streams") or []
    if not streams:
        raise InputError("no video stream in " + str(path))
    stream = streams[0]
    stream["frames"] = int(stream.get("nb_read_packets") or stream.get("nb_frames"))
    num, _, den = str(stream["r_frame_rate"]).partition("/")
    stream["fps"] = float(num) / float(den or 1)
    return stream


def encoder_args(name: str, crf: int, preset: str) -> List[str]:
    if name == "libx264":
        return ["-c:v", "libx264", "-preset", preset, "-crf", str(crf)]
    if name == "h264_nvenc":
        # Option set verified on the 5070 Ti by pointcloud_display/observer/session.py, with -cq set to --crf.
        return ["-c:v", "h264_nvenc", "-gpu", "0", "-preset", "p4", "-tune", "hq", "-rc", "vbr", "-cq", str(crf), "-b:v", "0"]
    if name == "h264_videotoolbox":
        return ["-c:v", "h264_videotoolbox", "-q:v", "50"]
    raise ValueError("unsupported encoder: " + name)


def encoder_available(ffmpeg: str, args: List[str]) -> Tuple[bool, str]:
    proc = run_capture([ffmpeg, "-hide_banner", "-v", "error", "-f", "lavfi", "-i",
                        "color=c=black:s=%dx%d:r=12.5:d=0.16" % (FRAME_W, FRAME_H)] + args + ["-pix_fmt", "yuv420p", "-f", "null", "-"])
    return proc.returncode == 0, proc.stderr.strip()[-500:]


def read_exact(stream, size: int) -> Optional[bytes]:
    buf = bytearray(size)
    view = memoryview(buf)
    got = 0
    while got < size:
        n = stream.readinto(view[got:])
        if not n:
            break
        got += n
    if got == 0:
        return None
    if got != size:
        raise InputError("decoder returned a partial frame (%d of %d bytes)" % (got, size))
    return bytes(buf)


def equal_limits(x0: float, x1: float, y0: float, y1: float, width_px: float, height_px: float):
    """Widen one range so that one metre spans the same pixels on both axes."""
    dx, dy = x1 - x0, y1 - y0
    want_dy = dx * height_px / width_px
    if want_dy >= dy:
        cy = (y0 + y1) / 2.0
        return (x0, x1), (cy - want_dy / 2.0, cy + want_dy / 2.0)
    want_dx = dy * width_px / height_px
    cx = (x0 + x1) / 2.0
    return (cx - want_dx / 2.0, cx + want_dx / 2.0), (y0, y1)


def assign_label_rows(times: List[float], labels: List[str], px_per_s: float, rows: int = 3) -> List[int]:
    """Greedy rows so marker labels do not overlap (about 6 px per character)."""
    ends = [-math.inf] * rows
    result = []
    for t, label in zip(times, labels):
        x = t * px_per_s
        width = 6.0 * len(label) + 8.0
        for row in range(rows):
            if x >= ends[row]:
                ends[row] = x + width
                result.append(row)
                break
        else:
            row = min(range(rows), key=lambda r: ends[r])
            ends[row] = x + width
            result.append(row)
    return result


class Renderer:
    """One reusable Agg figure; per frame only the dynamic artists change."""

    def __init__(self, ctx: dict):
        import numpy as np
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.figure import Figure
        from matplotlib.font_manager import FontProperties
        from matplotlib.patches import Circle, Rectangle
        from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar

        self.np = np
        self.ctx = ctx
        self.fig = Figure(figsize=(FRAME_W / 100.0, FRAME_H / 100.0), dpi=100)
        self.canvas = FigureCanvasAgg(self.fig)
        self.fig.patch.set_facecolor("white")
        fig = self.fig

        def box(x0, y0, w, h):
            return [x0 / FRAME_W, y0 / FRAME_H, w / FRAME_W, h / FRAME_H]

        self.camera = fig.figimage(np.zeros((CAM_H, CAM_W, 3), dtype=np.uint8), xo=0, yo=STRIP_H, origin="upper", zorder=0)
        fig.add_artist(Rectangle((0, (FRAME_H - 60) / FRAME_H), CAM_W / FRAME_W, 60 / FRAME_H, transform=fig.transFigure,
                                 facecolor="black", alpha=0.62, edgecolor="none", zorder=5))
        self.banner_run = fig.text(8 / FRAME_W, (FRAME_H - 16) / FRAME_H, "", color="white", fontsize=10.5,
                                   fontweight="bold", va="center", zorder=6)
        self.banner_phase = fig.text(8 / FRAME_W, (FRAME_H - 35) / FRAME_H, "", color="#ffd84d", fontsize=11.5,
                                     fontweight="bold", va="center", zorder=6)
        self.banner_recent = fig.text(8 / FRAME_W, (FRAME_H - 52) / FRAME_H, "", color="#dddddd", fontsize=8.5,
                                      va="center", zorder=6)
        fig.text((CAM_W - 6) / FRAME_W, (STRIP_H + 6) / FRAME_H, "runner third-person camera (observes only)",
                 color="white", fontsize=7.5, ha="right", va="bottom", zorder=6,
                 bbox={"facecolor": "black", "alpha": 0.5, "edgecolor": "none", "pad": 2})

        # Top-down map, equal scale; limits are widened to the box ratio so none are overridden.
        map_w, map_h = FRAME_W - CAM_W - 62, CAM_H - 62
        self.map = fig.add_axes(box(CAM_W + 50, STRIP_H + 34, map_w, map_h))
        ax = self.map
        ax.set_title("top-down world XY (m), equal scale", fontsize=9, pad=4)
        ax.tick_params(labelsize=7, length=2, pad=1)
        ax.set_xlabel("x (m)", fontsize=7.5, labelpad=1)
        ax.set_ylabel("y (m)", fontsize=7.5, labelpad=1)
        ax.grid(True, linewidth=0.4, alpha=0.4)
        xs, ys = ctx["trail_x"], ctx["trail_y"]
        tol = ctx["goal_tolerance_m"]
        extent_x = list(xs) + [g["ground_xyz_m"][0] for g in ctx["goals"].values()]
        extent_y = list(ys) + [g["ground_xyz_m"][1] for g in ctx["goals"].values()]
        for plan in ctx["plans"]:
            extent_x += [p[0] for p in plan["waypoints_xy"]]
            extent_y += [p[1] for p in plan["waypoints_xy"]]
        pad = tol + 0.35
        map_x, map_y = equal_limits(min(extent_x) - pad, max(extent_x) + pad, min(extent_y) - pad, max(extent_y) + pad,
                                    map_w, map_h)
        ax.set_xlim(*map_x)
        ax.set_ylim(*map_y)
        ax.set_aspect("equal", adjustable="box")
        points = ctx["points"]
        zoom_names = [name for name in ("cancel", "stop") if name in points]
        self.inset = None
        axes_list = [ax]
        if zoom_names:
            inset_w, inset_h = 0.86 * map_w, 0.34 * map_h
            self.inset = ax.inset_axes([0.03, 0.05, 0.86, 0.34])
            zx = [points[n]["xyz"][0] for n in zoom_names]
            zy = [points[n]["xyz"][1] for n in zoom_names]
            cx, cy = (min(zx) + max(zx)) / 2.0, (min(zy) + max(zy)) / 2.0
            half = max(0.35, (max(zx) - min(zx)) / 2.0 + 0.15)
            zoom_x, zoom_y = equal_limits(cx - half, cx + half, cy - 0.05, cy + 0.05, inset_w, inset_h)
            self.inset.set_xlim(*zoom_x)
            self.inset.set_ylim(*zoom_y)
            self.inset.set_aspect("equal", adjustable="box")
            # Right-side y labels stay inside the map instead of overprinting its own y labels.
            self.inset.tick_params(labelsize=6, length=2, pad=1, labelleft=False, labelright=True)
            self.inset.grid(True, linewidth=0.4, alpha=0.5)
            self.inset.set_facecolor("#fbfbf4")
            self.inset.text(0.01, 0.97, "zoom: cancel and stop points", transform=self.inset.transAxes, fontsize=6.5,
                            va="top", color="0.25")
            ax.add_patch(Rectangle((zoom_x[0], zoom_y[0]), zoom_x[1] - zoom_x[0], zoom_y[1] - zoom_y[0], fill=False,
                                   edgecolor="0.45", linewidth=0.8, zorder=6))
            axes_list.append(self.inset)
        self.plan_lines = []
        for plan in ctx["plans"]:
            for axis in axes_list:
                line, = axis.plot([p[0] for p in plan["waypoints_xy"]], [p[1] for p in plan["waypoints_xy"]],
                                  linestyle=":", color="0.35", linewidth=1.0, zorder=2)
                self.plan_lines.append((plan, line))
        colors = {"goal-a": "#1b9e77", "goal-b": "#7570b3"}
        for goal_id, goal in sorted(ctx["goals"].items()):
            gx, gy = goal["ground_xyz_m"][:2]
            color = colors.get(goal_id, "black")
            ax.add_patch(Circle((gx, gy), tol, fill=False, color=color, linewidth=1.2, zorder=3))
            ax.plot([gx], [gy], marker="+", color=color, markersize=7, zorder=3)
            ax.annotate("goal " + goal_id.replace("goal-", "").upper(), (gx, gy + tol), xytext=(0, 3),
                        textcoords="offset points", ha="center", va="bottom", fontsize=8, color=color, fontweight="bold")
        if "start" in points:
            sx, sy = points["start"]["xyz"][:2]
            ax.plot([sx], [sy], marker="s", color="0.4", markersize=5, zorder=4)
            ax.annotate("start", (sx, sy), xytext=(-5, 0), textcoords="offset points", ha="right", va="center",
                        fontsize=7, color="0.3")
        self.trails, self.robots = [], []
        for axis in axes_list:
            trail, = axis.plot([], [], color="#1f77b4", linewidth=1.6, zorder=5)
            robot, = axis.plot([], [], marker="o", color="#1f77b4", markersize=5, zorder=7)
            self.trails.append(trail)
            self.robots.append(robot)
        self.heading = ax.quiver([0.0], [0.0], [0.0], [0.0], angles="xy", scale_units="xy", scale=1.0, color="#d62728",
                                 width=0.012, zorder=8)
        self.timed_points = []
        # Main map: cancel label above, stop label below. Inset: both below, extending away from each other.
        for name, marker, color, main_offset, inset_offset, inset_ha in (
                ("cancel", "X", "#ff7f0e", (0, 8), (4, -16), "right"),
                ("stop", "o", "#d62728", (0, -15), (-4, -16), "left")):
            if name not in points:
                continue
            px, py = points[name]["xyz"][:2]
            when = ctx["event_time"].get("cancel_sent" if name == "cancel" else "still_confirmed")
            placements = [(ax, name, main_offset, "center")]
            if self.inset is not None:
                placements.append((self.inset, "%s x=%.3f y=%.3f" % (name, px, py), inset_offset, inset_ha))
            for axis, label, offset, ha in placements:
                artist, = axis.plot([px], [py], marker=marker, linestyle="none", markersize=7, zorder=9,
                                    markerfacecolor=color if name == "cancel" else "none", markeredgecolor=color,
                                    markeredgewidth=1.4)
                text = axis.annotate(label, (px, py), xytext=offset, textcoords="offset points", ha=ha,
                                     fontsize=7, color=color, fontweight="bold", zorder=10,
                                     bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none", "pad": 1})
                self.timed_points.append((when, artist, text))
        missing_points = [name for name in ("start", "cancel", "stop") if name not in points]
        if missing_points:
            ax.text(0.02, 0.02, "not recorded: " + ", ".join(p + " point" for p in missing_points), transform=ax.transAxes,
                    fontsize=7, color="#b00000", va="bottom")
        span = ax.get_xlim()[1] - ax.get_xlim()[0]
        bar = 1.0 if span >= 2.5 else 0.5
        ax.add_artist(AnchoredSizeBar(ax.transData, bar, "%g m" % bar, "upper right", pad=0.5, sep=2, frameon=False,
                                      size_vertical=0.03, fontproperties=FontProperties(size=7)))
        goal_proxy, = ax.plot([], [], marker="o", markerfacecolor="none", markeredgecolor="0.3", linestyle="none")
        handles = [self.trails[0], goal_proxy]
        names = ["trail (metrics base_xyz)", "goal circle r = %.2f m" % tol]
        if self.plan_lines:
            handles.append(self.plan_lines[0][1])
            names.append("PCT route (after plan)")
        ax.legend(handles, names, loc="upper left", fontsize=6.5, frameon=True, framealpha=0.8, handlelength=1.6,
                  borderpad=0.3)

        # Bottom time strip.
        t0, t1 = ctx["t_range"]
        left, width = 62, FRAME_W - 62 - 16
        self.speed_ax = fig.add_axes(box(left, 98, width, 78))
        self.force_ax = fig.add_axes(box(left, 36, width, 50), sharex=self.speed_ax)
        sim, speed, cmd, force = ctx["series"]
        self.speed_ax.plot(sim, speed, color="#1f77b4", linewidth=1.0, label="measured speed |v_xy|")
        self.speed_ax.plot(sim, cmd, color="#ff7f0e", linewidth=1.0, label="admitted cmd |v_xy|")
        self.force_ax.plot(sim, force, color="#8c564b", linewidth=1.0)
        self.speed_ax.set_ylabel("m/s", fontsize=7.5, labelpad=2)
        self.force_ax.set_ylabel("non-foot\nforce N", fontsize=7, labelpad=2)
        self.force_ax.set_xlabel("simulation time (s)", fontsize=7.5, labelpad=1)
        # Headroom keeps the upper-left legend clear of the curves.
        self.speed_ax.set_ylim(0.0, max(0.2, max(max(speed), max(cmd)) * 1.4))
        self.force_ax.set_ylim(0.0, max(1.0, max(force) * 1.15))
        self.speed_ax.set_xlim(t0, t1)
        for axis in (self.speed_ax, self.force_ax):
            axis.tick_params(labelsize=7, length=2, pad=1)
            axis.grid(True, linewidth=0.4, alpha=0.4)
        self.speed_ax.tick_params(labelbottom=False)
        self.force_ax.text(0.995, 0.92, "max %.1f N" % max(force), transform=self.force_ax.transAxes, ha="right", va="top",
                           fontsize=6.5, color="0.3")
        self.speed_ax.legend(loc="upper left", fontsize=6.5, ncol=2, frameon=True, framealpha=0.85, borderpad=0.3,
                             handlelength=1.4, columnspacing=1.0)
        transform = self.speed_ax.get_xaxis_transform()
        timeline = timeline_events(ctx["events"])
        dwell = [e for e in timeline if e["key"] == "still_dwell_start"]
        still = [e for e in timeline if e["key"] == "still_confirmed"]
        if dwell and still:
            for axis in (self.speed_ax, self.force_ax):
                axis.axvspan(dwell[0]["sim_time_s"], still[0]["sim_time_s"], color="#2ca02c", alpha=0.15, linewidth=0)
            self.speed_ax.text(dwell[0]["sim_time_s"], 0.05, " still dwell", transform=transform, fontsize=6.5,
                               color="#2ca02c", va="bottom")
        marked = [e for e in timeline if e["key"] != "still_dwell_start"]
        px_per_s = width / max(1e-6, t1 - t0)
        label_rows = assign_label_rows([e["sim_time_s"] - t0 for e in marked], [e["label"] for e in marked], px_per_s)
        for event, row in zip(marked, label_rows):
            bad = event["key"] in {"driver_error"} or event.get("unexpected_status") or event.get("accepted") is False
            color = "#b00000" if bad else "0.25"
            for axis in (self.speed_ax, self.force_ax):
                axis.axvline(event["sim_time_s"], color=color, linewidth=0.8, linestyle="--", alpha=0.8)
            self.speed_ax.text(event["sim_time_s"], 1.04 + 0.2 * row, " " + event["label"], transform=transform,
                               fontsize=7.5, color=color, va="bottom", ha="left", clip_on=False)
        notes = []
        if ctx["missing"]:
            notes.append("event not recorded: " + ", ".join(ctx["labels"][k] for k in ctx["missing"]))
        outside = [e for e in ctx["events"] if e["placement"] != "timeline"]
        if outside:
            notes.append("outside recorded state: " + ", ".join(
                "%s (+%.1f s)" % (e["label"], e.get("state_row_lag_s") or 0.0) for e in outside))
        if notes:
            fig.text((FRAME_W - 16) / FRAME_W, 3 / FRAME_H, " | ".join(notes), ha="right", va="bottom", fontsize=7,
                     color="#b00000")
        self.cursors = [axis.axvline(t0, color="black", linewidth=1.3) for axis in (self.speed_ax, self.force_ax)]
        self.future = []
        for axis in (self.speed_ax, self.force_ax):
            rect = Rectangle((t0, 0.0), t1 - t0, 1.0, transform=axis.get_xaxis_transform(), facecolor="white",
                             alpha=0.55, edgecolor="none", zorder=4)
            axis.add_patch(rect)
            self.future.append(rect)

    def render(self, frame_rgb: bytes, frame_no: int, total: int, cam_row: dict, state_idx: int):
        np, ctx = self.np, self.ctx
        t = float(cam_row["sim_time_s"])
        self.camera.set_data(np.frombuffer(frame_rgb, dtype=np.uint8).reshape(CAM_H, CAM_W, 3))
        xs, ys = ctx["trail_x"], ctx["trail_y"]
        x, y, yaw = xs[state_idx], ys[state_idx], ctx["trail_yaw"][state_idx]
        for trail, robot in zip(self.trails, self.robots):
            trail.set_data(xs[: state_idx + 1], ys[: state_idx + 1])
            robot.set_data([x], [y])
        self.heading.set_offsets([[x, y]])
        self.heading.set_UVC([0.3 * math.cos(yaw)], [0.3 * math.sin(yaw)])
        for when, artist, text in self.timed_points:
            visible = when is not None and t >= when - 1e-9
            artist.set_visible(visible)
            text.set_visible(visible)
        for plan, line in self.plan_lines:
            line.set_visible(plan["sim_time_s"] is not None and t >= plan["sim_time_s"] - 1e-9)
        for cursor in self.cursors:
            cursor.set_xdata([t, t])
        t1 = ctx["t_range"][1]
        for rect in self.future:
            rect.set_x(t)
            rect.set_width(max(0.0, t1 - t))
        phase, done = phase_at(ctx["events"], t)
        self.banner_run.set_text("%s    sim t = %.2f s    frame %d/%d" % (ctx["run_id"], t, frame_no + 1, total))
        self.banner_phase.set_text("phase: " + phase)
        recent = [e for e in done if e["key"] != "still_dwell_start"][-3:]
        self.banner_recent.set_text("recent events: " + (
            "  |  ".join("%s @ %.2f s" % (e["label"], e["sim_time_s"]) for e in recent) if recent else "none yet"))
        self.canvas.draw()
        return self.canvas.buffer_rgba()


def build_context(run: Path, paths: dict) -> dict:
    journal = load_json(paths["pilot_journal"])
    camera_rows = load_camera_rows(paths["camera_frames"])
    state_rows = load_state_rows(paths["metrics"])
    state = StateIndex(state_rows)
    run_id, run_id_source = resolve_run_id(run, paths, journal)
    parsed = extract_journal(journal, run_id, state)
    pilot = load_json(paths["pilot"]) if paths.get("pilot") else None
    goals = resolve_goals(journal, pilot)
    tolerance = float(pilot["goal_xy_tolerance_m"]) if pilot and "goal_xy_tolerance_m" in pilot else DEFAULT_GOAL_TOLERANCE_M
    event_time = {}
    for event in timeline_events(parsed["events"]):
        event_time.setdefault(event["key"], event["sim_time_s"])
    labels = {key: label for key, label, _ in EXPECTED_EVENTS}
    commands_differ = max(abs(a - b) for r in state_rows for a, b in zip(r["admitted_command"], r["raw_command"]))
    return {
        "run_id": run_id,
        "run_id_source": run_id_source,
        "journal_passed": journal.get("passed"),
        "camera_rows": camera_rows,
        "state": state,
        "trail_x": [float(r["base_xyz"][0]) for r in state_rows],
        "trail_y": [float(r["base_xyz"][1]) for r in state_rows],
        "trail_yaw": [float(r["base_rpy_rad"][2]) for r in state_rows],
        "series": (state.sim, [float(r["horizontal_speed_mps"]) for r in state_rows],
                   [float(r["command_horizontal_norm_mps"]) for r in state_rows],
                   [float(r["nonfoot_force_max_n"]) for r in state_rows]),
        "admitted_vs_raw_max_abs_diff": commands_differ,
        "t_range": (min(0.0, state.sim[0], float(camera_rows[0]["sim_time_s"])),
                    max(state.sim[-1], float(camera_rows[-1]["sim_time_s"]))),
        "goals": goals,
        "goal_tolerance_m": tolerance,
        "goal_tolerance_source": "inputs/pilot.json goal_xy_tolerance_m" if pilot and "goal_xy_tolerance_m" in pilot else "default 0.25 m (pilot.json absent)",
        "event_time": event_time,
        "labels": labels,
        **parsed,
    }


def render_video(ctx: dict, video: Path, n_render: int, output: Path, ffmpeg: str, fps_text: str,
                 enc_args: List[str], log_prefix: Path) -> dict:
    renderer = Renderer(ctx)
    decoder_log = Path(str(log_prefix) + ".decode.log").open("w", encoding="utf-8")
    encoder_log = Path(str(log_prefix) + ".encode.log").open("w", encoding="utf-8")
    decoder = subprocess.Popen(
        [ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-i", str(video), "-map", "0:v:0",
         "-vf", "scale=%d:%d:flags=lanczos" % (CAM_W, CAM_H), "-fps_mode", "passthrough",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE, stderr=decoder_log)
    encode_cmd = [ffmpeg, "-hide_banner", "-nostdin", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba",
                  "-s", "%dx%d" % (FRAME_W, FRAME_H), "-framerate", fps_text, "-i", "-"] + enc_args + [
                  "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", "-f", "mp4", str(output)]
    encoder = subprocess.Popen(encode_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=encoder_log)
    frame_bytes = CAM_W * CAM_H * 3
    decoded = rendered = 0
    row_rules = set()
    error = None
    try:
        while True:
            frame = read_exact(decoder.stdout, frame_bytes)
            if frame is None:
                break
            decoded += 1
            if rendered >= n_render:
                continue
            cam_row = ctx["camera_rows"][rendered]
            state_idx, rule = ctx["state"].row_for_frame(cam_row)
            row_rules.add(rule)
            encoder.stdin.write(renderer.render(frame, rendered, n_render, cam_row, state_idx))
            rendered += 1
    except BrokenPipeError as exc:
        error = "encoder closed its input: %s" % exc
    finally:
        try:
            encoder.stdin.close()
        except BrokenPipeError:
            pass
        encoder_rc = encoder.wait()
        if decoder.poll() is None:
            decoder.kill()
        decoder_rc = decoder.wait()
        decoder_log.close()
        encoder_log.close()
    return {"decoded_frames": decoded, "rendered_frames": rendered, "encoder_returncode": encoder_rc,
            "decoder_returncode": decoder_rc, "state_row_rules": sorted(row_rules), "error": error,
            "encode_command": encode_cmd}


def ffmpeg_version(ffmpeg: str) -> str:
    proc = run_capture([ffmpeg, "-hide_banner", "-version"])
    return proc.stdout.splitlines()[0] if proc.returncode == 0 and proc.stdout else "unknown"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run", type=Path, help="run directory (local package or remote run root)")
    parser.add_argument("--output", type=Path, required=True, help="output .mp4; the sidecar is written beside it as .json")
    parser.add_argument("--artifacts-dir", type=Path, default=None,
                        help="default RUN/returned_artifacts; use RUN/artifacts on the execution host")
    parser.add_argument("--video", type=Path, default=None, help="override the third-person source video path")
    parser.add_argument("--encoder", choices=ENCODERS, default="libx264")
    parser.add_argument("--fallback-encoder", choices=ENCODERS, default=None,
                        help="used when --encoder is unavailable or its encode fails")
    parser.add_argument("--crf", type=int, default=30, help="libx264 CRF, or the NVENC -cq value")
    parser.add_argument("--preset", default="slow", help="libx264 preset")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    started = time.monotonic()
    try:
        import numpy  # noqa: F401
        import matplotlib
        matplotlib.use("Agg")
    except ImportError as exc:
        raise SystemExit("make_walk_review.py needs numpy and matplotlib in %s: %s" % (sys.executable, exc))
    ffmpeg = shutil.which(args.ffmpeg or "ffmpeg")
    ffprobe = shutil.which(args.ffprobe or "ffprobe")
    if not ffmpeg or not ffprobe:
        raise SystemExit("ffmpeg/ffprobe not found (ffmpeg=%r ffprobe=%r)" % (args.ffmpeg, args.ffprobe))
    run = args.run.resolve()
    artifacts = (args.artifacts_dir or run / "returned_artifacts").resolve()
    output = args.output.resolve()
    if output.suffix != ".mp4":
        raise SystemExit("--output must end with .mp4")
    if output.exists():
        raise SystemExit("refusing to overwrite " + str(output))
    try:
        paths = locate_inputs(run, artifacts, args.video)
        probe = probe_video(ffprobe, paths["video"])
        ctx = build_context(run, paths)
        n_render, rule = align_frames(probe["frames"], len(ctx["camera_rows"]))
    except InputError as exc:
        raise SystemExit("walk review refused: %s" % exc)
    run_clock = load_json(paths["run_clock"])
    summary = load_json(paths["summary"]) if paths.get("summary") else {}
    capture_fps = (summary.get("camera") or {}).get("capture_fps")
    if capture_fps is not None and abs(float(capture_fps) - probe["fps"]) > 1e-6:
        raise SystemExit("walk review refused: video %.4f fps differs from summary camera.capture_fps %s" % (probe["fps"], capture_fps))
    frame_times = [float(r["sim_time_s"]) for r in ctx["camera_rows"][:n_render]]
    frame_dt = sorted(b - a for a, b in zip(frame_times, frame_times[1:]))
    frame_dt_median = frame_dt[len(frame_dt) // 2] if frame_dt else None

    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.stem + ".partial.mp4")
    if partial.exists():
        partial.unlink()
    attempts = []
    candidates = [args.encoder] + ([args.fallback_encoder] if args.fallback_encoder and args.fallback_encoder != args.encoder else [])
    result = None
    used = None
    for name in candidates:
        enc_args = encoder_args(name, args.crf, args.preset)
        ok, detail = encoder_available(ffmpeg, enc_args)
        attempt = {"encoder": name, "args": enc_args, "probe_ok": ok}
        attempts.append(attempt)
        if not ok:
            attempt["probe_error"] = detail
            continue
        try:
            result = render_video(ctx, paths["video"], n_render, partial, ffmpeg, probe["r_frame_rate"], enc_args,
                                  output.with_name(output.stem + "." + name))
        except BaseException:
            if partial.exists():
                partial.unlink()
            raise
        attempt.update({k: v for k, v in result.items() if k != "encode_command"})
        failed = (result["error"] or result["encoder_returncode"] != 0 or result["decoder_returncode"] != 0
                  or result["rendered_frames"] != n_render)
        if not failed:
            used = name
            break
        if partial.exists():
            partial.unlink()
    if used is None:
        raise SystemExit("walk review failed; encoder attempts: " + json.dumps(attempts, indent=2)[:4000])
    if result["decoded_frames"] != probe["frames"]:
        partial.unlink()
        raise SystemExit("walk review failed: decoded %d frames but ffprobe counted %d" % (result["decoded_frames"], probe["frames"]))
    out_probe = probe_video(ffprobe, partial)
    if out_probe["frames"] != n_render:
        partial.unlink()
        raise SystemExit("walk review failed: output has %d frames, expected %d" % (out_probe["frames"], n_render))
    partial.replace(output)
    out_bytes = output.stat().st_size
    duration = float(out_probe.get("duration") or n_render / probe["fps"])
    per_17 = out_bytes * SIZE_TARGET_EPISODE_S / max(duration, 1e-6)

    inputs = {name: file_record(path) for name, path in paths.items() if path is not None}
    sidecar = {
        "schema_version": 1,
        "tool": {"path": str(Path(__file__).resolve()), "sha256": sha256_file(Path(__file__).resolve())},
        "claim": "Visual review aid built from recorded run files; not an acceptance check.",
        "run_id": ctx["run_id"],
        "run_id_source": ctx["run_id_source"],
        "run_dir": str(run),
        "artifacts_dir": str(artifacts),
        "journal_passed": ctx["journal_passed"],
        "inputs": inputs,
        "source_video": {k: probe.get(k) for k in ("codec_name", "width", "height", "r_frame_rate", "nb_frames", "nb_read_packets", "duration", "frames")},
        "frame_alignment": {
            "video_frames": probe["frames"],
            "camera_rows": len(ctx["camera_rows"]),
            "rendered_frames": n_render,
            "decoded_frames": result["decoded_frames"],
            "rule": rule,
            "state_row_rules": result["state_row_rules"],
        },
        "time": {
            "rendered_sim_time_range_s": [frame_times[0], frame_times[-1]],
            "timeline_range_s": list(ctx["t_range"]),
            "frame_sim_dt_median_s": frame_dt_median,
            "video_fps": probe["fps"],
            "playback_speed_vs_sim": (1.0 / probe["fps"]) / frame_dt_median if frame_dt_median else None,
            "run_clock": run_clock,
            "event_mapping": ("wall/backend monotonic time -> sim_time_s of the last metrics row with "
                              "state_sample_monotonic_ns <= event (review_two_goal.py rule); events more than "
                              "%.2f s after that row are listed as outside recorded state" % MAX_EVENT_STATE_LAG_S),
        },
        "series": {
            "speed": "metrics.jsonl horizontal_speed_mps",
            "command": "metrics.jsonl command_horizontal_norm_mps (admitted command)",
            "admitted_vs_raw_command_max_abs_diff": ctx["admitted_vs_raw_max_abs_diff"],
            "force": "metrics.jsonl nonfoot_force_max_n",
            "trail": "metrics.jsonl base_xyz; heading metrics.jsonl base_rpy_rad[2]",
        },
        "goals": ctx["goals"],
        "goal_tolerance_m": ctx["goal_tolerance_m"],
        "goal_tolerance_source": ctx["goal_tolerance_source"],
        "points": ctx["points"],
        "plans": [{k: v for k, v in p.items() if k != "waypoints_xy"} for p in ctx["plans"]],
        "events": [dict(e, first_frame_index=next((i for i, ft in enumerate(frame_times)
                                                   if e["sim_time_s"] is not None and ft >= e["sim_time_s"] - 1e-9), None))
                   for e in ctx["events"]],
        "missing_events": ctx["missing"],
        "encoder": {
            "requested": args.encoder,
            "fallback": args.fallback_encoder,
            "used": used,
            "attempts": attempts,
            "command": result["encode_command"],
            "ffmpeg": ffmpeg,
            "ffmpeg_version": ffmpeg_version(ffmpeg),
        },
        "output": {
            "path": str(output),
            "sha256": sha256_file(output),
            "bytes": out_bytes,
            "width": out_probe.get("width"),
            "height": out_probe.get("height"),
            "frames": out_probe["frames"],
            "duration_s": duration,
            "codec": out_probe.get("codec_name"),
        },
        "size_target": {
            "target_bytes_per_17_s": SIZE_TARGET_BYTES,
            "bytes_per_17_s": per_17,
            "within_target": per_17 <= SIZE_TARGET_BYTES,
        },
        "render_wall_seconds": time.monotonic() - started,
    }
    sidecar_path = output.with_suffix(".json")
    sidecar_path.write_text(json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not sidecar["size_target"]["within_target"]:
        print("warning: %.0f bytes per 17 s exceeds the %d byte target" % (per_17, SIZE_TARGET_BYTES), file=sys.stderr)
    print(json.dumps({"output": str(output), "sidecar": str(sidecar_path), "bytes": out_bytes, "frames": out_probe["frames"],
                      "duration_s": duration, "encoder": used, "frame_rule": rule, "missing_events": ctx["missing"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
