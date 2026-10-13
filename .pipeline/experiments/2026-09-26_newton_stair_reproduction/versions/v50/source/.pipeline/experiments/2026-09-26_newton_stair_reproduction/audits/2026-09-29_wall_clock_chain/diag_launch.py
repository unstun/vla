"""Diagnostic run of an unchanged frozen configuration with the instrumented worker (diag_worker.py).

Run under scripts/run_bounded.py exactly like a trial, with run_local_episode.py's own arguments after
this script's path. The only substitution: the Newton worker command `python scripts/newton_episode.py`
becomes `python diag_worker.py`, which runs the same pinned file after adding timing and stall stacks.
Around the episode this launcher also runs the external wake-up lateness probe (a separate process) and
samples host load, top processes and VM paging counters once per second into diagnostics/.
The planner container's `docker run` gains two environment variables: PYTHONPATH gets container_site/,
whose sitecustomize.py records each Python process's garbage collections and the bridge's body-state
receive/deliver times and publish-callback durations into diagnostics/linux/ (observation only).
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time

H = Path(__file__).resolve().parent
E = H.parents[1]
sys.path.insert(0, str(E / "scripts"))
import run_local_episode  # noqa: E402

episode = str(run_local_episode.BASE / "scripts/newton_episode.py")
original_run = subprocess.run


def run(args, *positional, **keywords):
    if isinstance(args, list) and args[1:] == [episode]:
        args = [args[0], str(H / "diag_worker.py")]
    return original_run(args, *positional, **keywords)


original_popen = subprocess.Popen
container_command = []


class Popen(original_popen):
    def __init__(self, args, *positional, **keywords):
        if isinstance(args, list) and args[:2] == ["docker", "run"] and "--entrypoint" in args:
            out = Path(os.environ["NEWTON_RUN_DIR"]) / "diagnostics/linux"
            index = args.index("--entrypoint")
            args = args[:index] + ["-e", "PYTHONPATH=" + str(H / "container_site"),
                                   "-e", "DIAG_CONTAINER_OUT=" + str(out)] + args[index:]
            container_command.append(args)
        super().__init__(args, *positional, **keywords)


def sample_host(path, stop):
    with open(path, "w") as f:
        while not stop.is_set():
            top = subprocess.run(["ps", "-Ao", "pcpu,pmem,comm", "-r"], capture_output=True, text=True).stdout.splitlines()[1:11]
            vm = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
            counters = {key: int(value) for key, value in re.findall(r'"?([A-Za-z ]+)"?:\s+(\d+)\.', vm)
                        if key.strip() in ("Pageins", "Pageouts", "Swapins", "Swapouts", "Pages free", "Decompressions",
                                           "Compressions")}
            f.write(json.dumps({"monotonic_ns": time.monotonic_ns(), "loadavg": os.getloadavg(), "vm": counters,
                                "top": [line.strip() for line in top]}) + "\n")
            f.flush()
            stop.wait(1.)


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    diagnostics = out / "diagnostics"
    diagnostics.mkdir(exist_ok=True)
    containers = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True, check=True)
    (diagnostics / "launch.json").write_text(json.dumps({
        "argv": sys.argv[1:], "containers_before": containers.stdout.split(),
        "worker_substitution": {"from": episode, "to": str(H / "diag_worker.py")}}, indent=2) + "\n")
    if containers.stdout.split():
        raise SystemExit("Other containers are running")
    stop = threading.Event()
    sampler = threading.Thread(target=sample_host, args=(diagnostics / "host.jsonl", stop), daemon=True)
    sampler.start()
    probe = subprocess.Popen([sys.executable, str(H / "probe_latency.py"), str(diagnostics / "probe_out.npy")])
    subprocess.run = run
    subprocess.Popen = Popen
    try:
        sys.argv = [str(E / "scripts/run_local_episode.py")] + sys.argv[1:]
        run_local_episode.main()
    finally:
        subprocess.run = original_run
        subprocess.Popen = original_popen
        (diagnostics / "container_command_actual.json").write_text(json.dumps(container_command, indent=2) + "\n")
        probe.terminate()
        probe.wait(timeout=10)
        stop.set()
        sampler.join(timeout=5)


if __name__ == "__main__":
    main()
