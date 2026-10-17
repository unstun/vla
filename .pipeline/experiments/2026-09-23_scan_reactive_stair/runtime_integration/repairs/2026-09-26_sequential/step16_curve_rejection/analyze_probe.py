"""Extract native diagnostic curves and verify logged paired positions."""
import hashlib
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
LOG = HERE / "scan29_curve_probe_v1/replay_result/scan.log"


def evaluate(controls, knots, t):
    k = 3
    while knots[k + 1] < t:
        k += 1
    values = [list(p) for p in controls[k - 3:k + 1]]
    for r in range(1, 4):
        for i in range(3, r - 1, -1):
            a = (t - knots[i + k - 3]) / (knots[i + 1 + k - r] - knots[i + k - 3])
            values[i] = [(1 - a) * x + a * y for x, y in zip(values[i - 1], values[i])]
    return values[3]


def main():
    text = LOG.read_text()
    # C++ buffered stdout and ROS stderr share one file. Removing complete ROS
    # records rejoins a numeric CSV record interrupted by a logger write; no
    # numeric values are reconstructed or inferred. Raw evidence is unchanged.
    clean = re.sub(r"\[(?:WARN|INFO|ERROR)\] \[\d+\.\d+\] \[[^\]]+\]: [^\n]*\n", "", text)
    tables = {"seed": {}, "samples": {}, "timed_initial": {}, "final": {}}
    knots = {"timed_initial": {}, "final": {}}
    for line in clean.splitlines():
        fields = line.split(",")
        if fields[0] in {"REJECT_SEED", "REJECT_SAMPLE"}:
            table = tables["seed" if fields[0] == "REJECT_SEED" else "samples"]
            assert len(fields) == 5 and int(fields[1]) not in table
            table[int(fields[1])] = list(map(float, fields[2:]))
        elif fields[0] == "REJECT_CONTROL":
            assert len(fields) == 6 and int(fields[2]) not in tables[fields[1]]
            tables[fields[1]][int(fields[2])] = list(map(float, fields[3:]))
        elif fields[0] == "REJECT_KNOT":
            assert len(fields) == 4 and int(fields[2]) not in knots[fields[1]]
            knots[fields[1]][int(fields[2])] = float(fields[3])
    def ordered(table, count):
        assert set(table) == set(range(count))
        return [table[i] for i in range(count)]
    data = {"seed": ordered(tables["seed"], 69), "samples": ordered(tables["samples"], 426)}
    result = {}
    for label in ("timed_initial", "final"):
        controls = ordered(tables[label], 428)
        times = ordered(knots[label], 432)
        data[label] = {"controls": controls, "knots": times}
        check = re.search(r"REJECT_PROBE curve=" + label + r" status=(\d+) first_t=([\d.]+) duration=([\d.]+) samples=(\d+)", text)
        pair = re.search(r"REJECT_PROBE paired=" + label + r" parent_edge=(\d+) distance=([\d.]+) p=\(([^)]+)\) projected=\(([^)]+)\) curve_yaw=([-\d.]+) parent_yaw=([-\d.]+) same_position_parent_occupied=(\d+) projected_curve_occupied=(\d+) projected_parent_occupied=(\d+)", text)
        assert check and pair and int(check[1]) == 1
        p = list(map(float, pair[3].split(",")))
        calculated = evaluate(controls, times, float(check[2]))
        residual = math.sqrt(sum((a - b) ** 2 for a, b in zip(p, calculated)))
        assert residual < 1e-10
        result[label] = {
            "collision_time_s": float(check[2]), "duration_s": float(check[3]), "checked_samples": int(check[4]),
            "position": p, "projected": list(map(float, pair[4].split(","))),
            "parent_edge": int(pair[1]), "distance_to_seed_m": float(pair[2]),
            "curve_yaw_rad": float(pair[5]), "parent_yaw_rad": float(pair[6]),
            "heading_difference_degrees": abs(float(pair[5]) - float(pair[6])) * 180 / math.pi,
            "same_position_parent_occupied": bool(int(pair[7])),
            "projected_curve_occupied": bool(int(pair[8])), "projected_parent_occupied": bool(int(pair[9])),
            "native_vs_independent_position_residual_m": residual,
        }
    stamps = re.findall(r"initial_spline_collision [^\n]*body_stamp=([\d.]+) now=([\d.]+)", text)
    assert len(stamps) == 4 and all(a == b == "5.56999988" for a, b in stamps)
    result.update({
        "log_sha256": hashlib.sha256(LOG.read_bytes()).hexdigest(),
        "same_body_clock_stamp_s": 5.56999988,
        "timed_initial_first_blocked_verdict": "WrongHeight at front footprint",
        "final_first_blocked_verdict": "UnknownSupport at rear footprint",
        "claim": "Both timed initialization and final curve already fail original full sampled collision checks. Paired same-time queries isolate heading at the initial failure; at the final failure either the seed heading or the projected position clears this particular point. This does not establish either substitution clears the full curve, nor authorize replacing execution heading or relaxing Unknown.",
    })
    (HERE / "GEOMETRY.json").write_text(json.dumps(data, indent=2) + "\n")
    result["geometry_sha256"] = hashlib.sha256((HERE / "GEOMETRY.json").read_bytes()).hexdigest()
    (HERE / "RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
