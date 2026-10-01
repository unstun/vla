"""Repair native A* discovery and immutable open-queue records in a fresh copy."""
import hashlib
import json
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_19"
OUT = HERE.parent / "builds/scan_20"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(path, old, new):
    # Existing upstream files mix CRLF and LF. Preserve every untouched byte.
    source = path.read_bytes().decode()
    pattern = r"\r?\n".join(re.escape(line) for line in old.split("\n"))
    matches = list(re.finditer(pattern, source))
    if len(matches) != 1:
        raise ValueError("source anchor changed: " + old[:80])
    match = matches[0]
    ending = "\r\n" if "\r\n" in match.group() else "\n"
    replacement = new.replace("\n", ending)
    path.write_bytes((source[:match.start()] + replacement + source[match.end():]).encode())


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or json.loads((BASE / "build_result.json").read_text()).get("passed") is not True:
        raise ValueError("scan_19 source/build identity gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    header = OUT / "src/path_searching/include/path_searching/dyn_a_star.h"
    cpp = OUT / "src/path_searching/src/dyn_a_star.cpp"
    once(header, "#include <queue>", "#include <queue>\n#include <limits>\n#include <cstdint>")
    once(header, "constexpr double inf = 1 >> 20;", "constexpr double inf = std::numeric_limits<double>::infinity();")
    once(header, "GridNodePtr cameFrom{NULL};", "GridNodePtr cameFrom{NULL};\n\tstd::uint64_t queue_revision{0};")
    once(header, "class NodeComparator", '''// Heap keys are snapshots, not references to mutable node scores. A better
// path creates a new record; obsolete records cannot close or finish a node.
struct OpenSetEntry
{
    GridNodePtr node;
    double f_at_enqueue;
    std::uint64_t revision;
    int round;

    explicit OpenSetEntry(GridNodePtr value)
        : node(value), f_at_enqueue(value->fScore),
          revision(value->queue_revision), round(value->rounds) {}

    bool current(int search_round) const
    {
        return round == search_round && node->rounds == search_round &&
               revision == node->queue_revision && node->state == GridNode::OPENSET;
    }
};

class NodeComparator''')
    once(header, "bool operator()(GridNodePtr node1, GridNodePtr node2)",
         "bool operator()(const OpenSetEntry &node1, const OpenSetEntry &node2) const")
    once(header, "return node1->fScore > node2->fScore;", "return node1.f_at_enqueue > node2.f_at_enqueue;")
    old_queue = "std::priority_queue<GridNodePtr, std::vector<GridNodePtr>, NodeComparator>"
    new_queue = "std::priority_queue<OpenSetEntry, std::vector<OpenSetEntry>, NodeComparator>"
    once(header, old_queue, new_queue)
    once(cpp, old_queue, new_queue)
    once(cpp, "    startPtr->cameFrom = NULL;", "    startPtr->cameFrom = NULL;\n    ++startPtr->queue_revision;")
    once(cpp, "    openSet_.push(startPtr);", "    openSet_.emplace(startPtr);")
    timeout = '''        const auto time_2 = std::chrono::steady_clock::now();
        if (std::chrono::duration<double>(time_2 - time_1).count() > 0.2)
        {
            RCLCPP_WARN(rclcpp::get_logger("path_searching"),
                        "Failed in A-star path search: 0.2 second time limit exceeded");
            return ASTAR_RET::SEARCH_ERR;
        }'''
    once(cpp, timeout, "")
    once(cpp, '''        num_iter++;
        current = openSet_.top();
        openSet_.pop();''', '''        // The unchanged wall budget also covers obsolete heap records.
        const auto time_2 = std::chrono::steady_clock::now();
        if (std::chrono::duration<double>(time_2 - time_1).count() > 0.2)
        {
            RCLCPP_WARN(rclcpp::get_logger("path_searching"),
                        "Failed in A-star path search: 0.2 second time limit exceeded");
            return ASTAR_RET::SEARCH_ERR;
        }
        num_iter++;
        const OpenSetEntry entry = openSet_.top();
        openSet_.pop();
        if (!entry.current(rounds_)) continue;
        current = entry.node;''')
    once(cpp, "                neighborPtr->rounds = rounds_;", "                // A rejected approach must leave this node undiscovered.")
    once(cpp, '''                    //discover a new node
                    neighborPtr->state = GridNode::OPENSET;''', '''                    // Discover only after the original occupancy check passes.
                    neighborPtr->rounds = rounds_;
                    ++neighborPtr->queue_revision;
                    neighborPtr->state = GridNode::OPENSET;''')
    once(cpp, "                    openSet_.push(neighborPtr);", "                    openSet_.emplace(neighborPtr);")
    once(cpp, '''                { //in open set and need update
                    neighborPtr->cameFrom = current;
                    neighborPtr->gScore = tentative_gScore;
                    neighborPtr->fScore = tentative_gScore + getHeu(neighborPtr, endPtr);
                }''', '''                { // Improved cost: enqueue a fresh key and invalidate old records.
                    ++neighborPtr->queue_revision;
                    neighborPtr->cameFrom = current;
                    neighborPtr->gScore = tentative_gScore;
                    neighborPtr->fScore = tentative_gScore + getHeu(neighborPtr, endPtr);
                    openSet_.emplace(neighborPtr);
                }''')
    manifest = {"base": "scan_19", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
                "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in (header, cpp)},
                "change": "Discover after occupancy passes; true infinite initial cost; immutable heap keys with revision/round validation and requeue on improved cost",
                "preserved": "Original occupancy calls and rules, heuristic, XYZ directed-edge model, source maps/tracks, 0.2 s wall budget, seed edge and final spline gates",
                "generator_sha256": sha(Path(__file__))}
    (OUT / "astar_bookkeeping_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
