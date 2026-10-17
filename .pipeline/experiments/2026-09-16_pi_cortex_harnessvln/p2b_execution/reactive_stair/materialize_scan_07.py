#!/usr/bin/env python3
"""Hash-gated SCAN candidate with a precomputed ETH-style support score."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
P2B = HERE.parent
SOURCE = P2B / "builds/scan_06"
OUTPUT = P2B / "builds/scan_07"
ETH_REFERENCE = Path(__file__).resolve().parents[5] / "references/upstream/2026-09-23_eth_stepfilter_reference/StepFilter.cpp"
EXPECTED_SOURCE_MANIFEST_SHA = "f3a3d93c70f89e037028be5fca9e972940955b221cc171f067bd021b56e17258"
EXPECTED_CANDIDATE_MANIFEST_SHA = "c825ece0a6c5127d7b3f1210d57c104a1770dbfbbb465c9c7823aff8b1367551"
EXPECTED_ETH_SHA = "cdcf18ef0b6396770ea779fd03683b757ddd78640bc4817205377713186920f2"
EXPECTED_GRID_H = "d883d4df1af47f14f04454f785e72f642915a66776520dbee323fb85fb343b46"
EXPECTED_GRID_CPP = "c3b11e5ad9b5802dd6a7415134f581c43638af5bc44e81b876694402d615ba8e"


class Refused(RuntimeError):
    pass


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gate() -> dict[str, str]:
    source_manifest = SOURCE / "source_sha256.json"
    candidate_manifest = SOURCE / "reactive_stair_candidate_manifest.json"
    if sha(source_manifest) != EXPECTED_SOURCE_MANIFEST_SHA or \
       sha(candidate_manifest) != EXPECTED_CANDIDATE_MANIFEST_SHA:
        raise Refused("scan_06 source identity changed")
    if sha(ETH_REFERENCE) != EXPECTED_ETH_SHA:
        raise Refused("pinned ETH StepFilter source identity changed")
    build = json.loads((SOURCE / "build_result.json").read_text())
    if build.get("passed") is not True or build.get("source_matches_before_after") is not True:
        raise Refused("scan_06 Foxy build identity not accepted")
    recorded = json.loads(source_manifest.read_text())
    if recorded.get("src/plan_env/include/plan_env/grid_map.h") != EXPECTED_GRID_H or \
       recorded.get("src/plan_env/src/grid_map.cpp") != EXPECTED_GRID_CPP:
        raise Refused("scan_06 GridMap hash mismatch")
    actual = {"src/" + path.relative_to(SOURCE / "src").as_posix(): sha(path)
              for path in (SOURCE / "src").rglob("*") if path.is_file() and "__pycache__" not in path.parts}
    if actual != recorded:
        missing = sorted(set(recorded) - set(actual))
        extra = sorted(set(actual) - set(recorded))
        changed = sorted(k for k in set(actual) & set(recorded) if actual[k] != recorded[k])
        raise Refused(f"scan_06 source gate: missing={missing}, extra={extra}, changed={changed}")
    return {path.removeprefix("src/"): value for path, value in recorded.items()}


def one(data: bytes, old: bytes, new: bytes, purpose: str) -> bytes:
    if data.count(old) != 1:
        raise Refused(f"{purpose}: expected one exact anchor, got {data.count(old)}")
    return data.replace(old, new)


def materialize() -> dict:
    if OUTPUT.exists():
        raise Refused("scan_07 already exists")
    base = gate()
    try:
        shutil.copytree(SOURCE / "src", OUTPUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        root = OUTPUT / "src"
        before = {path.relative_to(root).as_posix(): sha(path) for path in root.rglob("*") if path.is_file()}
        if before != base:
            raise Refused("copied scan_06 source gate failed")
        grid_h = root / "plan_env/include/plan_env/grid_map.h"
        data = grid_h.read_bytes()
        data = one(data, b"#include <plan_env/reactive_collision.h>\r\n",
                   b"#include <plan_env/reactive_collision.h>\r\n"
                   b"#include <plan_env/eth_step_score_adaptation.h>\r\n",
                   "step-score include")
        data = one(data, b"  reactive_stair::TerrainSnapshot reactive_terrain_;\n",
                   b"  reactive_stair::TerrainSnapshot reactive_terrain_;\n"
                   b"  reactive_stair::StepScoreResult reactive_step_result_;\n",
                   "step-score state")
        grid_h.write_bytes(data)

        methods = root / "plan_env/include/plan_env/scan_reactive_grid_methods.inc"
        data = methods.read_bytes()
        data = one(data,
                   b"  if (reactive_decision_.acceptTerrain(terrain)) reactive_terrain_ = std::move(terrain);",
                   b"  reactive_stair::StepScoreResult scored =\n"
                   b"      reactive_stair::precomputeEthStyleStepScores(terrain);\n"
                   b"  if (reactive_decision_.acceptTerrain(scored.support)) {\n"
                   b"    reactive_terrain_ = scored.support;\n"
                   b"    reactive_step_result_ = std::move(scored);\n"
                   b"  }",
                   "precomputed score hookup")
        methods.write_bytes(data)

        added = {
            "plan_env/include/plan_env/eth_step_score_adaptation.h": HERE / "eth_step_score_adaptation.h",
            "plan_env/include/plan_env/ETH_STEPFILTER_LICENSE.txt": HERE / "ETH_STEPFILTER_LICENSE.txt",
        }
        for relative, source in added.items():
            shutil.copy2(source, root / relative)
        changed = {
            path.relative_to(root).as_posix(): sha(path)
            for path in root.rglob("*") if path.is_file() and
            (path.relative_to(root).as_posix() not in base or
             sha(path) != base[path.relative_to(root).as_posix()])
        }
        manifest = {
            "schema": "scan_eth_step_score_candidate_v1",
            "status": "source_candidate_unbuilt",
            "base": "scan_06",
            "base_sha256": base,
            "changed_sha256": changed,
            "base_source_manifest_sha256": sha(SOURCE / "source_sha256.json"),
            "eth_stepfilter_commit": "14d24c059e1c43466aadf328280adf6394d78039",
            "eth_stepfilter_cpp_sha256": sha(ETH_REFERENCE),
            "formula": "ETH two-pass max-min and second-pass score; local sparse-layer and hard-height adaptations",
            "local_parameters": {"resolution_m": 0.10, "critical_height_m": 0.26,
                                 "first_radius_m": 0.15, "second_radius_m": 0.15,
                                 "critical_cell_number": 4},
            "runtime_blocker": "integrated P2B pilot does not launch /pct_tomogram publisher; no current-track producer",
            "claim": "local source candidate; no scan_07 Foxy build or simulator integration",
        }
        (OUTPUT / "eth_step_score_candidate_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return manifest
    except Exception:
        if OUTPUT.exists():
            shutil.rmtree(OUTPUT)
        raise


if __name__ == "__main__":
    result = materialize()
    print(json.dumps({"status": result["status"], "changed_sha256": result["changed_sha256"]}, indent=2))
