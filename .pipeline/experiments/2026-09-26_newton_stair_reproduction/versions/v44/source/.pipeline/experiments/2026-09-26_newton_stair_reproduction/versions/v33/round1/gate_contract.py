"""K3 of versions/v33/PLAN.md: the gate contract, v32's gate (red) against v33's (green).

Each gate is loaded as its own two-module package (contracts.py and control_gate.py only), from
parent_source/ for red and from runtime_sources/ for green. Cases:
C1 wall equivalence: 20,000 random sequences of 200 events under the default configuration give identical
   outputs and state in red and green after every event.
C2 host stall, C3 lost poses, C4 stopped simulator, C5 fail closed, C6 clock behind the pose, C7 configuration,
C8 check order: scripted timelines with the expected red and green results stated in each case.
Usage: python3 gate_contract.py [<label>]; writes gate_contract_<label>.json (default label "mac") next to this
script and exits non-zero on any failure. Runs under Python 3.10 (the pinned image) and 3.12.
"""
import ast
import importlib
import json
from pathlib import Path
import platform
import random
import shutil
import sys
import tempfile

H = Path(__file__).resolve().parent
E = H.parents[1]
SRC = "runtime_sources/backend_adapter/backend_adapter"


def load(tag, directory, root):
    package = Path(root) / tag
    package.mkdir()
    (package / "__init__.py").write_text("")
    for name in ("contracts.py", "control_gate.py"):
        shutil.copyfile(directory / name, package / name)
    if root not in sys.path:
        sys.path.insert(0, root)
    return importlib.import_module(tag + ".control_gate"), importlib.import_module(tag + ".contracts")


def identity(c, run="run", generation=1):
    return c.CommandIdentity(run_id=run, epoch=1, request_id="req", goal_id="goal", route_id="route",
                             command_id="cmd", generation=generation, map_epoch="map", map_revision=0)


def state(c, seq, t, speed=0.0, stamp=None, epoch="map", with_stamp_field=True):
    kwargs = dict(state_sequence=seq, monotonic_s=t, position_world_m=(0.0, 0.0, 0.0),
                  velocity_world_mps=(speed, 0.0, 0.0), map_epoch=epoch, map_revision=0)
    if with_stamp_field:
        kwargs["stamp_s"] = stamp
    return c.MeasuredState(**kwargs)


def observe(gate):
    return {"closed_reason": gate.closed_reason, "owner": gate.owner.to_dict() if gate.owner else None,
            "cancel_pending": gate.cancel_pending, "hold_ack": gate.hold_ack, "transport_ok": gate.transport_ok,
            "last_heartbeat_s": gate.last_heartbeat_s, "still_since_s": gate.still_since_s,
            "events": [(e["kind"], e["data"]) for e in gate.events]}


def run_sequence(g, c, rng_state, with_stamp_field):
    rng = random.Random(rng_state)
    gate = g.CommandGate(c.GateConfig())
    ids = [identity(c), identity(c, generation=2), identity(c, run="other")]
    t, seq, sim, trace = 100.0, 0, 50.0, []
    for _ in range(200):
        t += rng.choice([0.0, 0.005, 0.02, 0.05, 0.1, 0.19, 0.21, 0.24, 0.26, 0.4])
        sim += rng.choice([0.0, 0.005, 0.02])
        kind = rng.choice(["admit", "heartbeat", "pose", "pose", "tick", "tick", "raw", "loss", "cancel", "hold",
                           "invalidate", "release", "pose_old_seq", "pose_other_map"])
        who = rng.choice(ids)
        try:
            if kind == "admit":
                gate.admit(who)
                out = None
            elif kind == "heartbeat":
                gate.observe_heartbeat(now_s=t)
                out = None
            elif kind in ("pose", "pose_other_map"):
                seq += 1
                stamp = rng.choice([None, sim])
                gate.observe_measurement(state(c, seq, t, rng.choice([0.0, 0.03, 0.2]), stamp,
                                               "other" if kind == "pose_other_map" else "map", with_stamp_field))
                out = None
            elif kind == "pose_old_seq":
                gate.observe_measurement(state(c, max(seq, 1), t, 0.0, None, "map", with_stamp_field))
                out = None
            elif kind == "tick":
                out = gate.tick(now_s=t)
            elif kind == "raw":
                out = gate.gate_raw_command(who, (0.3, 0.0, 0.1), now_s=t)
            elif kind == "loss":
                gate.observe_transport_loss()
                out = None
            elif kind == "cancel":
                gate.request_cancel(who, "reason")
                out = None
            elif kind == "hold":
                gate.confirm_consumer_hold(who)
                out = None
            elif kind == "invalidate":
                gate.observe_map_invalidated()
                out = None
            else:
                out = gate.clear_owner_if_quiescent()
            result = None if out is None else (out if isinstance(out, bool) else
                                               (out.allowed, out.command_xyz_yaw, out.reason,
                                                out.identity.to_dict() if out.identity else None))
            error = None
        except Exception as exc:  # the same exceptions must occur in both
            result, error = None, type(exc).__name__ + ":" + str(exc)
        trace.append((kind, result, error, observe(gate)))
    return trace


