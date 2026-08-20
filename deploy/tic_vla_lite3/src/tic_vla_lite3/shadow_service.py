"""Live TIC-VLA service. Shadow is default; active requires explicit selection."""

from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path
from typing import Optional

from .config import ShadowConfig, load_config
from .frame_source import DelayedFrameBuffer
from .live_bridge import LiveBridgeClient
from .model_runtime import (AsyncModelRuntime, PINNED_BASE_REVISION,
                            PINNED_CHECKPOINT_SHA256, PINNED_SOURCE_COMMIT,
                            sha256)
from .protocol import BodyCommand, encode_command
from .state_source import ReasoningReferenceBuffer
from .trajectory_adapter import TrajectoryAdapter


def append_jsonl(path: Path, value: dict) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, separators=(",", ":"), sort_keys=True,
                                allow_nan=False) + "\n")


def resolve_mode(requested: Optional[str], config: ShadowConfig) -> str:
    """Resolve one audited service mode; omission preserves shadow by default."""
    mode = config.mode if requested is None else requested
    if mode not in ("shadow", "active"):
        raise ValueError("mode")
    return mode


def command_from_proposal(session_id: str, plan_sequence: int,
                          source_frame_sequence: int,
                          reasoning_generation: int, mode: str,
                          proposed: object) -> BodyCommand:
    """Create the sole body-command packet projection used by live service."""
    if mode not in ("shadow", "active"):
        raise ValueError("mode")
    valid = bool(getattr(proposed, "valid"))
    return BodyCommand(
        session_id, plan_sequence, source_frame_sequence, reasoning_generation,
        mode, valid, float(getattr(proposed, "vx_mps")) if valid else 0.0,
        0.0, float(getattr(proposed, "wz_radps")) if valid else 0.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dynav-overlay", required=True, type=Path)
    parser.add_argument("--base-model", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--mode", choices=("shadow", "active"), default=None,
                        help="explicitly select active; omitted uses config (shadow by default)")
    parser.add_argument("--instruction", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--bridge-host", default="192.168.1.103")
    parser.add_argument("--bridge-port", type=int, default=45451)
    parser.add_argument("--controller-host", required=True)
    parser.add_argument("--controller-port", type=int, default=45461)
    parser.add_argument("--duration-s", type=float, required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    if args.duration_s <= 0.0:
        raise ValueError("duration")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame_dir = args.output_dir / "frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    config = load_config(args.config)
    mode = resolve_mode(args.mode, config)
    log_path = args.output_dir / (mode + ".jsonl")
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    history = DelayedFrameBuffer(max(config.delayed_context_s) + 2.0)
    adapter = TrajectoryAdapter(config.adapter)
    generation_references = ReasoningReferenceBuffer()
    plan_sequence = 0
    last_udp_send_s: Optional[float] = None
    observed_generation: Optional[int] = None
    generation_observed_s: Optional[float] = None
    manifest = {
        "schema": "tic-vla-lite3.service-run.v2",
        "mode": mode,
        "motor_command_sent": False,
        "instruction": args.instruction,
        "session_id": args.session_id,
        "bridge": [args.bridge_host, args.bridge_port],
        "controller": [args.controller_host, args.controller_port],
        "safety_clock": "orin_steady_monotonic",
        "config": str(args.config),
        "max_frame_source_age_s": config.max_frame_age_s,
        "max_state_source_age_s": config.max_state_age_s,
        "tic_vla_source_commit": PINNED_SOURCE_COMMIT,
        "base_model_revision": PINNED_BASE_REVISION,
        "checkpoint_sha256_verified": PINNED_CHECKPOINT_SHA256,
        "config_sha256": sha256(args.config),
        "dynav_overlay_sha256": sha256(args.dynav_overlay / "ticvla.py"),
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    with AsyncModelRuntime(args.dynav_overlay, args.base_model,
                           args.checkpoint) as runtime, \
            LiveBridgeClient(args.bridge_host, args.bridge_port, 5.0) as bridge:
        # The requested live duration starts only after the resident model is
        # loaded and both live endpoints are available.
        started = time.monotonic()
        while time.monotonic() - started < args.duration_s:
            cycle_started = time.monotonic()
            observation = bridge.receive()
            proposed = adapter.zero("warming_history")
            reasoning_generation = 0
            cache_available = False
            reasoning_cache_age_s: Optional[float] = None
            inference_seconds = 0.0
            try:
                if observation.frame_source_age_s > config.max_frame_age_s:
                    raise ValueError("stale_frame_source")
                if observation.state_source_age_s > config.max_state_age_s:
                    raise ValueError("stale_state_source")
                history.append(observation.frame)
                context = history.context(
                    observation.received_monotonic_s, config.delayed_context_s,
                    config.history_tolerance_s)
                current_path = frame_dir / ("frame_%09d.jpg" % observation.frame.sequence)
                current_path.write_bytes(observation.frame.rgb_jpeg)
                context_paths = []
                for sample in context:
                    path = frame_dir / ("frame_%09d.jpg" % sample.sequence)
                    if not path.exists():
                        path.write_bytes(sample.rgb_jpeg)
                    context_paths.append(path)
                state = observation.state
                generation_reference = generation_references.reference(state)
                robot_state = [state.vx_mps, state.vy_mps, state.wz_radps,
                               state.x_m - generation_reference.x_m,
                               state.y_m - generation_reference.y_m]
                inference_started = time.monotonic()
                result = runtime.predict_async(
                    context_paths, args.instruction, robot_state,
                    observation.frame.sequence,
                    {"position": [state.x_m, state.y_m, 0.0],
                     "quaternion": [0.0, 0.0, 0.0, 1.0]},
                    max(0.0, observation.received_monotonic_s -
                        generation_reference.received_monotonic_s),
                    context_paths)
                inference_seconds = time.monotonic() - inference_started
                generation_references.observe(
                    result.reasoning_generation_start, result.generation_pose,
                    observation.received_monotonic_s)
                reasoning_generation = generation_reference.sequence
                cache_available = result.cache_available
                if observed_generation != reasoning_generation:
                    observed_generation = reasoning_generation
                    generation_observed_s = time.monotonic()
                if generation_observed_s is not None:
                    reasoning_cache_age_s = time.monotonic() - generation_observed_s
                proposed = adapter.adapt(result.waypoints[0],
                                         observation.frame.sequence,
                                         observation.received_monotonic_s,
                                         time.monotonic())
            except ValueError as exc:
                proposed = adapter.zero(str(exc))
            plan_sequence += 1
            packet = command_from_proposal(
                args.session_id, plan_sequence, observation.frame.sequence,
                reasoning_generation, mode, proposed)
            payload = encode_command(packet)
            udp.sendto(payload, (args.controller_host, args.controller_port))
            udp_sent_s = time.monotonic()
            udp_interval_s = (None if last_udp_send_s is None else
                              udp_sent_s - last_udp_send_s)
            last_udp_send_s = udp_sent_s
            append_jsonl(log_path, {
                "plan_seq": plan_sequence,
                "frame_seq": observation.frame.sequence,
                "state_seq": observation.state.sequence,
                "frame_source_age_s": observation.frame_source_age_s,
                "state_source_age_s": observation.state_source_age_s,
                "inference_seconds": inference_seconds,
                "cycle_seconds": time.monotonic() - cycle_started,
                "cache_available": cache_available,
                "reasoning_generation": reasoning_generation,
                "reasoning_cache_age_s": reasoning_cache_age_s,
                "udp_interval_s": udp_interval_s,
                "command_age_s_at_send": 0.0,
                "valid": proposed.valid,
                "reason": proposed.reason,
                "vx_mps": packet.vx_mps,
                "vy_mps": packet.vy_mps,
                "wz_radps": packet.wz_radps,
                "mode": mode,
                "motor_command_sent": False,
                "packet_bytes": len(payload),
            })
            minimum_sequence = observation.frame.sequence - 80
            for old in frame_dir.glob("frame_*.jpg"):
                if int(old.stem.split("_")[1]) < minimum_sequence:
                    old.unlink()
    udp.close()


if __name__ == "__main__":
    main()
