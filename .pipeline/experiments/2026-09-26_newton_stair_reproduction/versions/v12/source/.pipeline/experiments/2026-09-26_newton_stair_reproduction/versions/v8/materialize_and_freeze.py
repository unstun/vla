"""One immutable terrain-neighborhood change on verified v7 source."""
from datetime import datetime, timezone
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
PARENT = BASE / "runtime/scan46_cruise_v7"
TARGET = BASE / "runtime/scan47_sparse_terrain_v8"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parent = json.loads((HERE.parent / "v7/manifest.json").read_text())
    if (HERE / "manifest.json").exists() or TARGET.exists():
        raise FileExistsError("Refuse to overwrite a candidate or frozen v8")
    for path, digest in parent["source_files"].items():
        if sha(ROOT / path) != digest:
            raise ValueError("Parent source changed: " + path)
    for name in ("source_sha256.json", "install_sha256.json"):
        for path, digest in json.loads((PARENT / name).read_text()).items():
            if sha(PARENT / path) != digest:
                raise ValueError("Parent native identity mismatch: " + path)
    TARGET.mkdir()
    shutil.copytree(PARENT / "src", TARGET / "src")
    relative = Path("src/plan_env/include/plan_env/eth_step_score_adaptation.h")
    path = TARGET / relative
    original = path.read_text()
    data = original
    anchor = "if (cell == input.cells.end()) { complete = false; break; }"
    if data.count(anchor) != 2:
        raise ValueError("Pinned missing-neighbor anchors changed")
    data = data.replace(anchor, "if (cell == input.cells.end()) continue; // ETH skips absent measurements.")
    anchor = "if (!std::isfinite(neighbor_score.first_pass_height_m)) { complete = false; break; }"
    if data.count(anchor) != 1:
        raise ValueError("Pinned second-pass anchor changed")
    data = data.replace(anchor, "if (!std::isfinite(neighbor_score.first_pass_height_m)) continue;")
    data = data.replace("// fail-closed windows, a V12 hard step-height gate, and tread-interior support.",
                        "// ETH-style missing-neighbor skips, a V12 hard height gate, and tread support.")
    data = data.replace("// or ambiguous same-level coverage keeps the complete scoring window Unknown.",
                        "// or ambiguous association in a present cell keeps that local window Unknown.")
    data = data.replace("// Adaptation: every selected neighbor must be present, and a multilevel\n  // neighbor contributes its unambiguous nearest ground surface.",
                        "// ETH skips missing neighbors. A present multilevel neighbor still needs\n  // an unambiguous nearby surface; do not join different building floors.")
    data = data.replace("// Adaptation: incomplete neighborhoods are Unknown; the local first-pass\n  // height must also stay below the V12 critical value. This hard gate avoids",
                        "// ETH skips missing/invalid neighboring scores. The queried cell's own\n  // first-pass height must stay below the V12 critical value. This avoids")
    path.write_text(data)
    native_files = {str(p.relative_to(TARGET)): sha(p) for p in sorted((TARGET / "src").rglob("*")) if p.is_file()}
    (TARGET / "source_sha256.json").write_text(json.dumps(native_files, indent=2) + "\n")
    patch = "".join(difflib.unified_diff(original.splitlines(True), data.splitlines(True),
                                       fromfile="v7/" + str(relative), tofile="v8/" + str(relative)))
    (HERE / "changes.patch").write_text(patch)
    for name in ("building_planner.yaml", "flat_planner.yaml"):
        shutil.copyfile(HERE.parent / "v7" / name, HERE / name)
    selected = {ROOT / path for path in parent["source_files"]}
    selected.update(p for p in (TARGET / "src").rglob("*") if p.is_file())
    selected.add(TARGET / "source_sha256.json")
    selected.update(p for p in HERE.iterdir() if p.is_file())
    records = {}
    for path in sorted(selected):
        name = str(path.relative_to(ROOT))
        records[name] = sha(path)
        copy = HERE / "source" / name
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, copy)
    (HERE / "manifest.json").write_text(json.dumps({
        "version": "v8", "parent": "v7", "status": "frozen_unvalidated",
        "frozen_utc": datetime.now(timezone.utc).isoformat(),
        "change": "Skip absent terrain neighbors as pinned ETH StepFilter while preserving explicit height/layer/obstacle rejection",
        "source_files": records, "changed_files": [str((TARGET / relative).relative_to(ROOT))],
        "native_build": str(TARGET.relative_to(ROOT)), "source_snapshot_prefix": "source/",
        "acceptance_plan": "PLAN.md",
    }, indent=2) + "\n")
    # Cache reuse is separate from frozen sources and never changes the parent.
    for folder in ("build", "install"):
        shutil.copytree(PARENT / folder, TARGET / folder)
    print(json.dumps({"version": "v8", "source_files": len(records), "native_source_files": len(native_files)}))


if __name__ == "__main__":
    main()
