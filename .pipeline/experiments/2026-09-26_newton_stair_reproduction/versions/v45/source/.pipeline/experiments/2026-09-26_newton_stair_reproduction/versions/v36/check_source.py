"""Compare owned changes to frozen v35 and verify cross-layer configuration."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
OLD = BASE / "runtime/scan66_periodic_replan_v35"
NEW = BASE / "runtime/scan67_nav2_contract_v36"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parent = json.loads((HERE.parent / "v35/manifest.json").read_text())
    for name, digest in parent["source_files"].items():
        assert sha(ROOT / name) == digest and sha(HERE.parent / "v35/source" / name) == digest, name
    native = {str(p.relative_to(NEW)):sha(p) for p in sorted((NEW / "src").rglob("*")) if p.is_file()}
    old_native = json.loads((OLD / "source_sha256.json").read_text())
    assert native.keys() == old_native.keys()
    assert native == json.loads((NEW / "source_sha256.json").read_text())
    mappings = [(OLD / name, NEW / name) for name in native if native[name] != old_native[name]]
    mappings += [(BASE / "scripts" / name, HERE / name) for name in
                 ("run_local_episode.py", "native_graph.py", "native_backend_entry.py")]
    mappings += [(HERE.parent / "v35" / name, HERE / name) for name in
                 ("building_planner.yaml", "flat_planner.yaml")]
    mappings.append((BASE / "config_archived/controller.yaml", HERE / "controller.yaml"))
    for p in (HERE / "backend_ros").rglob("*.py"):
        old = BASE / "runtime_sources/backend_ros" / p.relative_to(HERE / "backend_ros")
        if old.exists() and sha(old) != sha(p):
            mappings.append((old, p))
    patch, records = [], []
    for old, new in mappings:
        before, after = old.read_bytes(), new.read_bytes()
        preserved = HERE / "parent_source" / new.relative_to(ROOT)
        preserved.parent.mkdir(parents=True, exist_ok=True)
        if preserved.exists():
            assert preserved.read_bytes() == before
        else:
            preserved.write_bytes(before)
        records.append({"parent":str(old.relative_to(ROOT)),"target":str(new.relative_to(ROOT)),
            "parent_sha256":sha(old),"target_sha256":sha(new),"preserved_preimage":str(preserved.relative_to(ROOT))})
        patch += list(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                      fromfile="a/"+str(new.relative_to(ROOT)),tofile="b/"+str(new.relative_to(ROOT))))
    (HERE / "changes.patch").write_text("".join(patch))
    (HERE / "changes.json").write_text(json.dumps(records,indent=2)+"\n")
    cfg=json.loads((HERE / "navigation_contract.json").read_text())
    assert cfg["controller_frequency"] == cfg["local_planner_frequency"] == 30.0
    assert cfg["global_planner_frequency"] == 1.0
    for name in ("building_planner.yaml","flat_planner.yaml"):
        assert "fsm.replan_frequency: 30.0" in (HERE/name).read_text()
    controller=(HERE/"controller.yaml").read_text()
    for key, value in (("controller_frequency",30.),("goal_xy_tolerance",.25),("goal_yaw_tolerance",.25),("goal_z_tolerance",.20)):
        assert f"{key}: {value}" in controller
    # Accepted-curve feasibility and safety solver bodies retain exact bytes.
    assert (NEW/"src/plan_manage/src/planner_manager.cpp").read_bytes() == (OLD/"src/plan_manage/src/planner_manager.cpp").read_bytes()
    assert (NEW/"src/path_searching/src/dyn_a_star.cpp").read_bytes() == (OLD/"src/path_searching/src/dyn_a_star.cpp").read_bytes()
    result={"passed":True,"frozen_parent_files":len(parent["source_files"]),"native_files":len(native),
        "changed_native_files":[name for name in native if native[name]!=old_native[name]],"changed_existing_files":len(records),
        "planner_and_astar_unchanged":True,"physics_run":False,"navigation_validated":False}
    (HERE/"source_check.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
