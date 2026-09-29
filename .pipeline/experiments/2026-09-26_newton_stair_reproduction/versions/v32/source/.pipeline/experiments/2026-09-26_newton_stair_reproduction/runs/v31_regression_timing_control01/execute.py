"""Paired A* wall-time control for the v31 native regression.

The regression's A* searches have a 0.2 s wall-time budget, and the v31 runs
(runs/v31_native_regression01, under load; 02, alone) differed from v30 only
where a search crossed it or took longer. This control runs the four
timing-sensitive fixtures with the regression probes already built against v30
(runs/v30_native_regression01/probe_build, runtime scan62) and v31
(runs/v31_native_regression01/probe_build, runtime scan63), in alternating
containers (v30 first in odd repetitions, v31 first in even ones), five
repetitions each, with no other container running. Commands and inputs are the
regression's own (inside.sh). Writes execution.json.
"""
from pathlib import Path
import json, subprocess, time

P = Path(__file__).resolve().parent
E = P.parents[1]
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"
BUILDS = {"v30": ("runtime/scan62_support_evidence_v30", "runs/v30_native_regression01/probe_build", "versions/v30"),
          "v31": ("runtime/scan63_input_refresh_v31", "runs/v31_native_regression01/probe_build", "versions/v31")}
records = []
for rep in range(1, 6):
    for build in (["v30", "v31"] if rep % 2 else ["v31", "v30"]):
        assert not subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, check=True).stdout.strip()
        runtime, probe, version = BUILDS[build]
        name = f"{build}_rep{rep}"
        command = ["docker", "run", "--rm", "--pull=never", "--platform=linux/amd64", "--network=none", "--cpus=2",
                   "--memory=4g", "--name", f"vla-v31-timing-{name.replace('_', '-')}", "-e", "ROS_DOMAIN_ID=232",
                   "-e", "ROS_LOCALHOST_ONLY=1", "-e", f"VLA_REP={name}",
                   "-v", f"{E}:/archive:ro", "-v", f"{E / runtime}:/workspace:ro", "-v", f"{E / probe}:/probe:ro",
                   "-v", f"{E / version}:/version:ro", "-v", f"{P}:/attempt:rw",
                   "-v", f"{E}/audits/2026-09-27_v18_frontier/inputs:/moving:ro",
                   "-v", f"{E}/audits/2026-09-27_pct_precision/ground_precise.f32:/moving/ground.f32:ro",
                   "--entrypoint", "/bin/bash", IMAGE, "/attempt/inside.sh"]
        start = time.monotonic()
        result = subprocess.run(command, capture_output=True, text=True, timeout=900)
        records.append({"name": name, "build": build, "repetition": rep, "exit_code": result.returncode,
                        "wall_s": time.monotonic() - start, "stderr_tail": result.stderr[-500:], "command": command})
        print(name, result.returncode, round(time.monotonic() - start, 1), flush=True)
(P / "execution.json").write_text(json.dumps(records, indent=2) + "\n")
