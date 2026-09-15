"""Eight bounded Lite3 capability trials with owned process-group cleanup."""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import threading
import time
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp", type=Path, required=True)
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    exp = args.exp.resolve()
    pkg = exp / "lite3_capabilities_v1"
    base = exp / "lite3_v1"
    suite = json.loads((pkg / "cases/suite.json").read_text())
    work = exp / "work/LightNav-0-lite3-capabilities-v1"
    model_py = exp / "work/LightNav-0/.venv/bin/python"
    demo_py = exp / "work/LightNav-0/mujoco_demo/.venv/bin/python"
    run = pkg / "runs" / args.run
    run.mkdir(parents=True, exist_ok=False)
    for port in (8050, 8088):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", port))
    gpu = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.total,memory.free",
                                   "--format=csv,noheader,nounits"], text=True)
    total, free = map(int, gpu.strip().split(","))
    if free < 0.8 * total + 512:
        raise RuntimeError(f"Insufficient GPU headroom: {gpu}")
    base_env = dict(os.environ)
    for key in ("LIGHTNAV_ATTN", "LIGHTNAV_SKIP_VERSION_GUARD", "VLLM_QUANT",
                "VLN_EVAL_TEMPERATURE", "VLN_EVAL_TOP_K", "VLN_EVAL_TOP_P",
                "VLN_EVAL_TRAJ_TOP1", "VLN_KV_CACHE_GIB", "VLN_VLLM_ENFORCE_EAGER",
                "MAX_BATCH_SIZE", "ASPECT_MODE", "TASK", "RECORD_DIR", "CAM_HEIGHT",
                "CAM_HFOV_DEG", "WAYPOINT_DT_S", "HOST", "PORT"):
        base_env.pop(key, None)
    processes = []
    handles = []
    stop_sampler = threading.Event()
    deadline = time.monotonic() + 720
    started = time.time()
    outcome = {"completed": False}

    def stop_signal(*_):
        raise KeyboardInterrupt("navigation supervisor interrupted")

    signal.signal(signal.SIGTERM, stop_signal)
    signal.signal(signal.SIGINT, stop_signal)

    def launch(name, cmd, env):
        out = run / name
        out.mkdir()
        stdout, stderr = (out / "stdout.log").open("w"), (out / "stderr.log").open("w")
        handles.extend([stdout, stderr])
        proc = subprocess.Popen(list(map(str, cmd)), env=env, cwd=work,
                                stdout=stdout, stderr=stderr, start_new_session=True)
        processes.append((name, proc))
        (out / "process.json").write_text(json.dumps({
            "pid": proc.pid, "pgid": os.getpgid(proc.pid), "command": list(map(str, cmd)),
            "started_unix": time.time(), "work": str(work),
            "pythonpath": env.get("PYTHONPATH"),
        }, indent=2)+"\n")
        return proc

    def sample():
        with (run / "gpu_samples.jsonl").open("w", buffering=1) as stream:
            while not stop_sampler.is_set():
                r = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.free,utilization.gpu",
                                    "--format=csv,noheader,nounits"], capture_output=True, text=True,
                                   timeout=5)
                stream.write(json.dumps({"wall": time.time(), "mono": time.monotonic(),
                                         "gpu": r.stdout.strip(), "exit": r.returncode})+"\n")
                stop_sampler.wait(0.5)

    def stop_process(name, proc):
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=3)
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        processes.remove((name, proc))

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    try:
        ready = run / "model.ready"
        model = launch("model", [model_py, "-m", "lightnav.serving.ws_server",
            "--task", "vln", "--backend", "vllm_local", "--model_path", exp / "checkpoints/LightNav-0",
            "--host", "127.0.0.1", "--port", "8050", "--gpu_memory_utilization", "0.80",
            "--max_batch_size", "8", "--record_dir", run / "records", "--ready_file", ready,
            "--cam_hfov_deg", "112.2", "--cam_height", "0.38"],
            {**base_env, "PYTHONPATH": str(work / "src"), "CUDA_VISIBLE_DEVICES": "0"})
        warm_deadline = min(deadline, time.monotonic()+300)
        while not ready.exists():
            if model.poll() is not None or time.monotonic() > warm_deadline:
                raise RuntimeError("Model failed readiness gate")
            time.sleep(0.5)
        outcomes = []
        for scene in ("clear", "blocked"):
            if time.monotonic() >= deadline-70:
                raise RuntimeError("Insufficient service-window budget for another scene")
            demo_env = {**base_env, "MUJOCO_GL": "egl",
                        "LIGHTNAV_V3_TRACE_DIR": str(run / f"capture_{scene}"),
                        "PYTHONPATH": f"{work / 'mujoco_demo'}:{exp / 'work/lite3-v1-python-overlay'}"}
            demo_name = f"demo_{scene}"
            demo = launch(demo_name, [demo_py, "-m", "vln_mujoco", "--robot", "lite3",
                "--robot-model", base / "assets/lite3/lite3.xml",
                "--walking-policy", base / "policy/policy_stateless_h10.onnx",
                "--scene-model", pkg / "cases" / f"{scene}.xml",
                "--host", "127.0.0.1", "--port", "8088", "--vln-server", "ws://127.0.0.1:8050"], demo_env)
            demo_deadline = min(deadline, time.monotonic()+60)
            while True:
                if demo.poll() is not None or time.monotonic() > demo_deadline:
                    raise RuntimeError("Lite3 demo failed readiness gate")
                try:
                    with urllib.request.urlopen("http://127.0.0.1:8088/api/health", timeout=1) as response:
                        health = json.load(response)
                    if health["simulation"]["camera"]["ready"]:
                        break
                except (OSError, ValueError, KeyError):
                    pass
                time.sleep(0.5)
            (run / f"initial_health_{scene}.json").write_text(json.dumps(health, indent=2)+"\n")
            for case in [c for c in suite["cases"] if c["scene"] == scene]:
                if time.monotonic() >= deadline-60:
                    raise RuntimeError("Service-window deadline prevents another case")
                case_id = case["id"]
                harness_name = f"harness_{case_id}"
                print(f"START CASE {case_id}: {case['instruction']}", flush=True)
                harness = launch(harness_name, [demo_py, pkg / "scripts/run_episode.py",
                    "--case", pkg / "cases" / f"{case_id}.json", "--rep", case_id,
                    "--run-dir", run / "cases" / case_id,
                    "--wall-timeout", str(case["wall_timeout_s"]), "--decision-cap", str(case["decision_cap"]),
                    "--post-stop", str(case["post_stop_s"]), "--reset-settle", str(case["reset_settle_s"])], demo_env)
                harness.wait(timeout=min(55, max(1, deadline-time.monotonic())))
                if harness.returncode:
                    raise RuntimeError(f"Episode harness failed for {case_id}")
                episode = json.loads((run / "cases" / case_id / "episode.json").read_text())
                result = {"id": case_id, "termination": episode["termination"],
                          "decisions": episode["decisions"], "end_pose": episode["end_pose"]}
                outcomes.append(result)
                outcome["cases"] = outcomes
                print(json.dumps(result, ensure_ascii=False), flush=True)
                stop_process(harness_name, harness)
                if episode["termination"] == "recorder_failure":
                    raise RuntimeError("Recorder failed; preserve evidence and stop suite")
            stop_process(demo_name, demo)
        outcome["completed"] = len(outcomes) == len(suite["cases"])
    except BaseException as exc:
        outcome["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        cleanup = {}
        for name, proc in reversed(processes):
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=3)
            # The parent can exit before its workers; clean remaining owned group.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            cleanup[name] = {"pid": proc.pid, "exit_code": proc.returncode}
        stop_sampler.set()
        sampler.join(timeout=6)
        for handle in handles:
            handle.close()
        outcome.update(service_window_seconds=time.time()-started, cleanup=cleanup,
                       started_unix=started, ended_unix=time.time())
        (run / "result.json").write_text(json.dumps(outcome, indent=2)+"\n")
        print(json.dumps(outcome, indent=2), flush=True)
    if not outcome["completed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
