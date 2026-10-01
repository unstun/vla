"""Run execute.py here while sampling the Docker VM's containers every 5 s; writes alone_check.json."""
from datetime import datetime, timezone
from pathlib import Path
import json, subprocess, sys, threading

P = Path(__file__).resolve().parent
command = json.loads((P / "request.json").read_text())["command"]
own = command[command.index("--name") + 1]
samples, done = [], threading.Event()


def sample():
    while not done.is_set():
        names = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True).stdout.split()
        samples.append({"utc": datetime.now(timezone.utc).isoformat(), "containers": names})
        done.wait(5)


thread = threading.Thread(target=sample)
thread.start()
result = subprocess.run([sys.executable, str(P / "execute.py")])
done.set()
thread.join()
others = [s for s in samples if any(name != own for name in s["containers"])]
(P / "alone_check.json").write_text(json.dumps({
    "container": own, "interval_s": 5, "samples": len(samples), "samples_with_other_containers": len(others),
    "other_containers_seen": sorted({n for s in others for n in s["containers"] if n != own}),
    "samples_with_own_container": sum(own in s["containers"] for s in samples),
    "first_utc": samples[0]["utc"] if samples else None, "last_utc": samples[-1]["utc"] if samples else None,
    "execute_exit_code": result.returncode}, indent=2) + "\n")
raise SystemExit(result.returncode)
