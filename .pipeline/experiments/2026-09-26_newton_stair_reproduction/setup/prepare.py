"""Pin already archived local inputs before the platform reproduction."""
import hashlib
import json
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parents[1]
PROJECT = BASE.parents[2]
OLD = PROJECT / ".pipeline/experiments/2026-09-23_scan_reactive_stair/runtime_integration/runs/walk_scan28_height030_right_v1"
P2B = PROJECT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    if (BASE / "setup/source_identity.json").exists():
        raise FileExistsError("Preparation already recorded")
    build = P2B / "builds/scan_33"
    expected = json.loads((build / "source_sha256.json").read_text())
    actual = {name: sha(build / name) for name in expected}
    if expected != actual:
        raise ValueError("Archived SCAN33 source mismatch")
    target = BASE / "builds/scan33_humble_amd64_v1"
    target.mkdir(parents=True, exist_ok=False)
    shutil.copytree(build / "src", target / "src")
    (target / "source_sha256.json").write_text(json.dumps(expected, indent=2) + "\n")
    inputs = BASE / "inputs"
    inputs.mkdir()
    records = []
    names = ["building.usda", "actor_route.json", "stair_scenario.json", "stair_geometry.json",
             "new_building.pickle", "locomotion_height_contract.json", "pilot.json",
             "input_manifest.json", "execution_manifest.json", "sensor_rig", "official_human", "livox_mid360"]
    for name in names:
        source = OLD / "inputs" / name
        destination = inputs / name
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copyfile(source, destination)
        for path in (sorted(destination.rglob("*")) if destination.is_dir() else [destination]):
            if path.is_file():
                rel = path.relative_to(inputs)
                source_file = OLD / "inputs" / rel
                digest = sha(path)
                assert digest == sha(source_file)
                records.append({"path": str(path.relative_to(BASE)), "source": str(source_file),
                                "sha256": digest, "bytes": path.stat().st_size})
    shutil.copytree(OLD / "config", BASE / "config_archived")
    refs = BASE / "references"
    refs.mkdir()
    for name, source in {
        "official_building_human.py": OLD / "rtx_candidate/official_building_human.py",
        "replay_stair_inputs.py": OLD.parents[1] / "replay_stair_inputs.py",
        "pct_sim_clock_core.py": P2B / "reactive_stair/pct_sim_clock_core.py",
    }.items():
        shutil.copyfile(source, refs / name)
        records.append({"path": str((refs / name).relative_to(BASE)), "source": str(source),
                        "sha256": sha(source), "bytes": source.stat().st_size})
    identity = {"archived_run": str(OLD), "scan33_source_files": len(expected),
                "scan33_source_manifest_sha256": sha(build / "source_sha256.json"), "inputs": records,
                "newton_environment": str(PROJECT / ".pipeline/experiments/2026-09-26_newton_macos_policy/runtime/.venv"),
                "scan_ros_image": "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb",
                "platform_change": "Local Linux amd64 Humble under Docker replaces remote Foxy; native source is initially identical."}
    (BASE / "setup/source_identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    print(json.dumps({"scan_files": len(expected), "input_files": len(records),
                      "input_bytes": sum(r["bytes"] for r in records)}, indent=2))


if __name__ == "__main__":
    main()
