"""v291: support-aware stopping assistance before the unchanged v216 PD gate.

This is an opt-in candidate. A quiet loaded leg keeps its torque-matched target
at the original RL gains while unlanded legs retain policy output. Formal PD
entry still requires the parent's full support/motion dwell. No physics claim.
"""
import hashlib
import importlib.util
import os
from pathlib import Path
import numpy as np

PARENT = Path(os.environ.get('V291_PARENT_STANCE', str(Path(__file__).resolve().parents[1] / 'v216/stance_hold.py')))
PARENT_SHA256 = 'ad33d885820cab324a9768d4b528f58a313965aa3781873ca772d3b8e188d280'
if hashlib.sha256(PARENT.read_bytes()).hexdigest() != PARENT_SHA256:
    raise RuntimeError('Frozen v216 stance source changed')
spec = importlib.util.spec_from_file_location('v291_parent_stance', PARENT)
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)
for _name in dir(parent):
    if not _name.startswith('__'):
        globals()[_name] = getattr(parent, _name)


class StanceHold(parent.StanceHold):
    def __init__(self, *args, settling_capture=False, **kwargs):
        self.settling_capture = bool(settling_capture)
        super().__init__(*args, **kwargs)
        if self.settling_capture and self.joint_count != 12:
            raise ValueError('Supported-leg settling requires the original 12-joint Lite3 order')

    def reset(self):
        super().reset()
        self._settling_targets = np.zeros(12)
        self.settling_contact_mask = np.zeros(4, dtype=bool)

    def update(self, x):
        had_capture = bool(np.any(self.settling_contact_mask))
        out = super().update(x)  # Original validation, dwell and transition logic.
        if not self.settling_capture or self.setting == 'off':
            self.settling_contact_mask[:] = False
            return out
        if had_capture and out.mode == 'RL' and out.reason == 'fixed_stand_cancelled:new_command':
            # Captured joints are not raw policy output. Reuse the real 0.25 s
            # handback instead of jumping to a different target on cancellation.
            self._set_mode('REJOIN', 'settling_capture_cancelled:new_command', float(x.now_s))
            self._phase_start = float(x.now_s)
            self.progress = 0.0
            self._rejoin_target = np.array(x.applied_target, dtype=float, copy=True)
            self._rejoin_kp = np.array(x.applied_kp, dtype=float, copy=True)
            self._rejoin_kd = np.array(x.applied_kd, dtype=float, copy=True)
            self.counters['rejoins'] += 1
            self.settling_contact_mask[:] = False
            return self._output(self._rejoin_target, self._rejoin_kp, self._rejoin_kd, False)
        quiet_body = (x.linear_speed <= SETTLE_LINEAR_SPEED_MAX and
                      x.angular_speed <= SETTLE_ANGULAR_SPEED_MAX and
                      x.tilt_deg <= SETTLE_TILT_MAX_DEG)
        if out.mode == 'STAND_TRANSITION' and had_capture:
            # The old crossfade starts from its live policy component. Keep the
            # already arrested legs in that component, rather than reintroducing
            # a stepping target at the first PD tick. Gains and blend are intact.
            policy = np.array(x.policy_target, dtype=float, copy=True)
            mask = np.repeat(self.settling_contact_mask, 3)
            policy[mask] = self._settling_targets[mask]
            ramp = self._entry_crossfade(float(x.now_s) - self._phase_start, policy, np.asarray(x.joint_pos))
            return self._output(self._clip_target(ramp[0]), ramp[1], ramp[2], False)
        if out.mode != 'STAND_SETTLING' or not quiet_body:
            self.settling_contact_mask[:] = False
            return out
        q = np.asarray(x.joint_pos)
        qd = np.asarray(x.joint_vel)
        applied = np.asarray(x.applied_target)
        kp = np.asarray(x.applied_kp)
        kd = np.asarray(x.applied_kd)
        for leg, force in enumerate(x.foot_forces):
            indices = slice(leg * 3, leg * 3 + 3)
            if force <= HOLD_CONTACT_N:
                self.settling_contact_mask[leg] = False
            if (not self.settling_contact_mask[leg] and force >= ENTRY_FOOT_FORCE_N and
                    np.all(np.abs(qd[indices]) <= SETTLE_JOINT_SPEED_MAX)):
                # Match the complete applied stiffness+damping torque on entry.
                target = q[indices] + (kp[indices] * (applied[indices] - q[indices]) +
                         (BASE_KD - kd[indices]) * qd[indices]) / BASE_KP
                if self._lower is not None and (np.any(target < self._lower[indices]) or
                                                np.any(target > self._upper[indices])):
                    continue
                self._settling_targets[indices] = target
                self.settling_contact_mask[leg] = True
        mask = np.repeat(self.settling_contact_mask, 3)
        if not np.any(mask):
            return out
        out.target[mask] = self._settling_targets[mask]
        # False means the policy no longer owns every joint. Newton's existing
        # applied-action history then records the actual mixed target correctly.
        out.policy_owns_joints = False
        return out

    def status(self):
        result = super().status()
        result.update(settling_capture=self.settling_capture,
                      settling_contact_mask=self.settling_contact_mask.tolist())
        return result
