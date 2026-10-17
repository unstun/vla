"""Hash-gated, inactive Building runner source candidate for official USD mesh hits.

This prepares source for review. It does not prepare a P2B launcher or run Isaac.
The official actor is a visual mesh target, not a procedural LiDAR capsule.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from official_building_human import verify_official_bundle


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
PILOT_MATERIALIZER = PROJECT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/materialize_runner_patch.py"
FALLBACK = PROJECT / "references/upstream/2026-09-16_lite3_isaac_harness_backend/source/machine-dog-nav/integration/lite3_sim_bridge/lite3_sim_bridge/run_isaac_v12_fallback.py"
CONTRACT = FALLBACK.with_name("official_human_contract.py")
ASSET_ROOT = PROJECT / "references/upstream/2026-09-24_isaac_official_police_human"
CACHE_DIR = HERE.parent / "official_human_cache"
EXPECTED = {
    PILOT_MATERIALIZER: "3102d91ec328492126fa384cfb35e0f3089ffdb649466753896a04d42d3c60f4",
    FALLBACK: "6104fe686bcd3bc0480c0afc1b41dde84d1a35d45a6dbbe9e51d98e6719ba3e3",
    CONTRACT: "a23020f3f269a044bf3ea0b65830309de155c07b19419f9ab52b1df5cd1621ff",
}
BASE_SHA = "2b282dc3aa589d90834fc884871dc6f4e75db1c3166b6a0a8e1bd76cc02f8a90"


def digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replace_once(source: str, before: str, after: str) -> str:
    if source.count(before) != 1:
        raise ValueError(f"official Building source anchor count {source.count(before)}: {before[:70]}")
    return source.replace(before, after, 1)


def overlay(base: str) -> str:
    source = replace_once(
        base,
        '    parser.add_argument("--seed", type=int, default=42)\n',
        '    parser.add_argument("--official-human-asset-root", type=Path, required=True)\n'
        '    parser.add_argument("--official-human-cache-dir", type=Path, required=True)\n'
        '    parser.add_argument("--official-human-route", type=Path, required=True)\n'
        '    parser.add_argument("--seed", type=int, default=42)\n',
    )
    source = replace_once(
        source,
        '    if args.case == "native_nominal" and args.contact_policy != "native_v12":\n'
        '        raise SystemExit("native_nominal records contact and preserves native V12 termination")\n'
        '    from .feedback_dropout import FeedbackDropout\n',
        '    if args.case == "native_nominal" and args.contact_policy != "native_v12":\n'
        '        raise SystemExit("native_nominal records contact and preserves native V12 termination")\n'
        '    from .official_building_human import verify_official_bundle, load_actor_route\n'
        '    verify_official_bundle(args.official_human_asset_root, args.official_human_cache_dir)\n'
        '    load_actor_route(args.official_human_route, sha256(args.scene))\n'
        '    if not args.unfiltered_planner_cloud:\n'
        '        raise SystemExit("official mesh candidate requires raw unfiltered LiDAR delivery")\n'
        '    from .feedback_dropout import FeedbackDropout\n',
    )
    source = replace_once(
        source,
        '             "lidar_pattern_csv", "robot_asset", "canonical_robot_asset"}\n',
        '             "lidar_pattern_csv", "robot_asset", "canonical_robot_asset",\n'
        '             "official_human_asset_root", "official_human_cache_dir",\n'
        '             "official_human_route"}\n',
    )
    source = replace_once(
        source,
        '    from lite3_sim_bridge import run_isaac_v12_fallback as v12\n',
        '    from lite3_sim_bridge import run_isaac_v12_fallback as v12\n'
        '    from .official_building_human import (\n'
        '        VISUAL_ROOT, actor_state, load_actor_route, make_visual_wrapper,\n'
        '        verify_official_bundle, visual_pose,\n'
        '    )\n',
    )
    source = replace_once(
        source,
        '    cfg.scene.sky_light = AssetBaseCfg(\n',
        '    # The only LiDAR actor target is the NVIDIA character mesh. The Warp\n'
        '    # ray caster caches vertices and follows its root transform; skinned\n'
        '    # limb motion in the ray mesh is unproven until the Isaac smoke.\n'
        '    official_assets = verify_official_bundle(\n'
        '        args.official_human_asset_root, args.official_human_cache_dir)\n'
        '    official_route = load_actor_route(args.official_human_route, sha256(args.scene))\n'
        '    visual_usd = args.output / "official_human_visual.usda"\n'
        '    official_visual_identity = make_visual_wrapper(\n'
        '        visual_usd, Path(official_assets["character_usd"]),\n'
        '        Path(official_assets["cache_npz"]), v12)\n'
        '    cfg.scene.official_human_visual = AssetBaseCfg(\n'
        '        prim_path=VISUAL_ROOT,\n'
        '        spawn=sim_utils.UsdFileCfg(usd_path=str(visual_usd)),\n'
        '        init_state=AssetBaseCfg.InitialStateCfg(\n'
        '            pos=tuple(official_route["points"][0])),\n'
        '        collision_group=-1,\n'
        '    )\n'
        '    cfg.scene.navigation_lidar.mesh_prim_paths.append(\n'
        '        MultiMeshRayCasterCfg.RaycastTargetCfg(\n'
        '            prim_expr=VISUAL_ROOT, merge_prim_meshes=True,\n'
        '            track_mesh_transforms=True))\n'
        '    cfg.scene.navigation_lidar.update_mesh_ids = True\n'
        '    write_json(args.output / "official_human_source_identity.json", {\n'
        '        "assets": official_assets, "visual_wrapper": official_visual_identity,\n'
        '        "route_sha256": official_route["route_sha256"],\n'
        '        "lidar_target": VISUAL_ROOT, "track_mesh_transforms": True,\n'
        '        "sensor_geometry": "official USD mesh, frozen vertices at raycaster initialization",\n'
        '        "planner_input": "raw LiDAR only; actor truth is scoring-only",\n'
        '        "physics_contact": "unverified; no procedural capsule is spawned",\n'
        '    })\n'
        '    cfg.scene.sky_light = AssetBaseCfg(\n',
    )
    source = replace_once(
        source,
        '    robot = env.scene["robot"]\n',
        '    robot = env.scene["robot"]\n'
        '    official_animation_player = v12._OfficialHumanAnimationPlayer(\n'
        '        env.sim.stage, Path(official_assets["cache_npz"]),\n'
        '        "phase_conditioned", visual_root_path=VISUAL_ROOT)\n',
    )
    source = replace_once(
        source,
        '            for step in range(total_steps):\n',
        '            human_truth_file = recording_cleanup.enter_context(\n'
        '                (args.output / "official_human_truth.jsonl").open(\n'
        '                    "w", encoding="utf-8"))\n'
        '            for step in range(total_steps):\n',
    )
    source = replace_once(
        source,
        '                sim_time = float(env.sim.current_time) - initial_sim_time\n'
        '                external_finish_ready_status = None\n',
        '                sim_time = float(env.sim.current_time) - initial_sim_time\n'
        '                human_truth = actor_state(official_route, sim_time)\n'
        '                human_visual = visual_pose(human_truth)\n'
        '                visual_readback = v12._set_official_human_visual_pose(\n'
        '                    env.sim.stage, human_visual, visual_root_path=VISUAL_ROOT)\n'
        '                human_animation = official_animation_player.update(\n'
        '                    sim_time, "crossing" if human_truth["phase"] == "walking" else "waiting")\n'
        '                human_truth_file.write(json.dumps({\n'
        '                    "step": step, "sim_time_s": sim_time,\n'
        '                    "actor_truth": human_truth, "visual_readback": visual_readback,\n'
        '                    "animation": human_animation,\n'
        '                }, sort_keys=True) + "\\n")\n'
        '                human_truth_file.flush()\n'
        '                external_finish_ready_status = None\n',
    )
    compile(source, "candidate_run_pct_scan_building.py", "exec")
    return source


def materialize(output: Path) -> dict:
    for path, expected in EXPECTED.items():
        if digest(path) != expected:
            raise ValueError(f"pinned source hash changed: {path}")
    assets = verify_official_bundle(ASSET_ROOT, CACHE_DIR)
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        base = temp / "run_pct_scan_building.py"
        subprocess.run([
            sys.executable, str(PILOT_MATERIALIZER), "--output", str(base),
            "--patch", str(temp / "base.patch"),
            "--hashes", str(temp / "base_hashes.json"), "--check",
        ], check=True, stdout=subprocess.DEVNULL)
        if digest(base) != BASE_SHA:
            raise ValueError("current patched Building runner source hash changed")
        result = overlay(base.read_text())
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    runner = output / "run_pct_scan_building.py"
    helper = output / "official_building_human.py"
    runner.write_text(result)
    shutil.copy2(HERE / "official_building_human.py", helper)
    manifest = {
        "schema_version": 1,
        "status": "inactive_source_candidate_requires_isaac_first_hit_smoke",
        "base_runner_sha256": BASE_SHA,
        "runner_sha256": digest(runner),
        "helper_sha256": digest(helper),
        "pinned_source_sha256": {str(path.relative_to(PROJECT)): value
                                 for path, value in EXPECTED.items()},
        "official_asset_identity": assets,
        "required_next_gate": (
            "Isaac first-hit smoke of official USD mesh at two world poses; "
            "then physics contact, stair route, ROS launcher and episode review"
        ),
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(materialize(args.output), indent=2, sort_keys=True))
