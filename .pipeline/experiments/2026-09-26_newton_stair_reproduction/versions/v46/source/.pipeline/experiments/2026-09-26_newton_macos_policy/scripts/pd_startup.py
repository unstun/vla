"""Simulation adapter for the pinned Lite3 SDK's preparation/stand sequence."""
import ctypes
import hashlib
import json
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
SDK_PREPARE = np.tile(np.array([0., -70., 150.]) * (3.1415926 / 180.), 4).astype(np.float32)


class SdkSpline:
    def __init__(self):
        root = BASE / "runtime/lite3_sdk_spline"
        library = root / "liblite3_spline.dylib"
        self.identity = json.loads((root / "build_identity.json").read_text())
        source = BASE.parents[2] / "references/upstream/2026-09-27_lite3_pd_startup/src/motionexample.cpp"
        if hashlib.sha256(source.read_bytes()).hexdigest() != self.identity["source_sha256"]:
            raise ValueError("SDK source differs from compiled spline identity")
        if hashlib.sha256(library.read_bytes()).hexdigest() != self.identity["library_sha256"]:
            raise ValueError("SDK spline library hash mismatch; rebuild from pinned source")
        self.library = ctypes.CDLL(str(library))
        self.function = self.library.lite3_spline
        self.function.argtypes = [ctypes.c_double] * 5 + [ctypes.POINTER(ctypes.c_double)]
        self.function.restype = None

    def sample(self, initial, goal, elapsed, duration, dt=.001):
        if not np.isfinite([elapsed, duration, dt]).all() or elapsed < 0 or duration < dt or dt <= 0:
            raise ValueError("Invalid spline time")
        initial, goal = np.asarray(initial), np.asarray(goal)
        if initial.shape != goal.shape or not np.isfinite(initial).all() or not np.isfinite(goal).all():
            raise ValueError("Invalid spline endpoints")
        positions, velocities = np.empty(initial.size), np.empty(initial.size)
        values = (ctypes.c_double * 3)()
        for i, (first, last) in enumerate(zip(initial.flat, goal.flat, strict=True)):
            self.function(float(first), float(last), elapsed, dt, duration, values)
            positions[i], velocities[i] = values[0], (values[1] - values[0]) / dt
        return positions.reshape(initial.shape).astype(np.float32), velocities.reshape(initial.shape).astype(np.float32)


class PDStartup:
    """Measured entry gate; all times use the uninterrupted physics-step clock."""
    def __init__(self, reference):
        self.reference = np.asarray(reference, dtype=np.float32).copy()
        self.spline = SdkSpline()
        self.phase, self.entered = "crouch", 0.
        self.initial = SDK_PREPARE.copy()
        self.stable_since = None
        self.handoff_time = None
        self.events = [{"phase": self.phase, "time_s": 0.}]

    @property
    def ready(self):
        return self.phase == "policy"

    def advance(self, time, q, qd, base_z, base_up, linear_speed, angular_speed):
        if not np.isfinite(np.r_[time, q, qd, base_z, base_up, linear_speed, angular_speed]).all():
            raise ValueError("Nonfinite startup state")
        if time >= 8. and self.phase not in ("handoff", "policy"):
            raise TimeoutError("PD startup did not reach measured standing stability within 8 s")
        next_phase = None
        elapsed = time - self.entered
        if self.phase == "crouch" and elapsed >= 1.:
            next_phase = "prepare"
        elif self.phase == "prepare" and elapsed >= 1.:
            next_phase = "stand"
        elif self.phase == "stand" and elapsed >= 1.5:
            next_phase = "settle"
        elif self.phase == "settle":
            stable = (base_up >= .98 and base_z >= .25 and
                      np.max(np.abs(q - self.reference)) <= .15 and np.max(np.abs(qd)) <= .3 and
                      linear_speed <= .03 and angular_speed <= .08)
            if not stable:
                self.stable_since = None
            elif self.stable_since is None:
                self.stable_since = time
            elif time - self.stable_since >= .5:
                next_phase = "handoff"
                self.handoff_time = time
        elif self.phase == "handoff" and elapsed >= .25:
            next_phase = "policy"
        if next_phase:
            self.phase, self.entered = next_phase, time
            self.initial = np.asarray(q, dtype=np.float32).copy()
            self.events.append({"phase": self.phase, "time_s": time, "measured_q": self.initial.tolist()})

    def motor_command(self, time, policy_target):
        elapsed = max(0., time - self.entered)
        zeros = np.zeros(12, np.float32)
        if self.phase == "crouch":
            return SDK_PREPARE.copy(), zeros, 0., .7
        if self.phase in ("prepare", "stand"):
            goal, duration = ((SDK_PREPARE, 1.) if self.phase == "prepare" else (self.reference, 1.5))
            position, velocity = self.spline.sample(self.initial, goal, elapsed, duration)
            return position, velocity, 60., .7
        if self.phase == "settle":
            return self.reference.copy(), zeros, 80., .7
        if self.phase == "handoff":
            alpha = float(self.spline.sample(np.array(0.), np.array(1.), elapsed, .25)[0])
            kp, kd = 80. * (1. - alpha) + 20. * alpha, .7 * (1. - alpha) + .5 * alpha
            # Blend the two PD torques exactly, including both gain changes.
            position = (80. * (1. - alpha) * self.reference + 20. * alpha * policy_target) / kp
            return position, zeros, kp, kd
        return policy_target, zeros, 20., .5
