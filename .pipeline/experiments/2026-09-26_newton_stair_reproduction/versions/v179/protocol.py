"""Predeclared policy-only velocity schedule, independent of robot feedback."""
CONDITIONS = [(0.2, 3.0), (0.2, 3.3), (0.35, 2.8), (0.35, 3.1), (0.5, 2.4), (0.5, 2.7)]
STOP_SECONDS = 10.0
RESTART_SECONDS = 3.0
LATE_START_SECONDS = 2.0
DRIFT_FLAG_METERS = 0.05
STAIR_SCENARIO = {"spawn_ground_xyz_m": [-5.42, 6.413188839, 0.05804443359375],
                  "spawn_yaw_rad": -1.5707963267948966, "spawn_body_height_m": 0.35}


def phases(attempt):
    if not 1 <= attempt <= len(CONDITIONS):
        raise ValueError("Attempt must be 1..6")
    speed, duration = CONDITIONS[attempt - 1]
    return [("walk1", duration, [speed, 0.0, 0.0]),
            ("stop1", STOP_SECONDS, [0.0, 0.0, 0.0]),
            ("walk2", RESTART_SECONDS, [speed, 0.0, 0.0]),
            ("stop2", STOP_SECONDS, [0.0, 0.0, 0.0])]


def schedule(attempt, dt=0.02):
    index = 0
    for label, seconds, command in phases(attempt):
        count = round(seconds / dt)
        if abs(count * dt - seconds) > 1e-9:
            raise ValueError("Phase duration must align to policy steps")
        for step in range(count):
            yield dict(index=index, phase=label, phase_step=step, command=list(command))
            index += 1
