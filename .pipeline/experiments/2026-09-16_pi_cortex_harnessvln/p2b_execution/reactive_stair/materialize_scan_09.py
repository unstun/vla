#!/usr/bin/env python3
"""Hash-gated scan_09 correction for Humble PCT PointCloud2 density metadata."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
P2B = HERE.parent
SOURCE = P2B / "builds/scan_08"
OUTPUT = P2B / "builds/scan_09"
EXPECTED_SOURCE_MANIFEST_SHA = "a0209cd4d1144b8e2591a5490a9034e3e250fb12e4c66bde44c4183a42a08278"
EXPECTED_CANDIDATE_MANIFEST_SHA = "40262d4ca510048a222f7c426ebdbd2d3cdede6d89118d81484f37c7830908b8"
NODE_REL = Path("scan_reactive_tracker/scan_reactive_tracker/node.py")
OLD = ('            if not msg.is_dense or msg.header.frame_id != "world":\n'
       '                raise ValueError("invalid PCT frame or density")\n')
NEW = ('            if msg.header.frame_id != "world":\n'
       '                raise ValueError("invalid PCT frame")\n')


class Refused(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate() -> dict[str, str]:
    source_manifest = SOURCE / "source_sha256.json"
    candidate_manifest = SOURCE / "moving_cluster_candidate_manifest.json"
    if sha(source_manifest) != EXPECTED_SOURCE_MANIFEST_SHA or \
       sha(candidate_manifest) != EXPECTED_CANDIDATE_MANIFEST_SHA:
        raise Refused("scan_08 source identity changed")
    result_file = SOURCE / "build_result.json"
    if not result_file.is_file():
        raise Refused("scan_08 Foxy build result not yet returned")
    build = json.loads(result_file.read_text())
    if build.get("passed") is not True or build.get("source_matches_before_after") is not True:
        raise Refused("scan_08 Foxy build identity not accepted")
    recorded = json.loads(source_manifest.read_text())
    actual = {"src/" + path.relative_to(SOURCE / "src").as_posix(): sha(path)
              for path in (SOURCE / "src").rglob("*")
              if path.is_file() and "__pycache__" not in path.parts}
    if actual != recorded:
        missing = sorted(set(recorded) - set(actual))
        extra = sorted(set(actual) - set(recorded))
        changed = sorted(key for key in set(actual) & set(recorded)
                         if actual[key] != recorded[key])
        raise Refused(f"scan_08 source gate: missing={missing}, extra={extra}, changed={changed}")
    return {path.removeprefix("src/"): value for path, value in recorded.items()}


def materialize() -> dict:
    if OUTPUT.exists():
        raise Refused("scan_09 already exists")
    base = gate()
    try:
        shutil.copytree(SOURCE / "src", OUTPUT / "src",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        root = OUTPUT / "src"
        before = {path.relative_to(root).as_posix(): sha(path)
                  for path in root.rglob("*") if path.is_file()}
        if before != base:
            raise Refused("copied scan_08 source gate failed")
        node = root / NODE_REL
        code = node.read_text()
        if code.count(OLD) != 1 or code.count(NEW) != 0:
            raise Refused("PCT density check anchor changed")
        code = code.replace(OLD, NEW)
        if code.count("non-finite PCT point") != 1:
            raise Refused("finite PCT record validation missing")
        node.write_text(code)
        manifest = {
            "schema": "scan09_pct_density_correction_v1",
            "status": "source_candidate_unbuilt",
            "base": "scan_08",
            "base_sha256": base,
            "changed_sha256": {NODE_REL.as_posix(): sha(node)},
            "base_source_manifest_sha256": sha(SOURCE / "source_sha256.json"),
            "reason": "Humble sensor_msgs_py.point_cloud2.create_cloud sets is_dense=false for finite PCT points",
            "preserved": "world frame, float32 field validation, finite point validation, source hash gate, incomplete-on-invalid behavior",
            "claim": "source correction only; no scan_09 Foxy build or ROS topic replay",
        }
        (OUTPUT / "pct_density_candidate_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return manifest
    except Exception:
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        raise


if __name__ == "__main__":
    result = materialize()
    print(json.dumps({"status": result["status"], "changed_sha256": result["changed_sha256"]}, indent=2))
