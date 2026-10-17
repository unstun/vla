#!/usr/bin/env python3
"""Hash-gated scan_08 candidate with a sensor-derived cluster tracker package."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
P2B = HERE.parent
SOURCE = P2B / "builds/scan_07"
OUTPUT = P2B / "builds/scan_08"
EXPECTED_SOURCE_MANIFEST_SHA = "07e98ed78f9b964f049500a5fc8b5e6a0f3a999d1dbf196d56274699c5ee98d5"
EXPECTED_CANDIDATE_MANIFEST_SHA = "25b4dbbb5f19a097eb47cfece97726d347725e9323cefb64c27c79bcaa813739"


class Refused(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate() -> dict[str, str]:
    source_manifest = SOURCE / "source_sha256.json"
    candidate_manifest = SOURCE / "eth_step_score_candidate_manifest.json"
    if sha(source_manifest) != EXPECTED_SOURCE_MANIFEST_SHA or \
       sha(candidate_manifest) != EXPECTED_CANDIDATE_MANIFEST_SHA:
        raise Refused("scan_07 source identity changed")
    build = json.loads((SOURCE / "build_result.json").read_text())
    if build.get("passed") is not True or build.get("source_matches_before_after") is not True:
        raise Refused("scan_07 Foxy build identity not accepted")
    recorded = json.loads(source_manifest.read_text())
    actual = {"src/" + path.relative_to(SOURCE / "src").as_posix(): sha(path)
              for path in (SOURCE / "src").rglob("*")
              if path.is_file() and "__pycache__" not in path.parts}
    if actual != recorded:
        missing = sorted(set(recorded) - set(actual))
        extra = sorted(set(actual) - set(recorded))
        changed = sorted(key for key in set(actual) & set(recorded)
                         if actual[key] != recorded[key])
        raise Refused(f"scan_07 source gate: missing={missing}, extra={extra}, changed={changed}")
    return {path.removeprefix("src/"): value for path, value in recorded.items()}


def materialize() -> dict:
    if OUTPUT.exists():
        raise Refused("scan_08 already exists")
    base = gate()
    try:
        shutil.copytree(SOURCE / "src", OUTPUT / "src",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        root = OUTPUT / "src"
        before = {path.relative_to(root).as_posix(): sha(path)
                  for path in root.rglob("*") if path.is_file()}
        if before != base:
            raise Refused("copied scan_07 source gate failed")
        package = root / "scan_reactive_tracker"
        module = package / "scan_reactive_tracker"
        resource = package / "resource"
        module.mkdir(parents=True)
        resource.mkdir()
        shutil.copy2(HERE / "moving_cluster_core.py", module / "core.py")
        io_text = (HERE / "moving_cluster_io.py").read_text()
        old = "from moving_cluster_core import TerrainSupport"
        if io_text.count(old) != 1:
            raise Refused("tracker IO import anchor changed")
        (module / "io.py").write_text(
            io_text.replace(old, "from scan_reactive_tracker.core import TerrainSupport")
        )
        shutil.copy2(HERE / "moving_cluster_node.py", module / "node.py")
        (module / "__init__.py").write_text("")
        shutil.copy2(HERE / "tracker_package.xml", package / "package.xml")
        shutil.copy2(HERE / "tracker_setup.py", package / "setup.py")
        shutil.copy2(HERE / "tracker_setup.cfg", package / "setup.cfg")
        (resource / "scan_reactive_tracker").write_text("")
        added = {path.relative_to(root).as_posix(): sha(path)
                 for path in package.rglob("*") if path.is_file()}
        manifest = {
            "schema": "scan08_moving_cluster_tracker_candidate_v1",
            "status": "source_candidate_unbuilt",
            "base": "scan_07",
            "base_sha256": base,
            "added_sha256": added,
            "base_source_manifest_sha256": sha(SOURCE / "source_sha256.json"),
            "source_topic_cloud": "/quad_0/cloud",
            "source_topic_pose": "/quad_0/lidar_pose",
            "source_topic_ground": "/pct_tomogram",
            "output_topic": "/tracked_person_snapshot",
            "source_label": "sensor_lidar_moving_cluster_candidate_v1",
            "claim": "candidate moving shape and motion clustering, not validated human recognition; no scan_08 Foxy build or episode",
        }
        (OUTPUT / "moving_cluster_candidate_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return manifest
    except Exception:
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        raise


if __name__ == "__main__":
    result = materialize()
    print(json.dumps({"status": result["status"], "added_sha256": result["added_sha256"]}, indent=2))
