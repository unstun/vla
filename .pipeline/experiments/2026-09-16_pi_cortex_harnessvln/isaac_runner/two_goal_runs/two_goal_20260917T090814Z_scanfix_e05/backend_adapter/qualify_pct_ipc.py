#!/usr/bin/env python3
"""Actual PCT worker IPC qualification for the P2B backend adapter.

Host mode syncs the owned adapter slice and parent frozen P2B inputs to gpu5070ti,
then runs a CPU-only Podman container. Inside mode starts the real
backend_adapter.pct_worker server and drives it through PctIpcClient.
"""
from __future__ import annotations

import argparse
import json
import hashlib
import os
import pathlib
import shlex
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Mapping, Tuple

HERE = pathlib.Path(__file__).resolve().parent
EXP = HERE.parent
P2B = EXP / "p2b_execution"
PCT_IMAGE = "40f0fa16091e2b6e24fd82058ceb01dbe76c001276234af0b9a44ac0e3787555"
FOXY_IMAGE = "e4aa7154"
REMOTE_ROOT = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/backend_adapter_qualification"


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def files_under(root: pathlib.Path) -> List[pathlib.Path]:
    return [p for p in sorted(root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".pyc")]


def rel_to_exp(path: pathlib.Path) -> str:
    return str(path.relative_to(EXP))


def expected_sources() -> Dict[str, str]:
    files: List[pathlib.Path] = []
    for sub in [HERE / "backend_adapter", HERE / "tests", HERE / "config"]:
        files.extend(files_under(sub))
    files.extend([HERE / "qualify_pct_ipc.py", HERE / "verify.py", HERE / "README.md", HERE / "RESULT.md"])
    files.extend([EXP / "navigation_service/core.py", EXP / "navigation_service/__init__.py"])
    manifest = json.loads((P2B / "pct_runtime_manifest.json").read_text())
    for rel in manifest["files"]:
        files.append(P2B / rel)
    for rel in ["pct_runtime_manifest.json", "input_manifest.json", "inputs/pilot.json", "inputs/new_building.pickle"]:
        files.append(P2B / rel)
    return {rel_to_exp(p): sha256(p) for p in sorted(set(files))}


def pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def wait_port(port: int, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.05):
                return
        except OSError as exc:
            last = exc
            time.sleep(0.05)
    raise RuntimeError("pct_worker_port_not_ready:%s:%s" % (port, last))


