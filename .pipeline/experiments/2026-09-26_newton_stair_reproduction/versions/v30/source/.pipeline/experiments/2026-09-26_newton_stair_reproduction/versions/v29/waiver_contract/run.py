"""Run the waiver contract against one native tree: python3 run.py <label> <native_tree_dir>.

Compiles waiver_contract/source against the tree inside the pinned image and
replays three frozen states from audits/2026-09-28_v28_start_thrash. Writes
<label>/{request.json,inside.sh,execution.json,build.log,<state>.json,...}.
"""
from pathlib import Path
import json
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[2]
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"
STATES = {"stopped": "stopped/inputs", "z_0p3650": "height_sweep/z_0p3650/inputs", "control": "control/inputs"}

label, tree = sys.argv[1], Path(sys.argv[2]).resolve()
assert json.loads((tree / "build_result.json").read_text())["passed"]
out = HERE / label
out.mkdir()
lines = ["set -e", "source /opt/ros/humble/setup.bash", "source /workspace/install/setup.bash",
         "cmake -S /contract -B /attempt/build -DCMAKE_BUILD_TYPE=Release > /attempt/build.log 2>&1",
         "cmake --build /attempt/build -j2 --target waiver_contract >> /attempt/build.log 2>&1"]
for name, inputs in STATES.items():
    lines += ["set +e",
              f"env VLA_RAW_GROUND=/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32 "
              f"VLA_CONTRACT_INPUT=/archive/audits/2026-09-28_v28_start_thrash/{inputs} VLA_CONTRACT_OUTPUT=/attempt/{name}.json "
              f"/attempt/build/waiver_contract --ros-args --params-file /version/building_planner.yaml > /attempt/{name}.log 2>&1",
              f"echo $? > /attempt/{name}_exit_code.txt", "set -e"]
(out / "inside.sh").write_text("\n".join(lines) + "\n")
request = {"command": ["docker", "run", "--rm", "--pull=never", "--platform=linux/amd64", "--network=none", "--cpus=3", "--memory=6g",
                       "--name", "vla-v29-waiver-contract-" + label.replace("_", "-"),
                       "-e", "ROS_DOMAIN_ID=232", "-e", "ROS_LOCALHOST_ONLY=1",
                       "-v", f"{BASE}:/archive:ro", "-v", f"{tree}:/workspace:ro", "-v", f"{BASE / 'versions/v29'}:/version:ro",
                       "-v", f"{HERE / 'source'}:/contract:ro", "-v", f"{out}:/attempt:rw",
                       "--entrypoint", "/bin/bash", IMAGE, "/attempt/inside.sh"],
           "deadline_s": 1800, "native_tree": str(tree.relative_to(BASE.parents[2])),
           "claim": "Known-footprint waiver contract (versions/v29/PLAN.md step 2) against one native tree; frozen saved states only."}
(out / "request.json").write_text(json.dumps(request, indent=2) + "\n")
started = time.monotonic()
with (out / "execution.log").open("w") as log:
    result = subprocess.run(request["command"], stdout=log, stderr=subprocess.STDOUT, timeout=request["deadline_s"])
(out / "execution.json").write_text(json.dumps({"exit_code": result.returncode, "wall_s": time.monotonic() - started}, indent=2) + "\n")
print(label, result.returncode)
raise SystemExit(result.returncode)
