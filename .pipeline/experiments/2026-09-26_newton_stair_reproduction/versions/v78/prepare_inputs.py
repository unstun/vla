"""Convert the exact archived measurements using the established float32 wire layout."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import io
import json
import pickle
import shutil
import subprocess
import sys
import zipfile
import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
parser = argparse.ArgumentParser()
parser.add_argument("--capture", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=False)
with zipfile.ZipFile(args.capture) as capture:
    identity = json.loads(capture.read("identity.json"))
    records = json.loads(capture.read("sensor_records.json"))
    listing = []
    for r in records:
        i = r["sensor"]["scan_window"]["scan_index"]
        data = capture.read(r["file"])
        assert hashlib.sha256(data).hexdigest() == identity["source_members"][r["file"]]["sha256"]
        points = np.asarray(np.load(io.BytesIO(data), allow_pickle=False)["sensor_points"], dtype="<f4")
        assert points.shape == (r["sensor"]["point_count"], 3)
        (args.output / f"cloud_{i:05d}.f32").write_bytes(points.tobytes())
        body = r["body_sensor"]
        for name, position, quaternion in (("body", body["position"], body["quaternion"]), ("sensor", body["sensor_position"], body["sensor_quaternion"])):
            w, x, y, z = quaternion
            (args.output / f"{name}_{i:05d}.txt").write_text(" ".join(map(repr, [*position, x, y, z, w])) + "\n")
        listing.append(f"{i} {r['stamp_ns']} body_{i:05d}.txt sensor_{i:05d}.txt cloud_{i:05d}.f32")
    (args.output / "scans.txt").write_text("\n".join(listing) + "\n")
    (args.output / "original_spike.log").write_bytes(capture.read("original_spike.log"))

info = json.loads((BASE / "versions/v76/physical_floor_input.json").read_text())
producer = ROOT / info["producer"]["path"]
assert sha(producer) == info["producer"]["sha256"]
spec = importlib.util.spec_from_file_location("pinned_ground_producer", producer)
core = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = core
spec.loader.exec_module(core)
source = pickle.loads((BASE / "inputs/new_building.pickle").read_bytes())
precise = np.load(BASE / "inputs/new_building_original_precision.npz", allow_pickle=False)["data"]
navigation = core.selected_ground_points(source, paired_elevations=precise[3]).astype("<f4").tobytes()
assert hashlib.sha256(navigation).hexdigest() == info["navigation_payload_sha256"]
(args.output / "navigation.f32").write_bytes(navigation)
shutil.copyfile(BASE / "audits/2026-09-27_dense_static_sampling/raw_ground.f32", args.output / "surface.f32")
assert sha(args.output / "surface.f32") == info["selected_surface_payload_sha256"]
subprocess.run([sys.executable, str(BASE / "versions/v76/derive_mac_floor.py"), "--output", str(args.output / "physical_floor.f32")], check=True)
identity.update(capture_zip_sha256=sha(args.capture), prepared_files={p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in args.output.iterdir() if p.is_file()}, scope="Recorded scan/body/sensor sequence with exact paired support inputs. Observer scan history, not native DDS take batching or full planner-state restoration.")
(args.output / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
print(json.dumps({"scans": len(records), "prepared_bytes": sum(p.stat().st_size for p in args.output.iterdir() if p.is_file()), "paired_support_hashes_verified": True}))
