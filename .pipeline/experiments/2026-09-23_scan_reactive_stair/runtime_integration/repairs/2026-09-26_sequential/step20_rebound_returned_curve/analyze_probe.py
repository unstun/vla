"""Compare failed callback controls with the returned trial and inspect planes."""
import hashlib
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
LOG = HERE / "scan31_returned_curve_probe_v1/replay_result/scan.log"
NUMBER = r"[-+\d.eE]+"
sub = lambda a, b: [x - y for x, y in zip(a, b)]
dot = lambda a, b: sum(x * y for x, y in zip(a, b))
norm = lambda p: math.sqrt(dot(p, p))


def ordered(table, count=None):
    if count is None:
        count = len(table)
    assert set(table) == set(range(count))
    return [table[i] for i in range(count)]


def intersections(controls, segments, paths):
    output = []
    for segment_index, (begin, end) in enumerate(segments):
        path = paths[segment_index] if segment_index < len(paths) else []
        record = {"segment": segment_index, "begin": begin, "end": end,
                  "internal_control_count": max(0, end - begin - 1), "path_nodes": len(path), "controls": []}
        for j in range(begin + 1, end):
            normal = sub(controls[j + 1], controls[j - 1])
            values = [dot(sub(p, controls[j]), normal) for p in path]
            current = len(path) // 2
            found = None
            reason = "no_path" if not path else "no_sign_crossing_in_native_walk"
            visited = []
            if path:
                value = last_value = values[current]
                for _ in range(2 * len(path) + 2):
                    previous = current
                    current += -1 if value >= 0 else 1
                    if not 0 <= current < len(path):
                        break
                    value = values[current]
                    visited.append([previous, current])
                    if value * last_value <= 0 and (abs(value) > 0 or abs(last_value) > 0):
                        delta = sub(path[current], path[previous])
                        denominator = dot(normal, delta)
                        if abs(denominator) < 1e-8:
                            reason = "denominator_below_1e_8"
                            break
                        u = dot(normal, sub(controls[j], path[current])) / denominator
                        p = [a + u * d for a, d in zip(path[current], delta)]
                        found = {"point": p, "distance": norm(sub(p, controls[j])), "denominator": denominator}
                        reason = "nonzero_intersection" if found["distance"] > 1e-5 else "direction_length_at_most_1e_5"
                        break
            # Independently enumerate all segments to detect a crossing that
            # the native midpoint/direction walk never visited. No map query.
            candidates = []
            for k in range(1, len(path)):
                if values[k - 1] * values[k] > 0 or (values[k - 1] == values[k] == 0):
                    continue
                delta = sub(path[k], path[k - 1])
                denominator = dot(normal, delta)
                if abs(denominator) < 1e-8:
                    continue
                u = -values[k - 1] / denominator
                if not 0 <= u <= 1:
                    continue
                p = [a + u * d for a, d in zip(path[k - 1], delta)]
                candidates.append({"path_edge": k - 1, "point": p, "distance": norm(sub(p, controls[j]))})
            record["controls"].append({"index": j, "normal": normal, "dot_values": values,
                "native_visited": visited, "native_reason": reason, "native_intersection": found,
                "all_edge_intersections": candidates})
        output.append(record)
    return output