def inside(output: pathlib.Path) -> None:
    from backend_adapter.contracts import PlannerRequest
    from backend_adapter.pct_ipc import PctIpcClient, PctIpcClientConfig

    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise RuntimeError("output_directory_not_empty:%s" % output)
    root = pathlib.Path("/qualification/experiment")
    expected = json.loads((pathlib.Path("/qualification/source_sha256.json")).read_text())
    actual = {rel: sha256(root / rel) for rel in expected}
    if actual != expected:
        mismatch = {k: (actual.get(k), expected[k]) for k in expected if actual.get(k) != expected[k]}
        raise RuntimeError("source_hash_mismatch:" + json.dumps(mismatch, sort_keys=True)[:2000])

    runtime_manifest = json.loads((root / "p2b_execution/pct_runtime_manifest.json").read_text())
    for rel, digest in runtime_manifest["files"].items():
        actual_digest = sha256(root / "p2b_execution" / rel)
        if actual_digest != digest:
            raise RuntimeError("pct_runtime_hash_mismatch:%s" % rel)
    input_manifest = json.loads((root / "p2b_execution/input_manifest.json").read_text())
    for item in input_manifest["files"]:
        if item["path"] in {"inputs/pilot.json", "inputs/new_building.pickle"}:
            actual_digest = sha256(root / "p2b_execution" / item["path"])
            if actual_digest != item["sha256"]:
                raise RuntimeError("input_hash_mismatch:%s" % item["path"])

    pilot = json.loads((root / "p2b_execution/inputs/pilot.json").read_text())
    port = pick_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = "/qualification/experiment/backend_adapter:/qualification/experiment/p2b_execution/pct_runtime/python:" + env.get("PYTHONPATH", "")
    env["LD_LIBRARY_PATH"] = "/qualification/experiment/p2b_execution/pct_runtime/lib:" + env.get("LD_LIBRARY_PATH", "")
    cmd = [
        sys.executable, "-m", "backend_adapter.pct_worker",
        "--host", "127.0.0.1", "--port", str(port),
        "--pct-source-root", "/qualification/experiment/p2b_execution/pct_runtime/python",
        "--rsg-root", "/qualification/experiment/p2b_execution/inputs",
        "--tomogram-path", "/qualification/experiment/p2b_execution/inputs/new_building.pickle",
        "--reference-height-m", str(pilot["nominal_body_height_m"]),
    ]
    worker_stdout = output / "pct_worker.stdout.log"
    worker_stderr = output / "pct_worker.stderr.log"
    worker_out = worker_stdout.open("w")
    worker_err = worker_stderr.open("w")
    proc = subprocess.Popen(cmd, stdout=worker_out, stderr=worker_err, env=env, text=True)
    records = []
    try:
        wait_port(port, 30.0)
        client = PctIpcClient(PctIpcClientConfig(host="127.0.0.1", port=port, connect_timeout_s=0.5, response_timeout_s=10.0))
        start = tuple(float(x) for x in pilot["spawn_ground_xyz_m"])
        for goal in pilot["goals"]:
            request = PlannerRequest(
                request_id="ipc-" + goal["goal_id"],
                goal_id=goal["goal_id"],
                start_xyz_m=start,
                target_xyz_m=tuple(float(x) for x in goal["ground_xyz_m"]),
                frame_id=pilot["frame_id"],
                map_epoch="flat_nominal",
                map_revision=1,
                start_layer=int(pilot["pct_layer"]),
                target_layer=int(pilot["pct_layer"]),
                optimize=True,
            )
            begin = time.monotonic()
            route = client.plan(request)
            elapsed = time.monotonic() - begin
            if route.goal_id != request.goal_id or route.frame_id != pilot["frame_id"] or route.map_epoch != "flat_nominal" or route.map_revision != 1:
                raise RuntimeError("route_identity_mismatch")
            if route.z_semantics != "lite3_body_reference_no_display_offset":
                raise RuntimeError("bad_z_semantics")
            if len(route.waypoints_m) != 10:
                raise RuntimeError("unexpected_waypoint_count:%s" % len(route.waypoints_m))
            for point in route.waypoints_m:
                if not all(isinstance(v, float) and abs(v) < 1e6 for v in point):
                    raise RuntimeError("nonfinite_waypoint")
            target = tuple(float(x) for x in goal["ground_xyz_m"])
            endpoint_xy = ((route.waypoints_m[-1][0] - target[0]) ** 2 + (route.waypoints_m[-1][1] - target[1]) ** 2) ** 0.5
            if endpoint_xy > float(pilot["goal_xy_tolerance_m"]):
                raise RuntimeError("endpoint_xy_out_of_tolerance:%s" % endpoint_xy)
            rec = {
                "goal_id": goal["goal_id"],
                "route_id": route.route_id,
                "elapsed_wall_s": elapsed,
                "point_count": len(route.waypoints_m),
                "endpoint_error_xy_m": endpoint_xy,
                "start_xyz_m": list(start),
                "target_xyz_m": list(target),
                "waypoints_m": [list(p) for p in route.waypoints_m],
                "z_semantics": route.z_semantics,
                "display_offset_validation": "pct_worker_verified_wrapper_z_minus_native_height_equals_0.5_before_returning_body_reference_z",
            }
            (output / (goal["goal_id"] + ".json")).write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
            records.append({k: v for k, v in rec.items() if k != "waypoints_m"})
            start = target

        bad = {}
        try:
            bad_req = PlannerRequest(
                request_id="ipc-bad-optimize", goal_id="goal-a", start_xyz_m=tuple(float(x) for x in pilot["spawn_ground_xyz_m"]),
                target_xyz_m=tuple(float(x) for x in pilot["goals"][0]["ground_xyz_m"]), frame_id=pilot["frame_id"],
                map_epoch="flat_nominal", map_revision=1, start_layer=int(pilot["pct_layer"]), target_layer=int(pilot["pct_layer"]), optimize=False)
            client.plan(bad_req)
            bad["optimize_false"] = "unexpected_success"
        except Exception as exc:
            bad["optimize_false"] = type(exc).__name__ + ":" + str(exc)
        try:
            PctIpcClient(PctIpcClientConfig(host="127.0.0.1", port=pick_port(), connect_timeout_s=0.05, response_timeout_s=0.05)).plan(bad_req)
            bad["unavailable"] = "unexpected_success"
        except Exception as exc:
            bad["unavailable"] = type(exc).__name__ + ":" + str(exc)

        class Hang(socketserver.BaseRequestHandler):
            def handle(self):
                time.sleep(1.0)
        hang_port = pick_port()
        hang_server = socketserver.TCPServer(("127.0.0.1", hang_port), Hang)
        hang_thread = threading.Thread(target=hang_server.serve_forever, daemon=True)
        hang_thread.start()
        try:
            PctIpcClient(PctIpcClientConfig(host="127.0.0.1", port=hang_port, connect_timeout_s=0.05, response_timeout_s=0.10)).plan(bad_req)
            bad["timeout"] = "unexpected_success"
        except Exception as exc:
            bad["timeout"] = type(exc).__name__ + ":" + str(exc)
        finally:
            hang_server.shutdown()
            hang_server.server_close()
        for key, value in bad.items():
            if value == "unexpected_success":
                raise RuntimeError("bad_case_unexpected_success:" + key)

        result = {
            "passed": True,
            "python": sys.version,
            "worker_command": cmd,
            "source_hashes_checked": len(expected),
            "runtime_file_hashes_checked": len(runtime_manifest["files"]),
            "routes": records,
            "bad_cases": bad,
            "claim": "Actual pct_worker process plus PctIpcClient RPC in one CPU-only container; synthetic measured-start compute inputs only; no ROS, Isaac, controller, GPU or motion evidence.",
        }
        (output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        worker_out.close()
        worker_err.close()


def host() -> pathlib.Path:
    run_id = datetime.now(timezone.utc).strftime("pct_ipc_%Y%m%dT%H%M%SZ")
    out = HERE / "qualification" / run_id
    out.mkdir(parents=True, exist_ok=False)
    expected = expected_sources()
    (out / "source_sha256.json").write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n")
    (out / "files.txt").write_text("\n".join(sorted(expected)) + "\n")
    remote = REMOTE_ROOT + "/" + run_id
    commands = []

    def run(label: str, cmd: List[str], stdin: str | None = None, timeout: int = 600) -> subprocess.CompletedProcess:
        started = time.time()
        proc = subprocess.run(cmd, input=stdin, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        (out / (label + ".log")).write_text(proc.stdout)
        commands.append({"label": label, "command": cmd, "exit_code": proc.returncode, "wall_seconds": round(time.time() - started, 3)})
        (out / "commands.json").write_text(json.dumps(commands, indent=2, sort_keys=True) + "\n")
        print(label, proc.returncode, flush=True)
        proc.check_returncode()
        return proc

    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "gpu5070ti"]
    run("remote_preflight", ssh + ["python3 --version && podman --version && podman image exists " + PCT_IMAGE + " && echo pct_image_ok"], timeout=60)
    run("mkdir", ssh + [shlex.join(["mkdir", "-p", remote + "/experiment", remote + "/result", remote + "/foxy_tests"])], timeout=60)
    run("sync", ["rsync", "-a", "--files-from=" + str(out / "files.txt"), str(EXP) + "/", "gpu5070ti:" + remote + "/experiment/"], timeout=300)
    run("sync_hashes", ["rsync", "-a", str(out / "source_sha256.json"), "gpu5070ti:" + remote + "/source_sha256.json"], timeout=60)
    gate = "import hashlib,json,pathlib\nroot=pathlib.Path(%r)/'experiment'\nexpected=json.loads((pathlib.Path(%r)/'source_sha256.json').read_text())\nactual={k:hashlib.sha256((root/k).read_bytes()).hexdigest() for k in expected}\nassert actual==expected\nprint(json.dumps({'matched':True,'files':len(actual)},sort_keys=True))\n" % (remote, remote)
    run("source_gate", ssh + ["python3 -"], stdin=gate, timeout=120)
    inner = "set -e\nsource /opt/ros/humble/setup.bash\nexport PYTHONDONTWRITEBYTECODE=1\nexport PYTHONPATH=/qualification/experiment/backend_adapter:/qualification/experiment/p2b_execution/pct_runtime/python:${PYTHONPATH:-}\nexport LD_LIBRARY_PATH=/qualification/experiment/p2b_execution/pct_runtime/lib:${LD_LIBRARY_PATH:-}\nexec python3 /qualification/experiment/backend_adapter/qualify_pct_ipc.py --inside --output /qualification/result"
    run("pct_ipc_container", ssh + [shlex.join(["podman", "run", "--rm", "--name", "p2b-pct-ipc-" + run_id.lower(), "--pull=never", "--network=none", "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "OPENBLAS_NUM_THREADS=1", "-e", "OMP_NUM_THREADS=2", "-v", remote + ":/qualification", PCT_IMAGE, "bash", "-lc", inner])], timeout=240)
    foxy_cmd = "set -e\nsource /opt/ros/foxy/setup.bash || true\nexport PYTHONDONTWRITEBYTECODE=1\ncd /work/backend_adapter\npython3 --version\npython3 -m unittest discover -s tests -v"
    run("foxy38_tests", ssh + [shlex.join(["podman", "run", "--rm", "--name", "p2b-foxy-tests-" + run_id.lower(), "--pull=never", "--network=none", "-e", "PYTHONDONTWRITEBYTECODE=1", "-v", remote + "/experiment:/work:ro", FOXY_IMAGE, "bash", "-lc", foxy_cmd])], timeout=180)
    (out / "result").mkdir(parents=True, exist_ok=True)
    try:
        run("return_result", ["rsync", "-a", "gpu5070ti:" + remote + "/result/", str(out / "result") + "/"], timeout=120)
    except subprocess.CalledProcessError:
        run("return_result_retry", ["rsync", "-a", "gpu5070ti:" + remote + "/result/", str(out / "result") + "/"], timeout=120)
    remote_hash = "import hashlib,json,pathlib\nr=pathlib.Path(%r)/'result'\nprint(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in r.rglob('*') if p.is_file()},sort_keys=True))\n" % remote
    run("return_hashes", ssh + ["python3 -"], stdin=remote_hash, timeout=60)
    returned = json.loads((out / "return_hashes.log").read_text())
    local = {str(p.relative_to(out / "result")): sha256(p) for p in (out / "result").rglob("*") if p.is_file()}
    verdict = {"passed": returned == local, "remote": remote, "local": str(out), "returned_hashes": returned, "local_hashes": local}
    (out / "sync_verdict.json").write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n")
    if not verdict["passed"]:
        raise RuntimeError("returned_hash_mismatch")
    print(str(out))
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--inside", action="store_true")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    if args.inside:
        if args.output is None:
            raise SystemExit("--output required with --inside")
        inside(args.output)
    else:
        host()
