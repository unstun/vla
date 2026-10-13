"""Derive the v35 trial entry points from the reviewed, frozen v34 runner."""
from pathlib import Path
import hashlib
import json
import shutil

H = Path(__file__).resolve().parent
B = H.parents[1]
R = B.parents[2]
G = B / "hosts/2026-09-29_gpu5070ti"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
substitutions = [("runtime/scan65_evidence_floor_v34", "runtime/scan66_periodic_replan_v35"), ("v34", "v35")]
records = {}
for name in ("v34_trial_run.sh", "checks/p1_gates_v34.py"):
    source = G / name
    target = G / name.replace("v34", "v35")
    assert not target.exists()
    old = source.read_bytes()
    new = old
    for before, after in substitutions:
        new = new.replace(before.encode(), after.encode())
    assert b"v34" not in new and b"scan65" not in new
    target.write_bytes(new)
    records[name] = {"source_sha256": sha(source), "target": str(target.relative_to(R)),
                     "target_sha256": sha(target), "substitutions_only": True}
native = json.loads((H / "prepared.json").read_text())["native_build"]
identity = B / "repairs/2026-09-26_generic_occupancy/candidate66_periodic_replan_v35_identity.json"
assert not identity.exists()
identity.write_text(json.dumps({"integration_version": "v35", "parent": "v34",
    "native_build": native, "source_sha256": json.loads((H / "native_source_sha256.json").read_text()),
    "review_gate": "versions/v35/freeze.py requires both independent read-only review axes to pass",
    "claim": "Periodic local scheduling component-tested; navigation unvalidated"}, indent=2) + "\n")
shutil.copyfile(H / "RESULTS.md", H / "COMPONENT_RESULTS.md")
(H / "trial_derivation.json").write_text(json.dumps(records, indent=2) + "\n")
print(json.dumps(records, indent=2))
