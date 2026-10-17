"""Check that the trial publishes exactly the grounds the contract scored: python3 runtime_input_identity.py.

scripts/native_graph.py starts pct_sim_clock_publisher.py twice for the
Building: /pct_tomogram from inputs/new_building.pickle with the original-
precision elevations, and /pct_ground_surface from
inputs/new_building_dense_surface.npy. This rebuilds both payloads with the
publisher's own functions and compares their bytes with the contract inputs.
Writes runtime_input_identity.json.
"""
from pathlib import Path
import hashlib, json, sys

import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[2]
sys.path.insert(0, str(BASE / "runtime_sources/bridge"))
from lite3_sim_bridge import pct_sim_clock_core as core  # noqa: E402

source = core.load_pinned_map(BASE / "inputs/new_building.pickle")
elevations = core.load_paired_elevations(BASE / "inputs/new_building_original_precision.npz", source)
published = {
    "navigation /pct_tomogram": (core.selected_ground_points(source, "identity", 0.03, cost_limit=20.0, paired_elevations=elevations),
                                 BASE / "audits/2026-09-27_pct_precision/ground_precise.f32"),
    "surface evidence /pct_ground_surface": (core.load_dense_surface_points(BASE / "inputs/new_building_dense_surface.npy"),
                                             BASE / "audits/2026-09-27_dense_static_sampling/raw_ground.f32"),
}
report = {}
for topic, (points, contract_input) in published.items():
    payload = core.cloud_payload(points, 1, "world").data
    report[topic] = {"published_points": len(points), "published_sha256": hashlib.sha256(payload).hexdigest(),
                     "contract_input": str(contract_input.relative_to(BASE)),
                     "contract_input_sha256": hashlib.sha256(contract_input.read_bytes()).hexdigest(),
                     "identical": payload == contract_input.read_bytes()}
report = {"passed": all(r["identical"] for r in report.values()), "topics": report}
(HERE / "runtime_input_identity.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=1))
