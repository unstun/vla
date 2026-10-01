"""K4 of versions/v33/PLAN.md: counterfactual replay of every surveyed run's body-pose receipts through v33's gate.

For every run with runs/<run>/backend_body_callbacks.jsonl (at least 50 callbacks) the recorded receipts
(entered_ns: backend wall clock; stamp_ns: the pose's stamp) drive CommandGate.measurement_stale, which the gate's
tick and raw-command paths use unchanged in their check order. It is evaluated on a 20 ms wall grid and at every
receipt, so the heartbeat, which the replay cannot reproduce, does not decide.
- Wall base (the v32 rule; K3 C1 shows v33's wall base is identical): stale episodes, each a recorded wall gap over
  0.25 s that the grid hits. This reproduces the recorded odom_stale conditions and validates the replay.
- Simulation base, three /clock models:
  M1 newest pose received: /clock equals the newest received stamp. The simulation age is then always 0, so
     only the 2.0 s backstop can trip; M1 tests the backstop against the recorded wall gaps.
  M2 next stamp: throughout the gap before receipt i+1, /clock already equals stamp i+1.
  M3 burst (added after review round 1, N1): throughout that gap, /clock already equals the newest stamp received
     within 50 ms after it. M2 and M3 are approximations, not bounds: the backend's single-threaded executor
     takes one pose per wait cycle from a depth-5 queue while the depth-1 /clock jumps to the newest value.
     The direct measurement, the in-container observer's /clock against the backend's newest pose, is in
     evidence/clock_lead_survey.json.
- Synthetic loss: the receipts whose stamps fall in 0.30 s of simulation time from the run's median stamp are
  dropped while /clock keeps following them (M1 on the full record); the simulation base must trip.
Pass: the simulation base has no stale evaluation in any run under M1, M2 or M3, and trips in every run's synthetic
loss.
Writes replay_gate.json next to this script.
"""
import bisect
import glob
import importlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

H = Path(__file__).resolve().parent
E = H.parents[1]


def load_green():
    root = tempfile.mkdtemp(prefix="v33_replay_")
    package = Path(root) / "gate_v33_replay"
    package.mkdir()
    (package / "__init__.py").write_text("")
    for name in ("contracts.py", "control_gate.py"):
        shutil.copyfile(E / "runtime_sources/backend_adapter/backend_adapter" / name, package / name)
    sys.path.insert(0, root)
    return (importlib.import_module("gate_v33_replay.control_gate"), importlib.import_module("gate_v33_replay.contracts"),
            root)


def replay(g, c, wall, stamp, base, clock_model, clock_wall=None, clock_stamp=None):
    """Return the wall times of stale evaluations (grid and receipts), grouped into episodes."""
    clock = [None]
    burst = []  # M3: the newest stamp received within 50 ms after each receipt i+1
    for k in range(len(wall)):
        j, newest = min(k + 1, len(wall) - 1), stamp[min(k + 1, len(wall) - 1)]
        while j + 1 < len(wall) and wall[j + 1] - wall[min(k + 1, len(wall) - 1)] <= 0.05:
            j += 1
            newest = max(newest, stamp[j])
        burst.append(newest)
    gate = g.CommandGate(c.GateConfig(odom_time_base=base, odom_wall_backstop_s=2.0), sim_clock=lambda: clock[0])
    grid_start, grid_end = wall[0], wall[-1]
    times = sorted(set([grid_start + 0.02 * k for k in range(int((grid_end - grid_start) / 0.02) + 1)] + wall))
    stale, last = [], None
    for t in times:
        i = bisect.bisect_right(wall, t) - 1  # newest receipt at or before t
        if i < 0:
            continue
        measurement = c.MeasuredState(state_sequence=i + 1, monotonic_s=wall[i], position_world_m=(0.0, 0.0, 0.0),
                                      velocity_world_mps=(0.0, 0.0, 0.0), map_epoch="map", map_revision=0,
                                      stamp_s=stamp[i])
        if clock_model == "M1":
            if clock_wall is None:
                clock[0] = stamp[i]
            else:  # the clock follows the full record while some receipts are dropped
                j = bisect.bisect_right(clock_wall, t) - 1
                clock[0] = clock_stamp[j] if j >= 0 else None
        elif clock_model == "M2":  # the clock already equals the next receipt's stamp throughout the gap
            clock[0] = stamp[min(i + 1, len(stamp) - 1)] if t < wall[-1] else stamp[i]
        else:  # M3: the clock already equals the newest stamp received within 50 ms after the gap
            clock[0] = burst[i] if t < wall[-1] else stamp[i]
        if gate.measurement_stale(measurement, t):
            if last is None or t - last > 0.05:
                stale.append([round(t, 3), None])
            stale[-1][1] = round(t, 3)
            last = t
    return stale


def main():
    g, c, root = load_green()
    runs, ok = [], True
    for path in sorted(glob.glob(str(E / "runs/*/backend_body_callbacks.jsonl"))):
        rows = [json.loads(line) for line in open(path) if line.strip()]
        if len(rows) < 50:
            continue
        wall = [r["entered_ns"] / 1e9 for r in rows]
        stamp = [r["stamp_ns"] / 1e9 for r in rows]
        wall_base = replay(g, c, wall, stamp, "wall", "M1")
        m1 = replay(g, c, wall, stamp, "simulation", "M1")
        m2 = replay(g, c, wall, stamp, "simulation", "M2")
        m3 = replay(g, c, wall, stamp, "simulation", "M3")
        middle = stamp[len(stamp) // 2]
        keep = [k for k, s in enumerate(stamp) if not (middle < s <= middle + 0.30)]
        loss = replay(g, c, [wall[k] for k in keep], [stamp[k] for k in keep], "simulation", "M1",
                      clock_wall=wall, clock_stamp=stamp)
        dropped = len(stamp) - len(keep)
        gaps_over = sum(1 for a, b in zip(wall, wall[1:]) if b - a > 0.25)
        entry = {"run": Path(path).parent.name, "callbacks": len(rows), "wall_gaps_over_0p25_s": gaps_over,
                 "wall_base_stale_episodes": len(wall_base), "wall_base_first": wall_base[:3],
                 "simulation_M1_stale": len(m1), "simulation_M2_stale": len(m2), "simulation_M3_stale": len(m3),
                 "synthetic_loss_dropped_receipts": dropped, "synthetic_loss_detected": bool(loss),
                 "synthetic_loss_first_stale": loss[:1]}
        entry["passed"] = not m1 and not m2 and not m3 and bool(loss)
        ok = ok and entry["passed"]
        runs.append(entry)
    summary = {"runs": len(runs), "passed": ok,
               "runs_with_wall_base_stale": sum(r["wall_base_stale_episodes"] > 0 for r in runs),
               "wall_base_stale_episodes": sum(r["wall_base_stale_episodes"] for r in runs),
               "simulation_M1_stale_total": sum(r["simulation_M1_stale"] for r in runs),
               "simulation_M2_stale_total": sum(r["simulation_M2_stale"] for r in runs),
               "simulation_M3_stale_total": sum(r["simulation_M3_stale"] for r in runs),
               "synthetic_losses_detected": sum(r["synthetic_loss_detected"] for r in runs)}
    (H / "replay_gate.json").write_text(json.dumps({"summary": summary, "runs": runs}, indent=2) + "\n")
    print(json.dumps(summary))
    shutil.rmtree(root, ignore_errors=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
