"""Run the fill contract against one native tree: python3 run.py <label> <native_tree_dir>.

Adapted from versions/v30/support_contract/run.py. Compiles fill_contract/source against the tree inside the pinned
image, then applies the tree's rule to the synthetic cases and the pinned Building grounds (fill_contract) and
replays the node delivery orders (fill_order_contract). Writes <label>/{request.json,inside.sh,execution.json,...}.
"""
from pathlib import Path
import json
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[2]
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"
NAV = "/archive/audits/2026-09-27_pct_precision/ground_precise.f32"
EVIDENCE = "/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32"

label, tree = sys.argv[1], Path(sys.argv[2]).resolve()
assert json.loads((tree / "build_result.json").read_text())["passed"]
out = HERE / label
out.mkdir()
lines = ["set -e", "source /opt/ros/humble/setup.bash", "source /workspace/install/setup.bash",
         "cmake -S /contract -B /attempt/build -DCMAKE_BUILD_TYPE=Release > /attempt/build.log 2>&1",
         "cmake --build /attempt/build -j2 >> /attempt/build.log 2>&1",
         "set +e",
         f"/attempt/build/fill_contract /version/fill_contract/cases.txt {NAV} {EVIDENCE} /attempt > /attempt/fill.log 2>&1",
         "echo $? > /attempt/fill_exit_code.txt"]
for order in ("nav_first", "evidence_first"):
    lines += [f"env VLA_ORDER={order} VLA_NAVIGATION_GROUND={NAV} VLA_SURFACE_EVIDENCE={EVIDENCE} "
              f"VLA_CONTRACT_OUTPUT=/attempt/order_{order}.json /attempt/build/fill_order_contract "
              f"--ros-args --params-file /version/building_planner.yaml > /attempt/order_{order}.log 2>&1",
              f"echo $? > /attempt/order_{order}_exit_code.txt"]
lines.append("set -e")
(out / "inside.sh").write_text("\n".join(lines) + "\n")
request = {"command": ["docker", "run", "--rm", "--pull=never", "--platform=linux/amd64", "--network=none", "--cpus=3", "--memory=6g",
                       "--name", "vla-v34-fill-contract-" + label.replace("_", "-"),
                       "-e", "ROS_DOMAIN_ID=232", "-e", "ROS_LOCALHOST_ONLY=1",
                       "-v", f"{BASE}:/archive:ro", "-v", f"{tree}:/workspace:ro", "-v", f"{BASE / 'versions/v34'}:/version:ro",
                       "-v", f"{HERE / 'source'}:/contract:ro", "-v", f"{out}:/attempt:rw",
                       "--entrypoint", "/bin/bash", IMAGE, "/attempt/inside.sh"],
           "deadline_s": 1800, "native_tree": str(tree.relative_to(BASE.parents[2])),
           "claim": "Evidence floor fill contract (versions/v34/PLAN.md K2) against one native tree: synthetic cases, pinned Building grounds and node delivery orders."}
(out / "request.json").write_text(json.dumps(request, indent=2) + "\n")
started = time.monotonic()
with (out / "execution.log").open("w") as log:
    result = subprocess.run(request["command"], stdout=log, stderr=subprocess.STDOUT, timeout=request["deadline_s"])
(out / "execution.json").write_text(json.dumps({"exit_code": result.returncode, "wall_s": time.monotonic() - started}, indent=2) + "\n")
print(label, result.returncode)
raise SystemExit(result.returncode)
