"""Bake NVIDIA's official Biped-retargeted pose into a runtime replay cache.

The cache is generated on the execution host from versioned Isaac Sim assets.
It is an experiment artifact, not vendored character or animation content.
"""

import argparse
import hashlib
import json
from pathlib import Path

from isaacsim import SimulationApp

from .official_human_contract import (
    BIPED_URL,
    CACHE_SCHEMA_VERSION,
    CHARACTER_URL,
    cache_content_sha256,
)

FPS = 30
IDLE_FRAMES = 60
WALK_WARMUP_FRAMES = 30
WALK_FRAMES = 90


def _capture_pose(character, np):
    translations, rotations_xyzw = character.get_joint_local_transforms()
    translations = np.asarray(translations, dtype=np.float32)
    rotations_xyzw = np.asarray(rotations_xyzw, dtype=np.float32)
    if translations.ndim != 2 or translations.shape[1] != 3:
        raise RuntimeError(f"unexpected translation shape: {translations.shape}")
    if rotations_xyzw.shape != (translations.shape[0], 4):
        raise RuntimeError(f"unexpected rotation shape: {rotations_xyzw.shape}")
    if not np.isfinite(translations).all() or not np.isfinite(rotations_xyzw).all():
        raise RuntimeError("official retarget output contains non-finite values")
    norms = np.linalg.norm(rotations_xyzw, axis=1, keepdims=True)
    if np.any(norms < 0.5):
        raise RuntimeError("official retarget output contains an invalid quaternion")
    return translations, rotations_xyzw / norms


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)

    app = SimulationApp({"headless": True})

    import numpy as np
    import omni.kit.app
    import omni.timeline
    import omni.usd
    from pxr import UsdGeom, UsdSkel

    extension_manager = omni.kit.app.get_app().get_extension_manager()
    for extension_id in ("omni.anim.people", "isaacsim.replicator.agent.core"):
        extension_manager.set_extension_enabled_immediate(extension_id, True)
    for _ in range(8):
        app.update()

    import omni.anim.graph.core as animation_graph
    from isaacsim.replicator.agent.core.stage_util import CharacterUtil
    from omni.anim.people.scripts.commands.goto import GoTo
    from omni.anim.people.scripts.navigation_manager import NavigationManager

    context = omni.usd.get_context()
    context.new_stage()
    for _ in range(8):
        app.update()
    stage = context.get_stage()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    biped = CharacterUtil.load_default_biped_to_stage()
    CharacterUtil.load_character_usd_to_stage(
        CHARACTER_URL,
        (0.0, 0.0, 0.0),
        180.0,
        "Character",
    )
    for _ in range(45):
        app.update()
    characters = CharacterUtil.get_characters_in_stage()
    if len(characters) != 1:
        raise RuntimeError(f"expected one official character, got {len(characters)}")
    skel_root = characters[0]
    animation_graph_prim = CharacterUtil.get_anim_graph_from_character(biped)
    if animation_graph_prim is None or not animation_graph_prim.IsValid():
        raise RuntimeError("official Biped animation graph is absent")
    CharacterUtil.setup_animation_graph_to_character(characters, animation_graph_prim)

    timeline = omni.timeline.get_timeline_interface()
    timeline.set_target_framerate(FPS)
    timeline.play()
    for _ in range(12):
        app.update()
    character = animation_graph.get_character(str(skel_root.GetPath()))
    if character is None:
        raise RuntimeError("official Biped animation graph failed to bind")

    skeleton_prims = [
        prim
        for prim in stage.Traverse()
        if prim.GetTypeName() == "Skeleton"
        and str(prim.GetPath()).startswith(str(skel_root.GetPath()))
    ]
    if len(skeleton_prims) != 1:
        raise RuntimeError(f"expected one official skeleton, got {len(skeleton_prims)}")
    joints = np.asarray(
        [
            str(value)
            for value in UsdSkel.Skeleton(skeleton_prims[0]).GetJointsAttr().Get()
        ]
    )
    if len(joints) != character.get_joint_count():
        raise RuntimeError("official skeleton and AnimationGraph joint counts differ")

    idle_translations = []
    idle_rotations = []
    for _ in range(IDLE_FRAMES):
        app.update()
        translations, rotations = _capture_pose(character, np)
        idle_translations.append(translations)
        idle_rotations.append(rotations)

    navigation = NavigationManager(str(skel_root.GetPath()), False, False)
    command = GoTo(
        character,
        ["GoTo", "0.0", "8.0", "0.0", "180.0"],
        navigation,
        character_name="Character",
        update_metadata_callback_fn=lambda **_kwargs: None,
    )
    for _ in range(WALK_WARMUP_FRAMES):
        command.execute(1.0 / FPS)
        app.update()
    walk_translations = []
    walk_rotations = []
    for _ in range(WALK_FRAMES):
        command.execute(1.0 / FPS)
        app.update()
        translations, rotations = _capture_pose(character, np)
        walk_translations.append(translations)
        walk_rotations.append(rotations)

    arrays = {
        "schema_version": np.asarray([CACHE_SCHEMA_VERSION], dtype=np.int32),
        "fps": np.asarray([FPS], dtype=np.int32),
        "joints": joints,
        "character_url": np.asarray([CHARACTER_URL]),
        "biped_url": np.asarray([BIPED_URL]),
        "idle_translations": np.stack(idle_translations).astype(np.float32),
        "idle_rotations_xyzw": np.stack(idle_rotations).astype(np.float32),
        "walk_translations": np.stack(walk_translations).astype(np.float32),
        "walk_rotations_xyzw": np.stack(walk_rotations).astype(np.float32),
    }
    content_sha256 = cache_content_sha256(arrays)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(args.output, **arrays)
    file_sha256 = hashlib.sha256(args.output.read_bytes()).hexdigest()
    manifest = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "claim": (
            "runtime-generated replay cache of the official Isaac Sim 5.1 Biped "
            "AnimationGraph output after ControlRig retargeting to the official "
            "male_adult_police_04 skeleton"
        ),
        "character_url": CHARACTER_URL,
        "biped_url": BIPED_URL,
        "animation_graph": str(animation_graph_prim.GetPath()),
        "skel_root": str(skel_root.GetPath()),
        "skeleton": str(skeleton_prims[0].GetPath()),
        "joint_count": int(len(joints)),
        "fps": FPS,
        "idle_frame_count": IDLE_FRAMES,
        "walk_warmup_frame_count": WALK_WARMUP_FRAMES,
        "walk_frame_count": WALK_FRAMES,
        "cache_content_sha256": content_sha256,
        "cache_file_sha256": file_sha256,
        "cache_path": str(args.output.resolve()),
        "redistribution": (
            "generated on the execution host from referenced NVIDIA content; "
            "the cache is an experiment artifact and is not vendored as source"
        ),
        "local_procedural_gait": False,
        "direct_gpu_animation_graph_used": False,
    }
    args.manifest.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("OFFICIAL_HUMAN_CACHE=" + json.dumps(manifest, sort_keys=True), flush=True)
    timeline.stop()
    app.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
