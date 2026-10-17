"""Observe first strict-endpoint search; preserve every occupancy call and decision."""
import json
from pathlib import Path
import shutil
import sys

HERE=Path(__file__).resolve().parent
P2B=HERE.parents[6]/".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
sys.path.insert(0,str(P2B/"reactive_stair"))
from materialize_scan_20 import once,sha


def main():
    base=P2B/"builds/scan_28"
    out=P2B/"builds/scan28_live_frontier_trace"
    if out.exists():
        raise FileExistsError(out)
    expected=json.loads((base/"source_sha256.json").read_text())
    actual={"src/"+p.relative_to(base/"src").as_posix():sha(p)
            for p in (base/"src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual!=expected or not json.loads((base/"build_result.json").read_text())["passed"]:
        raise ValueError("scan28 identity gate failed")
    shutil.copytree(base/"src",out/"src",ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
    helper=out/"src/plan_env/include/plan_env/search_frontier_trace.h"
    shutil.copy2(HERE.parent/"step4_frontier/search_frontier_trace.h",helper)
    astar=out/"src/path_searching/src/dyn_a_star.cpp"
    methods=out/"src/plan_env/include/plan_env/scan_reactive_grid_methods.inc"
    for p in (astar,methods):
        p.write_bytes(b'#include <plan_env/search_frontier_trace.h>\n'+p.read_bytes())
    once(astar,"    ++rounds_;",'''    ++rounds_;
    stair_trace::Scope audit(rounds_ == 1);
    audit.endpoints = {start_pt.x(), start_pt.y(), start_pt.z(), end_pt.x(), end_pt.y(), end_pt.z()};''')
    once(astar,'                     "Unable to handle the initial or end point, force return!");',
         '                     "Unable to handle the initial or end point, force return!");\n        audit.reason = "initialization_error";')
    once(astar,"    GridNodePtr startPtr = GridNodeMap_[start_idx(0)][start_idx(1)][start_idx(2)];",'''    const auto trace_start = Index2Coord(start_idx), trace_end = Index2Coord(end_idx);
    audit.adjusted = {trace_start.x(), trace_start.y(), trace_start.z(), trace_end.x(), trace_end.y(), trace_end.z()};
    GridNodePtr startPtr = GridNodeMap_[start_idx(0)][start_idx(1)][start_idx(2)];''')
    once(astar,"        current = entry.node;",'''        current = entry.node;
        if (audit.enabled) {
          const auto p = Index2Coord(current->index);
          audit.nodes.push_back({p.x(), p.y(), p.z(), current->gScore});
        }''')
    before="""                if (!grid_map_->collisionFreeSegment(Index2Coord(current->index),
                                                     Index2Coord(neighborPtr->index)))"""
    after="""                if (audit.enabled) {
                  const auto a = Index2Coord(current->index), b = Index2Coord(neighborPtr->index);
                  audit.nextEdge(a.x(), a.y(), a.z(), b.x(), b.y(), b.z());
                }
                const bool trace_edge_clear = grid_map_->collisionFreeSegment(Index2Coord(current->index),
                                                     Index2Coord(neighborPtr->index));
                audit.endEdge(trace_edge_clear);
                if (!trace_edge_clear)"""
    once(astar,before,after)
    once(astar,"            const bool terminal_clear = grid_map_->collisionFreeSegment(Index2Coord(current->index), end_pt);",'''            if (audit.enabled) {
              const auto a = Index2Coord(current->index);
              audit.nextEdge(a.x(), a.y(), a.z(), end_pt.x(), end_pt.y(), end_pt.z());
            }
            const bool terminal_clear = grid_map_->collisionFreeSegment(Index2Coord(current->index), end_pt);
            audit.endEdge(terminal_clear);''')
    text=astar.read_text()
    assert text.count("return ASTAR_RET::SUCCESS;")==2
    text=text.replace("return ASTAR_RET::SUCCESS;",'audit.reason = "success"; return ASTAR_RET::SUCCESS;')
    for line in text.splitlines():
        if '"Failed in A-star path search: 0.2 second time limit exceeded' in line:
            text=text.replace(line,line+'\n            audit.reason = "time_limit";')
    astar.write_text(text)
    once(methods,"  const auto verdict = reactive_decision_.decide(query, obstacle);",'''  const auto verdict = reactive_decision_.decide(query, obstacle);
  stair_trace::query(point.x(), point.y(), point.z(), static_cast<int>(verdict), static_cast<int>(obstacle.occupancy));''')
    (out/"frontier_trace_manifest.json").write_text(json.dumps({
        "base":"scan_28","base_source_manifest_sha256":sha(base/"source_sha256.json"),
        "changed_sha256":{str(p.relative_to(out)):sha(p) for p in (helper,astar,methods)},
        "generator_sha256":sha(Path(__file__)),
        "claim":"First native search only; original query/verdict and edge outcome observation, including strict terminal edge. No additional map query, collision or acceptance change. Deferred output after original search affects later scheduling; only first search geometry is interpreted. Existing .2s wall cap retained; diagnostic overhead is not a timing comparison."},indent=2)+"\n")
    print(out)


if __name__=="__main__":
    main()
