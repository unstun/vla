"""Summarize the first traced native component; never infer missing verdicts."""
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path

VERDICTS = ("Free", "InvalidQuery", "OutOfMap", "MissingInput", "StaleInput", "Person",
            "UnknownObstacle", "StaticObstacle", "UnknownSupport", "UnsupportedTerrain", "WrongHeight")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    log = args.run / "replay_result/scan.log"
    target = args.run / "frontier_review.json"
    if target.exists():
        raise FileExistsError(target)
    rows = [line.strip().split(",") for line in log.open() if line.startswith("STF_")]
    summary = [r for r in rows if r[0] == "STF_SUMMARY"]
    assert len(summary) == 1
    _, reason, node_count, edge_count, query_count, dropped, elapsed = summary[0]
    original = next([float(v) for v in r[1:]] for r in rows if r[0] == "STF_INPUT")
    adjusted = next([float(v) for v in r[1:]] for r in rows if r[0] == "STF_ADJUSTED")
    start, goal = adjusted[:3], adjusted[3:]
    nodes = [[float(v) for v in r[1:]] for r in rows if r[0] == "STF_NODE"]
    edges = {int(r[1]): {"from": [float(v) for v in r[2:5]], "to": [float(v) for v in r[5:8]],
                         "clear": int(r[8]) == 1, "queries": []} for r in rows if r[0] == "STF_EDGE"}
    queries = [{"edge": int(r[1]), "verdict": VERDICTS[int(r[2])], "occupancy": int(r[3]),
                "point": [float(v) for v in r[4:7]]} for r in rows if r[0] == "STF_QUERY"]
    for query in queries:
        if query["edge"] > 0:
            edges[query["edge"]]["queries"].append(query)
    assert len(nodes) == int(node_count) and len(edges) == int(edge_count) and len(queries) == int(query_count)
    assert int(dropped) == 0 and reason != "time_limit"
    ordered = sorted(nodes, key=lambda n: math.dist(n[:3], goal))
    blocked = []
    for key, edge in edges.items():
        rejected = [q for q in edge["queries"] if q["verdict"] != "Free"]
        if edge["clear"]:
            assert not rejected
        else:
            blocked.append({"edge": key, "from": edge["from"], "to": edge["to"],
                            "first_rejection": rejected[0] if rejected else {"verdict": "unobserved_precondition"}})
    # Edges leaving the closest 10 cm shell are useful for locating the frontier,
    # but remain only the attempted graph edges, not proof of physical infeasibility.
    closest_distance = math.dist(ordered[0][:3], goal)
    frontier = [e for e in blocked if math.dist(e["from"], goal) < closest_distance + .10]
    result = {"reason": reason, "nodes": len(nodes), "edges": len(edges), "queries": len(queries),
              "query_records_dropped": int(dropped), "search_wall_s_with_instrumentation": float(elapsed),
              "emit_wall_s": next(float(r[1]) for r in rows if r[0] == "STF_EMIT_WALL_S"),
              "raw_start_goal": original, "adjusted_start_goal": adjusted,
              "node_bbox_min": [min(n[i] for n in nodes) for i in range(3)],
              "node_bbox_max": [max(n[i] for n in nodes) for i in range(3)],
              "start_distance_to_goal": math.dist(start, goal), "closest_distance_to_goal": closest_distance,
              "closest_nodes": ordered[:20], "query_verdict_counts": dict(collections.Counter(q["verdict"] for q in queries)),
              "blocked_edge_counts": dict(collections.Counter(e["first_rejection"]["verdict"] for e in blocked)),
              "frontier_blocked_counts": dict(collections.Counter(e["first_rejection"]["verdict"] for e in frontier)),
              "frontier_blocked_edges": frontier,
              "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
              "claim": "First native graph search only. Edge zero is initialization. Later ROS scheduling is affected by buffered trace emission; not a production timing comparison or physical-route impossibility proof."}
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("frontier_blocked_edges", "closest_nodes")}, indent=2))


if __name__ == "__main__":
    main()
