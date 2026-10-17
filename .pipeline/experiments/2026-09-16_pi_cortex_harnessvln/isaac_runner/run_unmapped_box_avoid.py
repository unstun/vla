#!/usr/bin/env python3
"""One PCT global / SCAN local walk around the unmapped Building box.

Reuses the two-goal package (PCT worker, /p2b/route, scan_planner_node,
closed_loop_controller, V12). Sends only pilot.json goal-b. Does not edit
that pilot, the two-goal driver, or the pinned planner.yaml.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shlex
import sys
from typing import List, Sequence, Tuple


HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parent
PLANNER_YAML = EXPERIMENT / "p2b_execution/baseline_config/planner.yaml"
PINNED_PLANNER_SHA256 = "42a265a35cefb69eae43896acdd13780d1a7bd36a874b2f3aae967376b6e435e"
DEFAULT_REMOTE_ROOT = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/unmapped_box_avoid"
DEFAULT_REMOTE_SCAN = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_04"
DEFAULT_SCAN_BUILD = EXPERIMENT / "p2b_execution/builds/scan_04"
RESULT_PATH = EXPERIMENT / "livox_mid360_stand_probe/RESULT_unmapped_box_avoid.md"


def load_sibling(name: str):
    spec = importlib.util.spec_from_file_location(name, str(HERE / (name + ".py")))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pinned_planner_sha256() -> str:
    return hashlib.sha256(PLANNER_YAML.read_bytes()).hexdigest()


def livox_box_flags(remote_run: str) -> List[str]:
    qualify = load_sibling("qualify_stand_runner")
    remote = remote_run.rstrip("/")
    return [
        "--unmapped-box", "lidar",
        "--lidar-pattern-mode", "livox_mid360",
        "--lidar-pattern-csv", remote + "/" + qualify.MID360_CSV_PACKAGE_REL,
        "--robot-asset", remote + "/" + qualify.ISAAC_URDF_PACKAGE_REL,
        "--canonical-robot-asset", remote + "/" + qualify.CANONICAL_URDF_PACKAGE_REL,
        "--lidar-max-range", str(qualify.LIVOX_LIDAR_MAX_RANGE_M),
    ]


def build_avoid_runner_argv(args, remote_run: str, run_id: str, pilot: dict) -> List[str]:
    two = load_sibling("run_two_goal_pilot")
    return two.build_runner_argv(args, remote_run, run_id, pilot) + livox_box_flags(remote_run)


def route_xy_crosses_box(waypoints: Sequence[Sequence[float]], box_aabb: dict) -> bool:
    lo = box_aabb["min_xyz_m"]
    hi = box_aabb["max_xyz_m"]
    points = [(float(p[0]), float(p[1])) for p in waypoints]
    if any(_point_in_xy(point, lo, hi) for point in points):
        return True
    return any(_segment_crosses_xy(a, b, lo, hi) for a, b in zip(points, points[1:]))


def torso_intersects_box(base_xyz, yaw_rad: float, body_height_m: float, box_aabb: dict) -> bool:
    box = load_sibling("unmapped_box")
    ground = (
        float(base_xyz[0]),
        float(base_xyz[1]),
        float(base_xyz[2]) - float(body_height_m),
    )
    robot = box.robot_aabb_world(ground, float(yaw_rad), float(body_height_m))
    return box.aabbs_intersect(robot, {
        "min_xyz_m": tuple(float(v) for v in box_aabb["min_xyz_m"]),
        "max_xyz_m": tuple(float(v) for v in box_aabb["max_xyz_m"]),
    })


def episode_verdict(waypoints, samples, goal_xyz, box_aabb, body_height_m, xy_tolerance_m) -> dict:
    crosses = route_xy_crosses_box(waypoints, box_aabb)
    overlap = any(
        torso_intersects_box(xyz, yaw, body_height_m, box_aabb) for xyz, yaw in samples
    )
    final = samples[-1][0]
    xy_error = math.hypot(float(final[0]) - float(goal_xyz[0]), float(final[1]) - float(goal_xyz[1]))
    arrived = xy_error <= float(xy_tolerance_m)
    if overlap or not crosses:
        status = "fail"
    elif not arrived:
        status = "incomplete"
    else:
        status = "pass"
    return {
        "status": status,
        "route_crosses_box": crosses,
        "torso_overlap": overlap,
        "arrived": arrived,
        "final_xy_error_m": xy_error,
    }


def _point_in_xy(point, lo, hi) -> bool:
    return lo[0] <= point[0] <= hi[0] and lo[1] <= point[1] <= hi[1]


def _segment_crosses_xy(start, end, lo, hi) -> bool:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    pairs = ((-dx, start[0] - lo[0]), (dx, hi[0] - start[0]), (-dy, start[1] - lo[1]), (dy, hi[1] - start[1]))
    enter, leave = 0.0, 1.0
    for direction, span in pairs:
        if abs(direction) <= 1e-12:
            if span < 0.0:
                return False
            continue
        hit = span / direction
        if direction < 0.0:
            if hit > leave:
                return False
            enter = max(enter, hit)
        else:
            if hit < enter:
                return False
            leave = min(leave, hit)
    return enter <= leave


def replace_runner_argv(commands: dict, argv: List[str]) -> dict:
    updated = dict(commands)
    run = list(commands["run"])
    parts = shlex.split(run[-1])
    index = parts.index("--runner-argv-json")
    parts[index + 1] = json.dumps(argv, separators=(",", ":"))
    run[-1] = shlex.join(parts)
    updated["run"] = run
    return updated


def driver_source() -> str:
    return r'''#!/usr/bin/env python3
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
'''


def prepare(args):
    two = load_sibling("run_two_goal_pilot")
    if not args.run_id:
        args.run_id = datetime.now(timezone.utc).strftime("avoid_%Y%m%dT%H%M%SZ")
    if pinned_planner_sha256() != PINNED_PLANNER_SHA256:
        raise RuntimeError("pinned planner.yaml hash changed before prepare")
    local_run, commands = two.prepare(args)
    load_sibling("qualify_stand_runner").stage_livox_assets(local_run)
    pilot = json.loads((local_run / "inputs/pilot.json").read_text(encoding="utf-8"))
    remote_run = args.remote_root.rstrip("/") + "/" + local_run.name
    argv = build_avoid_runner_argv(args, remote_run, local_run.name, pilot)
    runner_path = local_run / "bridge/lite3_sim_bridge/run_pct_scan_building.py"
    runner_module = two.import_runner(runner_path)
    baseline_scope = json.loads((two.P2B / "baseline_config/native_nominal_scope.json").read_text(encoding="utf-8"))
    scope = two.make_scope(
        runner_module,
        argv,
        two.sha256(local_run / "inputs/execution_manifest.json"),
        two.sha256(runner_path),
        pilot,
        baseline_scope,
    )
    scope["tcp_ports"] = {
        "telemetry": args.telemetry_port,
        "command": args.command_port,
        "http": args.http_port,
        "pct": args.pct_port,
    }
    scope["claim"] = (
        "One unmapped-box walk to goal-b. PCT on the prior map, SCAN from Livox. "
        "Not a navigation validation claim."
    )
    two.write_json(local_run / "inputs/two_goal_scope.json", scope)
    two.write_file(local_run / "pilot_driver.py", driver_source(), executable=True)
    commands = replace_runner_argv(commands, argv)
    two.write_json(local_run / "commands.json", commands)
    manifest_path = local_run / "inputs/package_manifest.json"
    manifest_path.unlink()
    two.write_json(manifest_path, two.package_manifest(local_run))
    request_path = local_run / "run_request.json"
    request = json.loads(request_path.read_text(encoding="utf-8"))
    request["unmapped_box"] = "lidar"
    request["lidar_pattern_mode"] = "livox_mid360"
    request["goal_id"] = "goal-b"
    request["claim_boundary"] = scope["claim"]
    two.write_json(request_path, request)
    return local_run, commands


def find_waypoints(node):
    if isinstance(node, dict):
        points = node.get("waypoints_m")
        if isinstance(points, list) and points:
            return points
        for value in node.values():
            found = find_waypoints(value)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = find_waypoints(item)
            if found:
                return found
    return None


def samples_from_metrics(path: Path):
    samples = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        xyz = row.get("base_xyz")
        rpy = row.get("base_rpy_rad")
        if isinstance(xyz, list) and len(xyz) == 3 and isinstance(rpy, list) and len(rpy) == 3:
            samples.append((tuple(float(v) for v in xyz), float(rpy[2])))
    return samples


def score_returned_run(local_run: Path) -> dict:
    box = load_sibling("unmapped_box")
    pilot = json.loads((local_run / "inputs/pilot.json").read_text(encoding="utf-8"))
    identity = box.unmapped_box_identity(
        "lidar",
        pilot["spawn_ground_xyz_m"],
        pilot["spawn_yaw_rad"],
        pilot["nominal_body_height_m"],
    )
    journal_path = local_run / "returned_artifacts/pilot_journal.json"
    metrics_path = local_run / "returned_artifacts/runner_output/metrics.jsonl"
    journal = json.loads(journal_path.read_text(encoding="utf-8")) if journal_path.is_file() else {}
    waypoints = find_waypoints(journal) or []
    samples = samples_from_metrics(metrics_path) if metrics_path.is_file() else []
    if not samples:
        return {
            "status": "incomplete",
            "route_crosses_box": bool(waypoints) and route_xy_crosses_box(waypoints, identity["robot_overlap"]["box_aabb"]),
            "torso_overlap": False,
            "arrived": False,
            "final_xy_error_m": None,
            "note": "no body samples in metrics.jsonl",
        }
    verdict = episode_verdict(
        waypoints,
        samples,
        pilot["goals"][1]["ground_xyz_m"],
        identity["robot_overlap"]["box_aabb"],
        pilot["nominal_body_height_m"],
        pilot["goal_xy_tolerance_m"],
    )
    verdict["box_aabb"] = identity["robot_overlap"]["box_aabb"]
    verdict["goal_xyz_m"] = pilot["goals"][1]["ground_xyz_m"]
    return verdict


def write_result(run_id: str, local_run: Path, verdict: dict) -> None:
    planner = pinned_planner_sha256()
    lines = [
        "# Unmapped box avoidance walk",
        "",
        "Label: one Isaac episode. Not a navigation validation claim.",
        "",
        "| Item | Value |",
        "| --- | --- |",
        "| Run | `%s` |" % run_id,
        "| Local package | `%s` |" % local_run,
        "| Status | %s |" % verdict.get("status"),
        "| PCT route crosses box xy | %s |" % verdict.get("route_crosses_box"),
        "| Expanded torso intersects box | %s |" % verdict.get("torso_overlap"),
        "| Final xy within 0.25 m of goal-b | %s |" % verdict.get("arrived"),
        "| Final xy error m | %s |" % verdict.get("final_xy_error_m"),
        "| Source planner.yaml SHA-256 | `%s` |" % planner,
        "",
        "Pass needs all three: the route crosses the box footprint, the torso never intersects it, and the dog stops within 0.25 m of goal-b.",
        "",
    ]
    if verdict.get("note"):
        lines.append(verdict["note"])
        lines.append("")
    RESULT_PATH.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--execute", action="store_true", default=False)
    parser.add_argument("--lead-authorized-execute", action="store_true", default=False)
    parser.add_argument("--host", default="gpu5070ti")
    parser.add_argument("--remote-root", default=DEFAULT_REMOTE_ROOT)
    parser.add_argument("--remote-v12-runtime", default=load_sibling("run_two_goal_pilot").DEFAULT_REMOTE_V12)
    parser.add_argument("--remote-checkpoint", default=load_sibling("run_two_goal_pilot").DEFAULT_REMOTE_CHECKPOINT)
    parser.add_argument("--accepted-scan-build-dir", default=str(DEFAULT_SCAN_BUILD))
    parser.add_argument("--remote-scan-workspace", default=DEFAULT_REMOTE_SCAN)
    parser.add_argument("--local-runs-root", type=Path, default=HERE / "unmapped_box_avoid_runs")
    parser.add_argument("--telemetry-port", type=int, default=46250)
    parser.add_argument("--command-port", type=int, default=46251)
    parser.add_argument("--http-port", type=int, default=8775)
    parser.add_argument("--pct-port", type=int, default=47641)
    parser.add_argument("--ros-domain-id", type=int, default=94)
    parser.add_argument("--cancel-displacement-m", type=float, default=0.4)
    parser.add_argument("--stance-hold", default="auto")
    parser.add_argument("--stance-entry-kd", default=None)
    parser.add_argument("--allow-missing-install-identity", action="store_true", default=False)
    parser.add_argument("--remote-only-bulk", action="store_true", default=False)
    return parser


def avoid_args(argv=None):
    return build_parser().parse_args([] if argv is None else argv)


def open_package(args):
    """Prepare a new package, or load one already prepared for this run id."""
    two = load_sibling("run_two_goal_pilot")
    existing = bool(args.run_id) and (Path(args.local_runs_root) / args.run_id).is_dir()
    if args.execute and existing:
        return two.load_prepared_run(args)
    return prepare(args)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    local_run, commands = open_package(args)
    print("prepared", local_run)
    if not args.execute:
        return 0
    two = load_sibling("run_two_goal_pilot")
    error = None
    try:
        two.execute(args, local_run, commands)
    except Exception as exc:
        error = exc
        print("execute failed:", exc, file=sys.stderr)
    verdict = score_returned_run(local_run)
    if error is not None and verdict.get("status") == "pass":
        verdict["status"] = "incomplete"
        verdict["note"] = "package collection or worker reported an error after a passing score: %s" % error
    write_result(local_run.name, local_run, verdict)
    print(json.dumps({k: verdict[k] for k in ("status", "route_crosses_box", "torso_overlap", "arrived", "final_xy_error_m")}, indent=2))
    return 0 if error is None and verdict.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
