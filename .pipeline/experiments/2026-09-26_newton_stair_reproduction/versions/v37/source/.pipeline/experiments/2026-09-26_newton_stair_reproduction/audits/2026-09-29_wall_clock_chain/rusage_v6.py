"""Read this process's macOS rusage_info_v6 (proc_pid_rusage, RUSAGE_INFO_V6) through ctypes.

Fields used (Apple sys/resource.h; times are Mach absolute ticks, converted with mach_timebase_info):
- ri_user_time + ri_system_time: CPU time of all threads;
- ri_user_ptime + ri_system_ptime: the part of it spent on performance cores;
- ri_runnable_time: time threads were runnable but not running (waiting for a CPU);
- ri_pageins: page-ins.
"""
import ctypes
import os

FIELDS = ["user_time", "system_time", "pkg_idle_wkups", "interrupt_wkups", "pageins", "wired_size", "resident_size",
          "phys_footprint", "proc_start_abstime", "proc_exit_abstime", "child_user_time", "child_system_time",
          "child_pkg_idle_wkups", "child_interrupt_wkups", "child_pageins", "child_elapsed_abstime",
          "diskio_bytesread", "diskio_byteswritten", "cpu_time_qos_default", "cpu_time_qos_maintenance",
          "cpu_time_qos_background", "cpu_time_qos_utility", "cpu_time_qos_legacy", "cpu_time_qos_user_initiated",
          "cpu_time_qos_user_interactive", "billed_system_time", "serviced_system_time", "logical_writes",
          "lifetime_max_phys_footprint", "instructions", "cycles", "billed_energy", "serviced_energy",
          "interval_max_phys_footprint", "runnable_time", "flags", "user_ptime", "system_ptime", "pinstructions",
          "pcycles", "energy_nj", "penergy_nj", "secure_time_in_system", "secure_ptime_in_system",
          "neural_footprint", "lifetime_max_neural_footprint", "interval_max_neural_footprint"]


class RusageInfoV6(ctypes.Structure):
    _fields_ = [("uuid", ctypes.c_uint8 * 16)] + [(name, ctypes.c_uint64) for name in FIELDS] + \
               [("reserved", ctypes.c_uint64 * 9)]


class Timebase(ctypes.Structure):
    _fields_ = [("numer", ctypes.c_uint32), ("denom", ctypes.c_uint32)]


_lib = ctypes.CDLL("/usr/lib/libSystem.dylib")
_lib.proc_pid_rusage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
_timebase = Timebase()
_lib.mach_timebase_info(ctypes.byref(_timebase))
TICK_NS = _timebase.numer / _timebase.denom
RUSAGE_INFO_V6 = 6
PID = os.getpid()


def read():
    """Return (cpu_ns, pcore_cpu_ns, runnable_ns, pageins) for this process."""
    info = RusageInfoV6()
    if _lib.proc_pid_rusage(PID, RUSAGE_INFO_V6, ctypes.byref(info)) != 0:
        raise OSError(ctypes.get_errno(), "proc_pid_rusage failed")
    return (int((info.user_time + info.system_time) * TICK_NS), int((info.user_ptime + info.system_ptime) * TICK_NS),
            int(info.runnable_time * TICK_NS), int(info.pageins))


if __name__ == "__main__":
    import time
    first = read()
    end = time.monotonic() + .2
    while time.monotonic() < end:
        pass
    second = read()
    print({"tick_ns": TICK_NS, "delta_cpu_ms": (second[0] - first[0]) / 1e6, "delta_pcore_ms": (second[1] - first[1]) / 1e6,
           "delta_runnable_ms": (second[2] - first[2]) / 1e6, "pageins": second[3]})
