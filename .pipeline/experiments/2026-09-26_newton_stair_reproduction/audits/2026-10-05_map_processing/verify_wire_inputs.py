"""Read-only remote comparison of the original wire poses and replay witnesses."""
from pathlib import Path
import hashlib
import json
import math
import zipfile

root = Path("/home/sun/vla_artifacts/2026-10-04_corner_start/v76_mac_trial01_attempt01")
manifest = json.loads((root / "storage_manifest.json").read_text())
archive = root / "raw_capture.zip"
assert hashlib.sha256(archive.read_bytes()).hexdigest() == "0b09868a9652ee6807432f278b27593a098554a50ecddf48db5586d746b8dce8"
planner = (root / "planner.yaml").read_bytes()
assert hashlib.sha256(planner).hexdigest() == manifest["files"]["planner.yaml"]["sha256"]
records = {r["stamp_ns"]: r for r in map(json.loads, (root / "sensor.jsonl").read_text().splitlines())}
errors = []
clouds = []
with zipfile.ZipFile(archive) as capture:
    for line in capture.read("artifacts/reactive_observations.jsonl").decode().splitlines():
        event = json.loads(line)
        data = event["data"]
        if event["event"] == "lidar_pose":
            stamp = data["header"]["stamp"]
            ns = stamp["sec"] * 10**9 + stamp["nanosec"]
            if 29200000000 <= ns <= 29900000000 and ns in records:
                original = records[ns]["body_sensor"]
                p = data["pose"]["pose"]["position"]
                q = data["pose"]["pose"]["orientation"]
                errors.append({"stamp_ns": ns,
                    "xyz_error_m": math.dist([p["x"], p["y"], p["z"]], original["sensor_position"]),
                    "quaternion_max_error": max(abs(a-b) for a, b in zip([q["w"], q["x"], q["y"], q["z"]], original["sensor_quaternion"]))})
        elif event["event"] == "cloud" and 29200000000 <= data.get("stamp_ns", 0) <= 29900000000:
            assert data["width"] == records[data["stamp_ns"]]["sensor"]["point_count"]
            clouds.append(data)
assert len(errors) == len(clouds) == 7
assert all(row["xyz_error_m"] == row["quaternion_max_error"] == 0 for row in errors)
print(json.dumps({"passed": True, "planner_sha256": hashlib.sha256(planner).hexdigest(),
    "pose_witnesses": errors, "wire_clouds": clouds,
    "comparison": "Actual wire pose values/cloud widths match replay witnesses. Does not establish native callback batching or historical map state.",
    "gpu_job_started": False}, indent=2))
