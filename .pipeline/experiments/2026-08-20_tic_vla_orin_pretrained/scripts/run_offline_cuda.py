#!/usr/bin/env python3
"""Run receive-only TIC-VLA inference on one local image and save raw evidence."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import subprocess
import time
from pathlib import Path
from types import MethodType

import numpy as np
import torch

from ticvla.models.ticvla import TICVLA


def install_single_process_distributed_query_shim():
    """Provide the read-only query used by InternVL on non-distributed Jetson Torch."""
    if not hasattr(torch.distributed, "is_initialized"):
        torch.distributed.is_initialized = lambda: False


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(path: Path):
    try:
        return path.read_text().strip()
    except (OSError, UnicodeDecodeError):
        return None


def sensor_snapshot():
    thermal = {}
    thermal_root = Path("/sys/class/thermal")
    for zone in sorted(thermal_root.glob("thermal_zone*")):
        kind = read_text(zone / "type") or zone.name
        raw = read_text(zone / "temp")
        if raw is not None:
            try:
                value = float(raw)
                thermal[kind] = value / 1000.0 if abs(value) > 1000 else value
            except ValueError:
                thermal[kind] = raw

    power = {}
    for path in sorted(Path("/sys/bus/i2c/drivers/ina3221x").glob("**/in_power*_input")):
        raw = read_text(path)
        if raw is not None:
            power[str(path)] = raw

    try:
        tegrastats = subprocess.run(
            ["timeout", "2", "tegrastats", "--interval", "1000"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        tegrastats_lines = [line for line in tegrastats.stdout.splitlines() if line.strip()]
        tegrastats_stderr = tegrastats.stderr.strip()
    except OSError as exc:
        tegrastats_lines = []
        tegrastats_stderr = repr(exc)
    return {
        "timestamp_unix": time.time(),
        "thermal_celsius": thermal,
        "power_sysfs_raw": power,
        "power_available": bool(power) or any("VDD_" in line for line in tegrastats_lines),
        "tegrastats_lines": tegrastats_lines,
        "tegrastats_stderr": tegrastats_stderr,
    }


def max_temperature(snapshot):
    values = [value for value in snapshot["thermal_celsius"].values() if isinstance(value, float)]
    return max(values) if values else None


class CallTimers:
    def __init__(self):
        self.values = {"vlm_chat": [], "vlm_forward": [], "extract_feature": [], "action_expert": []}

    def wrap(self, owner, method_name, label):
        original = getattr(owner, method_name)

        def timed(_self, *args, **kwargs):
            torch.cuda.synchronize()
            start = time.perf_counter()
            result = original(*args, **kwargs)
            torch.cuda.synchronize()
            self.values[label].append(time.perf_counter() - start)
            return result

        setattr(owner, method_name, MethodType(timed, owner))

    def reset(self):
        for values in self.values.values():
            values.clear()

    def snapshot(self):
        return {
            label: {"calls": len(values), "seconds": list(values), "total_seconds": sum(values)}
            for label, values in self.values.items()
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-checkpoint-sha256", required=True)
    parser.add_argument("--temperature-stop-c", type=float, default=85.0)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available")
    install_single_process_distributed_query_shim()
    checkpoint_hash = sha256(args.checkpoint)
    if checkpoint_hash != args.expected_checkpoint_sha256:
        raise RuntimeError("checkpoint SHA-256 mismatch")

    before_load = sensor_snapshot()
    before_load_max = max_temperature(before_load)
    if before_load_max is not None and before_load_max >= args.temperature_stop_c:
        raise RuntimeError("temperature stop threshold reached before model load")

    load_start = time.perf_counter()
    model = TICVLA(model_path=str(args.model), action_horizon_steps=30, train_vlm=False)
    checkpoint = torch.load(str(args.checkpoint), map_location="cpu")
    state_dict = checkpoint["state_dict"]
    direct_prefix = "model.vlm."
    action_prefix = "model.action_expert."
    vlm_state = {
        key[len(direct_prefix):]: value
        for key, value in state_dict.items()
        if key.startswith(direct_prefix)
    }
    action_state = {
        key[len(action_prefix):]: value
        for key, value in state_dict.items()
        if key.startswith(action_prefix)
    }
    model.vlm.load_state_dict(vlm_state, strict=True)
    model.action_expert.load_state_dict(action_state, strict=True)
    del checkpoint, state_dict, vlm_state, action_state
    gc.collect()

    device = torch.device("cuda:0")
    torch.cuda.init()
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats(device)
    model.to(device)
    model.eval()
    torch.cuda.synchronize()
    load_seconds = time.perf_counter() - load_start
    load_memory = {
        "allocated_bytes": torch.cuda.memory_allocated(device),
        "reserved_bytes": torch.cuda.memory_reserved(device),
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(device),
        "peak_reserved_bytes": torch.cuda.max_memory_reserved(device),
    }
    after_load = sensor_snapshot()

    timers = CallTimers()
    timers.wrap(model.vlm, "chat", "vlm_chat")
    timers.wrap(model.vlm, "forward", "vlm_forward")
    timers.wrap(model.vlm, "extract_feature", "extract_feature")
    timers.wrap(model.action_expert, "forward", "action_expert")

    instruction = "Move forward safely and efficiently."
    robot_state = torch.zeros(5, dtype=torch.float32)
    records = []
    phases = [("warmup", 0), ("measured", 1), ("measured", 2), ("measured", 3)]
    for phase, index in phases:
        before = sensor_snapshot()
        before_max = max_temperature(before)
        if before_max is not None and before_max >= args.temperature_stop_c:
            raise RuntimeError("temperature stop threshold reached before inference")
        timers.reset()
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats(device)
        torch.cuda.synchronize()
        start = time.perf_counter()
        response, waypoints, prompt = model.predict(
            delayed_image_paths=[str(args.image)],
            current_image_path=str(args.image),
            instruction=instruction,
            robot_state=robot_state,
            history=None,
            current_timestamp=None,
            time_delay=0.0,
        )
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - start
        array = waypoints.detach().float().cpu().numpy()
        finite = bool(np.isfinite(array).all())
        after = sensor_snapshot()
        after_max = max_temperature(after)
        if not finite:
            raise RuntimeError("waypoint output contains NaN or Inf")
        if tuple(array.shape) != (1, 30, 2):
            raise RuntimeError("unexpected waypoint shape: %r" % (array.shape,))
        if after_max is not None and after_max >= args.temperature_stop_c:
            raise RuntimeError("temperature stop threshold reached after inference")

        name = "warmup" if phase == "warmup" else "measured_%d" % index
        np.save(str(args.output / (name + "_waypoints.npy")), array)
        record = {
            "name": name,
            "phase": phase,
            "index": index,
            "end_to_end_seconds": elapsed,
            "component_timers": timers.snapshot(),
            "language_output": response,
            "full_prompt": prompt,
            "waypoints": array.tolist(),
            "waypoint_shape": list(array.shape),
            "waypoint_dtype_model": str(waypoints.dtype),
            "waypoint_dtype_saved": str(array.dtype),
            "waypoint_all_finite": finite,
            "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated(device),
            "peak_cuda_reserved_bytes": torch.cuda.max_memory_reserved(device),
            "sensors_before": before,
            "sensors_after": after,
        }
        (args.output / (name + ".json")).write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n"
        )
        records.append(record)
        print(json.dumps({
            "name": name,
            "end_to_end_seconds": elapsed,
            "waypoint_shape": list(array.shape),
            "waypoint_all_finite": finite,
            "peak_cuda_allocated_bytes": record["peak_cuda_allocated_bytes"],
            "max_temperature_after_c": after_max,
            "power_available": after["power_available"],
        }, sort_keys=True), flush=True)

    measured = [record for record in records if record["phase"] == "measured"]
    summary = {
        "claim_boundary": (
            "Offline receive-only compatibility test using one non-DynaNav Lite3 image. "
            "The delayed and current frames repeat the same image; robot state and ego-motion are neutral "
            "placeholders. This does not validate temporal reasoning, planning reliability, navigation, "
            "obstacle avoidance, robot control, or safety."
        ),
        "model_path": str(args.model),
        "checkpoint_path": str(args.checkpoint),
        "checkpoint_sha256": checkpoint_hash,
        "image_path": str(args.image),
        "image_sha256": sha256(args.image),
        "input_contract": {
            "official_dynanav_sample": False,
            "single_offline_lite3_image": True,
            "delayed_current_same_image": True,
            "robot_state": [0.0] * 5,
            "time_delay_seconds": 0.0,
            "ego_motion_placeholder": "neutral dx=0, dy=0 in robot_state",
            "instruction": instruction,
        },
        "strict_checkpoint_load": True,
        "device": {
            "name": torch.cuda.get_device_name(device),
            "capability": list(torch.cuda.get_device_capability(device)),
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "python": platform.python_version(),
            "architecture": platform.machine(),
        },
        "model_load_seconds": load_seconds,
        "model_load_cuda_memory": load_memory,
        "sensors_before_load": before_load,
        "sensors_after_load": after_load,
        "warmup_count": 1,
        "measured_count": 3,
        "measured_end_to_end_seconds": [record["end_to_end_seconds"] for record in measured],
        "all_measured_waypoints_finite": all(record["waypoint_all_finite"] for record in measured),
        "measured_waypoint_shapes": [record["waypoint_shape"] for record in measured],
        "records": records,
        "environment": {
            "HF_HOME": os.environ.get("HF_HOME"),
            "HF_HUB_OFFLINE": os.environ.get("HF_HUB_OFFLINE"),
            "TRANSFORMERS_OFFLINE": os.environ.get("TRANSFORMERS_OFFLINE"),
        },
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "completed": True,
        "measured_end_to_end_seconds": summary["measured_end_to_end_seconds"],
        "all_measured_waypoints_finite": summary["all_measured_waypoints_finite"],
        "measured_waypoint_shapes": summary["measured_waypoint_shapes"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
