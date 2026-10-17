"""Resolve algorithm entry points without calling them or the factory executable."""

import ctypes
import json
import os
import resource


LIBRARY = "/snapshot/lib/ras_lib/libdeepras.so"
EXPORTS = [
    "_Z13MotionInitialRKNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEES6_RK12MotionConfig",
    "_Z6MotionPK8DataLegsRK8DataGyroRKdS6_RK15ControlCommandsPA140_dPS_",
]

library = ctypes.CDLL(LIBRARY, mode=os.RTLD_NOW | os.RTLD_LOCAL)
resolved = {name: bool(getattr(library, name)) for name in EXPORTS}
print(json.dumps({
    "loaded": True,
    "exports_resolved": resolved,
    "algorithm_functions_called": False,
    "factory_executable_started": False,
    "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
}, sort_keys=True), flush=True)
