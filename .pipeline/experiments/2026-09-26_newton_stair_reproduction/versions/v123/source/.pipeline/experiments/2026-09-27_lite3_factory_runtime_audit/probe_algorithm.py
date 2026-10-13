"""Synthetic measured-input test; never a physics or factory-motion validation."""

import argparse
import json
import math
import struct

from factory_process import FactoryProcess, ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--run", required=True)
    parser.add_argument("--hip-x", type=float, default=0.0)
    args = parser.parse_args()
    if not 1 <= args.steps <= 10000 or not args.run.replace("_", "").isalnum():
        raise ValueError("invalid bounded probe arguments")
    output = ROOT / "algorithm_probes" / args.run
    events = []
    last = None
    period = 0.002
    with FactoryProcess(output) as actor:
        with (output / "trace.jsonl").open("w") as log:
            for i in range(args.steps):
                now = i * period
                command = bytearray(552)
                command[73] = int(now >= 0.25)  # ParseCommand 0x7e058: toggle on 0x0c05.
                command[0] = int(now >= 7.0)  # Separate stand request after homing.
                # Frozen input deliberately cannot establish physical homing completion.
                q = [args.hip_x, math.radians(-70), math.radians(150)] * 4
                measured = q + [0.0] * 24 + [0.0] * 8 + [9.81]
                request = struct.pack("<47d552s", now, period, *measured, bytes(command))
                reply = actor.step(request)
                motor = struct.unpack_from("<72d", reply, 288)
                basic, gait, policy = struct.unpack_from("<3i", reply, 1984)
                phase, cycle = struct.unpack_from("<iI", reply, 2192)
                zero_flag = bool(reply[1984 + 0xbd])
                key = (basic, gait, policy, phase, zero_flag)
                if key != last:
                    events.append({"time": now, "basic": basic, "gait": gait,
                                   "policy": policy, "phase": phase, "zero_flag": zero_flag})
                    last = key
                if i % 50 == 0 or i == args.steps - 1:
                    log.write(json.dumps({"time": now, "cycle": cycle, "phase": phase,
                                          "zero_flag": zero_flag,
                                          "kp": motor[:12], "kd": motor[12:24],
                                          "tau": motor[24:36], "q": motor[36:48],
                                          "qd": motor[48:60]}) + "\n")
    result = {"steps": args.steps, "period": period, "events": events,
              "claim": "synthetic algorithm I/O only; frozen joints, no physics or encoder correction"}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
