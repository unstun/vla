"""After exhausted search only, test whether any popped node can reach exact goal."""
import json
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
P2B=HERE.parents[6]/".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
sys.path.insert(0,str(P2B/"reactive_stair"))
from materialize_scan_20 import once,sha


def main():
    base=P2B/"builds/scan28_live_frontier_trace"
    out=P2B/"builds/scan28_terminal_connector_probe"
    if out.exists():
        raise FileExistsError(out)
    expected=json.loads((base/"source_sha256.json").read_text())
    actual={"src/"+p.relative_to(base/"src").as_posix():sha(p)
            for p in (base/"src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual!=expected or not json.loads((base/"build_result.json").read_text())["passed"]:
        raise ValueError("frontier observer identity gate failed")
    shutil.copytree(base/"src",out/"src",ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
    astar=out/"src/path_searching/src/dyn_a_star.cpp"
    once(astar,"    return ASTAR_RET::SEARCH_ERR;\n}\n\nvector<Vector3d> AStar::getPath()",'''    if (audit.enabled && exact_endpoint) {
        // The original search has exhausted its queue. These new queries do
        // not change its return value, path, .2s search budget or old trace.
        stair_trace::active = nullptr;
        auto nodes = audit.nodes;
        const auto distance = [&](const std::array<double, 4>& n) {
            return (Eigen::Vector3d(n[0], n[1], n[2]) - end_pt).norm();
        };
        std::stable_sort(nodes.begin(), nodes.end(), [&](const std::array<double, 4>& a, const std::array<double, 4>& b) {
            return distance(a) < distance(b);
        });
        const auto probe_started = std::chrono::steady_clock::now();
        size_t tried = 0;
        bool found = false;
        for (const auto& n : nodes) {
            if (tried >= 4096) break;
            const Eigen::Vector3d from(n[0], n[1], n[2]);
            int blocked_sample = -1;
            const bool clear = grid_map_->collisionFreeSegment(from, end_pt, &blocked_sample);
            ++tried;
            if (tried <= 8 || clear) {
                RCLCPP_WARN(rclcpp::get_logger("path_searching"),
                    "TERMINAL_PROBE rank=%zu distance=%.12f clear=%d blocked_sample=%d from=(%.12f,%.12f,%.12f) yaw=%.12f",
                    tried, distance(n), clear, blocked_sample, n[0], n[1], n[2], grid_map_->collisionSegmentYaw(from, end_pt));
            }
            if (clear) {
                found = true;
                grid_map_->logInitialSplineCollision(from, grid_map_->collisionSegmentYaw(from, end_pt));
                break;
            }
        }
        RCLCPP_WARN(rclcpp::get_logger("path_searching"),
            "TERMINAL_PROBE completed tried=%zu popped=%zu found_clear=%d wall_ms=%.6f original_result=SEARCH_ERR",
            tried, nodes.size(), found, std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now()-probe_started).count());
    }
    return ASTAR_RET::SEARCH_ERR;
}

vector<Vector3d> AStar::getPath()''')
    (out/"terminal_probe_manifest.json").write_text(json.dumps({
        "base":base.name,"base_source_manifest_sha256":sha(base/"source_sha256.json"),
        "changed_sha256":{str(astar.relative_to(out)):sha(astar)},"generator_sha256":sha(Path(__file__)),
        "claim":"Only after original first strict search exhausts: test up to4096 popped nodes in increasing Euclidean distance to exact goal using original full segment predicate, stop at first clear. Original SEARCH_ERR and empty result preserved; observer query capture disabled for extra probes. Not a production acceptance or timing claim."},indent=2)+"\n")
    print(out)


if __name__=="__main__":
    main()
