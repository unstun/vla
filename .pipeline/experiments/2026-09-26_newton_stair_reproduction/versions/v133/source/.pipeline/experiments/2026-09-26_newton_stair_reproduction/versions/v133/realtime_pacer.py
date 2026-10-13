"""Pace every actual integration against native time and an absolute wall clock."""
import math
import time


class NativeClockPacer:
    def __init__(self, native_start_s, clock=time.monotonic, sleep=time.sleep):
        if not math.isfinite(native_start_s):
            raise ValueError("Nonfinite native start time")
        self.clock, self.sleep = clock, sleep
        self.native_start_s = self.last_native_s = native_start_s
        self.wall_start_s = clock()
        self.steps = 0
        self.max_lag_s = 0.
        self.lag_over_1ms_steps = 0
        self.sleep_s = 0.

    def wait(self, native_s):
        if not math.isfinite(native_s) or native_s <= self.last_native_s:
            raise ValueError("Native clock failed to advance after an actual integration")
        deadline = self.wall_start_s + native_s - self.native_start_s
        now = self.clock()
        delay = deadline - now
        if delay > 0.:
            self.sleep(delay)
            self.sleep_s += delay
        lag = max(0., self.clock() - deadline)
        self.max_lag_s = max(self.max_lag_s, lag)
        self.lag_over_1ms_steps += lag > .001
        self.last_native_s = native_s
        self.steps += 1

    def snapshot(self, native_s):
        wall = self.clock() - self.wall_start_s
        native = native_s - self.native_start_s
        return {"target_rtf": 1., "native_elapsed_s": native, "wall_elapsed_s": wall,
                "actual_rtf": native / wall if wall > 0. else None,
                "wall_anchor_monotonic_s": self.wall_start_s,
                "native_anchor_s": self.native_start_s, "physics_steps": self.steps,
                "fixed_step_nominal_elapsed_s": self.steps * .001,
                "current_lag_s": max(0., wall - native), "max_lag_s": self.max_lag_s,
                "lag_over_1ms_steps": self.lag_over_1ms_steps, "requested_sleep_s": self.sleep_s,
                "time_source": "actual native solver time", "dropped_physics_steps": 0}
