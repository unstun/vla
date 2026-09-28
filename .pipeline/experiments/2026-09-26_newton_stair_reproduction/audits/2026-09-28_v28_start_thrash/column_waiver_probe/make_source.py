"""Diagnostic counterfactual: point semantics plus a self-occlusion column.

Copies ../optimizer_trace/workspace (v28 with the known-footprint waiver tested
at the queried point, plus VLA_TRACE-gated tracing) and changes only the
vertical test of knownNavigationFootprintInterior. The measured-trunk band
|local z - 0.01| <= 0.06 becomes -0.05 <= local z <= 0.1085, where 0.1085 m is
the LiDAR origin's height above the body reference in the standing control
state (optimizer_trace/voxel_dump/control, sensor pose and body pose from the
same replay). The footprint circles, the Unknown and inflation tests, and the
torso-box function are unchanged. This tests whether never-observed cells
between the trunk band and the sensor cause the remaining optimizer failure.
Not a version and not a proposed threshold.
"""
from pathlib import Path
import hashlib, json, shutil

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "optimizer_trace"
TARGET = "src/plan_env/include/plan_env/known_lite3_trunk.h"
OLD = "  return dx * dx + y * y <= radius * radius && std::abs(z - 0.01) <= 0.06;\n"
NEW = "  return dx * dx + y * y <= radius * radius && z >= -0.05 && z <= 0.1085;\n"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert not (HERE / "workspace").exists()
for part in ("src", "build", "install"):
    shutil.copytree(PARENT / "workspace" / part, HERE / "workspace" / part, symlinks=True)
shutil.copytree(PARENT / "probe_source", HERE / "probe_source")
path = HERE / "workspace" / TARGET
before = path.read_bytes()
text = before.decode()
assert text.count(OLD) == 1
path.write_text(text.replace(OLD, NEW))
(HERE / "diagnostic_change.json").write_text(json.dumps({
    "parent_tree": "audits/2026-09-28_v28_start_thrash/optimizer_trace/workspace (point semantics + trace)",
    "file": "workspace/" + TARGET, "before_sha256": hashlib.sha256(before).hexdigest(), "after_sha256": sha(path),
    "change": "Known navigation footprint vertical test: |z - 0.01| <= 0.06 -> -0.05 <= z <= 0.1085 (body frame, queried point).",
    "status": "Diagnostic counterfactual only; not a version and not a proposed threshold."}, indent=2) + "\n")
print("prepared")
