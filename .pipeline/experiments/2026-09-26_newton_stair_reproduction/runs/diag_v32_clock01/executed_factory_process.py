"""Bounded local ARM64 process for the unchanged factory algorithm library."""

import json
import os
from pathlib import Path
import select
import subprocess
import time

from prepare_algorithm_inputs import ROOT, prepare

IMAGE = "sha256:1c102582b40d5305e310788c79e963e4b6cde13aea2bc5db3b7c1800e821935d"
REQUEST_BYTES = 928
REPLY_BYTES = 2200


class FactoryProcess:
    def __init__(self, output: Path, *, wall_limit=180):
        self.output = output
        output.mkdir(parents=True, exist_ok=False)
        prepare()
        self.name = f"vla-factory-algorithm-{os.getpid()}-{time.time_ns()}"
        self.started = time.monotonic()
        self.deadline = self.started + wall_limit
        self.process = None
        self.created = False
        self.log = (output / "stderr.log").open("wb")
        self.meta = {"image": IMAGE, "wall_limit": wall_limit, "scope": "local algorithm only",
                     "factory_library_sha256": "782a23d194f7e578b04f65beada1e003acd8d6be6a5b0fe1d115c8a77a542a3a"}
        command = [
            "docker", "create", "-i", "--pull", "never", "--name", self.name,
            "--network", "none", "--read-only", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", "--memory", "1g", "--cpus", "1",
            "--pids-limit", "64", "--user", f"{os.getuid()}:{os.getgid()}",
            "--tmpfs", "/tmp:rw,exec,nosuid,nodev,size=64m", "--workdir", "/snapshot/bin",
            "--env", "OMP_NUM_THREADS=1", "--env", "OPENBLAS_NUM_THREADS=1",
            "--env", "MKL_NUM_THREADS=1",
            "--env", "LD_LIBRARY_PATH=/snapshot/deps:/snapshot/lib/ras_lib",
            "--mount", f"type=bind,src={ROOT / 'private_snapshot'},dst=/snapshot,readonly",
            "--mount", f"type=bind,src={ROOT / 'factory_actor.cpp'},dst=/actor.cpp,readonly",
            "--entrypoint", "/bin/sh", IMAGE, "-c",
            "g++ -std=c++17 -O2 -Wall -Wextra -Werror /actor.cpp "
            "-Wl,--no-as-needed -pthread -lpthread -ldl -o /tmp/actor "
            "&& exec /tmp/actor /snapshot/algorithm_input/motion_config.bin "
            "/snapshot/algorithm_input/identity.txt",
        ]
        self.meta["create_command"] = command
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=15)
            self.created = True
            self.meta["container_id"] = result.stdout.strip()
            self.process = subprocess.Popen(["docker", "start", "-ai", self.name],
                                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=self.log, bufsize=0)
            if self.read(8, timeout=45) != b"VLAFACT1":
                raise RuntimeError("factory ready marker mismatch")
            self.meta["initialization_ok"] = True
        except BaseException as exc:
            self.meta["error"] = str(exc)
            self.close()
            raise

    def read(self, count, *, timeout=10):
        result = bytearray()
        deadline = min(self.deadline, time.monotonic() + timeout)
        while len(result) < count:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("factory process deadline")
            ready, _, _ = select.select([self.process.stdout], [], [], remaining)
            if not ready:
                raise TimeoutError("factory reply timeout")
            block = os.read(self.process.stdout.fileno(), count - len(result))
            if not block:
                raise RuntimeError("factory actor closed its output; inspect stderr.log")
            result.extend(block)
        return bytes(result)

    def step(self, request):
        if len(request) != REQUEST_BYTES:
            raise ValueError("bad request length")
        if time.monotonic() >= self.deadline:
            raise TimeoutError("factory process wall limit")
        self.process.stdin.write(request)
        self.process.stdin.flush()
        return self.read(REPLY_BYTES)

    def close(self):
        try:
            if self.process is not None:
                if self.process.stdin and not self.process.stdin.closed:
                    self.process.stdin.close()
                try:
                    self.meta["exit_code"] = self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.meta["timed_out"] = True
                    subprocess.run(["docker", "kill", self.name], capture_output=True, timeout=10)
                    self.meta["exit_code"] = self.process.wait(timeout=5)
            if self.created:
                inspected = subprocess.run(["docker", "inspect", self.name], capture_output=True,
                                           text=True, check=True, timeout=10)
                detail = json.loads(inspected.stdout)[0]
                self.meta.update(state=detail["State"], network_mode=detail["HostConfig"]["NetworkMode"],
                                 devices=detail["HostConfig"]["Devices"],
                                 read_only_rootfs=detail["HostConfig"]["ReadonlyRootfs"])
        finally:
            if self.created:
                cleanup = subprocess.run(["docker", "rm", "-f", self.name], capture_output=True, timeout=10)
                self.meta["cleanup_exit_code"] = cleanup.returncode
                self.created = False
            self.log.close()
            self.meta["wall_seconds"] = time.monotonic() - self.started
            (self.output / "process.json").write_text(json.dumps(self.meta, indent=2) + "\n")

    def __enter__(self):
        return self

    def __exit__(self, typ, value, trace):
        if value is not None:
            self.meta["error"] = str(value)
        self.close()
