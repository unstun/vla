"""Freeze v35's reviewed source and component evidence before its first physics."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import shutil

H = Path(__file__).resolve().parent
B = H.parents[1]
R = B.parents[2]
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
load = lambda path: json.loads(path.read_text())
assert not (H / "manifest.json").exists()
assert load(H / "source_checks.json")["passed"]
assert load(H / "contract/contract_results.json")["passed"]
assert load(H / "remote_sync/return_verification.json")["passed"]
for axis in ("spec", "standards"):
    review = load(H / f"reviews/{axis}.json")
    assert review["passed"] and not review["blocking_findings"], axis
parent = load(H.parent / "v34/manifest.json")
for name, digest in parent["source_files"].items():
    assert sha(R / name) == digest, name
    assert sha(H.parent / "v34/source" / name) == digest, name
prepared = load(H / "prepared.json")
N = R / prepared["native_build"]
reviewed = load(H / "native_source_sha256.json")
identity = load(B / "repairs/2026-09-26_generic_occupancy/candidate66_periodic_replan_v35_identity.json")
assert load(N / "source_sha256.json") == reviewed == prepared["source_sha256"] == identity["source_sha256"]
for name, digest in reviewed.items():
    assert sha(N / name) == digest, name
for name, digest in load(N / "install_sha256.json").items():
    assert sha(N / name) == digest, name
assert load(N / "build_result.json")["passed"]
for name in ("building_planner.yaml", "flat_planner.yaml"):
    original = (H.parent / "v34" / name).read_bytes()
    anchor = b"    fsm.thresh_replan: 1.0\n"
    assert original.count(anchor) == 1
    assert (H / name).read_bytes() == original.replace(anchor, anchor + b"    fsm.replan_frequency: 2.0\n")
test_sources = load(H / "contract/attempt_green04/request.json")["test_source_sha256"]
assert all(sha(H / "contract" / name) == digest for name, digest in test_sources.items())
selected = {R / name for name in parent["source_files"]}
selected.update(p for p in (N / "src").rglob("*") if p.is_file())
selected.update(N / name for name in ("source_sha256.json", "install_sha256.json", "build_result.json"))
excluded = {"source", "host", "probe_build", "__pycache__", "local_build_before_remote_return"}
mutable = {"RESULTS.md", "LOCAL_ONLY_BYTES.json", "quality_check.json", "manifest.json"}
for p in H.rglob("*"):
    parts = p.relative_to(H).parts
    if p.is_file() and not excluded.intersection(parts) and parts[0] not in mutable:
        selected.add(p)
G = B / "hosts/2026-09-29_gpu5070ti"
selected.update([G / "v35_trial_run.sh", G / "checks/p1_gates_v35.py",
    B / "repairs/2026-09-26_generic_occupancy/candidate66_periodic_replan_v35_identity.json"])
records = {}
for p in sorted(selected):
    name = str(p.relative_to(R))
    records[name] = sha(p)
    dest = H / "source" / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(p, dest)
manifest = {"version": "v35", "parent": "v34", "status": "frozen_unvalidated",
    "frozen_utc": datetime.now(timezone.utc).isoformat(), "source_files": records,
    "native_build": str(N.relative_to(R)), "source_snapshot_prefix": "source/",
    "change": "Nominal local replanning at configured 2 Hz, replacing displacement triggering; safety callbacks unchanged",
    "acceptance_plan": "PLAN.md", "trial_plan": "PHYSICAL_RUN_PLAN.md",
    "freeze_boundary": "After native build, actual-FSM contract, return identity and independent spec/standards reviews; before physics"}
(H / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"version": "v35", "source_files": len(records)}))
