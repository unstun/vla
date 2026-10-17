"""Bounded Foxy CPU qualification for the P2B backend_ros node.

This script syncs only the whitelisted P2B Python sources into an isolated
remote qualification root, runs the node inside the lead-provided Foxy image
against the read-only scan_02 install workspace, and pulls raw logs/results
back under backend_ros/qualification/.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import textwrap
import time
from typing import Dict, Iterable, List


ROOT = pathlib.Path(__file__).resolve().parent
EXPERIMENT = ROOT.parent
REMOTE_HOST = "gpu5070ti"
REMOTE_BASE = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/ros_binding_qualification"
SCAN02 = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_02"
FOXY_IMAGE = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_file(src: pathlib.Path, dst: pathlib.Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def should_skip(path: pathlib.Path) -> bool:
    parts = set(path.parts)
    return "__pycache__" in parts or "qualification" in parts or "checks" in parts


def copy_tree_files(src_root: pathlib.Path, dst_root: pathlib.Path, suffixes: Iterable[str]) -> None:
    allowed = tuple(suffixes)
    for path in src_root.rglob("*"):
        if not path.is_file() or should_skip(path):
            continue
        if allowed and path.suffix not in allowed:
            continue
        copy_file(path, dst_root / path.relative_to(src_root))


def run(command: List[str], cwd: pathlib.Path | None = None, timeout: int = 120) -> Dict[str, object]:
    started = time.monotonic()
    proc = subprocess.run(command, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout)
    return {
        "command": command,
        "returncode": proc.returncode,
        "elapsed_s": time.monotonic() - started,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def write_remote_probe(path: pathlib.Path) -> None:
    path.write_text(textwrap.dedent(
        r'''
        import json
        import os
        import pathlib
        import signal
        import subprocess
        import sys
        import time
        import urllib.error
        import urllib.request

        ROOT = pathlib.Path("/qualification")
        RESULT = ROOT / "result"
        RESULT.mkdir(parents=True, exist_ok=True)
        SOURCE = ROOT / "source"
        CONFIG = ROOT / "runtime_config.json"
        HTTP = "http://127.0.0.1:18765"

        def write(name, data):
            (RESULT / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        def get_json(path):
            with urllib.request.urlopen(HTTP + path, timeout=2.0) as response:
                return json.loads(response.read().decode("utf-8"))

        def post_json(path, payload):
            req = urllib.request.Request(
                HTTP + path,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=2.0) as response:
                    return response.status, json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                return exc.code, json.loads(exc.read().decode("utf-8"))

        env = dict(os.environ)
        env["PYTHONPATH"] = "/qualification/source/backend_ros:/qualification/source/backend_adapter:" + env.get("PYTHONPATH", "")
        cmd = [
            sys.executable,
            "-m",
            "p2b_backend_ros.node",
            "--config",
            str(CONFIG),
            "--run-id",
            "ros-bind-qual",
            "--run-epoch-ns",
            "987654321",
            "--applied-snapshot",
            "/qualification/missing_current_command.json",
            "--http-port",
            "18765",
            "--pct-port",
            "47631",
            "--ros-args",
            "-r",
            "__node:=p2b_backend_ros_qual",
        ]
        proc = subprocess.Popen(cmd, cwd=str(SOURCE), env=env, stdout=(RESULT / "node.stdout.log").open("w"), stderr=(RESULT / "node.stderr.log").open("w"))
        summary = {"node_command": cmd, "checks": []}
        try:
            deadline = time.monotonic() + 8.0
            state = None
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise RuntimeError("node_exited_before_http:%s" % proc.returncode)
                try:
                    state = get_json("/state")
                    break
                except Exception:
                    time.sleep(0.1)
            if state is None:
                raise RuntimeError("http_state_not_ready")
            write("state_initial.json", state)
            assert state["readiness"]["body_pose_ready"] is False
            assert state["readiness"]["applied_snapshot"]["configured"] is True
            assert state["readiness"]["applied_snapshot"]["ready"] is False
            summary["checks"].append("initial_state_missing_body_and_snapshot")

            invalid_status, invalid = post_json("/goal", {"request_id": "bad", "goal_id": "bad"})
            write("invalid_goal_response.json", {"http_status": invalid_status, "body": invalid})
            assert invalid_status == 400
            assert invalid["ok"] is False
            summary["checks"].append("invalid_goal_structured_refusal")

            valid_status, valid = post_json("/goal", {
                "request_id": "req-no-body",
                "goal_id": "goal-no-body",
                "target_ground_xyz": [1.0, 0.0, 0.0],
                "frame": "world",
                "map_epoch": "flat_nominal",
                "map_revision": 1,
            })
            write("valid_goal_no_body_initial_response.json", {"http_status": valid_status, "body": valid})
            assert valid_status == 202
            time.sleep(0.5)
            after_goal = get_json("/state")
            write("state_after_valid_goal_without_body.json", after_goal)
            jobs = list(after_goal["jobs"].values())
            assert jobs and jobs[-1]["status"] == "failed"
            assert jobs[-1]["error"] == "body_pose_not_ready"
            summary["checks"].append("valid_goal_fails_explicitly_without_body_or_pct")

            import rclpy
            from geometry_msgs.msg import Twist
            from scan_planner_msgs.msg import P2BStampedTwist

            received = []
            rclpy.init(args=None)
            probe = rclpy.create_node("p2b_backend_ros_cpu_probe")
            sub = probe.create_subscription(Twist, "/quad_0/cmd_vel", lambda msg: received.append([msg.linear.x, msg.linear.y, msg.angular.z]), 20)
            pub = probe.create_publisher(P2BStampedTwist, "/quad_0/raw_scan_cmd_vel", 20)
            raw = P2BStampedTwist()
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline and not received:
                pub.publish(raw)
                rclpy.spin_once(probe, timeout_sec=0.05)
            probe.destroy_node()
            rclpy.shutdown()
            assert proc.poll() is None
            assert received, "no_zero_cmd_vel_received"
            assert abs(received[-1][0]) < 1.0e-9 and abs(received[-1][1]) < 1.0e-9 and abs(received[-1][2]) < 1.0e-9
            write("cmd_vel_zero_probe.json", {"received": received[:20], "sample_count": len(received)})
            summary["checks"].append("invalid_raw_identity_zero_output_and_node_alive")

            summary["ok"] = True
        except Exception as exc:
            summary["ok"] = False
            summary["error"] = str(exc)
            raise
        finally:
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:
                    proc.wait(timeout=4.0)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=4.0)
            summary["node_returncode"] = proc.returncode
            write("summary.json", summary)
        ''').lstrip(), encoding="utf-8")


def main() -> int:
    run_id = time.strftime("ros_binding_%Y%m%dT%H%M%SZ", time.gmtime())
    qual_root = ROOT / "qualification" / run_id
    source = qual_root / "source"
    result = qual_root / "result"
    source.mkdir(parents=True)
    result.mkdir(parents=True)

    copy_tree_files(ROOT, source / "backend_ros", {".py", ".xml", ".cfg", ".json", ".md"})
    copy_tree_files(EXPERIMENT / "backend_adapter" / "backend_adapter", source / "backend_adapter" / "backend_adapter", {".py"})
    copy_file(EXPERIMENT / "backend_adapter" / "config" / "p2b_adapter.example.json", source / "backend_adapter" / "config" / "p2b_adapter.example.json")
    copy_file(EXPERIMENT / "navigation_service" / "core.py", source / "navigation_service" / "core.py")
    write_remote_probe(source / "remote_probe.py")

    runtime_config = json.loads((ROOT / "config" / "p2b_backend_ros.example.json").read_text(encoding="utf-8"))
    runtime_config["run_id"] = "ros-bind-qual"
    runtime_config["run_epoch_ns"] = 987654321
    runtime_config["http"]["port"] = 18765
    runtime_config["service"]["body_ready_timeout_s"] = 0.1
    runtime_config["service"]["command_timeout_s"] = 3.0
    runtime_config["service"]["stop_completion_timeout_s"] = 1.0
    runtime_config["gate"]["initial_heartbeat_grace_s"] = 0.3
    runtime_config["applied_evidence"]["current_command_path"] = "/qualification/missing_current_command.json"
    runtime_config["applied_evidence"]["finish_request_path"] = "/qualification/finish_request.json"
    (qual_root / "runtime_config.json").write_text(json.dumps(runtime_config, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    hashes = {}
    for path in sorted(source.rglob("*")):
        if path.is_file():
            hashes[str(path.relative_to(source))] = sha256(path)
    (qual_root / "source_sha256.json").write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    remote_dir = REMOTE_BASE + "/" + run_id
    preflight = run(["ssh", REMOTE_HOST, "mkdir -p " + remote_dir], timeout=30)
    sync = run(["rsync", "-a", str(qual_root) + "/", REMOTE_HOST + ":" + remote_dir + "/"], timeout=60)
    remote_command = (
        "podman run --rm --pull=never --network=host "
        "--name vla-p2b-ros-binding-%s "
        "-v %s:/qualification "
        "-v %s:/workspace:ro "
        "%s bash -lc 'source /opt/ros/foxy/setup.bash && source /workspace/install/setup.bash && timeout 60s python3 /qualification/source/remote_probe.py'"
    ) % (run_id.replace("_", "-").lower(), remote_dir, SCAN02, FOXY_IMAGE)
    remote_run = run(["ssh", REMOTE_HOST, remote_command], timeout=90)
    pull = run(["rsync", "-a", REMOTE_HOST + ":" + remote_dir + "/", str(qual_root) + "/"], timeout=60)

    remote_hash = run(["ssh", REMOTE_HOST, "cd " + remote_dir + "/source && python3 - <<'PY'\nimport hashlib, json, pathlib\nout={}\nfor p in sorted(pathlib.Path('.').rglob('*')):\n    if p.is_file():\n        h=hashlib.sha256(); h.update(p.read_bytes()); out[str(p)]=h.hexdigest()\nprint(json.dumps(out, sort_keys=True))\nPY"], timeout=30)
    if remote_hash["returncode"] == 0:
        (qual_root / "remote_source_sha256.json").write_text(str(remote_hash["stdout"]), encoding="utf-8")

    summary_path = qual_root / "result" / "summary.json"
    probe_ok = False
    if summary_path.exists():
        try:
            probe_ok = bool(json.loads(summary_path.read_text(encoding="utf-8")).get("ok"))
        except Exception:
            probe_ok = False
    report = {
        "schema": "p2b_backend_ros_foxy_cpu_qualification_v1",
        "ok": preflight["returncode"] == 0 and sync["returncode"] == 0 and remote_run["returncode"] == 0 and pull["returncode"] == 0 and probe_ok,
        "run_id": run_id,
        "local_dir": str(qual_root),
        "remote_dir": remote_dir,
        "image": FOXY_IMAGE,
        "scan02_mount": SCAN02,
        "preflight": preflight,
        "sync": sync,
        "remote_run": remote_run,
        "pull": pull,
        "claim": "Foxy CPU node startup/HTTP/readiness/invalid-goal/zero-output smoke only; no PCT worker, Isaac, GPU, C++ motion acceptance or robot claim.",
    }
    (qual_root / "qualification_report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(qual_root)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
