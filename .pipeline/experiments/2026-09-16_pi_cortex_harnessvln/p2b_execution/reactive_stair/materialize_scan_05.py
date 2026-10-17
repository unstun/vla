#!/usr/bin/env python3
"""Copy hash-verified scan_04 sources into an inactive scan_05 candidate.

The added header is an intake/decision contract only. No GridMap hook or ROS
producer is installed, so this command cannot establish planner integration.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
P2B = HERE.parent
SOURCE = P2B / "builds" / "scan_04"
OUTPUT = P2B / "builds" / "scan_05"
HEADER = HERE / "reactive_collision.h"
EXPECTED_GRID_H = "3a562e007f40dc78fd811b31f4326cf778cfb0e475a1d61fd0836eda3aaa28d4"
EXPECTED_GRID_CPP = "2b94d5e09a71f3d9349e9b816f0b1e42b3dbc03551a20b7452579122e88efc87"
EXPECTED_TERMINAL_FIX = "6eec7d6fbbd8df35817f526a644b86fbc8245df295ad69295b3cf3786139d081"
EXPECTED_PINNED_PLANNER = "42a265a35cefb69eae43896acdd13780d1a7bd36a874b2f3aae967376b6e435e"
EXPECTED_OVERLAY_MANIFEST = "bb51d47be0bf21b4b710f7a276fcece40eb478f2640e60c03bbb43c3fa6045f7"
EXPECTED_BUILT_MANIFEST = "442a856168c41f89e451f4d1be4398c982182013bd6c861b16c4f478d14e9484"
EXPECTED_TERMINAL_MANIFEST = "6f42946efe4209ee56511718ad967a2000dc9af5275688715fe4181ecc730ca6"
HEADER_REL = Path("plan_env/include/plan_env/reactive_collision.h")


class Refused(RuntimeError):
    pass


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes(source: Path, pinned_planner: Path) -> dict[str, str]:
    manifest = source / "overlay_manifest.json"
    if not manifest.is_file():
        raise Refused(f"missing source manifest: {manifest}")
    overlay = json.loads(manifest.read_text(encoding="utf-8"))["after"]
    built_manifest = source / "source_sha256.json"
    terminal_manifest = source / "terminal_accel_fix_manifest.json"
    if not built_manifest.is_file() or not terminal_manifest.is_file():
        raise Refused("missing built-source or terminal-fix identity manifest")
    for path, expected_hash in (
        (manifest, EXPECTED_OVERLAY_MANIFEST),
        (built_manifest, EXPECTED_BUILT_MANIFEST),
        (terminal_manifest, EXPECTED_TERMINAL_MANIFEST),
    ):
        if digest(path) != expected_hash:
            raise Refused(f"source identity manifest hash mismatch: {path}")
    built = json.loads(built_manifest.read_text(encoding="utf-8"))
    terminal = json.loads(terminal_manifest.read_text(encoding="utf-8"))
    key = "plan_manage/src/planner_manager.cpp"
    if overlay.get(key) != terminal.get("before_sha256") or \
       terminal.get("after_sha256") != EXPECTED_TERMINAL_FIX or \
       built.get("src/" + key) != EXPECTED_TERMINAL_FIX or \
       terminal.get("file") != "src/" + key:
        raise Refused("terminal-fix provenance chain changed")
    recorded = {key.removeprefix("src/"): value for key, value in built.items()}
    if set(recorded) != set(overlay):
        raise Refused("built-source file set differs from overlay manifest")
    for path, value in overlay.items():
        if path != key and recorded[path] != value:
            raise Refused(f"built-source provenance mismatch: {path}")
    if recorded.get("plan_env/include/plan_env/grid_map.h") != EXPECTED_GRID_H:
        raise Refused("scan_04 grid_map.h manifest identity changed")
    if recorded.get("plan_env/src/grid_map.cpp") != EXPECTED_GRID_CPP:
        raise Refused("scan_04 grid_map.cpp manifest identity changed")
    if digest(pinned_planner) != EXPECTED_PINNED_PLANNER:
        raise Refused("pinned planner.yaml changed")
    root = source / "src"
    actual = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise Refused(f"source symlink is not allowed: {path}")
        if path.is_file() and "__pycache__" not in path.parts:
            actual[path.relative_to(root).as_posix()] = digest(path)
    if actual != recorded:
        missing = sorted(set(recorded) - set(actual))
        extra = sorted(set(actual) - set(recorded))
        changed = sorted(k for k in set(actual) & set(recorded) if actual[k] != recorded[k])
        raise Refused(f"scan_04 source gate failed: missing={missing}, extra={extra}, changed={changed}")
    return recorded


def materialize(
    source: Path = SOURCE,
    output: Path = OUTPUT,
    pinned_planner: Path = P2B / "baseline_config" / "planner.yaml",
    header: Path = HEADER,
) -> dict:
    source = source.resolve()
    output = output.resolve()
    if source.name != "scan_04" or output.name != "scan_05":
        raise Refused("only scan_04 -> scan_05 is allowed")
    if source.parent != output.parent or source == output:
        raise Refused("source and output must be sibling build directories")
    if output.exists():
        raise Refused(f"output already exists: {output}")
    expected = source_hashes(source, pinned_planner)
    if not header.is_file():
        raise Refused(f"missing contract header: {header}")
    header_hash = digest(header)
    if HEADER_REL.as_posix() in expected:
        raise Refused("contract header already present in baseline")

    try:
        shutil.copytree(source / "src", output / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        copied = {path.relative_to(output / "src").as_posix(): digest(path)
                  for path in (output / "src").rglob("*") if path.is_file()}
        if copied != expected:
            raise Refused("copied source hash gate failed")
        target = output / "src" / HEADER_REL
        shutil.copy2(header, target)
        if digest(target) != header_hash:
            raise Refused("copied contract header hash gate failed")
        manifest = {
            "schema": "reactive_stair_scan_05_candidate_v1",
            "status": "inactive_no_live_adapter",
            "source": str(source),
            "source_manifest_sha256": digest(source / "overlay_manifest.json"),
            "built_source_manifest_sha256": digest(source / "source_sha256.json"),
            "terminal_fix_manifest_sha256": digest(source / "terminal_accel_fix_manifest.json"),
            "source_sha256": expected,
            "added": {HEADER_REL.as_posix(): header_hash},
            "pinned_planner_yaml_sha256": digest(pinned_planner),
            "claim": "header-only ROS-free contract; no GridMap hook, ROS subscription, build, or simulator run",
        }
        (output / "reactive_stair_candidate_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return manifest
    except Exception:
        if output.exists():
            shutil.rmtree(output)
        raise


if __name__ == "__main__":
    print(json.dumps(materialize(), indent=2, sort_keys=True))
