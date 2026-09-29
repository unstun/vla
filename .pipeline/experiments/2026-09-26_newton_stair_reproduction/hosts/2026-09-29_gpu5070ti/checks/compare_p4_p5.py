"""P4 and P5 of PORT.md: compare gpu5070ti's replay with the Mac's (versions/v32/gc_schedule_check/none/).
Usage: compare_p4_p5.py <replay directory in this port directory, for example p5_replay_none_attempt02>.

P4, the factory controller: each record row is [t, phase, zero, measured(45), motor(72), torque(12), q(19), qd(18), up].
The controller's request is determined by t and the measured state (factory_navigation_startup.py packs t, SIM_DT, the
measured values and a command block set from t alone), and its reply by the requests so far. So up to the first step
whose t or measured state differs between the hosts, every reply must be bit-identical.
P5, the physics: the replay's joint-state error against the trial (the Mac's was 0.0 over 946 steps), and the
host-to-host difference of every replayed step's joint state over time.
Prints JSON; writes nothing.
"""
import json
from pathlib import Path
import sys

import numpy as np

H = Path(__file__).resolve().parents[1]
MAC = H.parents[1] / "versions/v32/gc_schedule_check/none"


def main():
    LIN = H / sys.argv[1]
    mac = np.load(MAC / "factory_full_rate.npz")["records"]
    lin = np.load(LIN / "factory_full_rate.npz")["records"]
    n = min(len(mac), len(lin))
    request = slice(0, 48)  # t, phase and zero flag (replies of the previous step), measured state
    measured = np.r_[0, 3:48]  # t and the measured state alone
    motor = slice(48, 120)
    same_input = np.all(mac[:n, measured] == lin[:n, measured], axis=1)
    first_input_diff = int(np.argmin(same_input)) if not same_input.all() else None
    upto = n if first_input_diff is None else first_input_diff
    same_reply = np.all(mac[:upto, motor] == lin[:upto, motor], axis=1)
    p4 = {"records": [len(mac), len(lin)], "first_step_with_different_input": first_input_diff,
          "steps_with_identical_input_history": upto,
          "replies_bit_identical_over_that_history": bool(same_reply.all()),
          "first_reply_difference_within_it": None if same_reply.all() else int(np.argmin(same_reply)),
          "events_equal": json.loads((MAC / "factory_events.json").read_text())
          == json.loads((LIN / "factory_events.json").read_text()),
          "handoff_equal": json.loads((MAC / "factory_handoff.json").read_text())
          == json.loads((LIN / "factory_handoff.json").read_text())}
    if first_input_diff is not None:
        k = first_input_diff
        p4["at_first_input_difference"] = {"t": [float(mac[k, 0]), float(lin[k, 0])],
                                           "max_abs_measured_diff": float(np.max(np.abs(mac[k, measured] - lin[k, measured])))}
        p4["max_abs_reply_diff_after"] = float(np.max(np.abs(mac[k:n, motor] - lin[k:n, motor])))
    p4["passed"] = p4["replies_bit_identical_over_that_history"]

    summary = {h: json.loads((d / "summary.json").read_text()) for h, d in (("mac", MAC), ("gpu5070ti", LIN))}
    rows = {}
    for h, d in (("mac", MAC), ("gpu5070ti", LIN)):
        rows[h] = [json.loads(line) for line in open(d / "rows.jsonl")]
    m = min(len(rows["mac"]), len(rows["gpu5070ti"]))
    diff = np.array([np.max(np.abs(np.asarray(a["joint_q"]) - np.asarray(b["joint_q"])))
                     for a, b in zip(rows["mac"][:m], rows["gpu5070ti"][:m])])
    marks = [s for s in (0, 49, 99, 249, 499, 749, m - 1) if s < m]
    p5 = {"control_steps": [summary["mac"]["control_steps"], summary["gpu5070ti"]["control_steps"]],
          "joint_q_worst_error_vs_trial": [summary["mac"]["joint_q_worst_error"], summary["gpu5070ti"]["joint_q_worst_error"]],
          "loop_wall_s": [summary["mac"]["loop_wall_s"], summary["gpu5070ti"]["loop_wall_s"]],
          "host_to_host_joint_q_max_abs": float(diff.max()) if m else None,
          "first_step_differing": int(np.argmax(diff > 0)) if (diff > 0).any() else None,
          "host_to_host_at_steps": {int(s) + 1: float(diff[s]) for s in marks}}
    p5["bit_identical"] = p5["joint_q_worst_error_vs_trial"][1] == 0.0
    print(json.dumps({"P4": p4, "P5": p5}, indent=2))


if __name__ == "__main__":
    sys.exit(main())
