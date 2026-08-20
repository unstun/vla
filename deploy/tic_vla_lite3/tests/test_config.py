from pathlib import Path

import pytest

from tic_vla_lite3.config import load_config, load_shadow_config


CONFIG = Path(__file__).parents[1] / "config" / "safe_mvp.yaml"


def test_reviewed_config_loads_with_fixed_shadow_limits():
    value = load_shadow_config(CONFIG)
    assert value.mode == "shadow"
    assert value.adapter.vx_max_mps == 0.30
    assert value.adapter.wz_abs_max_radps == 0.20
    assert value.delayed_context_s == (9.0, 6.0, 3.0, 0.0)


def test_unknown_field_fails_closed(tmp_path):
    text = CONFIG.read_text(encoding="utf-8") + "unknown: true\n"
    path = tmp_path / "bad.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="root_fields"):
        load_shadow_config(path)


def test_active_mode_is_only_loaded_when_explicit_in_config(tmp_path):
    path = tmp_path / "active.yaml"
    path.write_text(CONFIG.read_text(encoding="utf-8").replace(
        "mode: shadow", "mode: active"), encoding="utf-8")
    assert load_config(path).mode == "active"


@pytest.mark.parametrize("before,after", [
    ("vx_max_mps: 0.30", "vx_max_mps: true"),
    ("vx_min_mps: 0.0", "vx_min_mps: false"),
    ("wz_abs_max_radps: 0.20", "wz_abs_max_radps: .nan"),
    ("yaw_filter_alpha: 0.35", "yaw_filter_alpha: 1.1"),
    ("max_age_s: 0.50", "max_age_s: -1.0"),
])
def test_invalid_safety_number_fails_closed(tmp_path, before, after):
    text = CONFIG.read_text(encoding="utf-8").replace(before, after)
    path = tmp_path / "bad.yaml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        load_shadow_config(path)
