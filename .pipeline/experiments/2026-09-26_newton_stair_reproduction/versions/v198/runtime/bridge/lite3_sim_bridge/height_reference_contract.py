"""The pinned V12 spawn height and locomotion reference have different meanings."""
import hashlib
from pathlib import Path

SPAWN_BODY_HEIGHT_M = 0.35
LOCOMOTION_REFERENCE_HEIGHT_M = 0.30
PINNED_SOURCES = {
    "source/robot_lab/robot_lab/tasks/lite3/env_cfg.py": "5d515802a6ac4d0aa24ae51a68414fd2d04e70356f0bfa418677e53105118cd5",
    "source/robot_lab/robot_lab/tasks/lite3/__init__.py": "f724c58505289ba8473b42bf12e98efca99649586ccd368141662e3cedde1e8c",
    "source/robot_lab/robot_lab/assets/deeprobotics.py": "bb95c272c7e7b0873cde9074e0682dbbfe1db7c42b33f4b6006321d215be496a",
}


def validate_declared_heights(spawn, reference):
    if spawn != SPAWN_BODY_HEIGHT_M or reference != LOCOMOTION_REFERENCE_HEIGHT_M:
        raise ValueError("height declaration differs from the fixed V12 spawn/reference contract")


def verify_runtime_height_contract(cfg, runtime, spawn, reference):
    validate_declared_heights(spawn, reference)
    actual_spawn = tuple(cfg.scene.robot.init_state.pos)
    target = float(cfg.rewards.base_height_l2.params["target_height"])
    if actual_spawn != (0., 0., SPAWN_BODY_HEIGHT_M) or target != LOCOMOTION_REFERENCE_HEIGHT_M:
        raise ValueError("actual registry configuration differs from the fixed height contract")
    hashes = {name: hashlib.sha256((Path(runtime) / name).read_bytes()).hexdigest() for name in PINNED_SOURCES}
    if hashes != PINNED_SOURCES:
        raise ValueError("V12 height source identity differs from the audited runtime")
    return {"spawn_body_height_m": spawn, "locomotion_reference_height_m": reference,
            "registry_reward_target_height_m": target, "registry_default_base_position_m": list(actual_spawn),
            "source_sha256": hashes,
            "claim": "Spawn remains ground+.35 m; planning/arrival height references use the pinned .30 m reward target. No policy, tolerance or obstacle inflation change."}
