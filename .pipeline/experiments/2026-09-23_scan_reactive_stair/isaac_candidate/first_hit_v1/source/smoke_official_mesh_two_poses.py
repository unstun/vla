"""Bounded Isaac first-hit smoke of the official human mesh, without a robot.

Only the NVIDIA police visual mesh is a raycast target. This smoke measures
rigid root-translation hits at two poses, not skin deformation or contacts.
It performs no navigation, controller launch, robot actuation, or training.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import traceback

from official_building_human import (
    VISUAL_ROOT, file_sha256, make_visual_wrapper, verify_official_bundle,
)

EXPECTED_FALLBACK_SHA = "6104fe686bcd3bc0480c0afc1b41dde84d1a35d45a6dbbe9e51d98e6719ba3e3"
EXPECTED_CONTRACT_SHA = "a23020f3f269a044bf3ea0b65830309de155c07b19419f9ab52b1df5cd1621ff"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda:0")
    args = parser.parse_args(argv)
    identity = verify_official_bundle(args.asset_root, args.cache_dir)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.mkdir(parents=True)

    # Isaac Lab modules must load after AppLauncher.
    from isaaclab.app import AppLauncher
    app = AppLauncher(headless=True, device=args.device).app
    try:
        import torch
        from pxr import UsdGeom
        import isaaclab.sim as sim_utils
        from isaaclab.sensors.ray_caster import MultiMeshRayCaster, patterns
        from isaaclab.sensors.ray_caster import MultiMeshRayCasterCfg
        from lite3_sim_bridge import run_isaac_v12_fallback as v12
        from lite3_sim_bridge import official_human_contract as contract
        if file_sha256(v12.__file__) != EXPECTED_FALLBACK_SHA:
            raise RuntimeError("pinned Isaac fallback source hash changed")
        if file_sha256(contract.__file__) != EXPECTED_CONTRACT_SHA:
            raise RuntimeError("pinned official human contract source hash changed")

        wrapper = make_visual_wrapper(
            args.output / "official_human_visual.usda",
            Path(identity["character_usd"]), Path(identity["cache_npz"]), v12)
        sim = sim_utils.SimulationContext(
            sim_utils.SimulationCfg(dt=0.01, device=args.device))
        stage = sim.stage
        UsdGeom.Xform.Define(stage, "/World/ProbeSensor")
        cfg = sim_utils.UsdFileCfg(usd_path=wrapper["path"])
        cfg.func(VISUAL_ROOT, cfg, translation=(3.0, 0.0, 0.02))
        sensor_cfg = MultiMeshRayCasterCfg(
            prim_path="/World/ProbeSensor",
            update_period=0.0,
            offset=MultiMeshRayCasterCfg.OffsetCfg(pos=(0.0, 0.0, 1.0)),
            ray_alignment="world",
            pattern_cfg=patterns.LidarPatternCfg(
                channels=48, vertical_fov_range=(-25.0, 25.0),
                horizontal_fov_range=(-30.0, 30.0), horizontal_res=0.5),
            max_distance=8.0,
            mesh_prim_paths=[MultiMeshRayCasterCfg.RaycastTargetCfg(
                prim_expr=VISUAL_ROOT, merge_prim_meshes=True,
                track_mesh_transforms=True)],
            update_mesh_ids=True,
            debug_vis=False,
        )
        sensor = MultiMeshRayCaster(sensor_cfg)
        sim.reset()
        target_prims = sorted(str(prim.GetPath()) for prim in stage.Traverse()
                              if prim.GetTypeName() == "Mesh"
                              and str(prim.GetPath()).startswith(VISUAL_ROOT + "/"))
        if len(target_prims) != 9:
            raise RuntimeError(f"official visual mesh prim count {len(target_prims)} != 9")
        player = v12._OfficialHumanAnimationPlayer(
            stage, Path(identity["cache_npz"]), "phase_conditioned",
            visual_root_path=VISUAL_ROOT)

        rows = []
        for index, y in enumerate((0.0, 1.0)):
            state = {
                "visual_root_xyz_m": (3.0, y, 0.02 - v12.OFFICIAL_HUMAN_SOURCE_FOOT_Z_M),
                "visual_quaternion_wxyz": (1.0, 0.0, 0.0, 0.0),
                "visual_foot_world_z_m": 0.02,
                "visual_top_world_z_m": 0.02 + v12.OFFICIAL_HUMAN_SOURCE_VISIBLE_TOP_Z_M,
                "capsule_bottom_world_z_m": None,
                "foot_to_capsule_bottom_error_m": None,
                "visual_yaw_radians": 0.0,
            }
            pose = v12._set_official_human_visual_pose(
                stage, state, visual_root_path=VISUAL_ROOT)
            animation = player.update(float(index) / 30.0, "crossing")
            sim.render()
            sensor.reset()
            sensor.update(dt=0.0, force_recompute=True)
            hits = sensor.data.ray_hits_w[0]
            finite = hits[torch.isfinite(hits).all(dim=-1)]
            row = {
                "pose_index": index, "root_y_m": y,
                "finite_hit_count": int(finite.shape[0]),
                "hit_mean_xyz_m": (
                    [float(value) for value in finite.mean(dim=0).cpu().tolist()]
                    if len(finite) else None),
                "hit_min_xyz_m": (
                    [float(value) for value in finite.min(dim=0).values.cpu().tolist()]
                    if len(finite) else None),
                "hit_max_xyz_m": (
                    [float(value) for value in finite.max(dim=0).values.cpu().tolist()]
                    if len(finite) else None),
                "visual_pose_readback": pose,
                "animation": animation,
            }
            rows.append(row)
        passed = (all(row["finite_hit_count"] >= 10 for row in rows)
                  and all(math.isfinite(row["hit_mean_xyz_m"][1]) for row in rows
                          if row["hit_mean_xyz_m"] is not None)
                  and rows[1]["hit_mean_xyz_m"] is not None
                  and rows[0]["hit_mean_xyz_m"] is not None
                  and rows[1]["hit_mean_xyz_m"][1] - rows[0]["hit_mean_xyz_m"][1] >= 0.4)
        result = {
            "schema_version": 1, "passed": bool(passed),
            "claim": "official USD mesh rigid-translation ray hits only; no robot or Building episode",
            "asset_identity": identity,
            "wrapper": wrapper,
            "probe_source_sha256": file_sha256(__file__),
            "target_prim_expr": VISUAL_ROOT,
            "target_mesh_prims": target_prims,
            "track_mesh_transforms": True,
            "raycast_target_count": 1,
            "poses": rows,
        }
        (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(json.dumps({"passed": result["passed"], "poses": rows}, sort_keys=True))
        return 0 if passed else 2
    except Exception as exc:
        (args.output / "result.json").write_text(json.dumps({
            "schema_version": 1, "passed": False,
            "failure_type": type(exc).__name__, "failure_message": str(exc),
            "traceback": traceback.format_exc(),
            "asset_identity": identity,
            "probe_source_sha256": file_sha256(__file__),
            "target_prim_expr": VISUAL_ROOT,
            "track_mesh_transforms": True,
            "raycast_target_count": 1,
        }, indent=2, sort_keys=True) + "\n")
        raise
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
