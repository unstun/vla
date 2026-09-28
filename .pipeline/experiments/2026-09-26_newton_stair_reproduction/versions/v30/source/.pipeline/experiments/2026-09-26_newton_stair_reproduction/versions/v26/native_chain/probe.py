"""Exercise the actual TCP worker using the captured physical-run request."""
from dataclasses import replace
import importlib.util
import json
import math
from pathlib import Path
import threading

from backend_adapter.contracts import PlannerRequest
from backend_adapter.pct_ipc import PctIpcClient, PctIpcClientConfig
from backend_adapter.pct_worker import NativePctConfig, NativePctPlanner, PctWorkerServer
from p2b_backend_ros.config import load_runtime_config
from p2b_backend_ros.node import LayeredPctClient

BASE = Path("/base")
OUT = Path("/audit")
OLD = BASE / "versions/v26/parent_source/runtime_sources/backend_ros/p2b_backend_ros/config.py"
spec = importlib.util.spec_from_file_location("old_config", OLD)
old_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_config)


class RecordedNativePlanner(NativePctPlanner):
    def __init__(self):
        super().__init__(NativePctConfig(
            BASE / "runtime_sources/pct_runtime/python", str(BASE / "inputs"),
            tomogram_path=str(BASE / "inputs/new_building.pickle")), reference_height_m=.30)
        self.received = []

    def plan(self, request):
        row = {"request": request.to_wire()}
        self.received.append(row)
        route = super().plan(request)
        row["route"] = route.to_wire()
        return route


captured = json.loads((BASE / "runs/v25_historical_full01/backend_latest.json").read_text())
captured_request = captured["pct"]["plan_history"][0]["request"]
request = replace(PlannerRequest.from_mapping(captured_request), start_layer=None, target_layer=None)
config_path = BASE / "runs/v25_historical_full01/backend_config.json"
adapter_path = OUT / "adapter_explicit_null.json"
adapter_path.write_text(json.dumps({"schema": "p2b_backend_adapter_config_v2",
                                  "pilot_contract": {"pct_layer": None}}))
planner = RecordedNativePlanner()
server = PctWorkerServer(("127.0.0.1", 0), planner)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
client = PctIpcClient(PctIpcClientConfig(port=server.server_address[1]))
rows = {}
result = {"passed": False, "captured_request": captured_request,
          "service_request_without_forced_layers": request.to_wire(),
          "transport": "actual loopback TCP JSON-line worker", "cases": rows}
try:
    cases = [
        ("old_loader", old_config.load_runtime_config(config_path), request),
        ("new_loader", load_runtime_config(config_path), request),
        ("explicit_fixed_layer", load_runtime_config(config_path, {"map": {"pct_layer": 1}}), request),
        ("adapter_explicit_null", load_runtime_config(adapter_path), request),
        ("automatic_config_explicit_request", load_runtime_config(config_path),
         replace(request, start_layer=1, target_layer=1)),
        ("fixed_config_explicit_request", load_runtime_config(config_path, {"map": {"pct_layer": 2}}),
         replace(request, start_layer=1, target_layer=1)),
    ]
    for name, resolved, current_request in cases:
        layered = LayeredPctClient(client, resolved["map"]["pct_layer"])
        route = layered.plan(current_request)
        snapshot = layered.snapshot()
        received = planner.received[-1]
        assert received["request"] == snapshot["plan_history"][0]["request"]
        assert received["route"] == route.to_wire()
        points = route.waypoints_m
        rows[name] = {
            "resolved_config": resolved, "runtime_snapshot": snapshot,
            "worker_received": received, "route": route.to_wire(),
            "point_count": len(points),
            "xy_length_m": sum(math.hypot(b[0]-a[0], b[1]-a[1]) for a, b in zip(points, points[1:])),
            "last_xyz_m": list(points[-1]),
        }
        (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    for name in ("old_loader", "explicit_fixed_layer", "automatic_config_explicit_request", "fixed_config_explicit_request"):
        row = rows[name]
        assert row["worker_received"]["request"]["start_layer"] == 1
        assert row["worker_received"]["request"]["target_layer"] == 1
        assert row["point_count"] == 145 and 17. < row["xy_length_m"] < 18.
        assert abs(row["last_xyz_m"][2] - 1.860560393) < 1e-7
        assert row["route"]["waypoints_m"] == rows["old_loader"]["route"]["waypoints_m"]
    for name in ("new_loader", "adapter_explicit_null"):
        row = rows[name]
        assert row["resolved_config"]["map"]["pct_layer"] is None
        assert row["worker_received"]["request"]["start_layer"] is None
        assert row["worker_received"]["request"]["target_layer"] is None
        assert 70. < row["xy_length_m"] < 80.
        assert abs(row["last_xyz_m"][2] - request.target_xyz_m[2] - .30) < .02
        assert math.dist(row["last_xyz_m"][:2], request.target_xyz_m[:2]) < .001
        assert row["route"]["waypoints_m"] == rows["new_loader"]["route"]["waypoints_m"]
    result["passed"] = True
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2.)
    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "cases": {
        name: {key: row[key] for key in ("point_count", "xy_length_m", "last_xyz_m")}
        for name, row in rows.items()}}, indent=2))
