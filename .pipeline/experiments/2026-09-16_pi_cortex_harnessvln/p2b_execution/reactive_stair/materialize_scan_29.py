"""Recover an exhausted strict search using fully checked longer terminal edges."""
import json
from pathlib import Path
import shutil

from materialize_scan_20 import once, sha

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_28"
OUT = HERE.parent / "builds/scan_29"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((BASE / "build_result.json").read_text())["passed"]:
        raise ValueError("scan_28 source/build identity gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    header = OUT / "src/path_searching/include/path_searching/dyn_a_star.h"
    source = OUT / "src/path_searching/src/dyn_a_star.cpp"
    once(header, "    // from a popped lattice node within two cells (3D Euclidean distance).", """    // from a popped lattice node within two cells (3D Euclidean distance).
    // After queue exhaustion only, longer checked edges can recover a result
    // within the same total budget, ordered by complete reached-path cost.""")
    once(source, "    int num_iter = 0;", """    struct TerminalCandidate {
        GridNodePtr node;
        double cost_m;
    };
    // Per-call state: only current, reached nodes are eligible for recovery.
    std::vector<TerminalCandidate> terminal_candidates;
    int num_iter = 0;""")
    once(source, "        current = entry.node;", """        current = entry.node;
        if (exact_endpoint) {
            const double terminal_distance = (Index2Coord(current->index) - end_pt).norm();
            const double cost = current->gScore * step_size_ + terminal_distance;
            if (terminal_distance > 2.0 * step_size_ && std::isfinite(cost))
                terminal_candidates.push_back({current, cost});
        }""")
    once(source, "    const auto time_2 = std::chrono::steady_clock::now();\n\n    const double elapsed", """    if (exact_endpoint && !terminal_candidates.empty()) {
        // Normal search exhausted. Near connectors were already checked.
        // Use its remaining budget, not a new deadline for this second stage.
        const auto expired = [&]() {
            if (std::chrono::duration<double>(std::chrono::steady_clock::now() - time_1).count() <= 0.2)
                return false;
            gridPath_.clear();
            has_exact_goal_ = false;
            RCLCPP_WARN(rclcpp::get_logger("path_searching"),
                        "Failed in A-star path search: 0.2 second time limit exceeded during terminal recovery");
            return true;
        };
        if (expired()) return ASTAR_RET::SEARCH_ERR;
        std::stable_sort(terminal_candidates.begin(), terminal_candidates.end(),
                        [](const TerminalCandidate& a, const TerminalCandidate& b) {
                            return a.cost_m < b.cost_m;
                        });
        if (expired()) return ASTAR_RET::SEARCH_ERR;
        size_t tried = 0;
        for (const auto& candidate : terminal_candidates) {
            if (expired()) return ASTAR_RET::SEARCH_ERR;
            const Eigen::Vector3d from = Index2Coord(candidate.node->index);
            const bool clear = grid_map_->collisionFreeSegment(from, end_pt);
            ++tried;
            if (expired()) return ASTAR_RET::SEARCH_ERR;
            if (!clear) continue;
            auto recovered_path = retrievePath(candidate.node);
            if (expired()) return ASTAR_RET::SEARCH_ERR;
            gridPath_ = std::move(recovered_path);
            exact_goal_ = end_pt;
            has_exact_goal_ = true;
            RCLCPP_INFO(rclcpp::get_logger("path_searching"),
                        "A-star exact endpoint recovered connector_m=%.12f cost_m=%.12f tried=%zu candidates=%zu",
                        (from - end_pt).norm(), candidate.cost_m, tried, terminal_candidates.size());
            return ASTAR_RET::SUCCESS;
        }
    }
    const auto time_2 = std::chrono::steady_clock::now();

    const double elapsed""")
    (OUT / "terminal_recovery_manifest.json").write_text(json.dumps({
        "base": "scan_28", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
        "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in (header, source)},
        "generator_sha256": sha(Path(__file__)),
        "change": "Only after strict search queue exhaustion: check longer terminal edges from popped reachable nodes, stable ordered by reached gScore*step + terminal length. Full original segment predicate and exact goal preserved.",
        "preserved": "Default optimizer AStar, normal near-connector acceptance order, total .2s budget, occupancy/support/person/Unknown predicates, manager seed recheck, cubic initialization/optimizer and final sampled trajectory gates.",
        "boundary": "Reject success after budget expiry; individual sort/collision calls are not preemptible. Cost ordering is among existing reached parent chains, not a global optimality guarantee. Expanded sampled fixed-heading graph does not validate continuous body rotation, fitted curve or live tracking."
    }, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
