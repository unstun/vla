"""Never-observed voxels around the robot, and the LiDAR mount from the pinned URDF.

Reads the local-only result_voxels.csv dumps (stopped and control) and the
[VOXEL-DUMP] line of each probe.log. A voxel is Unknown when its log-odds is
below clamp_min_log - 1e-3, the same test as GridMap::reactiveOccupancy.
Writes blind_zone.json.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parents[3]
URDF = EXPERIMENT / "inputs/sensor_rig/lite3_pro_sensor_rig_real_with_interface_isaac.urdf"


def rotation(roll, pitch, yaw):
    cr, sr, cp, sp, cy, sy = (math.cos(roll), math.sin(roll), math.cos(pitch), math.sin(pitch),
                              math.cos(yaw), math.sin(yaw))
    return np.array([[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
                     [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
                     [-sp, cp * sr, cp * cr]])


def quaternion(x, y, z, w):
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mount():
    joints = {joint.find("child").get("link"): joint for joint in ET.parse(URDF).getroot().findall("joint")}
    link, chain, transform = "mid360_scan_frame", [], np.eye(4)
    while link in joints:
        joint = joints[link]
        chain.append(joint)
        link = joint.find("parent").get("link")
    names = []
    for joint in reversed(chain):
        origin = joint.find("origin")
        step = np.eye(4)
        step[:3, :3] = rotation(*map(float, (origin.get("rpy") or "0 0 0").split()))
        step[:3, 3] = list(map(float, (origin.get("xyz") or "0 0 0").split()))
        transform = transform @ step
        names.append(joint.get("name"))
    return {"urdf": str(URDF.relative_to(EXPERIMENT)), "urdf_sha256": hashlib.sha256(URDF.read_bytes()).hexdigest(),
            "root_link": link, "joints": names, "origin_in_root_m": transform[:3, 3].round(5).tolist(),
            "nose_down_pitch_deg": round(math.degrees(math.asin(-transform[2, 0])), 3)}


def table(state):
    line = next(l for l in (HERE / state / "probe.log").read_text().splitlines() if l.startswith("[VOXEL-DUMP]"))
    numbers = re.search(r"clamp_min_log=(\S+).*body_q=\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+body=\s*(\S+)\s+(\S+)\s+(\S+)"
                        r"\s+sensor=\s*(\S+)\s+(\S+)\s+(\S+)", line).groups()
    clamp_min = float(numbers[0])
    rot = quaternion(*map(float, numbers[1:5]))  # Eigen coeffs() order: x, y, z, w.
    body, sensor = np.array(list(map(float, numbers[5:8]))), np.array(list(map(float, numbers[8:11])))
    dump = HERE / state / "result_voxels.csv"
    counts = {}
    for row in csv.DictReader(dump.open()):
        centre = np.array([float(row["cx"]), float(row["cy"]), float(row["cz"])])
        local = rot.T @ (centre - body)
        if abs(local[1]) > 0.35:
            continue
        cell = counts.setdefault("%.3f" % centre[2], {}).setdefault("%+.1f" % (math.floor(local[0] / 0.2) * 0.2), [0, 0])
        cell[0] += float(row["log_odds"]) < clamp_min - 1e-3
        cell[1] += 1
    layers = {z: {band: round(unknown / total, 2) for band, (unknown, total) in sorted(bands.items(), key=lambda kv: float(kv[0]))}
              for z, bands in sorted(counts.items()) if 0.2 < float(z) < 0.6}
    return {"voxel_dump": str(dump.relative_to(EXPERIMENT)), "voxel_dump_sha256": hashlib.sha256(dump.read_bytes()).hexdigest(),
            "body_z_m": body[2], "sensor_in_body_frame_m": (rot.T @ (sensor - body)).round(4).tolist(),
            "unknown_fraction_by_world_layer_centre_and_body_x_band_start": layers}


summary = {"lidar_mount": mount(),
           "selection": "voxels with |body-frame y| <= 0.35 m; columns are 0.2 m body-frame x bands, named by their start",
           "states": {state: table(state) for state in ("stopped", "control")}}
(HERE / "blind_zone.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary["lidar_mount"], indent=2))
for state, item in summary["states"].items():
    print(state, "body z", round(item["body_z_m"], 4), "sensor in body", item["sensor_in_body_frame_m"])
    for z, bands in item["unknown_fraction_by_world_layer_centre_and_body_x_band_start"].items():
        print("  ", z, " ".join("%s:%.2f" % (band, value) for band, value in bands.items()))
