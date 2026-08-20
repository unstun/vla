"""Resident wrapper around the official DynaNav TICVLA.predict_async path."""

from __future__ import annotations

import dataclasses
import gc
import hashlib
import importlib
import sys
import threading
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple

import numpy as np

PINNED_SOURCE_COMMIT = "9fa6f8b66b9e121d5df5df071297bba8e5353ebb"
PINNED_BASE_REVISION = "4415a3b810e636d11dfa86b0e9ba40bb00535aa8"
PINNED_CHECKPOINT_SHA256 = (
    "376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclasses.dataclass(frozen=True)
class RuntimeResult:
    response: Optional[str]
    waypoints: np.ndarray
    reasoning_generation_start: Optional[int]
    cache_available: bool
    generation_pose: Optional[dict]


class AsyncModelRuntime:
    """Loads once, verifies identities, and delegates inference unchanged."""

    def __init__(self, dynav_overlay: Path, base_model: Path, checkpoint: Path,
                 expected_checkpoint_sha256: str = PINNED_CHECKPOINT_SHA256,
                 device: str = "cuda:0") -> None:
        if sha256(checkpoint) != expected_checkpoint_sha256:
            raise RuntimeError("checkpoint_sha256_mismatch")
        if not (base_model / "config.json").is_file():
            raise RuntimeError("base_model_config_missing")
        if not (dynav_overlay / "ticvla.py").is_file():
            raise RuntimeError("dynav_overlay_missing")
        self._lock = threading.RLock()
        self._closed = False
        self._instruction: Optional[str] = None
        sys.path.insert(0, str(dynav_overlay))
        try:
            torch = importlib.import_module("torch")
            if not torch.cuda.is_available():
                raise RuntimeError("cuda_unavailable")
            if not hasattr(torch.distributed, "is_initialized"):
                torch.distributed.is_initialized = lambda: False
            torch.cuda.init()
            module = importlib.import_module("ticvla")
            model = module.TICVLA(model_path=str(base_model), device=device,
                                  num_action_chunks=30)
            payload = torch.load(str(checkpoint), map_location="cpu")
            state = payload["state_dict"]
            vlm_prefix = "model.vlm."
            action_prefix = "model.action_expert."
            vlm_state = {key[len(vlm_prefix):]: value for key, value in state.items()
                         if key.startswith(vlm_prefix)}
            action_state = {key[len(action_prefix):]: value for key, value in state.items()
                            if key.startswith(action_prefix)}
            model.vlm.load_state_dict(vlm_state, strict=True)
            model.action_expert.load_state_dict(action_state, strict=True)
            model.eval()
            self._torch = torch
            self._model = model
            del payload, state, vlm_state, action_state
            gc.collect()
        finally:
            if sys.path and sys.path[0] == str(dynav_overlay):
                sys.path.pop(0)

    def predict_async(self, image_paths: Sequence[Path], instruction: str,
                      robot_state: Sequence[float], current_step: int,
                      current_pose: Optional[dict], time_delay_s: float,
                      delayed_image_paths: Sequence[Path]) -> RuntimeResult:
        if len(robot_state) != 5:
            raise ValueError("robot_state must be [vx, vy, wz, dx, dy]")
        with self._lock:
            if self._closed:
                raise RuntimeError("runtime_closed")
            if self._instruction is not None and instruction != self._instruction:
                self._model.reset_episode_state()
            self._instruction = instruction
            # Official implementation accepts six values and removes vz itself.
            state6 = self._torch.tensor(
                [robot_state[0], robot_state[1], 0.0, robot_state[2],
                 robot_state[3], robot_state[4]], dtype=self._torch.float32)
            output = self._model.predict_async(
                image_paths=[str(path) for path in image_paths],
                instruction=instruction,
                robot_state=state6,
                current_step=current_step,
                current_robot_pose=current_pose,
                time_delay=float(time_delay_s),
                delayed_image_paths=[str(path) for path in delayed_image_paths],
                robot_type="legged robot",
            )
            response, waypoints, generation, cache, pose = output
            array = waypoints.detach().float().cpu().numpy()
            if array.shape != (1, 30, 2) or not np.isfinite(array).all():
                raise RuntimeError("invalid_waypoint_output")
            return RuntimeResult(response, array, generation, bool(cache), pose)

    def reset(self) -> None:
        with self._lock:
            if not self._closed:
                self._model.reset_episode_state()
                self._instruction = None

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._model.cleanup()
            self._closed = True

    def __enter__(self) -> "AsyncModelRuntime":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()