def first_block(gate, timeline):
    """timeline: list of (wall t, action) where action is a callable(gate, t) or None; returns (t, reason) of the first
    evaluation that is not allowed, or None."""
    for t, action in timeline:
        if action is not None:
            action(gate, t)
        gate.observe_heartbeat(now_s=t)  # keep the heartbeat fresh so that only the pose rule decides
        out = gate.tick(now_s=t)
        if not out.allowed:
            return round(t, 3), out.reason
    return None


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "mac"
    root = tempfile.mkdtemp(prefix="v33_gate_")
    red_g, red_c = load("gate_v32", H / "parent_source" / SRC, root)
    green_g, green_c = load("gate_v33", E / SRC, root)
    cases = {}

    # C1 wall equivalence. The tally shows the sequences reach the pose rule: "odom_stale" is a trip on it, and
    # "ok" and "measured_map_mismatch" are evaluations that passed it.
    mismatch, reasons = None, {}
    for n in range(20000):
        red = run_sequence(red_g, red_c, n, with_stamp_field=False)
        green = run_sequence(green_g, green_c, n, with_stamp_field=True)
        if red != green:
            index = next(i for i, (a, b) in enumerate(zip(red, green)) if a != b)
            mismatch = {"sequence": n, "event": index, "red": repr(red[index])[:400], "green": repr(green[index])[:400]}
            break
        for kind, result, error, _ in green:
            if isinstance(result, tuple):
                reasons[result[2]] = reasons.get(result[2], 0) + 1
    cases["C1_wall_equivalence"] = {"sequences": 20000, "events_each": 200, "first_mismatch": mismatch,
                                    "gate_output_reasons": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
                                    "passed": mismatch is None and reasons.get("odom_stale", 0) > 1000
                                    and reasons.get("ok", 0) > 1000}

    def sim_gate(c, g, clock, **config):
        return g.CommandGate(c.GateConfig(odom_time_base="simulation", odom_wall_backstop_s=2.0, **config),
                             sim_clock=lambda: clock[0])

    def start(gate, c, stamp=50.0, t0=100.0):
        gate.admit(identity(c))
        gate.observe_heartbeat(now_s=t0)
        gate.observe_measurement(state(c, 1, t0, 0.0, stamp, "map", with_stamp_field=hasattr(c.MeasuredState, "__dataclass_fields__") and "stamp_s" in c.MeasuredState.__dataclass_fields__))
        return gate

    grid = [100.0 + 0.01 * k for k in range(1, 251)]  # 10 ms wall grid over 2.5 s

    # C2 host stall: wall runs 1.5 s, the clock and the poses are frozen.
    clock = [50.0]
    green = start(sim_gate(green_c, green_g, clock), green_c)
    red = start(red_g.CommandGate(red_c.GateConfig()), red_c)
    stall = [(t, None) for t in grid if t <= 101.5]
    cases["C2_host_stall"] = {"red": first_block(red, stall), "green": first_block(green, stall)}
    cases["C2_host_stall"]["passed"] = (cases["C2_host_stall"]["red"] == (100.26, "odom_stale")
                                        and cases["C2_host_stall"]["green"] is None)

    # C3 lost poses: /clock runs on (1 ms of simulation per 1 ms of wall) while no pose arrives.
    clock = [50.0]
    green = start(sim_gate(green_c, green_g, clock), green_c)
    advance = [(t, (lambda g, t: clock.__setitem__(0, 50.0 + (t - 100.0)))) for t in grid]
    cases["C3_lost_poses"] = {"green": first_block(green, advance)}
    cases["C3_lost_poses"]["passed"] = cases["C3_lost_poses"]["green"] == (100.26, "odom_stale")
    # Exact boundary on the simulation age with the wall frozen: 0.24 s fresh, 0.26 s stale.
    probe = {}
    for age in (0.24, 0.26):
        clock = [50.0 + age]
        g = start(sim_gate(green_c, green_g, clock), green_c)
        probe[str(age)] = g.tick(now_s=100.001).reason
    cases["C3_lost_poses"]["age_probe"] = probe
    cases["C3_lost_poses"]["passed"] &= probe == {"0.24": "ok", "0.26": "odom_stale"}

    # C4 stopped simulator: nothing arrives; the backstop decides.
    probe = {}
    for wall in (1.99, 2.01):
        clock = [50.0]
        g = start(sim_gate(green_c, green_g, clock), green_c)
        g.observe_heartbeat(now_s=100.0 + wall)
        probe[str(wall)] = g.tick(now_s=100.0 + wall).reason
    cases["C4_stopped_simulator"] = {"green": probe, "passed": probe == {"1.99": "ok", "2.01": "odom_stale"}}

    # C5 fail closed.
    reasons = {}
    g = green_g.CommandGate(green_c.GateConfig(odom_time_base="simulation"))  # no sim_clock
    start(g, green_c)
    reasons["no_sim_clock"] = g.tick(now_s=100.01).reason
    g = green_g.CommandGate(green_c.GateConfig(odom_time_base="simulation"), sim_clock=lambda: None)
    start(g, green_c)
    reasons["clock_not_reported"] = g.tick(now_s=100.01).reason
    g = green_g.CommandGate(green_c.GateConfig(odom_time_base="simulation"), sim_clock=lambda: 50.0)
    g.admit(identity(green_c))
    g.observe_heartbeat(now_s=100.0)
    g.observe_measurement(state(green_c, 1, 100.0, 0.0, None))
    reasons["pose_without_stamp"] = g.tick(now_s=100.01).reason
    reasons["no_measurement"] = g.measurement_stale(None, 100.0)
    cases["C5_fail_closed"] = {"green": reasons, "passed": reasons == {
        "no_sim_clock": "odom_stale", "clock_not_reported": "odom_stale", "pose_without_stamp": "odom_stale",
        "no_measurement": True}}

    # C6 clock 5 ms behind the pose stamp.
    clock = [49.995]
    g = start(sim_gate(green_c, green_g, clock), green_c)
    cases["C6_clock_behind_pose"] = {"green": g.tick(now_s=100.01).reason}
    cases["C6_clock_behind_pose"]["passed"] = cases["C6_clock_behind_pose"]["green"] == "ok"

    # C7 configuration.
    results = {}
    default = green_c.GateConfig()
    results["default"] = [default.odom_time_base, default.odom_wall_backstop_s]
    for name, kwargs in (("unknown_base", {"odom_time_base": "gps"}), ("backstop_below_stale", {"odom_wall_backstop_s": 0.2}),
                         ("negative_backstop", {"odom_wall_backstop_s": -1.0}), ("backstop_equal_stale", {"odom_wall_backstop_s": 0.25})):
        try:
            green_c.GateConfig(**kwargs)
            results[name] = "accepted"
        except green_c.ContractError as exc:
            results[name] = "rejected:" + str(exc)
    try:
        state(green_c, 1, 100.0, 0.0, float("nan"))
        results["nan_stamp"] = "accepted"
    except green_c.ContractError as exc:
        results["nan_stamp"] = "rejected:" + str(exc)
    # native_graph.py's gate section: the archived config with the update native_graph.py applies.
    graph = (E / "scripts/native_graph.py").read_text()
    update = next(node for node in ast.walk(ast.parse(graph))
                  if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "update"
                  and isinstance(node.func.value, ast.Subscript) and getattr(node.func.value.slice, "value", None) == "gate")
    gate_section = json.loads((E / "config_archived/p2b_backend_ros.two_goal.json").read_text())["gate"]
    gate_section.update({k.arg: ast.literal_eval(k.value) for k in update.keywords})
    gate_section.pop("initial_heartbeat_grace_s", None)  # as node.build_runtime does
    generated = green_c.GateConfig(**gate_section)
    results["native_graph_gate"] = [generated.odom_time_base, generated.odom_wall_backstop_s, generated.odom_stale_s,
                                    generated.heartbeat_stale_s]
    cases["C7_configuration"] = {"green": results, "passed": (
        results["default"] == ["wall", 2.0] and results["unknown_base"] == "rejected:invalid_odom_time_base"
        and results["backstop_below_stale"] == "rejected:invalid_odom_wall_backstop_s"
        and results["negative_backstop"] == "rejected:invalid_odom_wall_backstop_s"
        and results["backstop_equal_stale"] == "accepted" and results["nan_stamp"] == "rejected:invalid_stamp_s"
        and results["native_graph_gate"] == ["simulation", 2.0, 0.25, 0.2])}

    # C8 check order: heartbeat and pose both stale -> heartbeat_stale first, in both bases.
    order = {}
    for base in ("wall", "simulation"):
        clock = [60.0]
        g = green_g.CommandGate(green_c.GateConfig(odom_time_base=base), sim_clock=lambda: clock[0])
        start(g, green_c)
        order[base] = g.tick(now_s=103.0).reason
    red_gate = start(red_g.CommandGate(red_c.GateConfig()), red_c)
    order["red"] = red_gate.tick(now_s=103.0).reason
    cases["C8_check_order"] = {"results": order, "passed": order == {"wall": "heartbeat_stale", "simulation": "heartbeat_stale",
                                                                      "red": "heartbeat_stale"}}

    report = {"label": label, "python": platform.python_version(), "cases": cases,
              "all_passed": all(v["passed"] for v in cases.values())}
    (H / f"gate_contract_{label}.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v["passed"] for k, v in cases.items()}), "python", platform.python_version())
    shutil.rmtree(root, ignore_errors=True)
    sys.exit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
