"""Execute the pinned native PCT route on original stair endpoints."""
import hashlib
import json
from pathlib import Path
import sys
from dataclasses import asdict

from backend_adapter.pct_worker import NativePctConfig, NativePctPlanner
from backend_adapter.contracts import PlannerRequest

base = Path("/repro")
out = base / "setup" / sys.argv[1]
out.mkdir(exist_ok=False)
scene = json.loads((base / "inputs/stair_scenario.json").read_text())
planner = NativePctPlanner(NativePctConfig(base / "runtime_sources/pct_runtime/python", "/repro/inputs",
                                          tomogram_path="/repro/inputs/new_building.pickle"), reference_height_m=.3)
print("Native PCT initialized", flush=True)
print("PlannerRequest", PlannerRequest.__dataclass_fields__.keys(), flush=True)
(out / "import.json").write_text(json.dumps({"initialized": True,
    "model": "new_building.pickle", "reference_height_m": .3,
    "request_fields": list(PlannerRequest.__dataclass_fields__)}, indent=2) + "\n")
request = PlannerRequest("newton-probe", "stair-goal", tuple(scene["spawn_ground_xyz_m"]),
                         tuple(scene["goal_ground_xyz_m"]), "world", "stair_reactive", 1,
                         start_layer=1, target_layer=1, optimize=True)
route = planner.plan(request)
(out / "route.json").write_text(json.dumps(asdict(route), indent=2) + "\n")
print("Native route", len(route.waypoints_m), route.waypoints_m[0], route.waypoints_m[-1], flush=True)
