"""Preserve v27 and restore only scan_27's finite paired rebound-constraint handling.

The generic materializer's --native-optimizer restore copied the pinned scan_04
optimizer over the scan33 lineage and silently dropped scan_27's guard. v28
re-applies exactly the frozen scan_26 -> scan_27 optimizer hunks. Each hunk must
occur once in v27, and the rewritten assignment and rebound blocks must then be
byte-identical to frozen scan_27. Every other v27 byte stays unchanged.
"""
from pathlib import Path
import difflib
import hashlib
import json
import re
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
OLD = BASE / "runtime/scan59_seed_shortcut_v27"
NEW = BASE / "runtime/scan60_constraint_guard_v28"
P2B = BASE.parent / "2026-09-16_pi_cortex_harnessvln/p2b_execution"
SCAN26, SCAN27 = P2B / "builds/scan_26", P2B / "builds/scan_27"
GENERATOR = P2B / "reactive_stair/materialize_scan_27.py"
OPTIMIZER = "src/bspline_opt/src/bspline_optimizer.cpp"
HELPER = "src/bspline_opt/include/bspline_opt/rebound_constraint_utils.h"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def lines(data):
    return re.split(rb"(?<=\n)", data)


def region(data, start, end):
    left = data.index(start)
    return data[left:data.index(end, left)]


def helper_functions(data):
    # validReboundSlot, appendReboundConstraint and copyReboundConstraint.
    return region(data, b"template <typename ControlPoints>\nbool validReboundSlot", b"}  // namespace reactive_stair")


def guarded_blocks(data):
    return (region(data, b"    /*** Assign data to each segment ***/", b"  int BsplineOptimizer::earlyExit"),
            region(data, b"  bool BsplineOptimizer::check_collision_and_rebound", b"  bool BsplineOptimizer::BsplineOptimizeTrajRebound"))


parent = json.loads((HERE.parent / "v27/manifest.json").read_text())
assert not NEW.exists() and not (HERE / "prepared.json").exists()
for name, digest in parent["source_files"].items():
    assert sha(ROOT / name) == digest, name
native = json.loads((OLD / "source_sha256.json").read_text())
for name, digest in native.items():
    assert sha(OLD / name) == digest, name
for build in (SCAN26, SCAN27):
    for name, digest in json.loads((build / "source_sha256.json").read_text()).items():
        assert sha(build / name) == digest, (build.name, name)
    assert json.loads((build / "build_result.json").read_text())["passed"], build.name
guard = json.loads((SCAN27 / "rebound_validity_manifest.json").read_text())
assert guard["base"] == "scan_26" and guard["generator_sha256"] == sha(GENERATOR)
assert guard["base_manifest_sha256"] == sha(SCAN26 / "source_sha256.json")
assert guard["changed_sha256"] == {HELPER: sha(SCAN27 / HELPER), OPTIMIZER: sha(SCAN27 / OPTIMIZER)}
# v27 already carries the helper; the three functions the guard calls must match scan_27.
assert helper_functions((OLD / HELPER).read_bytes()) == helper_functions((SCAN27 / HELPER).read_bytes())

shutil.copytree(OLD / "src", NEW / "src")
path = NEW / OPTIMIZER
before = path.read_bytes()
old26, new27 = lines((SCAN26 / OPTIMIZER).read_bytes()), lines((SCAN27 / OPTIMIZER).read_bytes())
text, applied = before, []
matcher = difflib.SequenceMatcher(a=old26, b=new27, autojunk=False)
for group in matcher.get_grouped_opcodes(3):
    old_hunk = b"".join(old26[group[0][1]:group[-1][2]])
    new_hunk = b"".join(new27[group[0][3]:group[-1][4]])
    assert text.count(old_hunk) == 1, old_hunk[:120]
    text = text.replace(old_hunk, new_hunk)
    applied.append({"scan26_lines": [group[0][1] + 1, group[-1][2]], "scan27_lines": [group[0][3] + 1, group[-1][4]]})
assert guarded_blocks(text) == guarded_blocks((SCAN27 / OPTIMIZER).read_bytes())
# Outside the two guarded blocks and the include, v28 keeps v27's bytes exactly.
strip = lambda data: data.replace(b"#include <bspline_opt/rebound_constraint_utils.h>\n", b"", 1).replace(
    guarded_blocks(data)[0], b"").replace(guarded_blocks(data)[1], b"")
assert strip(text) == strip(before) and text != before
path.write_bytes(text)

preimage = HERE / "parent_source" / OPTIMIZER
preimage.parent.mkdir(parents=True)
preimage.write_bytes(before)
(HERE / "changes.patch").write_bytes("".join(difflib.unified_diff(
    before.decode().splitlines(True), text.decode().splitlines(True),
    fromfile="v27/" + OPTIMIZER, tofile="v28/" + OPTIMIZER)).encode())
manifest = {str(p.relative_to(NEW)): sha(p) for p in sorted((NEW / "src").rglob("*")) if p.is_file()}
assert set(manifest) == set(native) and {name for name in manifest if manifest[name] != native[name]} == {OPTIMIZER}
(NEW / "source_sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
identity = BASE / "repairs/2026-09-26_generic_occupancy/candidate60_constraint_guard_v28_identity.json"
identity.write_text(json.dumps({
    "source_sha256": manifest, "integration_version": "v28",
    "restored_from": {"generator": str(GENERATOR.relative_to(ROOT)), "generator_sha256": sha(GENERATOR),
                      "scan26_optimizer_sha256": sha(SCAN26 / OPTIMIZER), "scan27_optimizer_sha256": sha(SCAN27 / OPTIMIZER),
                      "hunks": applied},
    "claim": "Unvalidated restoration of scan_27 finite paired rebound constraints; search, costs, thresholds and final gates unchanged"},
    indent=2) + "\n")
for name in ("building_planner.yaml", "flat_planner.yaml"):
    shutil.copyfile(HERE.parent / "v27" / name, HERE / name)
(HERE / "prepared.json").write_text(json.dumps({
    "parent": "v27", "status": "unfrozen_candidate", "native_build": str(NEW.relative_to(ROOT)),
    "changed_files": [str(path.relative_to(ROOT)), str(identity.relative_to(ROOT))],
    "native_parent": str(OLD.relative_to(ROOT)), "restored_generator_sha256": sha(GENERATOR),
    "applied_hunks": len(applied)}, indent=2) + "\n")
print(json.dumps({"v28": "native candidate prepared; acceptance pending", "hunks": len(applied)}))
