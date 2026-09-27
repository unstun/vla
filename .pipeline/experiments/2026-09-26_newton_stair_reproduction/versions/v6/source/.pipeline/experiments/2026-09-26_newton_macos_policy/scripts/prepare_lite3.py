"""Reuse only already-pinned VLA Lite3 inputs; never read sibling worktrees."""
import hashlib
import json
from pathlib import Path
import shutil

BASE = Path(__file__).resolve().parents[1]
PROJECT = BASE.parents[2]
OLD = PROJECT / ".pipeline/experiments/2026-09-10_x_navdp_lite3_rented4090"
PROVENANCE = PROJECT / ".pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/lite3_v1/setup"


def main():
    expected = json.loads((OLD / "setup/reused_source_manifest.json").read_text())
    records = []
    for item in expected:
        name = item["destination"]
        if not (name.startswith("assets/lite3/") or name.startswith("policy/") or name.startswith("lib/")):
            continue
        source = OLD / name
        actual = hashlib.sha256(source.read_bytes()).hexdigest()
        if actual != item["sha256"]:
            raise ValueError(f"Reused source changed: {source}")
        destination = BASE / ("references/lite3_reference/" + name[4:] if name.startswith("lib/") else name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        records.append({"source": str(source), "path": str(destination.relative_to(BASE)),
                        "sha256": actual, "bytes": destination.stat().st_size})
    # Empty package entrypoints are also pinned.
    for name in ("__init__.py", "robots/__init__.py"):
        source = OLD / "lib" / name
        destination = BASE / "references/lite3_reference" / name
        shutil.copyfile(source, destination)
        records.append({"source": str(source), "path": str(destination.relative_to(BASE)),
                        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "bytes": source.stat().st_size})
    for name in ("import_provenance.json", "lite3_asset_manifest.json"):
        destination = BASE / "setup" / ("lite3_" + name)
        shutil.copyfile(PROVENANCE / name, destination)
    result = {"source": str(OLD), "records": records,
              "robot_upstream": "https://github.com/DeepRoboticsLab/deep_robotics_model",
              "robot_commit": "1f46ba1f86c72ddafd3d79e1e9725805c202bf2b",
              "machine_dog_interface_commit": "a2e98845a212bd6a2128af778cb1304eeb660f5f",
              "changes": "None in copied robot, policy or reference controller; Newton adapter is separate.",
              "license_note": "Existing internal VLA research assets reused with original provenance; upstream robot license was not present in the inherited asset manifest and is not asserted here."}
    (BASE / "setup/lite3_inputs.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"files": len(records), "bytes": sum(r["bytes"] for r in records)}))


if __name__ == "__main__":
    main()
