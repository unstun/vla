import math

import numpy as np
import pytest

from lite3_sim_bridge.run_isaac_lite3 import AdapterFailure
from lite3_sim_bridge.run_isaac_v12_fallback import (
    OFFICIAL_HUMAN_BIPED_URL,
    OFFICIAL_HUMAN_CHARACTER_URL,
    _load_official_human_animation_cache,
    _official_human_clip_name,
)


def _cache_arrays(joint_count=101):
    translations = np.zeros((2, joint_count, 3), dtype=np.float32)
    translations[1, 1, 0] = 0.01
    rotations = np.zeros((2, joint_count, 4), dtype=np.float32)
    rotations[:, :, 3] = 1.0
    rotations[1, 2] = np.asarray(
        [math.sin(0.05), 0.0, 0.0, math.cos(0.05)],
        dtype=np.float32,
    )
    return {
        "schema_version": np.asarray([1], dtype=np.int32),
        "fps": np.asarray([30], dtype=np.int32),
        "joints": np.asarray([f"joint_{index}" for index in range(joint_count)]),
        "character_url": np.asarray([OFFICIAL_HUMAN_CHARACTER_URL]),
        "biped_url": np.asarray([OFFICIAL_HUMAN_BIPED_URL]),
        "idle_translations": translations.copy(),
        "idle_rotations_xyzw": rotations.copy(),
        "walk_translations": translations.copy(),
        "walk_rotations_xyzw": rotations.copy(),
    }


def _write_cache(path, arrays):
    np.savez_compressed(path, **arrays)


def test_official_human_cache_accepts_exact_dynamic_101_joint_contract(tmp_path):
    cache_path = tmp_path / "official.npz"
    _write_cache(cache_path, _cache_arrays())

    cache = _load_official_human_animation_cache(cache_path)

    assert cache["schema_version"] == 1
    assert cache["fps"] == 30
    assert len(cache["joints"]) == 101
    assert cache["idle_translations"].shape == (2, 101, 3)
    assert len(cache["content_sha256"]) == 64


def test_official_human_cache_rejects_wrong_joint_count(tmp_path):
    cache_path = tmp_path / "official.npz"
    _write_cache(cache_path, _cache_arrays(joint_count=100))

    with pytest.raises(AdapterFailure, match="identity is invalid"):
        _load_official_human_animation_cache(cache_path)


def test_official_human_cache_rejects_static_walk(tmp_path):
    cache_path = tmp_path / "official.npz"
    arrays = _cache_arrays()
    arrays["walk_translations"][:] = arrays["walk_translations"][0]
    arrays["walk_rotations_xyzw"][:] = arrays["walk_rotations_xyzw"][0]
    _write_cache(cache_path, arrays)

    with pytest.raises(AdapterFailure, match="walk Biped cache is a static pose"):
        _load_official_human_animation_cache(cache_path)


def test_official_human_cache_rejects_non_unit_quaternion(tmp_path):
    cache_path = tmp_path / "official.npz"
    arrays = _cache_arrays()
    arrays["idle_rotations_xyzw"][1, 5] = [0.0, 0.0, 0.0, 0.5]
    _write_cache(cache_path, arrays)

    with pytest.raises(AdapterFailure, match="idle Biped cache quaternions are not unit"):
        _load_official_human_animation_cache(cache_path)


@pytest.mark.parametrize(
    ("phase", "expected"),
    [
        ("waiting", "idle"),
        ("crossing", "walk"),
        ("holding", "idle"),
        ("parked", "idle"),
    ],
)
def test_official_human_phase_conditioned_clip_selection(phase, expected):
    assert _official_human_clip_name(phase, "phase_conditioned") == expected


@pytest.mark.parametrize("phase", ["waiting", "crossing", "holding", "parked"])
def test_official_human_continuous_walk_uses_walk_in_every_phase(phase):
    assert _official_human_clip_name(phase, "continuous_walk") == "walk"


def test_official_human_clip_selection_rejects_unknown_mode():
    with pytest.raises(AdapterFailure, match="unsupported official human animation mode"):
        _official_human_clip_name("waiting", "unknown")
