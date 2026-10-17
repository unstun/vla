"""Record every physics-substep contact, with an explicit optional fatal policy.

Historical Building trials selected `nonfoot_fatal`: any non-foot link at the
configured threshold latched a case failure. The user-selected native baseline
uses `stop_on_contact=False`: it records first contact and all later force
samples without stopping physics or latching command failure. V12 keeps its
own TORSO-only illegal-contact termination at 1 N in either profile.

PhysX integrates at 5 ms while the policy steps at 20 ms; post-step forces alone
can miss transient contact. This module samples each scene update. The contact
observation and the optional command-failure latch are separate responsibilities.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Optional, Sequence

# Reported in STATUS_V1.termination_code and in the runner's case record. Zero
# stays "no termination"; every latched case failure must be nonzero.
TERMINATION_CODE_NONFOOT_CONTACT = 2


@dataclass(frozen=True)
class ContactFailure:
    """The first substep at or above the threshold, kept as run evidence."""

    body_index: int
    body_name: Optional[str]
    force_n: float
    threshold_n: float
    step_index: int
    substep_index: int
    substep_age_s: float
    control_sim_time_s: float
    substep_sim_time_s: float
    termination_code: int = TERMINATION_CODE_NONFOOT_CONTACT

    def as_record(self) -> dict:
        return {
            "body_index": self.body_index,
            "body_name": self.body_name,
            "force_n": self.force_n,
            "threshold_n": self.threshold_n,
            "step_index": self.step_index,
            "substep_index": self.substep_index,
            "substep_age_s": self.substep_age_s,
            "control_sim_time_s": self.control_sim_time_s,
            "substep_sim_time_s": self.substep_sim_time_s,
            "termination_code": self.termination_code,
        }


class ContactHistoryError(RuntimeError):
    """Raised when a contact history cannot support an all-substep decision."""


class SubstepContactStop(RuntimeError):
    """Unwind the environment step immediately after the offending substep."""

    def __init__(self, failure):
        self.failure = failure
        super().__init__("nonfoot_contact_above_threshold")


class SubstepContactMonitor:
    """Inspect fresh contact data after each scene update, before the next step.

    The scene's original update remains the data owner. Reading the sensor data
    after it forces Isaac's lazy sensor update for this physics timestamp.
    No vendored environment or integration loop is copied or modified.
    """

    def __init__(self, *, read_forces, clock, on_failure, required_substeps,
                 stop_on_contact=True, **guard_args):
        self.stop_on_contact = bool(stop_on_contact)
        self.guard = NonFootContactGuard(
            required_substeps=1, continue_after_contact=not self.stop_on_contact,
            **guard_args)
        self.required_substeps = required_substeps
        self.read_forces, self.clock, self.on_failure = read_forces, clock, on_failure
        self.samples = []
        self.step_index = None
        self.control_steps = 0
        self.failure = None
        self.first_contact = None
        self._scene = None

    def install(self, scene):
        self._scene, self._original_update = scene, scene.update

        def update(*args, **kwargs):
            result = self._original_update(*args, **kwargs)
            if self.step_index is not None:
                sample = list(self.read_forces())
                self.samples.append(sample)
                failed = self.guard.observe([sample], self.clock(), self.step_index)
                if failed is not None and self.first_contact is None:
                    self.first_contact = replace(failed, substep_index=len(self.samples) - 1)
                if failed is not None and self.stop_on_contact:
                    self.failure = self.first_contact
                    self.on_failure("nonfoot_contact_above_threshold")
                    raise SubstepContactStop(self.failure)
            return result

        scene.update = update

    def begin(self, step_index):
        if self.failure is not None:
            raise SubstepContactStop(self.failure)
        self.step_index, self.samples = step_index, []
        self.control_steps += 1

    def end(self):
        self.step_index = None
        if len(self.samples) != self.required_substeps:
            raise ContactHistoryError("physics step/contact sample count mismatch")

    def restore(self):
        if self._scene is not None:
            self._scene.update = self._original_update
            self._scene = None

    def as_record(self):
        record = self.guard.as_record()
        record.update(required_substeps=self.required_substeps,
                      observed_control_steps=self.control_steps,
                      acquisition="after_each_physics_substep_scene_update",
                      contact_policy="nonfoot_fatal" if self.stop_on_contact else "native_v12",
                      contact_detected=self.guard.failure is not None,
                      first_contact=self.first_contact.as_record() if self.first_contact else None,
                      failed=self.failure is not None,
                      failure=self.failure.as_record() if self.failure else None)
        return record


class NonFootContactGuard:
    """Latch the first non-foot contact at or above the threshold.

    `observe` receives one control period's contact-force history: an ordered
    sequence of per-body force norms, one entry per physics substep. Entries are
    scanned oldest-first so the latched event is the earliest failing substep,
    not merely the largest one.
    """

    def __init__(
        self,
        threshold_n: float,
        nonfoot_indices: Sequence[int],
        body_names: Optional[Sequence[str]] = None,
        physics_dt_s: float = 0.005,
        required_substeps: int = 1,
        newest_first: bool = True,
        continue_after_contact: bool = False,
    ) -> None:
        if not (math.isfinite(threshold_n) and threshold_n > 0.0):
            raise ValueError("threshold_n must be finite and positive")
        if not (math.isfinite(physics_dt_s) and physics_dt_s > 0.0):
            raise ValueError("physics_dt_s must be finite and positive")
        if required_substeps < 1:
            raise ValueError("required_substeps must be at least one")
        self._threshold_n = float(threshold_n)
        self._nonfoot_indices = tuple(int(index) for index in nonfoot_indices)
        self._body_names = tuple(body_names) if body_names is not None else None
        self._physics_dt_s = float(physics_dt_s)
        self._required_substeps = int(required_substeps)
        self._newest_first = bool(newest_first)
        self._continue_after_contact = bool(continue_after_contact)
        self._failure: Optional[ContactFailure] = None
        self._observed_substeps = 0
        self._observed_control_steps = 0
        self._maximum_nonfoot_force_n = 0.0

    @property
    def threshold_n(self) -> float:
        return self._threshold_n

    @property
    def required_substeps(self) -> int:
        return self._required_substeps

    @property
    def failed(self) -> bool:
        return self._failure is not None

    @property
    def failure(self) -> Optional[ContactFailure]:
        return self._failure

    @property
    def observed_substeps(self) -> int:
        return self._observed_substeps

    @property
    def observed_control_steps(self) -> int:
        return self._observed_control_steps

    @property
    def maximum_nonfoot_force_n(self) -> float:
        """Maximum over every inspected substep, not only post-step samples."""
        return self._maximum_nonfoot_force_n

    def observe(
        self,
        history: Sequence[Sequence[float]],
        control_sim_time_s: float,
        step_index: int,
    ) -> Optional[ContactFailure]:
        """Evaluate one control period and return a newly latched failure.

        A history shorter than `required_substeps` cannot prove that every
        physics substep was inspected, so it raises instead of reporting a
        silent zero.
        """
        if self._failure is not None and not self._continue_after_contact:
            # A latched case failure is terminal: nothing after it is admitted.
            return None
        rows = [tuple(float(value) for value in row) for row in history]
        if len(rows) < self._required_substeps:
            raise ContactHistoryError(
                "contact history covers {} substeps, need {}".format(
                    len(rows), self._required_substeps
                )
            )
        # Trim to this control period and order it oldest-first. `age` counts
        # substeps back from the post-step sample, so age 0 is the newest.
        count = self._required_substeps
        if self._newest_first:
            window = rows[:count]
            samples = [(window[index], index) for index in range(count)]
            samples.reverse()
        else:
            window = rows[-count:]
            samples = [(window[index], count - 1 - index) for index in range(count)]
        self._observed_control_steps += 1
        for row, age in samples:
            self._observed_substeps += 1
            for index in self._nonfoot_indices:
                if index >= len(row):
                    raise ContactHistoryError(
                        "contact history row has {} bodies; body index {} is out of "
                        "range".format(len(row), index)
                    )
                force = row[index]
                if not math.isfinite(force):
                    raise ContactHistoryError(
                        "contact history contains a non-finite force for body "
                        "index {}".format(index)
                    )
                if force > self._maximum_nonfoot_force_n:
                    self._maximum_nonfoot_force_n = force
                if force >= self._threshold_n and self._failure is None:
                    substep_age_s = age * self._physics_dt_s
                    self._failure = ContactFailure(
                        body_index=index,
                        body_name=(
                            self._body_names[index]
                            if self._body_names is not None and index < len(self._body_names)
                            else None
                        ),
                        force_n=force,
                        threshold_n=self._threshold_n,
                        step_index=int(step_index),
                        substep_index=int(count - 1 - age),
                        substep_age_s=substep_age_s,
                        control_sim_time_s=float(control_sim_time_s),
                        substep_sim_time_s=float(control_sim_time_s) - substep_age_s,
                    )
        return self._failure

    def as_record(self) -> dict:
        return {
            "threshold_n": self._threshold_n,
            "required_substeps": self._required_substeps,
            "physics_dt_s": self._physics_dt_s,
            "history_newest_first": self._newest_first,
            "nonfoot_body_indices": list(self._nonfoot_indices),
            "nonfoot_body_names": (
                [
                    self._body_names[index]
                    for index in self._nonfoot_indices
                    if index < len(self._body_names)
                ]
                if self._body_names is not None
                else None
            ),
            "observed_control_steps": self._observed_control_steps,
            "observed_substeps": self._observed_substeps,
            "maximum_nonfoot_force_n": self._maximum_nonfoot_force_n,
            "failed": self.failed,
            "failure": self._failure.as_record() if self._failure is not None else None,
        }


def required_substeps_for(policy_dt_s: float, physics_dt_s: float) -> int:
    """Physics substeps inside one control period, rounded up.

    A control period that is not an exact multiple of the physics period still
    has to be covered completely, so the count rounds up rather than down.
    """
    if not (math.isfinite(policy_dt_s) and policy_dt_s > 0.0):
        raise ValueError("policy_dt_s must be finite and positive")
    if not (math.isfinite(physics_dt_s) and physics_dt_s > 0.0):
        raise ValueError("physics_dt_s must be finite and positive")
    return max(1, int(math.ceil(policy_dt_s / physics_dt_s - 1.0e-9)))
