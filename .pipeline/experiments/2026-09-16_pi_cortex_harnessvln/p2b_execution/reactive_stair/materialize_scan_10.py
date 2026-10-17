#!/usr/bin/env python3
"""Hash-gated scan_10 tracker correction from the built scan_09 source."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
P2B = HERE.parent
SOURCE = P2B / "builds/scan_09"
OUTPUT = P2B / "builds/scan_10"
EXPECTED_SOURCE_MANIFEST_SHA = "361231961424999fb1cf6b8739a60fd67aa9457a5ecb17ce6ce99148d5b32def"
EXPECTED_CANDIDATE_MANIFEST_SHA = "089e440787920df4a4b94c7636a05732e207b0bc6e70bb744ed561eab7e144ce"
EXPECTED_OLD_CORE_SHA = "6e4bc9ad96e5a15827335dd983d9ce405a340ce8a2c2827d5c64a87244b4d42f"
CORE_REL = Path("scan_reactive_tracker/scan_reactive_tracker/core.py")


class Refused(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate() -> dict[str, str]:
    source_manifest = SOURCE / "source_sha256.json"
    candidate_manifest = SOURCE / "pct_density_candidate_manifest.json"
    if sha(source_manifest) != EXPECTED_SOURCE_MANIFEST_SHA or \
       sha(candidate_manifest) != EXPECTED_CANDIDATE_MANIFEST_SHA:
        raise Refused("scan_09 source identity changed")
    result_file = SOURCE / "build_result.json"
    if not result_file.is_file():
        raise Refused("scan_09 Foxy build result missing")
    build = json.loads(result_file.read_text())
    if build.get("passed") is not True or build.get("source_matches_before_after") is not True:
        raise Refused("scan_09 Foxy build identity not accepted")
    recorded = json.loads(source_manifest.read_text())
    actual = {"src/" + path.relative_to(SOURCE / "src").as_posix(): sha(path)
              for path in (SOURCE / "src").rglob("*")
              if path.is_file() and "__pycache__" not in path.parts}
    if actual != recorded:
        missing = sorted(set(recorded) - set(actual))
        extra = sorted(set(actual) - set(recorded))
        changed = sorted(key for key in set(actual) & set(recorded)
                         if actual[key] != recorded[key])
        raise Refused(f"scan_09 source gate: missing={missing}, extra={extra}, changed={changed}")
    base = {path.removeprefix("src/"): value for path, value in recorded.items()}
    if base.get(CORE_REL.as_posix()) != EXPECTED_OLD_CORE_SHA:
        raise Refused("scan_09 tracker core identity changed")
    return base


def materialize() -> dict:
    if OUTPUT.exists():
        raise Refused("scan_10 already exists")
    base = gate()
    try:
        shutil.copytree(SOURCE / "src", OUTPUT / "src",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        root = OUTPUT / "src"
        before = {path.relative_to(root).as_posix(): sha(path)
                  for path in root.rglob("*") if path.is_file()}
        if before != base:
            raise Refused("copied scan_09 source gate failed")
        core = root / CORE_REL
        shutil.copy2(HERE / "moving_cluster_core.py", core)
        if sha(core) == EXPECTED_OLD_CORE_SHA:
            raise Refused("tracker correction did not change core")
        changed = {CORE_REL.as_posix(): sha(core)}
        after = {path.relative_to(root).as_posix(): sha(path)
                 for path in root.rglob("*") if path.is_file()}
        if after != {**base, **changed}:
            raise Refused("scan_10 changed files outside tracker core")
        manifest = {
            "schema": "scan10_slow_motion_tracker_correction_v1",
            "status": "source_candidate_unbuilt",
            "base": "scan_09",
            "base_sha256": base,
            "changed_sha256": changed,
            "base_source_manifest_sha256": sha(SOURCE / "source_sha256.json"),
            "baseline_failure_sha256": sha(HERE.parent.parent.parent /
                "2026-09-23_scan_reactive_stair/scan09_slow_motion_review.json"),
            "source_label": "sensor_lidar_moving_cluster_candidate_v2",
            "reason": "0.03 m per frame never reached scan_09 adjacent-frame 0.08 m confirmation",
            "preserved": "current-only association, no velocity/prediction, fail-closed missing-track policy, terrain source separation",
            "claim": "source correction and local tests only; no scan_10 Foxy build or Isaac episode",
        }
        (OUTPUT / "slow_motion_candidate_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return manifest
    except Exception:
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        raise


if __name__ == "__main__":
    result = materialize()
    print(json.dumps({"status": result["status"],
                      "changed_sha256": result["changed_sha256"]}, indent=2))
