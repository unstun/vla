"""Remote-only bounded launcher. Validates source before spawning Isaac Sim."""
import datetime
import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--view", choices=("third_person", "top_down"), default="third_person")
    args = parser.parse_args()
    with socket.socket() as lock:
        lock.bind(("127.0.0.1", 18767))
        for item in json.loads((ROOT / "manifests/source.json").read_text()):
            if hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() != item["sha256"]:
                raise RuntimeError(f"Source sync gate failed: {item['path']}")
        if args.check:
            print("DEMO_SOURCE_SYNC_VERIFIED", flush=True)
            return
        run_id = args.run_id or datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        import re
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", run_id):
            raise ValueError("Invalid run ID")
        run = ROOT / "runs" / run_id
        run.mkdir(parents=True)
        import yaml
        from protocol import read_instruction_request
        scenario = yaml.safe_load((ROOT / "hospital_demo.yaml").read_text())
        request_sha256 = None
        inference_seed = None
        if args.offline:
            request_path = ROOT / "requests" / f"{run_id}.json"
            request = read_instruction_request(request_path)
            instruction = request["instruction"]
            inference_seed = request.get("inference_seed")
            request_bytes = request_path.read_bytes()
            request_sha256 = hashlib.sha256(request_bytes).hexdigest()
            (run / "input_request.json").write_bytes(request_bytes)
            scenario["episode_hospital_demo"]["instruction"] = instruction
        else:
            instruction = scenario["episode_hospital_demo"]["instruction"]
        scenario_path = run / "hospital_demo.yaml"
        scenario_path.write_text(yaml.safe_dump(scenario, allow_unicode=True, sort_keys=False))
        from distance_probe import ALLOWED_INSTRUCTIONS
        if instruction not in ALLOWED_INSTRUCTIONS:
            raise ValueError("This isolated probe requires its predeclared metric instruction")
        env = os.environ.copy()
        env["TICVLA_DEMO_VIEW"] = args.view
        env["TICVLA_DEMO_INSTRUCTION"] = instruction
        env.pop("TICVLA_INFERENCE_SEED", None)
        if inference_seed is not None:
            env["TICVLA_INFERENCE_SEED"] = str(inference_seed)
        if args.offline:
            env["TICVLA_DEMO_OFFLINE"] = "1"
        env.update(TICVLA_DEMO_RUN=str(run), TICVLA_DYNANAV_ROOT=str(ROOT / "work/DynaNav"),
                   TICVLA_OUTPUT_DIR=str(ROOT / "runs"),
                   PYTHONPATH=f"{ROOT / 'scripts'}:{ROOT / 'work/DynaNav'}:{ROOT / 'work'}:" + env.get("PYTHONPATH", ""))
        command = ["bash", str(ROOT / "work/DynaNav/run_benchmark.sh"), str(scenario_path),
                   "--run_id", run_id]
        meta = {"run_id": run_id, "started_unix": time.time(), "deadline_seconds": 600,
                "offline": args.offline,
                "camera_view": args.view,
                "instruction": instruction, "instruction_mode": "verbatim",
                "test_type": "native_metric_stop", "goal_termination_enabled": False,
                "automatic_backup_enabled": False, "distance_is_evaluation_only": True,
                "inference_seed": inference_seed,
                "request_sha256": request_sha256,
                "scenario_sha256": hashlib.sha256(scenario_path.read_bytes()).hexdigest(),
                "command": command, "source_manifest_sha256": hashlib.sha256((ROOT / "manifests/source.json").read_bytes()).hexdigest()}
        (ROOT / "runs/latest_run.txt").write_text(run_id + "\n")
        (run / "source.json").write_bytes((ROOT / "manifests/source.json").read_bytes())
        started = time.monotonic()
        timed_out = False
        with (run / "stdout.log").open("w") as stdout, (run / "stderr.log").open("w") as stderr, (run / "resources.jsonl").open("w") as resources:
            process = subprocess.Popen(command, cwd=ROOT / "work", env=env, stdout=stdout,
                                       stderr=stderr, start_new_session=True)
            meta.update(pid=process.pid, pgid=process.pid)
            (run / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
            print("DEMO_RUN", run_id, flush=True)
            try:
                while process.poll() is None:
                    if time.monotonic() - started > 600:
                        timed_out = True
                        break
                    gpu = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
                                         capture_output=True, text=True, timeout=5)
                    resources.write(json.dumps({"time_unix": time.time(), "gpu_csv": gpu.stdout.strip()}) + "\n")
                    resources.flush()
                    time.sleep(2)
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=10)
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                meta.update(exit_code=process.returncode, timed_out=timed_out,
                            wall_seconds=time.monotonic() - started, finished_unix=time.time())
                (run / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
        print(json.dumps(meta), flush=True)


if __name__ == "__main__":
    main()
