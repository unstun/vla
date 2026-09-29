"""P4b on gpu5070ti, added after P4's pre-registered test proved vacuous (no step had an identical input history).

Feeds the Mac's 11,020 recorded factory requests (versions/v32/gc_schedule_check/none/factory_full_rate.npz, copied to
p4b/mac_factory_full_rate.npz) to the emulated controller, open loop, in order, and compares every reply with the
Mac's recorded reply. Requests are rebuilt as scripts/factory_navigation_startup.py packs them: t, SIM_DT (0.001,
lite3_reference), the 45 measured values, and a 552-byte command block whose byte 73 is t >= 1 and byte 0 is t >= 7.5.
Pass: every reply's motor block (72 doubles), phase and zero flag are bit-identical to the Mac's. From attempt 02
the motor block is compared as raw 64-bit patterns (port review round 1, N9: attempt 01 compared values, which
treats +0 and -0 as equal).
Usage: p4b_request_replay.py <attempt>; writes p4b/attemptNN/ (the factory process record) and p4b/attemptNN.json.
"""
import json
from pathlib import Path
import struct
import sys
import time

import numpy as np

E = Path.home() / "vla_exec/vla/.pipeline/experiments"
sys.path.insert(0, str(E / "2026-09-27_lite3_factory_runtime_audit"))
from factory_process import FactoryProcess  # noqa: E402

SIM_DT = 0.001
H = E / "2026-09-26_newton_stair_reproduction/hosts/2026-09-29_gpu5070ti/p4b"


def main():
    attempt = int(sys.argv[1])
    result_path = H / f"attempt{attempt:02d}.json"
    assert not result_path.exists(), result_path
    records = np.load(H / "mac_factory_full_rate.npz")["records"]
    mismatched = []
    begin = time.monotonic()
    with FactoryProcess(H / f"attempt{attempt:02d}", wall_limit=600) as actor:
        ready_s = time.monotonic() - begin
        for k, row in enumerate(records):
            t = float(row[0])
            command = bytearray(552)
            command[73], command[0] = int(t >= 1.), int(t >= 7.5)
            raw = actor.step(struct.pack("<47d552s", t, SIM_DT, *row[3:48], bytes(command)))
            motor = np.frombuffer(raw, dtype="<f8", count=72, offset=288)
            phase, _ = struct.unpack_from("<iI", raw, 2192)
            zero = bool(raw[1984 + 0xbd])
            if not (np.array_equal(motor.view("<u8"), np.ascontiguousarray(row[48:120]).astype("<f8").view("<u8"))
                    and phase == int(row[1]) and zero == bool(row[2])):
                mismatched.append(k)
    wall = time.monotonic() - begin
    result = {"requests": len(records), "mismatched_replies": len(mismatched), "first_mismatches": mismatched[:10],
              "compile_and_ready_s": round(ready_s, 2), "wall_s": round(wall, 2),
              "mean_step_ms": round(1e3 * (wall - ready_s) / len(records), 3),
              "passed": not mismatched}
    result_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
