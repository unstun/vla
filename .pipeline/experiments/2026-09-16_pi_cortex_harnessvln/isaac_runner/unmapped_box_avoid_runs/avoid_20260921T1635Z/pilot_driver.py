#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path
import time
import urllib.request


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def post_json(base, endpoint, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base + endpoint, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(base, endpoint):
    with urllib.request.urlopen(base + endpoint, timeout=10.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def snapshot_ok(snapshot, run_id, max_age_s=2.0):
    if snapshot.get("run_id") != run_id:
        return False
    measured = snapshot.get("measured") or {}
    xyz = measured.get("base_xyz")
    if not isinstance(xyz, list) or len(xyz) != 3:
        return False
    if snapshot.get("wall_monotonic_ns") is None:
        return False
    age = (time.monotonic_ns() - int(snapshot["wall_monotonic_ns"])) / 1e9
    return 0.0 <= age <= max_age_s


def wait_snapshot(path, run_id, timeout_s=120.0):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        try:
            snap = read_json(path)
        except Exception:
            time.sleep(0.05)
            continue
        last = snap
        if snapshot_ok(snap, run_id):
            return snap
        time.sleep(0.05)
    raise RuntimeError("fresh runner snapshot unavailable; last=%r" % (last,))


def wait_http_ready(base, snapshot_path, run_id, observed_epoch, timeout_s=180.0):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        try:
            snap = wait_snapshot(snapshot_path, run_id, timeout_s=2.0)
            state = get_json(base, "/state")
        except Exception as exc:
            last = str(exc)
            time.sleep(0.1)
            continue
        readiness = state.get("readiness") or {}
        applied = readiness.get("applied_snapshot") or {}
        if (
            state.get("run_id") == run_id
            and int(state.get("run_epoch_ns", 0)) == int(observed_epoch)
            and readiness.get("body_pose_ready") is True
            and applied.get("ready") is True
            and snapshot_ok(snap, run_id)
        ):
            return state
        last = state
        time.sleep(0.1)
    raise RuntimeError("HTTP backend not ready; last=%r" % (last,))


def state_terminal_for(state, request_id, status):
    for item in state.get("terminal_results", []):
        if item.get("request_id") == request_id and item.get("status") == status:
            return item
    item = (state.get("jobs") or {}).get(request_id)
    if isinstance(item, dict) and item.get("status") == status:
        return item
    return None


def wait_terminal(base, request_id, status, journal, timeout_s=900.0):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        state = get_json(base, "/state")
        last = state
        journal.append({"event": "state_poll", "request_id": request_id, "want": status, "state": state, "wall_monotonic_ns": time.monotonic_ns()})
        terminal = state_terminal_for(state, request_id, status)
        if terminal is not None:
            return terminal
        time.sleep(0.2)
    raise RuntimeError("timed out waiting for %s status %s; last=%r" % (request_id, status, last))


def finish_request(path, run_id, request_id, observed_epoch, status, note):
    path = Path(path)
    payload = {
        "schema_version": 1,
        "run_id": run_id,
        "request_id": request_id,
        "observed_run_epoch_ns": int(observed_epoch),
        "requested_at_monotonic_ns": time.monotonic_ns(),
        "backend_terminal_status": status,
        "note": note,
    }
    tmp = path.with_name(path.name + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--http-port", type=int, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--cancel-displacement-m", type=float, default=0.4)
    args = parser.parse_args()
    run_root = Path(args.run_root)
    pilot = read_json(run_root / "inputs/pilot.json")
    snapshot_path = run_root / "artifacts/external_episode/current_command.json"
    finish_path = run_root / "artifacts/external_episode/finish_request.json"
    journal = []
    base = "http://127.0.0.1:%d" % args.http_port
    observed_epoch = 0
    try:
        initial = wait_snapshot(snapshot_path, args.run_id)
        observed_epoch = int(initial["run_epoch_ns"])
        ready = wait_http_ready(base, snapshot_path, args.run_id, observed_epoch)
        journal.append({"event": "backend_ready", "state": ready, "wall_monotonic_ns": time.monotonic_ns()})
        goal = pilot["goals"][1]
        request_id = args.run_id + "-goal-b"
        payload = {
            "request_id": request_id,
            "goal_id": "goal-b",
            "target_ground_xyz": goal["ground_xyz_m"],
            "frame": pilot["frame_id"],
            "map_epoch": "flat_nominal",
            "map_revision": 1,
        }
        resp = post_json(base, "/goal", payload)
        journal.append({"event": "post_goal", "payload": payload, "response": resp, "wall_monotonic_ns": time.monotonic_ns()})
        write_json(run_root / "artifacts/pilot_journal_live.json", {"events": journal})
        if resp.get("ok") is not True:
            raise RuntimeError("goal-b rejected: %r" % (resp,))
        wait_terminal(base, request_id, "arrived", journal, timeout_s=900.0)
        finish_request(finish_path, args.run_id, args.run_id + "-finish", observed_epoch, "FINISHED", "goal-b arrived")
        write_json(run_root / "artifacts/pilot_journal.json", {"passed": True, "events": journal})
        return 0
    except Exception as exc:
        journal.append({"event": "driver_error", "error": str(exc), "wall_monotonic_ns": time.monotonic_ns()})
        finish_request(finish_path, args.run_id, args.run_id + "-failed-finish", observed_epoch, "FAILED", str(exc))
        write_json(run_root / "artifacts/pilot_journal.json", {"passed": False, "error": str(exc), "events": journal})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
