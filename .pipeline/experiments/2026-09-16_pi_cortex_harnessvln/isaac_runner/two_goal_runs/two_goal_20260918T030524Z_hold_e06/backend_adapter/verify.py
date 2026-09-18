#!/usr/bin/env python3
"""Local verification for the P2B backend adapter contract slice."""

from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import time
from typing import Dict, List

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parents[3]
CHECKS = ROOT / "checks"
OWNED = [ROOT / "backend_adapter", ROOT / "tests", ROOT / "config", ROOT / "patches", ROOT / "verify.py", ROOT / "qualify_pct_ipc.py", ROOT / "README.md", ROOT / "RESULT.md"]
REFERENCE_SOURCES = [
    REPO / "references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_foxy/src/plan_manage/src/scan_replan_fsm.cpp",
    REPO / "references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_foxy/src/plan_manage/src/closed_loop_controller.cpp",
    REPO / "references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_global/src/pct/pct_planner/pct_planner/planner_wrapper.py",
    REPO / "references/upstream/2026-09-16_lite3_isaac_harness_backend/source/machine-dog-nav/integration/lite3_sim_bridge/lite3_sim_bridge/run_pct_scan_building.py",
    REPO / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/navigation_service/core.py",
    REPO / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/SNAPSHOT_SCHEMA.md",
]


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def files_under(path: pathlib.Path) -> List[pathlib.Path]:
    if not path.exists():
        return []
    if path.is_file():
        return [path]
    return [p for p in sorted(path.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]


def run(cmd: List[str], cwd: pathlib.Path) -> Dict[str, object]:
    started = time.time()
    proc = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return {
        "cmd": cmd,
        "returncode": proc.returncode,
        "wall_seconds": round(time.time() - started, 3),
        "output": proc.stdout,
    }


def materializer_smoke() -> Dict[str, object]:
    source = REPO / "references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_foxy/src"
    started = time.time()
    with tempfile.TemporaryDirectory(prefix="p2b_materialize_verify_") as td:
        output = pathlib.Path(td) / "src"
        cmd = [sys.executable, "-m", "backend_adapter.materialize_overlay", "--source", str(source), "--output", str(output)]
        proc = subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        checks = {}
        if proc.returncode == 0:
            fsm = (output / "plan_manage/src/scan_replan_fsm.cpp").read_text(encoding="utf-8")
            controller = (output / "plan_manage/src/closed_loop_controller.cpp").read_text(encoding="utf-8")
            admission = (output / "scan_planner_msgs/msg/P2BAdmission.msg").read_text(encoding="utf-8")
            checks = {
                "consumer_field": "string consumer" in admission,
                "fsm_candidate_identity_before_mutation": "P2BIdentity candidate" in fsm and "active_p2b_identity_ = candidate" in fsm,
                "legacy_path_disabled_in_p2b_mode": "Ignoring legacy initial_path in explicit P2B typed-route mode" in fsm,
                "controller_consumer_discriminator": 'out.consumer = "controller"' in controller,
                "controller_cancel_tombstone": "cancelled_generation_high_water_" in controller and "generation_cancelled_before_spline" in controller,
                "controller_generation_high_water": "max_generation_seen_ = std::max(max_generation_seen_, generation_)" in controller,
                "controller_guard_before_geometry_mutation": controller.find("const bool incoming_has_p2b_identity") < controller.find("Eigen::MatrixXd points") < controller.find("traj_ = {position, position.getDerivative()"),
            }
        return {
            "cmd": cmd,
            "returncode": proc.returncode if all(checks.values()) else 1,
            "wall_seconds": round(time.time() - started, 3),
            "output": proc.stdout + ("\nchecks=" + json.dumps(checks, sort_keys=True)),
        }


def main() -> int:
    CHECKS.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    owned_hashes = {str(p.relative_to(REPO)): sha256(p) for root in OWNED for p in files_under(root)}
    reference_hashes = {str(p.relative_to(REPO)): sha256(p) for p in REFERENCE_SOURCES if p.exists()}
    commands = [
        [sys.executable, "-m", "compileall", "-q", str(ROOT / "backend_adapter")],
        [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"],
        [sys.executable, "-m", "backend_adapter.run_adapter", "--config", str(ROOT / "config/p2b_adapter.example.json"), "--print-contract"],
    ]
    results = [run(cmd, ROOT) for cmd in commands]
    results.append(materializer_smoke())
    ok = all(item["returncode"] == 0 for item in results)
    record = {
        "schema": "p2b_backend_adapter_verify_v1",
        "ok": ok,
        "timestamp_utc": ts,
        "python": sys.version,
        "owned_hashes": owned_hashes,
        "reference_hashes": reference_hashes,
        "commands": results,
        "claim_boundary": "contract tests only; no ROS graph, simulator, native PCT worker or Isaac episode launched",
    }
    out = CHECKS / ("verify_%s.json" % ts)
    out.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    latest = CHECKS / "latest_verify.json"
    latest.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"ok": ok, "record": str(out), "owned_files": len(owned_hashes)}, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
