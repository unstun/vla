"""Derive an isolated v36 candidate, leaving all frozen v35 paths unchanged."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
OLD = BASE / "runtime/scan66_periodic_replan_v35"
NEW = BASE / "runtime/scan67_nav2_contract_v36"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not NEW.exists() and not (HERE / "prepared.json").exists()
    parent = json.loads((HERE.parent / "v35/manifest.json").read_text())
    for name, expected in parent["source_files"].items():
        assert sha(ROOT / name) == expected, name
        assert sha(HERE.parent / "v35/source" / name) == expected, name
    shutil.copytree(OLD / "src", NEW / "src")
    shutil.copytree(BASE / "runtime_sources/backend_ros", HERE / "backend_ros")
    for name in ("run_local_episode.py", "native_graph.py", "native_backend_entry.py"):
        shutil.copyfile(BASE / "scripts" / name, HERE / name)
    for name in ("building_planner.yaml", "flat_planner.yaml"):
        text = (HERE.parent / "v35" / name).read_text()
        assert text.count("fsm.replan_frequency: 2.0") == 1
        (HERE / name).write_text(text.replace("fsm.replan_frequency: 2.0", "fsm.replan_frequency: 30.0"))
    controller = (BASE / "config_archived/controller.yaml").read_text()
    (HERE / "controller.yaml").write_text(controller.replace("    time_forward: 0.8", "    controller_frequency: 30.0\n    time_forward: 0.8"))
    records = {str(p.relative_to(ROOT)): sha(p) for p in NEW.glob("src/**/*") if p.is_file()}
    (HERE / "parent_identity.json").write_text(json.dumps({"version": "v35", "frozen_files": len(parent["source_files"]),
        "manifest_sha256": sha(HERE.parent / "v35/manifest.json"), "native": json.loads((OLD / "source_sha256.json").read_text())}, indent=2) + "\n")
    (HERE / "prepared.json").write_text(json.dumps({"version": "v36", "parent": "v35", "status": "unfrozen",
        "native_build": str(NEW.relative_to(ROOT)), "initial_native_sha256": records}, indent=2) + "\n")
    print(json.dumps({"parent_files_verified": len(parent["source_files"]), "native_files_copied": len(records), "native": str(NEW)}))


if __name__ == "__main__":
    main()