def main():
    text = LOG.read_text()
    clean = re.sub(r"\[(?:WARN|INFO|ERROR)\] \[\d+\.\d+\] \[[^\]]+\]: [^\n]*\n", "", text)
    raw = {"seed": {}, "samples": {}, "timed_initial": {}, "final": {}}
    knots = {"timed_initial": {}, "final": {}}
    for line in clean.splitlines():
        f = line.split(",")
        if f[0] in {"REJECT_SEED", "REJECT_SAMPLE"}:
            table = raw["seed" if f[0] == "REJECT_SEED" else "samples"]
            assert len(f) == 5 and int(f[1]) not in table
            table[int(f[1])] = list(map(float, f[2:]))
        elif f[0] == "REJECT_CONTROL":
            assert len(f) == 6 and int(f[2]) not in raw[f[1]]
            raw[f[1]][int(f[2])] = list(map(float, f[3:]))
        elif f[0] == "REJECT_KNOT":
            assert len(f) == 4 and int(f[2]) not in knots[f[1]]
            knots[f[1]][int(f[2])] = float(f[3])
    seed_log = re.search(r"reactive_stair_seed_checked nodes=(\d+) samples=(\d+)", text)
    assert seed_log
    nodes, count = map(int, seed_log.groups())
    geometry = {"seed": ordered(raw["seed"], nodes), "samples": ordered(raw["samples"], count)}
    checks = {}
    for label in ("timed_initial", "final"):
        geometry[label] = {"controls": ordered(raw[label], count + 2), "knots": ordered(knots[label], count + 6)}
        m = re.search(r"REJECT_PROBE curve=" + label + r" status=(\d+) first_t=([\d.]+) duration=([\d.]+) samples=(\d+)", text)
        d = re.search(r"REJECT_PROBE dynamics=" + label + r" feasible=(\d+) native_ratio=([\d.]+) velocity_component_bound=([\d.]+) acceleration_component_bound=([\d.]+) start_position_error=([\d.]+) start_velocity_error=([\d.]+) start_acceleration_error=([\d.]+)", text)
        assert m and d
        checks[label] = {"status": int(m[1]), "first_time_s": float(m[2]), "duration_s": float(m[3]),
            "samples": int(m[4]), "native_dynamic_feasible": bool(int(d[1])),
            "velocity_component_bound": float(d[3]), "acceleration_component_bound": float(d[4]),
            "start_pva_errors": list(map(float, d.groups()[4:]))}
    stop = {}
    for m in re.finditer(r"ZERO_CONTROL,(\d+),(" + NUMBER + r"),(" + NUMBER + r"),(" + NUMBER + r"),(\d+),(\d+),(\d+)", text):
        assert int(m[1]) not in stop
        stop[int(m[1])] = {"position": list(map(float, m.groups()[1:4])), "flag": int(m[5]),
                          "base_count": int(m[6]), "direction_count": int(m[7])}
    stop = ordered(stop, count + 2)
    delta = max(abs(a - b) for s, p in zip(stop, geometry["final"]["controls"]) for a, b in zip(s["position"], p))
    assert delta == 0
    segments = {int(m[1]): [int(m[2]), int(m[3])] for m in re.finditer(r"ZERO_SEGMENT,(\d+),(\d+),(\d+)", text)}
    segments = ordered(segments)
    paths = {}
    for m in re.finditer(r"ZERO_PATH,(\d+),(\d+),(" + NUMBER + r"),(" + NUMBER + r"),(" + NUMBER + r")", text):
        path = paths.setdefault(int(m[1]), {})
        assert int(m[2]) not in path
        path[int(m[2])] = list(map(float, m.groups()[2:]))
    paths = [ordered(p) for p in ordered(paths)]
    assert len(paths) == len(segments) and all(len(p) >= 2 for p in paths)
    for (begin, end), path in zip(segments, paths):
        assert norm(sub(path[0], geometry["final"]["controls"][begin])) < 1e-10
        assert norm(sub(path[-1], geometry["final"]["controls"][end])) < 1e-10
    assert text.index("ZERO_CONTROL,0,") < text.index("rebound_no_valid_new_constraints") < text.index("REJECT_PROBE curve=")
    stamps = re.findall(r"initial_spline_collision [^\n]*body_stamp=([\d.]+) now=([\d.]+)", text)
    assert stamps and all(a == b == "5.56999988" for a, b in stamps)
    geometry["stop_state"] = {"controls": stop, "segments": segments, "paths": paths}
    (HERE / "GEOMETRY.json").write_text(json.dumps(geometry, indent=2) + "\n")
    result = {"checks": checks, "stop_vs_returned_max_component_difference": delta,
        "intersection_reconstruction": intersections(geometry["final"]["controls"], segments, paths),
        "log_sha256": hashlib.sha256(LOG.read_bytes()).hexdigest(),
        "geometry_sha256": hashlib.sha256((HERE / "GEOMETRY.json").read_bytes()).hexdigest(),
        "claim": "Returned controls exactly match captured zero-pair stop state, not necessarily solver-accepted q. Complete native curve checks and pure geometry reconstruction are diagnostic. No original failure or publication change; per-path total counts are not explicit in this observer, so reported arrays are the observed contiguous records."}
    (HERE / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
