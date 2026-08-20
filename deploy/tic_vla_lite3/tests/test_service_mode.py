from pathlib import Path

import numpy as np

from tic_vla_lite3.config import load_config
from tic_vla_lite3.protocol import decode_command, encode_command
from tic_vla_lite3.shadow_service import command_from_proposal, resolve_mode
from tic_vla_lite3.trajectory_adapter import TrajectoryAdapter


CONFIG = Path(__file__).parents[1] / "config" / "safe_mvp.yaml"


def _real_proposal():
    config = load_config(CONFIG)
    waypoints = np.column_stack((np.linspace(0.0, 3.0, 30),
                                 np.linspace(0.0, 0.3, 30)))
    return TrajectoryAdapter(config.adapter).adapt(waypoints, 1, 1.0, 1.01)


def test_service_defaults_to_reviewed_shadow_mode():
    config = load_config(CONFIG)
    assert resolve_mode(None, config) == "shadow"


def test_explicit_active_service_packet_carries_bounded_real_proposal():
    proposed = _real_proposal()
    assert proposed.valid and proposed.vx_mps > 0.0
    wire = encode_command(command_from_proposal(
        "fake-runtime", 7, 11, 2, "active", proposed))
    packet = decode_command(wire)
    assert packet.mode == "active"
    assert 0.0 < packet.vx_mps <= 0.30
    assert packet.vy_mps == 0.0
    assert abs(packet.wz_radps) <= 0.20


def test_shadow_packet_is_never_promoted_by_packet_projection():
    packet = decode_command(encode_command(command_from_proposal(
        "fake-runtime", 8, 12, 2, "shadow", _real_proposal())))
    assert packet.mode == "shadow"
