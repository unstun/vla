from pathlib import Path
import json, subprocess, sys, time
p = Path(__file__).resolve().parent
name = sys.argv[1]
r = json.loads((p / f"request_{name}.json").read_text())
t = time.monotonic()
with (p / f"execution_{name}.log").open("w") as f:
    result = subprocess.run(r["command"], stdout=f, stderr=subprocess.STDOUT, timeout=r["deadline_s"])
(p / f"execution_{name}.json").write_text(json.dumps({"exit_code": result.returncode, "wall_s": time.monotonic() - t}, indent=2) + "\n")
print(result.returncode)
raise SystemExit(result.returncode)
