"""Create an isolated logging-only native A* audit; preserve search decisions."""
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
BASE = P2B / "builds/scan_19"
OUT = P2B / "builds/scan19_audit_trace"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if expected != actual:
        raise ValueError("scan_19 source identity changed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    path = OUT / "src/path_searching/src/dyn_a_star.cpp"
    text = path.read_text()

    def once(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError("trace anchor changed: " + old[:80])
        text = text.replace(old, new, 1)

    text = '#include <map>\n#include <set>\n#include <sstream>\n#include <functional>\n' + text
    once('    ++rounds_;', '''    ++rounds_;
    // [DEBUG-stair-cause] A logging-only first-search observer. No extra
    // occupancy calls, queue operations, state changes or relaxed rules.
    const bool audit_active = rounds_ == 1;
    int audit_popped = 0, audit_pushed = 0, audit_checks = 0;
    int audit_blocked = 0, audit_free = 0, audit_skipped_closed = 0;
    int audit_blocked_then_free = 0, audit_unpushed_free = 0;
    int audit_updated_without_push = 0;
    const char *audit_reason = "exhausted";
    std::map<GridNodePtr, double> audit_first_rejected_yaw;
    std::set<GridNodePtr> audit_pushed_nodes;
    std::ostringstream audit_samples;
    int audit_sample_count = 0;
    struct AuditReturn { std::function<void()> report; ~AuditReturn() { report(); } };
    AuditReturn audit_return{[&]() {
      if (!audit_active) return;
      const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - time_1).count();
      std::cerr << "[DEBUG-stair-cause] summary reason=" << audit_reason
        << " popped=" << audit_popped << " pushed=" << audit_pushed
        << " occupancy_checks=" << audit_checks << " blocked=" << audit_blocked
        << " free=" << audit_free << " unique_rejected=" << audit_first_rejected_yaw.size()
        << " blocked_then_free=" << audit_blocked_then_free
        << " free_but_never_pushed=" << audit_unpushed_free
        << " updated_without_push=" << audit_updated_without_push
        << " closed_skips=" << audit_skipped_closed << " queue_left=" << openSet_.size()
        << " seconds=" << seconds << std::endl << audit_samples.str();
    }};
    if (audit_active) std::cerr << "[DEBUG-stair-cause] input start=" << start_pt.transpose()
      << " end=" << end_pt.transpose() << " step=" << step_size << " inf=" << inf << std::endl;''')
    once('        return ASTAR_RET::INIT_ERR;', '        audit_reason = "initialization_error";\n        return ASTAR_RET::INIT_ERR;')
    once('    GridNodePtr startPtr = GridNodeMap_[start_idx(0)][start_idx(1)][start_idx(2)];', '''    if (audit_active) std::cerr << "[DEBUG-stair-cause] adjusted start=" << Index2Coord(start_idx).transpose()
      << " end=" << Index2Coord(end_idx).transpose() << " start_idx=" << start_idx.transpose()
      << " end_idx=" << end_idx.transpose() << std::endl;
    GridNodePtr startPtr = GridNodeMap_[start_idx(0)][start_idx(1)][start_idx(2)];''')
    once('    openSet_.push(startPtr); //put start in open set', '''    openSet_.push(startPtr); //put start in open set
    if (audit_active) { ++audit_pushed; audit_pushed_nodes.insert(startPtr); }''')
    once('        openSet_.pop();', '        openSet_.pop();\n        if (audit_active) ++audit_popped;')
    once('            return ASTAR_RET::SUCCESS;', '            audit_reason = "success";\n            return ASTAR_RET::SUCCESS;')
    once('                    continue; //in closed set.', '''                    if (audit_active) ++audit_skipped_closed;
                    continue; //in closed set.''')
    once('''                if (checkOccupancy(Index2Coord(neighborPtr->index), neighbor_yaw))
                {
                    continue;
                }''', '''                const int audit_occupancy = checkOccupancy(Index2Coord(neighborPtr->index), neighbor_yaw);
                if (audit_active) ++audit_checks;
                if (audit_occupancy)
                {
                    if (audit_active) { ++audit_blocked; audit_first_rejected_yaw.emplace(neighborPtr, neighbor_yaw); }
                    continue;
                }
                if (audit_active) ++audit_free;''')
    once('                tentative_gScore = current->gScore + static_cost;', '''                tentative_gScore = current->gScore + static_cost;
                if (audit_active && audit_first_rejected_yaw.count(neighborPtr)) {
                  ++audit_blocked_then_free;
                  const bool was_pushed = audit_pushed_nodes.count(neighborPtr) != 0;
                  if (!was_pushed) ++audit_unpushed_free;
                  if (audit_sample_count++ < 20) audit_samples << "[DEBUG-stair-cause] blocked_then_free xyz="
                    << Index2Coord(neighborIdx).transpose() << " rejected_yaw=" << audit_first_rejected_yaw.at(neighborPtr)
                    << " free_yaw=" << neighbor_yaw << " state=" << neighborPtr->state
                    << " prior_g=" << neighborPtr->gScore << " candidate_g=" << tentative_gScore
                    << " explored=" << flag_explored << " ever_pushed=" << was_pushed << "\\n";
                }''')
    once('                    openSet_.push(neighborPtr); //put neighbor in open set and record it.', '''                    openSet_.push(neighborPtr); //put neighbor in open set and record it.
                    if (audit_active) { ++audit_pushed; audit_pushed_nodes.insert(neighborPtr); }''')
    once('                { //in open set and need update', '''                { //in open set and need update
                    if (audit_active && !audit_pushed_nodes.count(neighborPtr)) ++audit_updated_without_push;''')
    once('''                        "Failed in A-star path search: 0.2 second time limit exceeded");
            return ASTAR_RET::SEARCH_ERR;''', '''                        "Failed in A-star path search: 0.2 second time limit exceeded");
            audit_reason = "time_limit";
            return ASTAR_RET::SEARCH_ERR;''')
    path.write_text(text)
    manifest = {"base": "scan_19", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
                "changed_file": str(path.relative_to(OUT)), "changed_sha256": sha(path),
                "claim": "Logging-only first native search; no additional occupancy query, altered threshold, search bookkeeping fix or queue operation. Instrumentation has wall-time overhead; this remains a diagnostic candidate.",
                "debug_prefix": "[DEBUG-stair-cause]", "generator_sha256": sha(Path(__file__))}
    (OUT / "audit_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
