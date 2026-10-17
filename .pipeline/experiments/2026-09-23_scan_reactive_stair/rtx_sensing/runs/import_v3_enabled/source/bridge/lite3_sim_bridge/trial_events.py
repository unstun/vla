"""Measured runtime reset/pose-write attempts and terminal process outcomes."""


class TrialStateMutation(RuntimeError):
    pass


class TrialEvents:
    """Install after initialization; block and count runtime state mutations."""

    def __init__(self):
        self.autoresets = 0
        self.pose_injection_events = 0
        self.reset_attempts = 0
        self.pose_write_attempts = 0
        self._originals = []

    def install(self, env, robot):
        def reject_reset(ids, *args, **kwargs):
            if len(ids):
                self.reset_attempts += 1
                raise TrialStateMutation("environment termination before automatic reset")

        self._replace(env, "_reset_idx", reject_reset)
        methods = ("write_root_state_to_sim", "write_root_pose_to_sim",
                   "write_root_link_state_to_sim", "write_root_link_pose_to_sim",
                   "write_root_com_state_to_sim", "write_root_com_pose_to_sim")
        found = []
        for name in methods:
            if hasattr(robot, name):
                found.append(name)

                def reject_pose(*args, _name=name, **kwargs):
                    self.pose_write_attempts += 1
                    raise TrialStateMutation("runtime pose write blocked: " + _name)

                self._replace(robot, name, reject_pose)
        if not found:
            self.restore()
            raise TrialStateMutation("no articulation pose-write boundary found")

    def _replace(self, owner, name, method):
        self._originals.append((owner, name, getattr(owner, name)))
        setattr(owner, name, method)

    def restore(self):
        for owner, name, method in reversed(self._originals):
            setattr(owner, name, method)
        self._originals = []

    def as_record(self):
        return {"autoresets": self.autoresets,
                "pose_injection_events": self.pose_injection_events,
                "reset_attempts": self.reset_attempts,
                "pose_write_attempts": self.pose_write_attempts,
                "state_mutation_monitor": "runtime_state_writes_blocked_and_counted"}


def trial_exit_code(status):
    return 0 if status in ("GOAL_REACHED_AND_STOPPED", "DURATION_REACHED") else 3
