#!/usr/bin/env python3
"""Prepare or execute the P2B two-goal Isaac/PCT/SCAN pilot package.

Default mode is prepare-only. It materializes the already reviewed patched
runner, copies the current local sources needed by the pilot into an immutable
run directory, and writes exact remote commands plus a remote worker. Actual
physics execution is guarded by --execute --lead-authorized-execute and requires
an explicitly accepted SCAN workspace.

Stance hold defaults (PRD D8, 2026-09-18): `--stance-hold auto` with the
`--stance-entry-kd xfade1s` entry, as in the C2 series. `--stance-hold off`
stays available; it then accepts only the runner's `ramp` entry and passes no
entry flag to the runner. A prepared package without these `run_request.json`
fields keeps its recorded meaning: hold off, ramp entry.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import inspect
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
import time
from typing import Dict, Iterable, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXP = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln"
P2B = EXP / "p2b_execution"
BACKEND_ADAPTER = EXP / "backend_adapter"
BACKEND_ROS = EXP / "backend_ros"
NAVIGATION_SERVICE = EXP / "navigation_service"
PCT_RUNTIME = P2B / "pct_runtime"
BRIDGE_REF = (
    ROOT
    / "references/upstream/2026-09-16_lite3_isaac_harness_backend/source/"
    "machine-dog-nav/integration/lite3_sim_bridge"
)
ACQUISITION = ROOT / "references/upstream/2026-09-16_lite3_isaac_harness_backend/acquisition.json"
V12_REF = ROOT / "references/upstream/2026-09-11_lite3_v12_locomotion"
FOXY_IMAGE_ID = "e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8"
PCT_HUMBLE_IMAGE_ID = "40f0fa16091e2b6e24fd82058ceb01dbe76c001276234af0b9a44ac0e3787555"
DEFAULT_REMOTE_ROOT = "/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/two_goal_pilot"
DEFAULT_REMOTE_V12 = "/home/sun/machine-dog-nav-runs/2026-09-08_new_building_lite3_dynamics/source/v12"
DEFAULT_REMOTE_CHECKPOINT = (
    "/home/sun/machine-dog-nav-runs/2026-09-08_new_building_lite3_dynamics/"
    "source/checkpoint/model_149999.pt"
)
# The review check p2b_execution/review_two_goal.py requires an absolute 0.4 m.
CANCEL_DISPLACEMENT_MIN_M = 0.40
STANCE_HOLD_CHOICES = ("off", "auto")
# stance_hold.py STANCE_ENTRY_KD_MODES / STANCE_ENTRY_KD_DEFAULT; the launcher tests check the two agree.
STANCE_ENTRY_KD_CHOICES = ("ramp", "step1", "step2p5", "xfade1s", "xfade2s")
# The runner's own entry variant when no --stance-entry-kd is passed, and the only
# one accepted with --stance-hold off (recorded, not passed to the runner).
RUNNER_STANCE_ENTRY_KD = "ramp"
# Launcher defaults since PRD D8 (2026-09-18): the hold on with the D5/D6-selected
# crossfade entry. The patched runner keeps its own default --stance-hold off.
DEFAULT_STANCE_HOLD = "auto"
DEFAULT_STANCE_ENTRY_KD_AUTO = "xfade1s"
# Meaning of a prepared package whose run_request.json lacks these fields: it was
# prepared before the flags existed and ran the hold off with the ramp entry.
LEGACY_PACKAGE_STANCE_HOLD = "off"
LEGACY_PACKAGE_STANCE_ENTRY_KD = "ramp"
CANCEL_GOAL_A_CLEARANCE_MIN_M = 0.30
GPU_SAMPLE_INTERVAL_S = 1.0
# --remote-only-bulk leaves exactly these runner outputs (paths relative to
# artifacts/) on the execution host; their hashes come back in
# remote_only_artifacts.json. review_two_goal.py reads neither file's content.
REMOTE_ONLY_BULK_FILES = ("runner_output/clouds.jsonl", "runner_output/third_person_master.mp4")
REMOTE_ONLY_RECORD = "remote_only_artifacts.json"
WALK_REVIEW_SCRIPT = HERE / "make_walk_review.py"
WALK_REVIEW_DIR = "walk_review"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class PackageStorage:
    """Hardlink frozen, never-rewritten files into a run package, copying when linking fails.

    A hardlink shares the source inode, so its bytes and hash equal the source.
    Only files that the package never rewrites may be linked; editing a linked
    package file in place would edit the frozen source as well.
    """

    def __init__(self) -> None:
        self.linked: List[str] = []
        self.linked_bytes = 0
        self.copied: List[str] = []
        self.copy_reasons: Dict[str, str] = {}
        self.pairs: List[Tuple[str, str]] = []

    def link_or_copy(self, src, dst):
        src, dst = str(src), str(dst)
        self.pairs.append((src, dst))
        try:
            if os.path.islink(src):
                raise OSError("source is a symlink; copied to keep content semantics")
            os.link(src, dst)
        except OSError as exc:
            shutil.copy2(src, dst)
            self.copied.append(dst)
            self.copy_reasons.setdefault("%s: %s" % (exc.__class__.__name__, exc), dst)
        else:
            self.linked.append(dst)
            self.linked_bytes += os.stat(dst).st_size
        return dst

    def record(self, root: Path) -> dict:
        def rel(paths):
            return sorted(Path(p).relative_to(root).as_posix() for p in paths)

        return {
            "method": "os.link with shutil.copy2 fallback",
            "scope": "pct_runtime/ tree and inputs/{building.usda,new_building.pickle,pilot.json,input_manifest.json}",
            "linked_count": len(self.linked),
            "linked_bytes": self.linked_bytes,
            "copied_count": len(self.copied),
            "copied_paths": rel(self.copied),
            "copy_reasons": sorted(self.copy_reasons),
            "hash_checks": "package_manifest hashes every file; linked files are also compared with the source manifests",
        }


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def copytree_clean(src: Path, dst: Path, copy_function=shutil.copy2) -> None:
    def ignore(_dir, names):
        ignored = set()
        for name in names:
            if name in {"__pycache__", ".pytest_cache", ".mypy_cache", "build", "install", "log"}:
                ignored.add(name)
            if name.endswith((".pyc", ".pyo")):
                ignored.add(name)
        return ignored

    shutil.copytree(src, dst, ignore=ignore, copy_function=copy_function)


def dir_hashes(root: Path, max_bytes: Optional[int] = None) -> Dict[str, dict]:
    files: Dict[str, dict] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        if any(part in {"__pycache__", ".pytest_cache", "build", "install", "log"} for part in path.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        size = path.stat().st_size
        if max_bytes is not None and size > max_bytes:
            continue
        rel = path.relative_to(root).as_posix()
        files[rel] = {"sha256": sha256(path), "bytes": size}
    return files


def load_materializer():
    spec = importlib.util.spec_from_file_location(
        "materialize_runner_patch", str(HERE / "materialize_runner_patch.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def import_runner(runner_path: Path):
    spec = importlib.util.spec_from_file_location("patched_run_pct_scan_building", str(runner_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def verify_input_manifest() -> dict:
    manifest = json.loads((P2B / "input_manifest.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = P2B / item["path"]
        if sha256(path) != item["sha256"]:
            raise RuntimeError("input manifest mismatch: " + item["path"])
    return manifest


def verify_bridge_source() -> dict:
    acquisition = json.loads(ACQUISITION.read_text(encoding="utf-8"))
    expected = {
        name.removeprefix("integration/lite3_sim_bridge/"): digest
        for name, digest in acquisition["sha256"].items()
    }
    for rel, digest in expected.items():
        if sha256(BRIDGE_REF / rel) != digest:
            raise RuntimeError("frozen bridge source drift: " + rel)
    return expected


def verify_v12_reference() -> Dict[str, str]:
    expected = {}
    for line in (V12_REF / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.lstrip("*")
        path = V12_REF / name
        if sha256(path) != digest:
            raise RuntimeError("local V12 reference drift: " + name)
        expected[name] = digest
    return expected


def verify_pct_runtime_manifest() -> dict:
    manifest = json.loads((P2B / "pct_runtime_manifest.json").read_text(encoding="utf-8"))
    files = manifest.get("files")
    if isinstance(files, dict):
        items = files.items()
    elif isinstance(files, list):
        items = ((item["path"], item["sha256"]) for item in files)
    else:
        raise RuntimeError("unsupported PCT runtime manifest files shape")
    for rel, digest in items:
        path = P2B / rel
        if sha256(path) != digest:
            raise RuntimeError("PCT runtime manifest mismatch: " + rel)
    return manifest


def bridge_manifest(bridge_dir: Path, remote_bridge_dir: str) -> dict:
    files = []
    for path in sorted(p for p in bridge_dir.rglob("*") if p.is_file()):
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        rel = path.relative_to(bridge_dir).as_posix()
        files.append({"path": rel, "sha256": sha256(path), "bytes": path.stat().st_size})
    return {"schema_version": 1, "root": remote_bridge_dir, "files": files}


# scan_tree_hashes, compare_hash_maps and scan_workspace_gate are embedded
# verbatim in remote_worker.py (scan_gate_source) and in
# p2b_execution/capture_install_identity.py, so every SCAN identity is hashed
# by one implementation. They may use only Path and hashlib.
def scan_tree_hashes(workspace, subdir):
    """Hash regular files under workspace/subdir, keyed relative to workspace.

    Python bytecode caches are listed as excluded instead of hashed; the
    recorded scan_03 install identity contains none although the Foxy build
    ran compileall on the installed message package.
    """
    workspace = Path(workspace)
    files = {}
    excluded = []
    base = workspace / subdir
    if base.is_dir():
        for path in sorted(p for p in base.rglob("*") if p.is_file()):
            rel = path.relative_to(workspace)
            if "__pycache__" in rel.parts or path.suffix in (".pyc", ".pyo"):
                excluded.append(rel.as_posix())
                continue
            files[rel.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files, excluded


def compare_hash_maps(expected, actual):
    shared = set(expected) & set(actual)
    return {
        "expected_count": len(expected),
        "actual_count": len(actual),
        "missing": sorted(set(expected) - set(actual)),
        "unexpected": sorted(set(actual) - set(expected)),
        "mismatched": sorted(k for k in shared if expected[k] != actual[k]),
        "match": bool(expected) and expected == actual,
    }


def scan_workspace_gate(workspace, identity):
    """Compare a SCAN workspace with an accepted build identity; returns a record."""
    workspace = Path(workspace)
    identity = identity or {}
    record = {"schema_version": 1, "workspace": str(workspace), "passed": False, "errors": []}
    gate = identity.get("workspace_gate")
    if not isinstance(gate, dict):
        record["errors"].append("accepted SCAN identity lacks workspace_gate")
        return record
    expected_remote = gate.get("expected_remote_workspace")
    record["expected_remote_workspace"] = expected_remote
    if expected_remote is not None and expected_remote != str(workspace):
        record["errors"].append("workspace path differs from the build identity")
    source, source_excluded = scan_tree_hashes(workspace, "src")
    record["source"] = compare_hash_maps(gate.get("expected_source_files") or {}, source)
    record["source"]["excluded"] = source_excluded
    if not record["source"]["match"]:
        record["errors"].append("SCAN src/ differs from source_sha256.json")
    installed_expected = (identity.get("install_identity") or {}).get("installed_files")
    if installed_expected:
        installed, install_excluded = scan_tree_hashes(workspace, "install")
        record["install_checked"] = True
        record["install"] = compare_hash_maps(installed_expected, installed)
        record["install"]["excluded"] = install_excluded
        if not record["install"]["match"]:
            record["errors"].append("SCAN install/ differs from install_identity.json")
    elif gate.get("allow_missing_install_identity") is True:
        record["install_checked"] = False
        record["install_dir_exists"] = (workspace / "install").is_dir()
        if not record["install_dir_exists"]:
            record["errors"].append("SCAN workspace lacks install/")
    else:
        record["errors"].append("install identity missing and not explicitly allowed")
    record["passed"] = not record["errors"]
    return record


def scan_gate_source() -> str:
    return "\n\n".join(inspect.getsource(f) for f in (scan_tree_hashes, compare_hash_maps, scan_workspace_gate))


def build_scan_workspace_gate(scan_path: Path, remote_scan_workspace: Optional[str], allow_missing_install_identity: bool) -> dict:
    """Validate an accepted local SCAN build and freeze the remote gate expectations."""
    if not scan_path.exists():
        raise FileNotFoundError("accepted SCAN build dir missing: " + str(scan_path))
    source_manifest = scan_path / "source_sha256.json"
    if not source_manifest.is_file():
        raise RuntimeError("accepted SCAN build lacks source_sha256.json from build_scan.py: " + str(scan_path))
    expected_source = json.loads(source_manifest.read_text(encoding="utf-8"))
    if not expected_source or not all(isinstance(k, str) and k.startswith("src/") for k in expected_source):
        raise RuntimeError("source_sha256.json must map src/ paths to hashes")
    local_source, local_excluded = scan_tree_hashes(scan_path, "src")
    local_check = compare_hash_maps(expected_source, local_source)
    local_check["excluded"] = local_excluded
    if not local_check["match"]:
        raise RuntimeError("local SCAN src/ differs from source_sha256.json: " + json.dumps(local_check, sort_keys=True)[:2000])
    install_identity_path = scan_path / "install_identity.json"
    install_identity = None
    if install_identity_path.is_file():
        install_identity = json.loads(install_identity_path.read_text(encoding="utf-8"))
        installed = install_identity.get("installed_files")
        if not isinstance(installed, dict) or not installed or not all(str(k).startswith("install/") for k in installed):
            raise RuntimeError("install_identity.json must map install/ paths to hashes")
        if install_identity.get("source_matches") is not True or install_identity.get("source_file_count") != len(expected_source):
            raise RuntimeError("install_identity.json was not captured against this source manifest")
    elif not allow_missing_install_identity:
        raise RuntimeError(
            "accepted SCAN build lacks install_identity.json; capture it with "
            "p2b_execution/capture_install_identity.py or pass --allow-missing-install-identity"
        )
    build_result_path = scan_path / "build_result.json"
    build_result = json.loads(build_result_path.read_text(encoding="utf-8")) if build_result_path.is_file() else {}
    expected_remote = (install_identity or {}).get("remote_workspace") or build_result.get("remote_workspace")
    if remote_scan_workspace and expected_remote and remote_scan_workspace != expected_remote:
        raise RuntimeError("--remote-scan-workspace %s differs from the build identity %s" % (remote_scan_workspace, expected_remote))
    return {
        "schema_version": 1,
        "source_manifest_path": str(source_manifest),
        "source_manifest_sha256": sha256(source_manifest),
        "expected_source_files": expected_source,
        "install_identity_present": install_identity is not None,
        "installed_files_source": "accepted_scan_build_identity.install_identity.installed_files" if install_identity else None,
        "installed_file_count": len(install_identity["installed_files"]) if install_identity else None,
        "allow_missing_install_identity": bool(allow_missing_install_identity),
        "expected_remote_workspace": expected_remote,
        "local_source_check": {k: local_check[k] for k in ("expected_count", "actual_count", "match")},
        "exclusion_rule": "files under __pycache__/ and *.pyc/*.pyo are listed as excluded, not hashed",
        "remote_records": ["artifacts/scan_workspace_gate.json", "artifacts/scan_workspace_gate_after.json"],
    }


def cancel_trigger_check(value, pilot: dict) -> dict:
    """Refuse cancel triggers below the review minimum or too close to goal A."""
    value = finite_number(value, "cancel_displacement_m")
    spawn = [float(v) for v in pilot["spawn_ground_xyz_m"]]
    goal_a = [float(v) for v in pilot["goals"][0]["ground_xyz_m"]]
    straight = math.hypot(goal_a[0] - spawn[0], goal_a[1] - spawn[1])
    record = {
        "cancel_displacement_m": value,
        "minimum_m": CANCEL_DISPLACEMENT_MIN_M,
        "minimum_source": "p2b_execution/review_two_goal.py requires cancel displacement >= 0.4 m",
        "goal_a_clearance_min_m": CANCEL_GOAL_A_CLEARANCE_MIN_M,
        "spawn_to_goal_a_xy_m": straight,
        "maximum_allowed_m": straight - CANCEL_GOAL_A_CLEARANCE_MIN_M,
        "guaranteed_xy_distance_to_goal_a_at_trigger_m": straight - value,
        "bound": (
            "Triangle inequality on inputs/pilot.json: after XY displacement d from the start, the XY distance "
            "to goal A is at least |start - goal A| - d, and any route length to goal A is at least that. "
            "The driver measures d from its first runner snapshot, the standing pose near the spawn."
        ),
    }
    if value < CANCEL_DISPLACEMENT_MIN_M:
        raise ValueError("--cancel-displacement-m %.3f is below the %.2f m review minimum" % (value, CANCEL_DISPLACEMENT_MIN_M))
    if straight - value < CANCEL_GOAL_A_CLEARANCE_MIN_M:
        raise ValueError(
            "--cancel-displacement-m %.3f could trigger within %.2f m of goal A (spawn to goal A %.3f m)"
            % (value, CANCEL_GOAL_A_CLEARANCE_MIN_M, straight)
        )
    return record


def finite_number(value, name: str) -> float:
    val = float(value)
    if not (val == val and abs(val) != float("inf")):
        raise ValueError(name + " must be finite")
    return val


def validate_pilot(pilot: dict) -> None:
    if pilot.get("profile") != "diagnostic_simulator_truth_known_map":
        raise ValueError("unexpected pilot profile")
    if pilot.get("no_reference_route_replay") is not True:
        raise ValueError("pilot must forbid reference route replay")
    for name in ["max_sim_seconds", "max_wall_seconds", "goal_xy_tolerance_m", "goal_z_tolerance_m", "stop_dwell_sim_seconds", "stop_speed_mps", "stop_yaw_rate_radps", "stop_command_norm", "nominal_body_height_m", "spawn_yaw_rad"]:
        finite_number(pilot[name], name)
    if finite_number(pilot["max_sim_seconds"], "max_sim_seconds") != 45.0:
        raise ValueError("pilot max_sim_seconds must remain 45.0")
    if finite_number(pilot["max_wall_seconds"], "max_wall_seconds") != 1200.0:
        raise ValueError("pilot max_wall_seconds must remain 1200.0")
    if [goal.get("goal_id") for goal in pilot.get("goals", [])] != ["goal-a", "goal-b"]:
        raise ValueError("pilot goals must be goal-a then goal-b")
    for idx, point in enumerate([pilot["spawn_ground_xyz_m"]] + [g["ground_xyz_m"] for g in pilot["goals"]]):
        if len(point) != 3:
            raise ValueError("point must have 3 coordinates")
        for axis, value in enumerate(point):
            finite_number(value, "point[%d][%d]" % (idx, axis))


def native_baseline_limits() -> dict:
    scope = json.loads((P2B / "baseline_config/native_nominal_scope.json").read_text(encoding="utf-8"))
    cfg = scope.get("execution_configuration", scope)
    return {
        "max_vx": float(cfg["max_vx"]),
        "max_vy": float(cfg["max_vy"]),
        "max_wz": float(cfg["max_wz"]),
        "max_horizontal_norm": float(cfg["max_horizontal_norm"]),
        "speed_profile": str(cfg["speed_profile"]),
    }


def route_arc_length_xy(points: List[List[float]]) -> float:
    total = 0.0
    for prev, cur in zip(points, points[1:]):
        total += ((float(cur[0]) - float(prev[0])) ** 2 + (float(cur[1]) - float(prev[1])) ** 2) ** 0.5
    return total


def make_route_artifact(pilot: dict) -> dict:
    points = [[float(v) for v in pilot["spawn_ground_xyz_m"]]]
    points += [[float(v) for v in goal["ground_xyz_m"]] for goal in pilot["goals"]]
    geometry_sha = hashlib.sha256(
        json.dumps(points, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": 1,
        "route_id": "two_goal_spawn_and_legacy_metric_metadata",
        "semantics": "terrain_ground_xyz_m",
        "body_height_applied": False,
        "points_xyz_m": points,
        "geometry_sha256": geometry_sha,
        "statistics": {"arc_length_xy_m": route_arc_length_xy(points)},
        "note": (
            "Metadata only for runner spawn/legacy metrics. In external-goal mode "
            "the native runner must not command these targets; PCT recomputes each "
            "route from measured pose per HTTP goal request."
        ),
    }


def make_bridge_config(path: Path, telemetry_port: int, command_port: int) -> None:
    limits = native_baseline_limits()
    path.write_text(
        textwrap.dedent(
            f"""\
            /**:
              ros__parameters:
                telemetry_host: 127.0.0.1
                telemetry_port: {telemetry_port}
                command_host: 127.0.0.1
                command_port: {command_port}
                connect_timeout_seconds: 1.0
                reconnect_delay_seconds: 0.2
                command_rate_hz: 50.0
                source_command_timeout_seconds: 0.25
                use_sim_time: false
                publish_clock: true
                clock_topic: /clock
                require_dual_cloud_sensor_frame: true
                max_body_state_age_seconds: 0.05
                require_complete_body_state: true
                body_state_identity_topic: /quad_0/body_state_identity
                trial_fault_topic: /quad_0/trial_fault
                require_fresh_simulation_feedback: true
                max_simulation_stall_seconds: 0.25
                publish_twist_validity: true
                max_vx: {limits["max_vx"]}
                max_vy: {limits["max_vy"]}
                max_wz: {limits["max_wz"]}
                max_horizontal_command_norm: {limits["max_horizontal_norm"]}
                world_frame: world
                base_frame: base
                sensor_frame: lidar
                body_pose_topic: /quad_0/body_pose
                sensor_pose_topic: /quad_0/lidar_pose
                cloud_topic: /quad_0/cloud
                raw_cloud_topic: /quad_0/cloud_raw
                cmd_vel_topic: /quad_0/cmd_vel
            """
        ),
        encoding="utf-8",
    )


def make_backend_config(path: Path, pilot: dict, run_id: str, http_port: int, pct_port: int) -> None:
    config = json.loads((BACKEND_ROS / "config/p2b_backend_ros.example.json").read_text(encoding="utf-8"))
    config["run_id"] = run_id
    config["run_epoch_ns"] = 0
    config["map"] = {
        "epoch": "flat_nominal",
        "revision": 1,
        "frame_id": pilot["frame_id"],
        "nominal_body_height_m": pilot["nominal_body_height_m"],
        "pct_layer": pilot["pct_layer"],
    }
    config["http"] = {"host": "127.0.0.1", "port": http_port}
    config["pct_worker"]["host"] = "127.0.0.1"
    config["pct_worker"]["port"] = pct_port
    config["applied_evidence"] = {
        "current_command_path": "REMOTE_RUN/artifacts/external_episode/current_command.json",
        "finish_request_path": "REMOTE_RUN/artifacts/external_episode/finish_request.json",
        "stop_command_norm": pilot["stop_command_norm"],
        "stop_speed_mps": pilot["stop_speed_mps"],
        "stop_yaw_rate_radps": pilot["stop_yaw_rate_radps"],
        "stop_dwell_sim_seconds": pilot["stop_dwell_sim_seconds"],
    }
    config["arrival"] = {
        "xy_tolerance_m": pilot["goal_xy_tolerance_m"],
        "z_tolerance_m": pilot["goal_z_tolerance_m"],
        "monitor_period_s": 0.05,
    }
    config["service"]["command_timeout_s"] = pilot["max_sim_seconds"]
    write_json(path, config)


def _insert_ros_parameter(text: str, parameter_line: str) -> str:
    if parameter_line.strip().split(":", 1)[0] + ":" in text:
        return text
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if line.strip() == "ros__parameters:":
            indent = line[: len(line) - len(line.lstrip())] + "  "
            lines.insert(idx + 1, indent + parameter_line)
            return "\n".join(lines) + "\n"
    raise RuntimeError("ros__parameters block missing in SCAN config")


def make_scan_runtime_configs(config_dir: Path) -> None:
    """Write pilot-specific SCAN configs derived from baseline files.

    The accepted scan_03 source defaults to explicit P2B typed-route mode; this
    records that mode in the generated package under each node's ROS parameter
    block alongside the exact topic contract used by backend_ros and remaps.
    """
    planner_path = config_dir / "planner.yaml"
    controller_path = config_dir / "controller.yaml"
    planner_text = _insert_ros_parameter(
        planner_path.read_text(encoding="utf-8"),
        "p2b_mode: true",
    )
    controller_text = _insert_ros_parameter(
        controller_path.read_text(encoding="utf-8"),
        "p2b_mode: true",
    )
    planner_text += (
        "# P2B pilot remaps: body_pose:=/quad_0/body_pose, "
        "sensor_pose:=/quad_0/lidar_pose, cloud:=/quad_0/cloud.\n"
        "# P2B topics: /p2b/route, /p2b/scan_admission, /p2b/scan_cancel.\n"
    )
    controller_text += (
        "# P2B pilot remap: body_pose:=/quad_0/body_pose.\n"
        "# Command topics: /quad_0/raw_scan_cmd_vel -> backend gate -> /quad_0/cmd_vel.\n"
    )
    planner_path.write_text(planner_text, encoding="utf-8")
    controller_path.write_text(controller_text, encoding="utf-8")


def build_runner_argv(args, remote_run: str, run_id: str, pilot: dict) -> List[str]:
    limits = native_baseline_limits()
    return [
        "--scene", remote_run + "/inputs/building.usda",
        "--runtime", args.remote_v12_runtime,
        "--checkpoint", args.remote_checkpoint,
        "--route-artifact", remote_run + "/inputs/two_goal_route_artifact.json",
        "--scope", remote_run + "/inputs/two_goal_scope.json",
        "--execution-manifest", remote_run + "/inputs/execution_manifest.json",
        "--output", remote_run + "/artifacts/runner_output",
        "--case", "flat_nominal",
        "--duration-seconds", str(pilot["max_sim_seconds"]),
        "--telemetry-host", "127.0.0.1",
        "--telemetry-port", str(args.telemetry_port),
        "--command-host", "127.0.0.1",
        "--command-port", str(args.command_port),
        "--max-vx", str(limits["max_vx"]),
        "--max-vy", str(limits["max_vy"]),
        "--max-wz", str(limits["max_wz"]),
        "--max-horizontal-norm", str(limits["max_horizontal_norm"]),
        "--speed-profile", limits["speed_profile"],
        "--contact-policy", "native_v12",
        "--unfiltered-planner-cloud",
        "--goal-tolerance-m", str(pilot["goal_xy_tolerance_m"]),
        "--terminal-window-seconds", "2.0",
        "--terminal-command-norm", str(pilot["stop_command_norm"]),
        "--terminal-speed-mps", str(pilot["stop_speed_mps"]),
        "--terminal-yaw-rate-radps", str(pilot["stop_yaw_rate_radps"]),
        "--connection-ready-timeout-seconds", "120.0",
        "--max-wall-seconds", str(pilot["max_wall_seconds"]),
        "--video-fps", "12.5",
        "--camera-capture-stride", "4",
        "--complete-body-state",
        "--priority-telemetry",
        "--async-recording",
        "--freeze-gc",
        "--external-goal-mode",
        "--external-run-id", run_id,
        "--external-control-dir", remote_run + "/artifacts/external_episode",
        "--external-finish-stillness-seconds", str(pilot["stop_dwell_sim_seconds"]),
        "--external-status-freshness-seconds", "2.0",
        "--stance-hold", stance_hold_setting(args),
        *stance_entry_kd_flags(args),
        "--seed", "42",
        "--device", "cuda:0",
    ]


def stance_hold_setting(args) -> str:
    """Validated --stance-hold; unset means the PRD D8 default (auto)."""
    value = getattr(args, "stance_hold", None)
    if value is None:
        value = DEFAULT_STANCE_HOLD
    if value not in STANCE_HOLD_CHOICES:
        raise ValueError("--stance-hold must be one of %s" % (STANCE_HOLD_CHOICES,))
    return value


def stance_entry_kd_setting(args) -> str:
    """Validated --stance-entry-kd.

    Unset means xfade1s with the hold on (PRD D8) and the runner's ramp with the
    hold off. Any other entry needs --stance-hold auto, as the runner requires.
    """
    stance_hold = stance_hold_setting(args)
    value = getattr(args, "stance_entry_kd", None)
    if value is None:
        value = DEFAULT_STANCE_ENTRY_KD_AUTO if stance_hold == "auto" else RUNNER_STANCE_ENTRY_KD
    if value not in STANCE_ENTRY_KD_CHOICES:
        raise ValueError("--stance-entry-kd must be one of %s" % (STANCE_ENTRY_KD_CHOICES,))
    if stance_hold != "auto" and value != RUNNER_STANCE_ENTRY_KD:
        raise ValueError("--stance-entry-kd %s applies only with --stance-hold auto" % value)
    return value


def stance_entry_kd_flags(args) -> List[str]:
    """Runner argv for the entry variant: passed only with --stance-hold auto.

    With --stance-hold off the runner default (ramp) applies and the argv stays as
    before the flag existed; the scope records the resolved value either way.
    """
    value = stance_entry_kd_setting(args)
    if stance_hold_setting(args) != "auto":
        return []
    return ["--stance-entry-kd", value]


def make_scope(runner_module, runner_argv: List[str], execution_manifest_sha: str, patched_runner_sha: str, pilot: dict, baseline_scope: dict) -> dict:
    parsed = runner_module.build_parser().parse_args(runner_argv)
    execution_configuration = runner_module.execution_configuration(parsed)
    spawn = [float(v) for v in pilot["spawn_ground_xyz_m"]]
    goal_b = [float(v) for v in pilot["goals"][1]["ground_xyz_m"]]
    metadata_points = [spawn] + [[float(v) for v in goal["ground_xyz_m"]] for goal in pilot["goals"]]
    return {
        "schema_version": 1,
        "revision": "p2b-two-goal-pilot-prelaunch-r1",
        "profile": "diagnostic_simulator_truth_known_map_full_two_goal",
        "execution_source_sha256": patched_runner_sha,
        "execution_manifest_sha256": execution_manifest_sha,
        "execution_configuration": execution_configuration,
        "frozen_assets": baseline_scope["frozen_assets"],
        "platform_segment": {
            "start_ground_xyz_m": spawn,
            "goal_ground_xyz_m": goal_b,
            "nominal_body_height_m": float(pilot["nominal_body_height_m"]),
            "start_tangent_yaw_radians": float(pilot["spawn_yaw_rad"]),
            "semantics": "terrain_ground_xyz_m",
            "arc_length_xy_m": route_arc_length_xy(metadata_points),
            "note": "Scope metadata only; external-goal mode receives targets through backend HTTP.",
        },
        "pilot_goals": pilot["goals"],
        "resource_ceiling": {"simulation_seconds": pilot["max_sim_seconds"], "wall_seconds": pilot["max_wall_seconds"]},
        "ros_domain_id": 94,
        "tcp_ports": {"telemetry": 46240, "command": 46241, "http": 8765, "pct": 47631},
        "claim": (
            "Known-map + truth-pose diagnostic full P2B pilot. No actual LLM, Cortex, SLAM, "
            "or physical robot actuation. Acceptance requires two confirmed arrivals, one confirmed cancel, "
            "no reset/pose injection, and independent metrics review."
        ),
    }


def package_manifest(run_dir: Path) -> dict:
    files = []
    include_roots = ["bridge", "backend_adapter", "backend_ros", "navigation_service", "pct_runtime", "inputs", "config"]
    for root_name in include_roots:
        for path in sorted((run_dir / root_name).rglob("*")):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            rel = path.relative_to(run_dir).as_posix()
            files.append({"path": rel, "sha256": sha256(path), "bytes": path.stat().st_size})
    top_level = ["pilot_driver.py", "remote_worker.py", "source_env_hashes.json", "RUNBOOK.md"]
    if (run_dir / WALK_REVIEW_SCRIPT.name).exists():
        top_level.append(WALK_REVIEW_SCRIPT.name)
    for rel in top_level:
        path = run_dir / rel
        files.append({"path": rel, "sha256": sha256(path), "bytes": path.stat().st_size})
    return {"schema_version": 1, "root": str(run_dir), "files": files}


def check_linked_package_files(run_dir: Path, manifest: dict, pairs: Iterable[Tuple[str, str]], known: Dict[str, str]) -> int:
    """Linked or fallback-copied package files must hash as their frozen source manifests record."""
    hashes = {item["path"]: item["sha256"] for item in manifest["files"]}
    checked = 0
    for src, dst in pairs:
        rel = Path(dst).relative_to(run_dir).as_posix()
        want = known.get(rel) or sha256(Path(src))
        if hashes.get(rel) != want:
            raise RuntimeError("linked package file differs from its frozen source: " + rel)
        checked += 1
    return checked


def pilot_driver_source() -> str:
    return r'''#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path
import time
import urllib.error
import urllib.request


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def post_json(base, endpoint, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(base + endpoint, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=10.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(base, endpoint):
    with urllib.request.urlopen(base + endpoint, timeout=10.0) as resp:
        return json.loads(resp.read().decode("utf-8"))


def snapshot_ok(snapshot, run_id, max_age_s=2.0):
    if snapshot.get("run_id") != run_id:
        return False
    if not isinstance(snapshot.get("applied_command"), dict):
        return False
    measured = snapshot.get("measured")
    if not isinstance(measured, dict):
        return False
    if not isinstance(measured.get("base_xyz"), list) or len(measured.get("base_xyz")) != 3:
        return False
    if not isinstance(measured.get("base_quat_wxyz"), list) or len(measured.get("base_quat_wxyz")) != 4:
        return False
    for key in ["horizontal_speed_mps", "yaw_rate_radps", "command_obs_error"]:
        if key not in measured:
            return False
    if snapshot.get("wall_monotonic_ns") is None:
        return False
    age = (time.monotonic_ns() - int(snapshot["wall_monotonic_ns"])) / 1e9
    return 0.0 <= age <= max_age_s


def wait_snapshot(path, run_id, min_sim_s=0.0, timeout_s=120.0):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        try:
            snap = read_json(path)
        except Exception:
            time.sleep(0.05)
            continue
        last = snap
        if snapshot_ok(snap, run_id) and float(snap.get("sim_time_s", 0.0)) >= min_sim_s:
            return snap
        time.sleep(0.05)
    raise RuntimeError("fresh runner snapshot unavailable; last=%r" % (last,))


def xy_distance(a, b):
    return math.hypot(float(a[0]) - float(b[0]), float(a[1]) - float(b[1]))


def current_body_xyz(snapshot):
    measured = snapshot.get("measured") or {}
    xyz = measured.get("base_xyz")
    if not isinstance(xyz, list) or len(xyz) != 3:
        raise RuntimeError("snapshot missing measured.base_xyz")
    return [float(x) for x in xyz]


def state_terminal_for(state, request_id, status):
    for item in state.get("terminal_results", []):
        if item.get("request_id") == request_id and item.get("status") == status:
            return item
    jobs = state.get("jobs") or {}
    item = jobs.get(request_id)
    if isinstance(item, dict) and item.get("status") == status:
        return item
    return None


def owner_none_is_not_success(state):
    service = state.get("service") or {}
    return service.get("current_owner") is None


def wait_terminal(base, request_id, status, journal, timeout_s=120.0):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        state = get_json(base, "/state")
        last = state
        journal.append({"event": "state_poll", "request_id": request_id, "want": status, "state": state, "wall_monotonic_ns": time.monotonic_ns()})
        terminal = state_terminal_for(state, request_id, status)
        if terminal is not None:
            return terminal
        # owner None alone is explicitly recorded but never accepted as success.
        if owner_none_is_not_success(state):
            pass
        time.sleep(0.1)
    raise RuntimeError("timed out waiting for %s status %s; last=%r" % (request_id, status, last))


def wait_http_ready(base, journal, snapshot_path, run_id, observed_epoch, timeout_s=120.0):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        try:
            snap = wait_snapshot(snapshot_path, run_id, timeout_s=2.0)
            state = get_json(base, "/state")
        except Exception as exc:
            last = str(exc)
            time.sleep(0.1)
            continue
        journal.append({"event": "http_ready_poll", "state": state, "snapshot": snap, "wall_monotonic_ns": time.monotonic_ns()})
        readiness = state.get("readiness") or {}
        applied_ready = readiness.get("applied_snapshot") or {}
        body_pose = state.get("measurement_body_pose")
        if (
            state.get("run_id") == run_id
            and int(state.get("run_epoch_ns", 0)) == int(observed_epoch)
            and readiness.get("body_pose_ready") is True
            and isinstance(body_pose, dict)
            and applied_ready.get("configured") is True
            and applied_ready.get("ready") is True
            and snapshot_ok(snap, run_id)
        ):
            return state
        last = state
        time.sleep(0.1)
    raise RuntimeError("HTTP backend not ready with body pose and applied snapshot; last=%r" % (last,))


def wait_displacement(snapshot_path, run_id, start_xyz, min_distance_m, journal, timeout_s=120.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        snap = wait_snapshot(snapshot_path, run_id, timeout_s=2.0)
        body = current_body_xyz(snap)
        distance = xy_distance(body, start_xyz)
        journal.append({"event": "cancel_distance_poll", "distance_xy_m": distance, "snapshot": snap, "wall_monotonic_ns": time.monotonic_ns()})
        if distance >= min_distance_m:
            return snap
        time.sleep(0.05)
    raise RuntimeError("cancel displacement threshold %.3f m not reached" % min_distance_m)


def wait_post_stop(snapshot_path, run_id, dwell_sim_s, thresholds, journal, timeout_s=120.0):
    deadline = time.monotonic() + timeout_s
    start_sim = None
    last_good = None
    while time.monotonic() < deadline:
        snap = wait_snapshot(snapshot_path, run_id, timeout_s=2.0)
        measured = snap.get("measured") or {}
        applied = snap.get("applied_command") or {}
        vx = float(applied.get("vx", 0.0))
        vy = float(applied.get("vy", 0.0))
        wz = float(applied.get("wz", 0.0))
        cmd_ok = math.hypot(vx, vy) <= thresholds["cmd"] and abs(wz) <= thresholds["cmd"]
        speed_ok = abs(float(measured.get("horizontal_speed_mps", 999.0))) <= thresholds["speed"]
        yaw_ok = abs(float(measured.get("yaw_rate_radps", 999.0))) <= thresholds["yaw"]
        if cmd_ok and speed_ok and yaw_ok:
            if start_sim is None:
                start_sim = float(snap.get("sim_time_s", 0.0))
            last_good = snap
            if float(snap.get("sim_time_s", 0.0)) - start_sim >= dwell_sim_s:
                journal.append({"event": "post_stop_proof", "snapshot": snap, "dwell_start_sim_s": start_sim, "wall_monotonic_ns": time.monotonic_ns()})
                return snap
        else:
            start_sim = None
        journal.append({"event": "post_stop_poll", "cmd_ok": cmd_ok, "speed_ok": speed_ok, "yaw_ok": yaw_ok, "snapshot": snap, "wall_monotonic_ns": time.monotonic_ns()})
        time.sleep(0.05)
    raise RuntimeError("post-stop proof dwell not reached; last_good=%r" % (last_good,))


def flush_journal(run_root, journal):
    write_json(Path(run_root) / "artifacts/pilot_journal_live.json", {"events": journal})


def finish_request(path, run_id, request_id, observed_epoch, status, note):
    path = Path(path)
    payload = {
        "schema_version": 1,
        "run_id": run_id,
        "request_id": request_id,
        "observed_run_epoch_ns": int(observed_epoch),
        "requested_at_monotonic_ns": time.monotonic_ns(),
        "backend_terminal_status": status,
        "note": note,
    }
    tmp = path.with_name(path.name + ".tmp")
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--http-port", type=int, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--cancel-displacement-m", type=float, default=0.4)
    args = parser.parse_args()
    if not (math.isfinite(args.cancel_displacement_m) and args.cancel_displacement_m >= 0.4):
        parser.error("--cancel-displacement-m must be a finite value of at least 0.4")
    run_root = Path(args.run_root)
    pilot = read_json(run_root / "inputs/pilot.json")
    snapshot_path = run_root / "artifacts/external_episode/current_command.json"
    finish_path = run_root / "artifacts/external_episode/finish_request.json"
    journal = []
    base = "http://127.0.0.1:%d" % args.http_port
    thresholds = {"cmd": pilot["stop_command_norm"], "speed": pilot["stop_speed_mps"], "yaw": pilot["stop_yaw_rate_radps"]}
    final_status = "FAILED"
    observed_epoch = 0
    try:
        initial = wait_snapshot(snapshot_path, args.run_id, min_sim_s=0.0)
        observed_epoch = int(initial["run_epoch_ns"])
        start_xyz = current_body_xyz(initial)
        journal.append({"event": "initial_cancel_reference_snapshot", "snapshot": initial, "start_xyz": start_xyz, "wall_monotonic_ns": time.monotonic_ns()})
        flush_journal(run_root, journal)
        ready = wait_http_ready(base, journal, snapshot_path, args.run_id, observed_epoch)
        journal.append({"event": "backend_ready", "state": ready})
        flush_journal(run_root, journal)

        goal_a = pilot["goals"][0]
        goal_b = pilot["goals"][1]
        request_a1 = args.run_id + "-goal-a-attempt-1"
        payload_a1 = {"request_id": request_a1, "goal_id": "goal-a", "target_ground_xyz": goal_a["ground_xyz_m"], "frame": pilot["frame_id"], "map_epoch": "flat_nominal", "map_revision": 1}
        resp = post_json(base, "/goal", payload_a1)
        journal.append({"event": "post_goal", "payload": payload_a1, "response": resp, "snapshot": read_json(snapshot_path), "wall_monotonic_ns": time.monotonic_ns()})
        flush_journal(run_root, journal)
        if resp.get("ok") is not True:
            raise RuntimeError("goal-a attempt1 rejected: %r" % (resp,))
        moved = wait_displacement(snapshot_path, args.run_id, start_xyz, args.cancel_displacement_m, journal)
        cancel_resp = post_json(base, "/cancel", {"request_id": args.run_id + "-cancel-goal-a-attempt-1", "target_request_id": request_a1})
        journal.append({"event": "post_cancel", "response": cancel_resp, "trigger_snapshot": moved, "cancel_displacement_m": args.cancel_displacement_m, "wall_monotonic_ns": time.monotonic_ns()})
        flush_journal(run_root, journal)
        wait_terminal(base, request_a1, "cancelled", journal, timeout_s=120.0)
        wait_post_stop(snapshot_path, args.run_id, pilot["stop_dwell_sim_seconds"], thresholds, journal, timeout_s=120.0)

        request_a2 = args.run_id + "-goal-a-attempt-2"
        payload_a2 = {"request_id": request_a2, "goal_id": "goal-a", "target_ground_xyz": goal_a["ground_xyz_m"], "frame": pilot["frame_id"], "map_epoch": "flat_nominal", "map_revision": 1}
        resp = post_json(base, "/goal", payload_a2)
        journal.append({"event": "post_goal", "payload": payload_a2, "response": resp, "snapshot": read_json(snapshot_path), "wall_monotonic_ns": time.monotonic_ns()})
        flush_journal(run_root, journal)
        if resp.get("ok") is not True:
            raise RuntimeError("goal-a attempt2 rejected: %r" % (resp,))
        wait_terminal(base, request_a2, "arrived", journal, timeout_s=240.0)

        request_b = args.run_id + "-goal-b"
        payload_b = {"request_id": request_b, "goal_id": "goal-b", "target_ground_xyz": goal_b["ground_xyz_m"], "frame": pilot["frame_id"], "map_epoch": "flat_nominal", "map_revision": 1}
        resp = post_json(base, "/goal", payload_b)
        journal.append({"event": "post_goal", "payload": payload_b, "response": resp, "snapshot": read_json(snapshot_path), "wall_monotonic_ns": time.monotonic_ns()})
        flush_journal(run_root, journal)
        if resp.get("ok") is not True:
            raise RuntimeError("goal-b rejected: %r" % (resp,))
        wait_terminal(base, request_b, "arrived", journal, timeout_s=240.0)
        final_status = "FINISHED"
        finish_request(finish_path, args.run_id, args.run_id + "-finish", observed_epoch, "FINISHED", "two arrivals and one explicit cancel confirmed by backend")
        write_json(run_root / "artifacts/pilot_journal.json", {"passed": True, "events": journal})
        return 0
    except Exception as exc:
        journal.append({"event": "driver_error", "error": str(exc), "wall_monotonic_ns": time.monotonic_ns()})
        flush_journal(run_root, journal)
        try:
            post_json(base, "/cancel", {"request_id": args.run_id + "-failure-cancel"})
        except Exception as cancel_exc:
            journal.append({"event": "failure_cancel_error", "error": str(cancel_exc), "wall_monotonic_ns": time.monotonic_ns()})
        finish_request(finish_path, args.run_id, args.run_id + "-failed-finish", observed_epoch, "FAILED", str(exc))
        write_json(run_root / "artifacts/pilot_journal.json", {"passed": False, "error": str(exc), "events": journal})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
'''


def remote_worker_source() -> str:
    return r'''#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import socket
import subprocess
import sys
import threading
import time


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_manifest(root, manifest):
    root = Path(root)
    for entry in manifest["files"]:
        path = root / entry["path"]
        if sha256(path) != entry["sha256"]:
            raise RuntimeError("manifest mismatch: " + entry["path"])


def verify_v12_runtime(remote_runtime, expected):
    remote_runtime = Path(remote_runtime)
    for rel, digest in expected.items():
        path = remote_runtime / rel
        if sha256(path) != digest:
            raise RuntimeError("remote V12 runtime SHA-256 mismatch: " + rel)


def artifact_hashes(root):
    root = Path(root)
    result = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        result[rel] = sha256(path)
    return result


''' + scan_gate_source() + "\n\nGPU_SAMPLE_INTERVAL_S = %r\n" % GPU_SAMPLE_INTERVAL_S + r'''

def query_gpus(timeout_s=2.0):
    proc = subprocess.run(
        ["nvidia-smi", "--query-gpu=index,memory.used,memory.total,utilization.gpu", "--format=csv,noheader,nounits"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_s, check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("nvidia-smi exit %d: %s" % (proc.returncode, proc.stderr.strip()[-500:]))
    rows = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        values = [value.strip() for value in line.split(",")]
        try:
            utilization = float(values[3])
        except ValueError:
            utilization = None
        rows.append({"index": int(values[0]), "memory_used_mib": float(values[1]), "memory_total_mib": float(values[2]), "utilization_percent": utilization})
    if not rows:
        raise RuntimeError("nvidia-smi returned no GPU rows")
    return rows


class GpuSampler:
    """Device-wide nvidia-smi sampling in a background thread, one JSONL row per interval."""

    def __init__(self, path, interval_s):
        self.path = Path(path)
        self.interval_s = float(interval_s)
        self.stop_event = threading.Event()
        self.thread = None
        self.started = None
        self.summary = {
            "interval_s": self.interval_s,
            "samples_path": self.path.name,
            "scope": "device-wide nvidia-smi memory.used; includes any process on the GPU, not only this run",
            "sample_count": 0,
            "error_count": 0,
            "errors": [],
            "first_sample": None,
            "peak_memory_used_mib": None,
            "peak_elapsed_s": None,
            "peak_by_gpu": {},
        }

    def start(self):
        self.started = time.monotonic()
        self.thread = threading.Thread(target=self._loop, name="gpu-sampler", daemon=True)
        self.thread.start()

    def _record(self, row):
        summary = self.summary
        if summary["first_sample"] is None:
            summary["first_sample"] = row
        for gpu in row["gpus"]:
            peak = summary["peak_by_gpu"].setdefault(str(gpu["index"]), {"memory_used_mib": None})
            if peak["memory_used_mib"] is None or gpu["memory_used_mib"] > peak["memory_used_mib"]:
                peak.update(memory_used_mib=gpu["memory_used_mib"], memory_total_mib=gpu["memory_total_mib"], elapsed_s=row["elapsed_s"])
            if summary["peak_memory_used_mib"] is None or gpu["memory_used_mib"] > summary["peak_memory_used_mib"]:
                summary["peak_memory_used_mib"] = gpu["memory_used_mib"]
                summary["peak_elapsed_s"] = row["elapsed_s"]

    def _loop(self):
        with self.path.open("w", encoding="utf-8") as stream:
            while True:
                row = {"monotonic_ns": time.monotonic_ns(), "wall_time_ns": time.time_ns(), "elapsed_s": time.monotonic() - self.started}
                try:
                    row["gpus"] = query_gpus()
                    self._record(row)
                except Exception as exc:
                    row["error"] = "%s: %s" % (exc.__class__.__name__, exc)
                    self.summary["error_count"] += 1
                    if len(self.summary["errors"]) < 5:
                        self.summary["errors"].append(row["error"])
                stream.write(json.dumps(row, sort_keys=True) + "\n")
                stream.flush()
                self.summary["sample_count"] += 1
                if self.stop_event.wait(self.interval_s):
                    return

    def stop(self):
        if self.thread is None:
            return dict(self.summary, started=False)
        self.stop_event.set()
        self.thread.join(timeout=5.0)
        return dict(self.summary, started=True, stopped=not self.thread.is_alive(), sampled_wall_s=time.monotonic() - self.started)


def ensure_tcp_port_free(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", int(port)))
    except OSError as exc:
        raise RuntimeError("TCP port is not free on 127.0.0.1:%s (%s)" % (port, exc))
    finally:
        sock.close()


def ensure_container_absent(name):
    if subprocess.run(["podman", "container", "exists", name]).returncode == 0:
        raise RuntimeError("refusing to reuse existing container: " + name)


def wait_snapshot(path, run_id, min_sim_s, timeout_s=600.0, runner_proc=None):
    path = Path(path)
    runtime_error_path = path.parents[1] / "runner_output/runtime_error.json"
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        if runtime_error_path.exists():
            raise RuntimeError("runner_runtime_error_before_snapshot: " + runtime_error_path.read_text(encoding="utf-8")[:1000])
        if runner_proc is not None:
            exit_code = runner_proc.poll()
            if exit_code is not None:
                raise RuntimeError("runner_exited_before_snapshot: exit_code=%s last=%r" % (exit_code, last))
        try:
            snap = read_json(path)
        except Exception:
            time.sleep(0.05)
            continue
        last = snap
        if snap.get("run_id") == run_id and int(snap.get("run_epoch_ns", 0)) > 0 and float(snap.get("sim_time_s", 0.0)) >= min_sim_s:
            return snap
        time.sleep(0.05)
    raise RuntimeError("runner snapshot not ready; last=%r" % (last,))


def conda_python_script(command, pythonpath, ros_domain_id):
    env_exports = [
        "export PYTHONPATH=" + shlex.quote(pythonpath),
        "export PYTHONDONTWRITEBYTECODE=1",
        "export ROS_DOMAIN_ID=" + shlex.quote(str(ros_domain_id)),
        "export ROS_LOCALHOST_ONLY=1",
    ]
    return " && ".join([
        "source /home/sun/miniconda3/etc/profile.d/conda.sh",
        "conda activate isaaclab",
    ] + env_exports + [command])


def terminate_proc(proc, name, grace=20):
    record = {"name": name, "pid": getattr(proc, "pid", None), "action": "none", "ok": True}
    if proc is None:
        record["reason"] = "missing"
        return record
    if proc.poll() is not None:
        record["reason"] = "already_exited"
        record["returncode"] = proc.poll()
        return record
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        record["action"] = "sigterm"
    except ProcessLookupError:
        record["reason"] = "process_lookup_error"
        return record
    try:
        proc.wait(timeout=grace)
        record["returncode"] = proc.poll()
        return record
    except subprocess.TimeoutExpired:
        record["action"] = "sigkill"
        try:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5.0)
            record["returncode"] = proc.poll()
            return record
        except BaseException as exc:
            record["ok"] = False
            record["error_type"] = exc.__class__.__name__
            record["error"] = str(exc)
            return record
    except BaseException as exc:
        record["ok"] = False
        record["error_type"] = exc.__class__.__name__
        record["error"] = str(exc)
        return record


def cleanup_container(container, timeout_s=20.0):
    record = {"container": container, "timeout_s": timeout_s, "ok": False}
    try:
        proc = subprocess.run(["podman", "rm", "-f", container], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout_s, check=False)
        record.update({"returncode": proc.returncode, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:], "ok": proc.returncode == 0})
    except subprocess.TimeoutExpired as exc:
        record.update({"timeout": True, "error_type": "TimeoutExpired", "error": str(exc)})
    except BaseException as exc:
        record.update({"error_type": exc.__class__.__name__, "error": str(exc)})
    return record


def tcp_port_free_record(port):
    try:
        ensure_tcp_port_free(port)
        return {"port": int(port), "free": True}
    except BaseException as exc:
        return {"port": int(port), "free": False, "error_type": exc.__class__.__name__, "error": str(exc)}


def finalize_result_artifacts(artifacts, result, phase):
    record = {"phase": phase, "ok": False, "monotonic_ns": time.monotonic_ns()}
    try:
        result["last_result_write_phase"] = phase
        write_json(artifacts / "result.json", result)
        hashes = artifact_hashes(artifacts)
        write_json(artifacts / "artifact_hashes.json", hashes)
        record.update({"ok": True, "artifact_count": len(hashes)})
    except BaseException as exc:
        record.update({"error_type": exc.__class__.__name__, "error": str(exc)})
    return record


def start_popen(cmd, log_path, env=None):
    log = open(log_path, "w", encoding="utf-8")
    return subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--foxy-image-id", required=True)
    parser.add_argument("--pct-image-id", required=True)
    parser.add_argument("--remote-v12-runtime", required=True)
    parser.add_argument("--remote-checkpoint", required=True)
    parser.add_argument("--remote-scan-workspace", required=True)
    parser.add_argument("--runner-argv-json", required=True)
    parser.add_argument("--ros-domain-id", type=int, required=True)
    parser.add_argument("--telemetry-port", type=int, required=True)
    parser.add_argument("--command-port", type=int, required=True)
    parser.add_argument("--http-port", type=int, required=True)
    parser.add_argument("--pct-port", type=int, required=True)
    parser.add_argument("--cancel-displacement-m", type=float, required=True)
    args = parser.parse_args()

    started_monotonic = time.monotonic()
    run_root = Path(args.run_root)
    artifacts = run_root / "artifacts"
    logs = artifacts / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    result = {
        "passed": False,
        "claim": "known-map truth-pose diagnostic two-goal pilot; no LLM/Cortex/SLAM/physical robot",
        "remote_scan_workspace": args.remote_scan_workspace,
        "cancel_displacement_m": args.cancel_displacement_m,
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    gpu_sampler = GpuSampler(artifacts / "gpu_samples.jsonl", GPU_SAMPLE_INTERVAL_S)
    scan_ws = None
    scan_identity = None
    processes = []
    owned_containers = []
    bridge_container = "vla-p2b-bridge-" + run_root.name.lower().replace("_", "-")
    backend_container = "vla-p2b-backend-" + run_root.name.lower().replace("_", "-")
    pct_container = "vla-p2b-pct-" + run_root.name.lower().replace("_", "-")
    try:
        gpu_sampler.start()
        verify_manifest(run_root, read_json(run_root / "inputs/package_manifest.json"))
        verify_manifest(run_root / "bridge", read_json(run_root / "inputs/execution_manifest.json"))
        source_env = read_json(run_root / "source_env_hashes.json")
        if sha256(Path(args.remote_checkpoint)) != source_env["v12_checkpoint_sha256"]:
            raise RuntimeError("remote checkpoint SHA-256 mismatch")
        verify_v12_runtime(args.remote_v12_runtime, source_env["v12_runtime_expected"])
        if not args.remote_scan_workspace:
            raise RuntimeError("accepted remote SCAN workspace is required")
        scan_ws = Path(args.remote_scan_workspace)
        scan_identity = source_env.get("accepted_scan_build_identity")
        scan_gate = scan_workspace_gate(scan_ws, scan_identity)
        write_json(artifacts / "scan_workspace_gate.json", scan_gate)
        result["scan_workspace_gate"] = {"passed": scan_gate["passed"], "errors": scan_gate["errors"], "record": "scan_workspace_gate.json"}
        if not scan_gate["passed"]:
            raise RuntimeError("remote SCAN workspace hash gate failed: " + "; ".join(scan_gate["errors"]))
        for port in [args.telemetry_port, args.command_port, args.http_port, args.pct_port]:
            ensure_tcp_port_free(port)
        for container in [bridge_container, backend_container, pct_container]:
            ensure_container_absent(container)

        runner_argv = json.loads(args.runner_argv_json)
        image_checks = {}
        for label, image_id in [("foxy", args.foxy_image_id), ("pct_humble", args.pct_image_id)]:
            inspected = subprocess.check_output(["podman", "image", "inspect", "--format", "{{.Id}}", image_id], text=True).strip().removeprefix("sha256:")
            if inspected != image_id:
                raise RuntimeError(label + " image identity mismatch: " + inspected)
            image_checks[label] = inspected
        write_json(artifacts / "env_identity.json", {
            "images": image_checks,
            "remote_v12_runtime": args.remote_v12_runtime,
            "remote_checkpoint": args.remote_checkpoint,
            "remote_scan_workspace": args.remote_scan_workspace,
            "ros_domain_id": args.ros_domain_id,
            "ros_localhost_only": 1,
            "ros_container_ipc": "host",
            "transport_qualification": "backend_ros/qualification/cross_container_20260916T161849Z: isolated IPC failed, host IPC passed",
            "ports": {"telemetry": args.telemetry_port, "command": args.command_port, "http": args.http_port, "pct": args.pct_port},
        })

        bridge_cmd = [
            "podman", "run", "--rm", "--pull=never", "--network=host",
            "--ipc=host",
            "--name", bridge_container,
            "-e", "ROS_DOMAIN_ID=%d" % args.ros_domain_id,
            "-e", "ROS_LOCALHOST_ONLY=1",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-e", "PYTHONPATH=/bridge",
            "-v", str(run_root / "bridge") + ":/bridge:ro",
            "-v", str(run_root / "config") + ":/config:ro",
            args.foxy_image_id,
            "bash", "-lc",
            "source /opt/ros/foxy/setup.bash && exec python3 -c "
            + repr("from lite3_sim_bridge.foxy_bridge_node import main; main()")
            + " --ros-args --params-file /config/foxy_bridge_two_goal.yaml",
        ]
        write_json(artifacts / "bridge_command.json", bridge_cmd)
        bridge_proc = start_popen(bridge_cmd, logs / "foxy_bridge.log")
        processes.append(("bridge", bridge_proc))
        owned_containers.append(bridge_container)
        time.sleep(2.0)
        if bridge_proc.poll() is not None:
            raise RuntimeError("Foxy bridge exited early")

        runtime_source = Path(args.remote_v12_runtime) / "source"
        runner_pythonpath = ":".join([
            str(run_root / "bridge"),
            str(runtime_source / "rsl_rl"),
            str(runtime_source / "robot_lab"),
            os.environ.get("PYTHONPATH", ""),
        ])
        import_check = """
import importlib.util, json, os, sys
from pathlib import Path

def origin(name):
    spec = importlib.util.find_spec(name)
    if spec is None or spec.origin is None:
        raise SystemExit(name + ' spec not found')
    return str(Path(spec.origin).resolve())
robot = origin('robot_lab')
rsl = origin('rsl_rl')
expected_robot = str(Path(os.environ['EXPECTED_ROBOT_LAB_ROOT']).resolve())
expected_rsl = str(Path(os.environ['EXPECTED_RSL_RL_ROOT']).resolve())
if not robot.startswith(expected_robot + os.sep):
    raise SystemExit('robot_lab spec from unexpected path: ' + robot)
if not rsl.startswith(expected_rsl + os.sep):
    raise SystemExit('rsl_rl spec from unexpected path: ' + rsl)
print(json.dumps({'check_mode':'find_spec_no_module_execution','sys_executable':sys.executable,'conda_prefix':os.environ.get('CONDA_PREFIX'),'robot_lab_spec_origin':robot,'rsl_rl_spec_origin':rsl}, sort_keys=True))
"""
        env = os.environ.copy()
        env["EXPECTED_ROBOT_LAB_ROOT"] = str(runtime_source / "robot_lab")
        env["EXPECTED_RSL_RL_ROOT"] = str(runtime_source / "rsl_rl")
        import_cmd = ["bash", "-lc", conda_python_script("python -c " + shlex.quote(import_check), runner_pythonpath, args.ros_domain_id)]
        import_out = subprocess.check_output(import_cmd, text=True, stderr=subprocess.STDOUT, env=env)
        (logs / "isaac_import_check.log").write_text(import_out, encoding="utf-8")
        write_json(artifacts / "isaac_import_identity.json", json.loads(import_out.strip().splitlines()[-1]))

        runner_cmd = ["bash", "-lc", conda_python_script("exec python -m lite3_sim_bridge.run_pct_scan_building " + shlex.join(runner_argv), runner_pythonpath, args.ros_domain_id)]
        write_json(artifacts / "runner_command.json", runner_cmd)
        runner_proc = start_popen(runner_cmd, logs / "patched_isaac_runner.log", env=os.environ.copy())
        processes.append(("runner", runner_proc))
        snapshot_path = run_root / "artifacts/external_episode/current_command.json"
        first_snapshot = wait_snapshot(snapshot_path, run_root.name, 0.0, timeout_s=600.0, runner_proc=runner_proc)
        run_epoch_ns = int(first_snapshot["run_epoch_ns"])
        result["run_epoch_ns"] = run_epoch_ns

        pct_cmd = [
            "podman", "run", "--rm", "--pull=never", "--network=host", "--name", pct_container,
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-v", str(run_root) + ":/qualification:ro",
            args.pct_image_id,
            "bash", "-lc",
            "source /opt/ros/humble/setup.bash && "
            "export PYTHONPATH=/qualification/backend_adapter:/qualification/pct_runtime/python:${PYTHONPATH:-} && "
            "export LD_LIBRARY_PATH=/qualification/pct_runtime/lib:${LD_LIBRARY_PATH:-} && "
            "exec python3 -m backend_adapter.pct_worker "
            "--host 127.0.0.1 --port %d " % args.pct_port +
            "--pct-source-root /qualification/pct_runtime/python "
            "--rsg-root /qualification/inputs "
            "--tomogram-path /qualification/inputs/new_building.pickle "
            "--reference-height-m 0.35",
        ]
        write_json(artifacts / "pct_worker_command.json", pct_cmd)
        pct_proc = start_popen(pct_cmd, logs / "pct_worker.log")
        processes.append(("pct_worker", pct_proc))
        owned_containers.append(pct_container)
        time.sleep(2.0)
        if pct_proc.poll() is not None:
            raise RuntimeError("PCT worker exited early")

        backend_config_path = run_root / "config/p2b_backend_ros.two_goal.json"
        backend_cfg = read_json(backend_config_path)
        backend_cfg["run_epoch_ns"] = run_epoch_ns
        backend_cfg["applied_evidence"]["current_command_path"] = str(snapshot_path)
        backend_cfg["applied_evidence"]["finish_request_path"] = str(run_root / "artifacts/external_episode/finish_request.json")
        write_json(backend_config_path, backend_cfg)
        resolved_backend_config_path = artifacts / "resolved_backend_config.json"
        write_json(resolved_backend_config_path, {
            "schema_version": 1,
            "source_config": str(backend_config_path),
            "run_epoch_ns_source": "fresh runner current_command.json",
            "resolved_config": backend_cfg,
        })

        backend_script = """set -eo pipefail
source /opt/ros/foxy/setup.bash
source /workspace/install/setup.bash
export ROS_DOMAIN_ID={ros_domain_id}
export ROS_LOCALHOST_ONLY=1
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/backend_ros:/backend_adapter:/bridge:${{PYTHONPATH:-}}
ros2 run scan_planner scan_planner_node --ros-args --params-file /config/planner.yaml -r body_pose:=/quad_0/body_pose -r sensor_pose:=/quad_0/lidar_pose -r cloud:=/quad_0/cloud > /logs/scan_planner_node.log 2>&1 &
scan_pid=$!
ros2 run scan_planner closed_loop_controller --ros-args --params-file /config/controller.yaml -r body_pose:=/quad_0/body_pose > /logs/closed_loop_controller.log 2>&1 &
controller_pid=$!
cleanup() {{
  kill "$scan_pid" "$controller_pid" 2>/dev/null || true
}}
trap cleanup EXIT INT TERM
python3 -m p2b_backend_ros.node --config /config/p2b_backend_ros.two_goal.json --run-id {run_id} --run-epoch-ns {run_epoch_ns} --applied-snapshot {snapshot_path} --finish-request {finish_request_path} --pct-port {pct_port} --http-port {http_port}
""".format(
            ros_domain_id=args.ros_domain_id,
            run_id=shlex.quote(run_root.name),
            run_epoch_ns=run_epoch_ns,
            snapshot_path=shlex.quote(str(snapshot_path)),
            finish_request_path=shlex.quote(str(run_root / "artifacts/external_episode/finish_request.json")),
            pct_port=args.pct_port,
            http_port=args.http_port,
        )
        backend_cmd = [
            "podman", "run", "--rm", "--pull=never", "--network=host", "--name", backend_container,
            "--ipc=host",
            "-e", "ROS_DOMAIN_ID=%d" % args.ros_domain_id,
            "-e", "ROS_LOCALHOST_ONLY=1",
            "-v", str(run_root / "backend_ros") + ":/backend_ros:ro",
            "-v", str(run_root / "backend_adapter") + ":/backend_adapter:ro",
            "-v", str(run_root / "navigation_service") + ":/navigation_service:ro",
            "-v", str(run_root / "bridge") + ":/bridge:ro",
            "-v", str(run_root / "config") + ":/config:rw",
            "-v", str(logs) + ":/logs:rw",
            "-v", str(run_root) + ":" + str(run_root) + ":rw",
            "-v", str(scan_ws) + ":/workspace:ro",
            args.foxy_image_id,
            "bash", "-lc", backend_script,
        ]
        write_json(artifacts / "backend_command.json", backend_cmd)
        backend_proc = start_popen(backend_cmd, logs / "backend_container.log")
        processes.append(("backend", backend_proc))
        owned_containers.append(backend_container)
        time.sleep(2.0)
        if backend_proc.poll() is not None:
            raise RuntimeError("backend/SCAN container exited early")

        driver_cmd = ["python3", str(run_root / "pilot_driver.py"), "--run-root", str(run_root), "--http-port", str(args.http_port), "--run-id", run_root.name, "--cancel-displacement-m", repr(args.cancel_displacement_m)]
        write_json(artifacts / "pilot_driver_command.json", driver_cmd)
        driver = subprocess.run(driver_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=1200)
        (logs / "pilot_driver.log").write_text(driver.stdout, encoding="utf-8")
        result["pilot_driver_exit_code"] = driver.returncode
        if driver.returncode != 0:
            raise RuntimeError("pilot driver failed with exit %d" % driver.returncode)
        runner_exit = runner_proc.wait(timeout=1200.0)
        result["runner_exit_code"] = runner_exit
        if runner_exit != 0:
            raise RuntimeError("runner exit code %s" % runner_exit)
        summary = read_json(run_root / "artifacts/runner_output/summary.json")
        result["runner_summary"] = summary
        if summary.get("status") != "EXTERNAL_EPISODE_FINISHED":
            raise RuntimeError("unexpected runner summary status: " + str(summary.get("status")))
        result["passed"] = True
    except BaseException as exc:
        result["error"] = str(exc)
        result["error_type"] = exc.__class__.__name__
        raise
    finally:
        cleanup_records = []
        finalization_records = []
        try:
            for _name, proc in reversed(processes):
                cleanup_records.append(terminate_proc(proc, _name))
        except BaseException as exc:
            cleanup_records.append({"scope": "process_cleanup", "ok": False, "error_type": exc.__class__.__name__, "error": str(exc)})
        result["process_cleanup"] = cleanup_records
        finalization_records.append(finalize_result_artifacts(artifacts, result, "after_process_cleanup"))

        container_records = []
        for container in reversed(owned_containers):
            try:
                container_records.append(cleanup_container(container, timeout_s=20.0))
            except BaseException as exc:
                container_records.append({"container": container, "ok": False, "error_type": exc.__class__.__name__, "error": str(exc)})
        result["container_cleanup"] = container_records
        result["post_cleanup_ports"] = {
            "telemetry": tcp_port_free_record(args.telemetry_port),
            "command": tcp_port_free_record(args.command_port),
            "http": tcp_port_free_record(args.http_port),
            "pct": tcp_port_free_record(args.pct_port),
        }
        try:
            result["gpu_memory"] = gpu_sampler.stop()
        except BaseException as exc:
            result["gpu_memory"] = {"ok": False, "error_type": exc.__class__.__name__, "error": str(exc)}
        if scan_ws is not None and (result.get("scan_workspace_gate") or {}).get("passed"):
            try:
                scan_gate_after = scan_workspace_gate(scan_ws, scan_identity)
                write_json(artifacts / "scan_workspace_gate_after.json", scan_gate_after)
                result["scan_workspace_gate_after"] = {"passed": scan_gate_after["passed"], "errors": scan_gate_after["errors"], "record": "scan_workspace_gate_after.json"}
            except BaseException as exc:
                result["scan_workspace_gate_after"] = {"passed": False, "error_type": exc.__class__.__name__, "error": str(exc)}
            if not result["scan_workspace_gate_after"]["passed"]:
                result["passed"] = False
        result["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        result["remote_wall_seconds"] = time.monotonic() - started_monotonic
        result["remote_wall_seconds_scope"] = "remote_worker.py main() start to cleanup end, before the last result writes"
        result["cleanup_errors"] = [item for item in cleanup_records + container_records if item.get("ok") is False]
        result["artifact_finalization"] = finalization_records
        finalization_records.append(finalize_result_artifacts(artifacts, result, "after_container_cleanup"))
        result["artifact_finalization"] = finalization_records
        finalize_result_artifacts(artifacts, result, "final")
    # Reached only when the episode raised nothing: a post-run SCAN workspace
    # change must still fail the remote command instead of exiting 0.
    if (result.get("scan_workspace_gate_after") or {}).get("passed") is not True:
        raise SystemExit("SCAN workspace hash gate failed after the run; see artifacts/scan_workspace_gate_after.json")


if __name__ == "__main__":
    main()
'''


def remote_only_record_source(remote_run: str) -> str:
    """Python run on the execution host after the worker: hash the files left there."""
    return textwrap.dedent(
        f"""\
        import hashlib, json
        from pathlib import Path
        run = Path({remote_run!r})
        artifacts = run / "artifacts"
        manifest = json.loads((artifacts / "artifact_hashes.json").read_text(encoding="utf-8"))
        files = []
        for rel in {list(REMOTE_ONLY_BULK_FILES)!r}:
            path = artifacts / rel
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1 << 20), b""):
                    digest.update(chunk)
            files.append({{"path": rel, "remote_path": str(path), "bytes": path.stat().st_size,
                           "sha256": digest.hexdigest(), "manifest_sha256": manifest.get(rel)}})
        all_match = all(item["sha256"] == item["manifest_sha256"] for item in files)
        record = {{"schema_version": 1, "run_id": run.name, "remote_run": str(run),
                   "manifest": "artifacts/artifact_hashes.json", "files": files, "all_match": all_match,
                   "policy": "--remote-only-bulk: these bytes stay in the execution copy; only hashes and sizes return"}}
        (run / {REMOTE_ONLY_RECORD!r}).write_text(json.dumps(record, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
        if not all_match:
            raise SystemExit("remote-only artifact hash differs from artifact_hashes.json")
        """
    )


def walk_review_guard_source(remote_run: str) -> str:
    """Python run on the execution host before the render.

    The render uses the GPU encoder, so it starts only after remote_worker.py
    wrote its final result without cleanup errors and none of the process
    groups it started (bridge, Isaac runner, PCT, backend) is still alive. A
    local ssh timeout or disconnect can leave the worker running; this guard
    then refuses instead of sharing the GPU with Isaac. The guard record is
    written to walk_review/render_guard.json and returned with the review.
    """
    return textwrap.dedent(
        f"""\
        import json, os, subprocess, time
        from pathlib import Path
        run = Path({remote_run!r})
        result_path = run / "artifacts" / "result.json"
        record = {{"schema_version": 1, "checked_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "result_json": str(result_path), "problems": [], "alive_process_groups": []}}
        result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {{}}
        if not result_path.is_file():
            record["problems"].append("artifacts/result.json is missing")
        record["last_result_write_phase"] = result.get("last_result_write_phase")
        if result.get("last_result_write_phase") != "final":
            record["problems"].append("remote worker has not written its final result")
        if result.get("cleanup_errors"):
            record["problems"].append("remote worker cleanup reported errors")
        groups = sorted({{int(item["pid"]) for item in result.get("process_cleanup") or [] if item.get("pid")}})
        record["process_groups"] = groups
        for pgid in groups:
            try:
                os.killpg(pgid, 0)
            except ProcessLookupError:
                continue
            except PermissionError:
                pass
            record["alive_process_groups"].append(pgid)
        if record["alive_process_groups"]:
            record["problems"].append("worker process groups still alive: %s" % record["alive_process_groups"])
        try:
            apps = subprocess.run(["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
                                   "--format=csv,noheader"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True, timeout=10, check=False)
            record["gpu_compute_apps"] = {{"returncode": apps.returncode, "stdout": apps.stdout[-2000:]}}
        except Exception as exc:
            record["gpu_compute_apps"] = {{"error": "%s: %s" % (exc.__class__.__name__, exc)}}
        record["render_allowed"] = not record["problems"]
        out = run / {WALK_REVIEW_DIR!r}
        out.mkdir(exist_ok=True)
        (out / "render_guard.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
        if record["problems"]:
            raise SystemExit("walk review not started: " + "; ".join(record["problems"]))
        """
    )


def walk_review_remote_script(remote_run: str) -> str:
    """Shell command for the execution host: render the walk review from the remote original video.

    The guard (walk_review_guard_source) runs first with the system python3.
    ffmpeg/ffprobe are resolved in the non-login ssh shell (the one the display
    observer used for h264_nvenc) before conda changes PATH; the render uses the
    isaaclab conda Python like the runner. libx264 is the recorded fallback.
    """
    render = shlex.join([
        "python", remote_run + "/" + WALK_REVIEW_SCRIPT.name, remote_run,
        "--artifacts-dir", remote_run + "/artifacts",
        "--video", remote_run + "/artifacts/" + REMOTE_ONLY_BULK_FILES[1],
        "--output", remote_run + "/" + WALK_REVIEW_DIR + "/walk_review.mp4",
        "--encoder", "h264_nvenc",
        "--fallback-encoder", "libx264",
    ])
    inner = " && ".join([
        "source /home/sun/miniconda3/etc/profile.d/conda.sh",
        "conda activate isaaclab",
        "export PYTHONDONTWRITEBYTECODE=1",
        "exec " + render + ' --ffmpeg "$FFMPEG_BIN" --ffprobe "$FFPROBE_BIN"',
    ])
    guard = "python3 -c " + shlex.quote(walk_review_guard_source(remote_run))
    return guard + ' && FFMPEG_BIN="$(command -v ffmpeg)" FFPROBE_BIN="$(command -v ffprobe)" bash -lc ' + shlex.quote(inner)


def runbook_text(run_id: str, remote_run: str, cancel_displacement_m: float = CANCEL_DISPLACEMENT_MIN_M,
                 remote_only_bulk: bool = False, stance_hold: str = LEGACY_PACKAGE_STANCE_HOLD,
                 stance_entry_kd: str = LEGACY_PACKAGE_STANCE_ENTRY_KD) -> str:
    text = runbook_base_text(run_id, remote_run, cancel_displacement_m)
    if stance_hold == "auto":
        text += """
Stance hold (`--stance-hold auto`): the patched runner hands the joints from the V12 policy to a PD stand hold (Kp 60 / Kd 1) after an exactly zero command with a quiet, loaded and balanced four-foot stance, and blends back over 0.25 s when a command arrives (`isaac_runner/stance_hold.py`). The runner writes `runner_output/stance_hold_setup.json`, per-step `stance_*` fields in `metrics.jsonl` and a `stance_hold` summary block. `isaac_runner/analyze_stance_hold.py` reports the AC5 transition checks; the 41 review checks are unchanged.
"""
        text += f"""
Entry variant: `--stance-entry-kd {stance_entry_kd}` (`stance_hold.py` `STANCE_ENTRY_KD_MODES`; recorded in `run_request.json` and the runner summary `stance_hold.entry_kd`).
"""
    if remote_only_bulk:
        text += f"""
Remote-only bulk return (`--remote-only-bulk`): `{"`, `".join(REMOTE_ONLY_BULK_FILES)}` stay in `{remote_run}/artifacts/`. After the worker ends, the host hashes them into `{REMOTE_ONLY_RECORD}`, checks that the worker wrote its final result and that none of its process groups is alive (`{WALK_REVIEW_DIR}/render_guard.json`), then renders `{WALK_REVIEW_DIR}/walk_review.mp4` from the remote original video with `h264_nvenc` (fallback `libx264`), and returns the record and the review. Local verification accepts exactly those two files as absent. `p2b_execution/review_two_goal.py` accepts the same two files as absent only when the returned `{REMOTE_ONLY_RECORD}` has `all_match` true and hashes equal to `artifact_hashes.json` (task decision D9, 2026-09-17); its other 40 checks are unchanged.
"""
    return text


def runbook_base_text(run_id: str, remote_run: str, cancel_displacement_m: float) -> str:
    return f"""# P2B two-goal pilot prepared package

Run id: `{run_id}`
Remote run root: `{remote_run}`

This package is prepared for the actual P2B two-goal diagnostic pilot. It is not a completed run and it is not navigation evidence until executed after lead approval.

Claim boundary if later executed and accepted: known-map + truth-pose diagnostic integration of patched Isaac runner, native V12 policy, real Foxy bridge, real Humble PCT worker, real Foxy SCAN/controller, backend_adapter and backend_ros. It does not include an actual LLM, Cortex planner, SLAM, or physical robot interface.

Runtime sequence encoded by `remote_worker.py`:

1. Start device-wide GPU sampling (`artifacts/gpu_samples.jsonl`, every {GPU_SAMPLE_INTERVAL_S:g} s). Verify package, frozen inputs, patched bridge, local PCT runtime files, V12 runtime and checkpoint hashes, then hash the mounted SCAN workspace `src/` and `install/` trees against the accepted build identity (`artifacts/scan_workspace_gate.json`) and refuse on any difference.
2. Confirm localhost ports are free and owned container names are absent.
3. Start the Foxy bridge only.
4. Start one Isaac runner with `--case flat_nominal` and `--external-goal-mode`.
5. Read fresh `current_command.json` to capture the runner `run_epoch_ns`.
6. Start the Humble PCT worker.
7. Start SCAN, controller and backend_ros using that `run_epoch_ns`; it does not start a second bridge.
8. Run `pilot_driver.py`: POST goal-a attempt 1, cancel after at least {cancel_displacement_m:g} m measured displacement, require explicit cancelled plus post-cancel stop proof, POST goal-a attempt 2 and require arrived, POST goal-b and require arrived, then write the valid finish request.
9. After cleanup, re-hash the SCAN workspace (`artifacts/scan_workspace_gate_after.json`) and record the GPU peak and remote wall time in `artifacts/result.json`.

HTTP contract used by the driver:

- `GET /state`
- `POST /goal` with `request_id`, `goal_id`, `target_ground_xyz`, `frame`, `map_epoch`, `map_revision`
- `POST /cancel` with a new `request_id` and, for the planned cancel, `target_request_id`

Owner `None` alone is logged but never treated as success. The finish request is written as `FINISHED` only after explicit terminal records for one cancel and two arrivals. Failure paths attempt cancel/hold, write a `FAILED` finish request, preserve logs and return nonzero.
"""


def write_file(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        os.chmod(path, 0o755)


def prepare(args) -> Tuple[Path, dict]:
    run_id = args.run_id or datetime.now(timezone.utc).strftime("two_goal_%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", run_id):
        raise ValueError("run_id must be filesystem and shell friendly")
    local_run = Path(args.local_runs_root) / run_id
    if local_run.exists():
        raise FileExistsError("local run already exists: " + str(local_run))
    remote_run = args.remote_root.rstrip("/") + "/" + run_id

    input_manifest = verify_input_manifest()
    bridge_expected = verify_bridge_source()
    v12_expected = verify_v12_reference()
    pct_manifest = verify_pct_runtime_manifest()
    pilot = json.loads((P2B / "inputs/pilot.json").read_text(encoding="utf-8"))
    validate_pilot(pilot)
    cancel_check = cancel_trigger_check(args.cancel_displacement_m, pilot)
    stance_hold = stance_hold_setting(args)
    stance_entry_kd = stance_entry_kd_setting(args)
    scan_gate = None
    if args.accepted_scan_build_dir:
        scan_gate = build_scan_workspace_gate(
            Path(args.accepted_scan_build_dir), args.remote_scan_workspace, args.allow_missing_install_identity
        )
    baseline_scope = json.loads((P2B / "baseline_config/native_nominal_scope.json").read_text(encoding="utf-8"))

    (local_run / "inputs").mkdir(parents=True)
    (local_run / "config").mkdir()
    (local_run / "artifacts").mkdir()
    # Frozen inputs and the PCT runtime are never rewritten in the package, so
    # they are hardlinked. Config files are rewritten below and the bridge tree
    # receives the patched runner, so those stay real copies.
    storage = PackageStorage()
    for rel in ["inputs/building.usda", "inputs/new_building.pickle", "inputs/pilot.json", "input_manifest.json"]:
        src = P2B / rel
        dst = local_run / "inputs" / ("input_manifest.json" if rel == "input_manifest.json" else Path(rel).name)
        storage.link_or_copy(src, dst)
    for name in ["bridge.yaml", "controller.yaml", "planner.yaml", "native_nominal_scope.json", "pct_inputs.json"]:
        shutil.copy2(P2B / "baseline_config" / name, local_run / "config" / name)
    make_scan_runtime_configs(local_run / "config")
    copytree_clean(PCT_RUNTIME, local_run / "pct_runtime", copy_function=storage.link_or_copy)
    copytree_clean(BRIDGE_REF, local_run / "bridge")
    remote_only_bulk = bool(getattr(args, "remote_only_bulk", False))
    if remote_only_bulk:
        shutil.copy2(WALK_REVIEW_SCRIPT, local_run / WALK_REVIEW_SCRIPT.name)
    copytree_clean(BACKEND_ADAPTER, local_run / "backend_adapter")
    copytree_clean(BACKEND_ROS, local_run / "backend_ros")
    copytree_clean(NAVIGATION_SERVICE, local_run / "navigation_service")

    materializer = load_materializer()
    patched_runner = local_run / "bridge/lite3_sim_bridge/run_pct_scan_building.py"
    materializer.main([
        "--output", str(patched_runner),
        "--patch", str(local_run / "runner_external_episode.patch"),
        "--hashes", str(local_run / "runner_source_hashes.json"),
    ])
    patched_runner_sha = sha256(patched_runner)
    execution_manifest = bridge_manifest(local_run / "bridge", remote_run + "/bridge")
    write_json(local_run / "inputs/execution_manifest.json", execution_manifest)
    execution_manifest_sha = sha256(local_run / "inputs/execution_manifest.json")

    write_json(local_run / "inputs/two_goal_route_artifact.json", make_route_artifact(pilot))
    make_bridge_config(local_run / "config/foxy_bridge_two_goal.yaml", args.telemetry_port, args.command_port)
    make_backend_config(local_run / "config/p2b_backend_ros.two_goal.json", pilot, run_id, args.http_port, args.pct_port)
    runner_argv = build_runner_argv(args, remote_run, run_id, pilot)
    runner_module = import_runner(patched_runner)
    scope = make_scope(runner_module, runner_argv, execution_manifest_sha, patched_runner_sha, pilot, baseline_scope)
    write_json(local_run / "inputs/two_goal_scope.json", scope)
    write_file(local_run / "pilot_driver.py", pilot_driver_source(), executable=True)
    write_file(local_run / "remote_worker.py", remote_worker_source(), executable=True)
    write_file(local_run / "RUNBOOK.md", runbook_text(run_id, remote_run, cancel_check["cancel_displacement_m"], remote_only_bulk,
                                                    stance_hold, stance_entry_kd))

    v12_runtime_expected = {
        rel.removeprefix("source/v12_runtime/"): digest
        for rel, digest in v12_expected.items()
        if rel.startswith("source/v12_runtime/")
    }
    scan_identity = None
    if args.accepted_scan_build_dir:
        scan_path = Path(args.accepted_scan_build_dir)
        if not scan_path.exists():
            raise FileNotFoundError("accepted SCAN build dir missing: " + str(scan_path))
        install_identity_path = scan_path / "install_identity.json"
        scan_identity = {
            "local_path": str(scan_path),
            "files": dir_hashes(scan_path, max_bytes=64 * 1024 * 1024),
            "install_identity_path": str(install_identity_path) if install_identity_path.exists() else None,
            "install_identity_sha256": sha256(install_identity_path) if install_identity_path.exists() else None,
            "install_identity": json.loads(install_identity_path.read_text(encoding="utf-8")) if install_identity_path.exists() else None,
            "workspace_gate": scan_gate,
        }
    source_hashes = {
        "bridge_reference_expected": bridge_expected,
        "patched_runner_sha256": patched_runner_sha,
        "execution_manifest_sha256": execution_manifest_sha,
        "input_manifest_sha256": sha256(P2B / "input_manifest.json"),
        "pilot_sha256": sha256(P2B / "inputs/pilot.json"),
        "pct_runtime_manifest_sha256": sha256(P2B / "pct_runtime_manifest.json"),
        "pct_runtime_manifest": pct_manifest,
        "v12_runtime_expected": v12_runtime_expected,
        "v12_runtime_expected_file_count": len(v12_runtime_expected),
        "v12_checkpoint_sha256": sha256(V12_REF / "source/checkpoint/model_149999.pt"),
        "foxy_image_id": FOXY_IMAGE_ID,
        "pct_humble_image_id": PCT_HUMBLE_IMAGE_ID,
        "backend_adapter": dir_hashes(BACKEND_ADAPTER),
        "backend_ros": dir_hashes(BACKEND_ROS),
        "navigation_service": dir_hashes(NAVIGATION_SERVICE),
        "accepted_scan_build_identity": scan_identity,
        "accepted_scan_build_required_for_execute": True,
    }
    if remote_only_bulk:
        source_hashes["walk_review_tool"] = {"path": WALK_REVIEW_SCRIPT.name, "sha256": sha256(WALK_REVIEW_SCRIPT)}
    write_json(local_run / "source_env_hashes.json", source_hashes)
    manifest = package_manifest(local_run)
    known_hashes = dict(pct_manifest["files"]) if isinstance(pct_manifest["files"], dict) else {
        item["path"]: item["sha256"] for item in pct_manifest["files"]}
    known_hashes.update({item["path"]: item["sha256"] for item in input_manifest["files"] if item["path"].startswith("inputs/")})
    known_hashes["inputs/input_manifest.json"] = source_hashes["input_manifest_sha256"]
    known_hashes["inputs/pilot.json"] = source_hashes["pilot_sha256"]
    package_storage = storage.record(local_run)
    package_storage["linked_files_hash_checked"] = check_linked_package_files(local_run, manifest, storage.pairs, known_hashes)
    write_json(local_run / "inputs/package_manifest.json", manifest)

    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", args.host]
    runner_argv_json = json.dumps(runner_argv, separators=(",", ":"))
    remote_scan = args.remote_scan_workspace or "PENDING_ACCEPTED_SCAN_WORKSPACE"
    commands = {
        "remote_run": remote_run,
        "requires_lead_authorized_execute": True,
        "accepted_scan_build_required": True,
        "sync_whitelist": ["bridge/", "backend_adapter/", "backend_ros/", "navigation_service/", "pct_runtime/", "inputs/", "config/", "pilot_driver.py", "remote_worker.py", "source_env_hashes.json", "RUNBOOK.md"],
        "mkdir": ssh + [
            "python3 - <<'PY'\n"
            "from pathlib import Path\n"
            f"p=Path({remote_run!r})\n"
            "assert not p.exists(), p\n"
            "p.mkdir(parents=True)\n"
            "PY"
        ],
        "sync": [
            "rsync", "-a", "--delete",
            "--include=/bridge/***", "--include=/backend_adapter/***", "--include=/backend_ros/***", "--include=/navigation_service/***", "--include=/pct_runtime/***",
            "--include=/inputs/***", "--include=/config/***", "--include=/pilot_driver.py", "--include=/remote_worker.py", "--include=/source_env_hashes.json", "--include=/RUNBOOK.md",
            "--exclude=*", str(local_run) + "/", f"{args.host}:{remote_run}/",
        ],
        "run": ssh + [
            shlex.join([
                "python3", remote_run + "/remote_worker.py",
                "--run-root", remote_run,
                "--foxy-image-id", FOXY_IMAGE_ID,
                "--pct-image-id", PCT_HUMBLE_IMAGE_ID,
                "--remote-v12-runtime", args.remote_v12_runtime,
                "--remote-checkpoint", args.remote_checkpoint,
                "--remote-scan-workspace", remote_scan,
                "--runner-argv-json", runner_argv_json,
                "--ros-domain-id", str(args.ros_domain_id),
                "--telemetry-port", str(args.telemetry_port),
                "--command-port", str(args.command_port),
                "--http-port", str(args.http_port),
                "--pct-port", str(args.pct_port),
                "--cancel-displacement-m", repr(cancel_check["cancel_displacement_m"]),
            ])
        ],
        "collect": ["rsync", "-a", f"{args.host}:{remote_run}/artifacts/", str(local_run / "returned_artifacts") + "/"],
    }
    if remote_only_bulk:
        commands["sync_whitelist"].append(WALK_REVIEW_SCRIPT.name)
        commands["sync"].insert(commands["sync"].index("--exclude=*"), "--include=/" + WALK_REVIEW_SCRIPT.name)
        commands["collect"] = ["rsync", "-a"] + ["--exclude=/" + rel for rel in REMOTE_ONLY_BULK_FILES] + commands["collect"][2:]
        commands["remote_only_record"] = ssh + ["python3 - <<'PY'\n" + remote_only_record_source(remote_run) + "PY"]
        commands["walk_review"] = ssh + [walk_review_remote_script(remote_run)]
        commands["collect_extras"] = [
            "rsync", "-a", "--include=/" + REMOTE_ONLY_RECORD, "--include=/" + WALK_REVIEW_DIR + "/***", "--exclude=*",
            f"{args.host}:{remote_run}/", str(local_run) + "/",
        ]
        commands["collect_sequence"] = ["collect", "remote_only_record", "walk_review", "collect_extras"]
        commands["remote_only_bulk"] = {
            "files": list(REMOTE_ONLY_BULK_FILES),
            "record": REMOTE_ONLY_RECORD,
            "walk_review": WALK_REVIEW_DIR + "/walk_review.mp4",
        }
    write_json(local_run / "commands.json", commands)
    write_json(local_run / "run_request.json", {
        "schema_version": 1,
        "run_id": run_id,
        "local_run": str(local_run),
        "remote_run": remote_run,
        "default_execute": False,
        "execute_requires": ["--execute", "--lead-authorized-execute", "--remote-scan-workspace accepted path", "--accepted-scan-build-dir identity capture"],
        "case": "flat_nominal",
        "contact_policy": "native_v12",
        "duration_seconds": pilot["max_sim_seconds"],
        "max_wall_seconds": pilot["max_wall_seconds"],
        "ports": {"telemetry": args.telemetry_port, "command": args.command_port, "http": args.http_port, "pct": args.pct_port},
        "ros_domain_id": args.ros_domain_id,
        "claim_boundary": "Prepared only. If later executed and independently accepted, this is known-map/truth-pose P2B diagnostic integration, not LLM/Cortex/SLAM or physical robot evidence.",
        "cancel_displacement_m": cancel_check["cancel_displacement_m"],
        "cancel_trigger_check": cancel_check,
        "allow_missing_install_identity": bool(args.allow_missing_install_identity),
        "scan_workspace_gate": None if scan_gate is None else {
            "accepted_scan_build_dir": str(args.accepted_scan_build_dir),
            "source_manifest_sha256": scan_gate["source_manifest_sha256"],
            "source_file_count": len(scan_gate["expected_source_files"]),
            "install_identity_present": scan_gate["install_identity_present"],
            "installed_file_count": scan_gate["installed_file_count"],
            "allow_missing_install_identity": scan_gate["allow_missing_install_identity"],
            "expected_remote_workspace": scan_gate["expected_remote_workspace"],
            "remote_records": scan_gate["remote_records"],
        },
        "resource_recording": {
            "gpu_samples": "artifacts/gpu_samples.jsonl (nvidia-smi memory.used/memory.total/utilization.gpu, device-wide)",
            "gpu_sample_interval_s": GPU_SAMPLE_INTERVAL_S,
            "gpu_summary": "artifacts/result.json gpu_memory",
            "remote_wall_seconds": "artifacts/result.json remote_wall_seconds",
            "host_wall_seconds": "return_verdict.json host_wall_seconds",
        },
        "remote_only_bulk": remote_only_bulk,
        "remote_only_bulk_detail": None if not remote_only_bulk else {
            "remote_only_files": list(REMOTE_ONLY_BULK_FILES),
            "record": REMOTE_ONLY_RECORD + " (run package root; SHA-256 and bytes measured on the execution host)",
            "walk_review": WALK_REVIEW_DIR + "/walk_review.mp4 and walk_review.json, rendered remotely with h264_nvenc, libx264 fallback",
            "walk_review_tool_sha256": sha256(WALK_REVIEW_SCRIPT),
            "review_two_goal_note": "review_two_goal.py (D9, 2026-09-17) accepts exactly these two files as absent when remote_only_artifacts.json has all_match true and hashes equal to artifact_hashes.json; its other 40 checks are unchanged",
        },
        "package_storage": package_storage,
        "stance_hold": stance_hold,
        "stance_entry_kd": stance_entry_kd,
    })
    return local_run, commands


def run_command(label: str, command: List[str], log_path: Path, timeout: int = 1800) -> None:
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
    log_path.write_text(result.stdout, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"{label} failed with exit {result.returncode}: {result.stdout[-3000:]}")


def load_prepared_run(args) -> Tuple[Path, dict]:
    if not args.run_id:
        raise ValueError("--execute with an existing package requires --run-id")
    local_run = Path(args.local_runs_root) / args.run_id
    if not local_run.exists():
        raise FileNotFoundError("prepared local run does not exist: " + str(local_run))
    manifest = json.loads((local_run / "inputs/package_manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = local_run / entry["path"]
        if sha256(path) != entry["sha256"]:
            raise RuntimeError("prepared package hash mismatch: " + entry["path"])
    commands = json.loads((local_run / "commands.json").read_text(encoding="utf-8"))
    return local_run, commands


def verify_returned_artifacts(local_run: Path, remote_only: bool = False) -> dict:
    returned = local_run / "returned_artifacts"
    expected = json.loads((returned / "artifact_hashes.json").read_text(encoding="utf-8"))
    actual = {
        path.relative_to(returned).as_posix(): sha256(path)
        for path in sorted(p for p in returned.rglob("*") if p.is_file())
        if path.relative_to(returned).as_posix() != "artifact_hashes.json"
    }
    expected_no_self = {k: v for k, v in expected.items() if k != "artifact_hashes.json"}
    if not remote_only:
        return {"returned_hashes_match": actual == expected_no_self, "expected_count": len(expected_no_self), "actual_count": len(actual)}
    record = check_remote_only_record(local_run, expected_no_self)
    missing = sorted(set(expected_no_self) - set(actual))
    accepted = [rel for rel in missing if rel in record["declared"]]
    undeclared = [rel for rel in missing if rel not in record["declared"]]
    unexpected = sorted(set(actual) - set(expected_no_self))
    mismatched = sorted(rel for rel in set(actual) & set(expected_no_self) if actual[rel] != expected_no_self[rel])
    return {
        "returned_hashes_match": not (record["errors"] or undeclared or unexpected or mismatched),
        "expected_count": len(expected_no_self),
        "actual_count": len(actual),
        "remote_only_accepted": accepted,
        "missing_not_remote_only": undeclared,
        "unexpected": unexpected,
        "mismatched": mismatched,
        "remote_only_record": {k: v for k, v in record.items() if k != "declared"},
    }


def check_remote_only_record(local_run: Path, expected: Dict[str, str]) -> dict:
    """The returned record must declare exactly REMOTE_ONLY_BULK_FILES with manifest-equal hashes."""
    path = local_run / REMOTE_ONLY_RECORD
    result = {"path": REMOTE_ONLY_RECORD, "errors": [], "declared": {}}
    if not path.is_file():
        result["errors"].append(REMOTE_ONLY_RECORD + " was not returned")
        return result
    result["sha256"] = sha256(path)
    record = json.loads(path.read_text(encoding="utf-8"))
    files = record.get("files") or []
    declared = {item.get("path"): item for item in files}
    if len(declared) != len(files) or sorted(declared) != sorted(REMOTE_ONLY_BULK_FILES):
        result["errors"].append("declared files %s differ from the fixed list %s" % (sorted(map(str, declared)), list(REMOTE_ONLY_BULK_FILES)))
    for rel, item in declared.items():
        if rel not in REMOTE_ONLY_BULK_FILES:
            continue
        if item.get("sha256") != expected.get(rel) or item.get("manifest_sha256") != expected.get(rel):
            result["errors"].append(rel + ": remote hash differs from artifact_hashes.json")
        if not isinstance(item.get("bytes"), int) or item["bytes"] <= 0:
            result["errors"].append(rel + ": remote size missing")
    if record.get("all_match") is not True:
        result["errors"].append("remote record all_match is not true")
    result["declared"] = {rel: item for rel, item in declared.items() if rel in REMOTE_ONLY_BULK_FILES}
    result["files"] = [{k: item.get(k) for k in ("path", "bytes", "sha256")} for item in files]
    return result


def verify_walk_review(local_run: Path) -> dict:
    """The returned walk review must match its sidecar and name the manifest's input hashes."""
    base = local_run / WALK_REVIEW_DIR
    video, sidecar_path = base / "walk_review.mp4", base / "walk_review.json"
    result = {"video_present": video.is_file(), "sidecar_present": sidecar_path.is_file(), "ok": False, "errors": []}
    guard_path = base / "render_guard.json"
    if guard_path.is_file():
        guard = json.loads(guard_path.read_text(encoding="utf-8"))
        result["render_guard"] = {k: guard.get(k) for k in ("render_allowed", "problems", "alive_process_groups", "last_result_write_phase")}
    else:
        result["render_guard"] = None
    if not (result["video_present"] and result["sidecar_present"]):
        result["errors"].append("walk review video or sidecar was not returned")
        return result
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    manifest = json.loads((local_run / "returned_artifacts/artifact_hashes.json").read_text(encoding="utf-8"))
    result.update({"sha256": sha256(video), "bytes": video.stat().st_size,
                   "encoder_used": (sidecar.get("encoder") or {}).get("used"),
                   "frames": (sidecar.get("output") or {}).get("frames")})
    if (result["render_guard"] or {}).get("render_allowed") is not True:
        result["errors"].append("walk review has no passing render_guard.json")
    if result["sha256"] != (sidecar.get("output") or {}).get("sha256"):
        result["errors"].append("walk_review.mp4 hash differs from its sidecar")
    inputs = sidecar.get("inputs") or {}
    for name, rel in (("video", REMOTE_ONLY_BULK_FILES[1]), ("camera_frames", "runner_output/camera_frames.jsonl"),
                      ("metrics", "runner_output/metrics.jsonl"), ("pilot_journal", "pilot_journal.json")):
        if (inputs.get(name) or {}).get("sha256") != manifest.get(rel):
            result["errors"].append("walk review input %s is not the manifest's %s" % (name, rel))
    result["ok"] = not result["errors"]
    return result


def execute(args, local_run: Path, commands: dict) -> None:
    if not args.lead_authorized_execute:
        raise RuntimeError("refusing physics execution without --lead-authorized-execute")
    if not args.remote_scan_workspace or args.remote_scan_workspace == "PENDING_ACCEPTED_SCAN_WORKSPACE":
        raise RuntimeError("refusing execution without accepted --remote-scan-workspace")
    source_env = json.loads((local_run / "source_env_hashes.json").read_text(encoding="utf-8"))
    if not source_env.get("accepted_scan_build_identity"):
        raise RuntimeError("refusing execution without captured accepted SCAN build identity")
    if not source_env["accepted_scan_build_identity"].get("workspace_gate"):
        raise RuntimeError("refusing execution: package predates the SCAN workspace hash gate")
    remote_only = bool(commands.get("remote_only_bulk"))
    if bool(getattr(args, "remote_only_bulk", False)) != remote_only:
        raise RuntimeError("--remote-only-bulk differs from the prepared package (package remote_only_bulk=%s)" % remote_only)
    request_path = local_run / "run_request.json"
    if request_path.is_file():
        prepared_request = json.loads(request_path.read_text(encoding="utf-8"))
        prepared_cancel = prepared_request.get("cancel_displacement_m", CANCEL_DISPLACEMENT_MIN_M)
        requested_cancel = float(getattr(args, "cancel_displacement_m", CANCEL_DISPLACEMENT_MIN_M))
        if float(prepared_cancel) != requested_cancel:
            raise RuntimeError(
                "--cancel-displacement-m %r differs from the prepared package (package cancel_displacement_m=%r)"
                % (requested_cancel, prepared_cancel)
            )
        # Packages prepared before the flag ran the runner without a stance hold; the
        # PRD D8 default change (auto) does not change that recorded meaning.
        prepared_stance = prepared_request.get("stance_hold", LEGACY_PACKAGE_STANCE_HOLD)
        requested_stance = stance_hold_setting(args)
        if prepared_stance != requested_stance:
            raise RuntimeError(
                "--stance-hold %r differs from the prepared package (package stance_hold=%r)"
                % (requested_stance, prepared_stance)
            )
        # Packages prepared before the flag ran the runner default entry (ramp).
        prepared_entry_kd = prepared_request.get("stance_entry_kd", LEGACY_PACKAGE_STANCE_ENTRY_KD)
        requested_entry_kd = stance_entry_kd_setting(args)
        if prepared_entry_kd != requested_entry_kd:
            raise RuntimeError(
                "--stance-entry-kd %r differs from the prepared package (package stance_entry_kd=%r)"
                % (requested_entry_kd, prepared_entry_kd)
            )
    logs = local_run / "host_logs"
    logs.mkdir(exist_ok=True)
    remote_started = False
    original_error = None
    collect_error = None
    verdict = {"remote_worker_started": False, "host_wall_seconds": {}}

    def timed(label: str, log_name: str, timeout: int = 1800) -> None:
        started = time.monotonic()
        try:
            run_command(label, commands[label], logs / log_name, timeout=timeout)
        finally:
            verdict["host_wall_seconds"][label] = time.monotonic() - started

    try:
        timed("mkdir", "00_mkdir.log")
        timed("sync", "01_sync.log")
        remote_started = True
        verdict["remote_worker_started"] = True
        timed("run", "02_remote_worker.log", timeout=1500)
    except Exception as exc:  # noqa: BLE001 - preserve failure and collect artifacts
        original_error = exc
        verdict["run_error"] = str(exc)
    finally:
        if remote_started and not remote_only:
            try:
                timed("collect", "03_collect.log")
                verdict.update(verify_returned_artifacts(local_run))
            except Exception as exc:  # noqa: BLE001
                collect_error = exc
                verdict["collect_error"] = str(exc)
        elif remote_started:
            collect_error = collect_remote_only(commands, timed, verdict, local_run)
    write_json(local_run / "return_verdict.json", verdict)
    if original_error is not None:
        if collect_error is not None:
            raise RuntimeError("remote run failed and collection failed; run_error=%s; collect_error=%s" % (original_error, collect_error)) from original_error
        raise original_error
    if collect_error is not None:
        raise collect_error
    if not verdict.get("returned_hashes_match"):
        raise RuntimeError("returned artifact hashes do not match")
    if remote_only and not (verdict.get("walk_review") or {}).get("ok"):
        raise RuntimeError("walk review was not returned and verified: %s" % (verdict.get("walk_review") or {}).get("errors"))


COLLECT_STEP_LOGS = {
    "collect": ("03_collect.log", 1800),
    "remote_only_record": ("04_remote_only_record.log", 600),
    "walk_review": ("05_walk_review.log", 1800),
    "collect_extras": ("06_collect_extras.log", 1800),
}


def collect_remote_only(commands: dict, timed, verdict: dict, local_run: Path) -> Optional[Exception]:
    """Run every collect step even after one fails, then verify; only a walk review failure is non-fatal here."""
    step_errors = {}
    for label in commands["collect_sequence"]:
        log_name, timeout = COLLECT_STEP_LOGS[label]
        try:
            timed(label, log_name, timeout)
        except Exception as exc:  # noqa: BLE001 - keep collecting the remaining evidence
            step_errors[label] = str(exc)
    verdict["collect_step_errors"] = step_errors
    try:
        verdict.update(verify_returned_artifacts(local_run, remote_only=True))
        verdict["walk_review"] = verify_walk_review(local_run)
    except Exception as exc:  # noqa: BLE001
        verdict["collect_error"] = str(exc)
        return exc
    fatal = {label: error for label, error in step_errors.items() if label != "walk_review"}
    if fatal:
        verdict["collect_error"] = "; ".join("%s: %s" % item for item in sorted(fatal.items()))
        return RuntimeError("collection step failed: " + verdict["collect_error"])
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--execute", action="store_true", default=False)
    parser.add_argument("--lead-authorized-execute", action="store_true", default=False)
    parser.add_argument("--host", default="gpu5070ti")
    parser.add_argument("--remote-root", default=DEFAULT_REMOTE_ROOT)
    parser.add_argument("--remote-v12-runtime", default=DEFAULT_REMOTE_V12)
    parser.add_argument("--remote-checkpoint", default=DEFAULT_REMOTE_CHECKPOINT)
    parser.add_argument("--accepted-scan-build-dir", default=None)
    parser.add_argument("--remote-scan-workspace", default=None)
    parser.add_argument("--local-runs-root", type=Path, default=HERE / "two_goal_runs")
    parser.add_argument("--telemetry-port", type=int, default=46240)
    parser.add_argument("--command-port", type=int, default=46241)
    parser.add_argument("--http-port", type=int, default=8765)
    parser.add_argument("--pct-port", type=int, default=47631)
    parser.add_argument("--ros-domain-id", type=int, default=94)
    parser.add_argument(
        "--cancel-displacement-m", type=float, default=CANCEL_DISPLACEMENT_MIN_M,
        help="Measured XY displacement that triggers the goal-a cancel; at least 0.40 m and >= 0.30 m short of goal A.",
    )
    parser.add_argument(
        "--stance-hold", choices=STANCE_HOLD_CHOICES, default=DEFAULT_STANCE_HOLD,
        help=(
            "Runner stance hold mode passed to the patched runner, default auto (PRD D8): auto enables the PD stand "
            "hold (stance_hold.py), off keeps the RL-only control path. A package prepared without this field ran off."
        ),
    )
    parser.add_argument(
        "--stance-entry-kd", choices=STANCE_ENTRY_KD_CHOICES, default=None,
        help=(
            "Stance hold entry variant, passed to the runner with --stance-hold auto only: ramp, step1 or step2p5 "
            "(PRD D5), or the xfade1s / xfade2s crossfade with a 1 s landing grace (PRD D6). Default xfade1s with "
            "--stance-hold auto (PRD D8); with --stance-hold off only ramp, the runner default, is accepted. A package "
            "prepared without this field ran ramp."
        ),
    )
    parser.add_argument(
        "--allow-missing-install-identity", action="store_true", default=False,
        help="Accept a SCAN build without install_identity.json; the remote gate then checks src/ only and records it.",
    )
    parser.add_argument(
        "--remote-only-bulk", action="store_true", default=False,
        help=(
            "Needs Dr Sun's approval. Leave runner_output/clouds.jsonl and third_person_master.mp4 on the execution "
            "host, return their hashes in remote_only_artifacts.json and a remotely rendered walk review. "
            "review_two_goal.py accepts exactly these two files as absent when that record matches (D9)."
        ),
    )
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        local_run, commands = prepare(args)
    except FileExistsError:
        if not args.execute:
            raise
        local_run, commands = load_prepared_run(args)
    if args.execute:
        execute(args, local_run, commands)
    print(json.dumps({"local_run": str(local_run), "remote_run": commands["remote_run"], "execute": bool(args.execute), "commands_file": str(local_run / "commands.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
