"""Pure NumPy implementation of the frozen v12 Lite3 actuator contract."""

from __future__ import annotations

import numpy as np

from .source_pins import EFFORT_LIMITS, VELOCITY_LIMITS


def clip_torque_speed(
    requested_torque: np.ndarray,
    joint_velocity: np.ndarray,
    effort_limits: np.ndarray | None = None,
    velocity_limits: np.ndarray | None = None,
) -> np.ndarray:
    """Apply the exact four-quadrant linear clip used by `Lite3Actuator`.

    Positive velocity derates positive torque and leaves braking torque at the
    constant effort limit. Negative velocity is handled symmetrically.
    """

    requested = np.asarray(requested_torque, dtype=np.float32)
    velocity = np.asarray(joint_velocity, dtype=np.float32)
    effort = np.asarray(EFFORT_LIMITS if effort_limits is None else effort_limits, dtype=np.float32)
    speed = np.asarray(VELOCITY_LIMITS if velocity_limits is None else velocity_limits, dtype=np.float32)
    if requested.shape != (12,) or velocity.shape != (12,):
        raise ValueError(f"Expected 12 requested torques and velocities, got {requested.shape} and {velocity.shape}.")
    if effort.shape != (12,) or speed.shape != (12,):
        raise ValueError(f"Expected 12 effort and velocity limits, got {effort.shape} and {speed.shape}.")
    if not np.all(np.isfinite(requested)) or not np.all(np.isfinite(velocity)):
        raise ValueError("Torque-speed inputs must be finite.")
    if np.any(effort <= 0.0) or np.any(speed <= 0.0):
        raise ValueError("Effort and velocity limits must be positive.")

    max_effort = effort * (1.0 - velocity / speed)
    max_effort = np.minimum(np.maximum(max_effort, 0.0), effort)
    min_effort = effort * (-1.0 - velocity / speed)
    min_effort = np.maximum(np.minimum(min_effort, 0.0), -effort)
    return np.clip(requested, min_effort, max_effort).astype(np.float32)


def pd_torque(
    target_position: np.ndarray,
    joint_position: np.ndarray,
    joint_velocity: np.ndarray,
    p_gains: np.ndarray,
    d_gains: np.ndarray,
) -> np.ndarray:
    """Compute position-control torque before actuator saturation."""

    values = [
        np.asarray(target_position, dtype=np.float32),
        np.asarray(joint_position, dtype=np.float32),
        np.asarray(joint_velocity, dtype=np.float32),
        np.asarray(p_gains, dtype=np.float32),
        np.asarray(d_gains, dtype=np.float32),
    ]
    if any(value.shape != (12,) for value in values):
        raise ValueError(f"PD control requires five 12-vectors, got {[value.shape for value in values]}.")
    if not all(np.all(np.isfinite(value)) for value in values):
        raise ValueError("PD control inputs must be finite.")
    target, position, velocity, kp, kd = values
    return (kp * (target - position) - kd * velocity).astype(np.float32)
