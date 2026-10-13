"""Diagnostic-only copy of the v27 optimizer with rebound-assignment tracing.

Production sources are not modified. Each insertion is anchored exactly once,
tolerating the upstream file's mixed CRLF/LF endings like materialize_scan_20.once.
"""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[2] / "runtime/scan59_seed_shortcut_v27/src/bspline_opt/src/bspline_optimizer.cpp"
EXPECTED = "cb2e0422c8d676e55cbf0ff7ba5d16b75a516c4dda8473331b47e440b42fb342"
OUT = HERE / "diagnostic_src/bspline_optimizer.cpp"


def once(text, old, new):
    pattern = r"\r?\n".join(re.escape(line) for line in old.split("\n"))
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise ValueError("anchor count %d: %s" % (len(matches), old[:70]))
    match = matches[0]
    ending = "\r\n" if "\r\n" in match.group() else "\n"
    return text[:match.start()] + new.replace("\n", ending) + text[match.end():]


data = SOURCE.read_bytes()
assert hashlib.sha256(data).hexdigest() == EXPECTED
text = data.decode()
text = once(text, '#include "bspline_opt/bspline_optimizer.h"',
            '#include <cstdio>\n#include "bspline_opt/bspline_optimizer.h"')
# Rebound callback only: the 8-space "step 1" and 10/14-space lines are unique to it.
text = once(text, "      vector<vector<Eigen::Vector3d>> a_star_paths;\n      for (size_t i = 0; i < segment_ids.size(); ++i)",
            "      std::fprintf(stderr, \"[REBOUND-CALL] segments=%zu\\n\", segment_ids.size());\n"
            "      vector<vector<Eigen::Vector3d>> a_star_paths;\n      for (size_t i = 0; i < segment_ids.size(); ++i)")
text = once(text, "        // step 1\n        for (int j = segment_ids[i].first; j <= segment_ids[i].second; ++j)",
            "        std::fprintf(stderr, \"[REBOUND-SEGMENT] seg=%zu first=%d second=%d path_points=%zu\\n\", i,\n"
            "                     segment_ids[i].first, segment_ids[i].second, a_star_paths[i].size());\n"
            "        // step 1\n        for (int j = segment_ids[i].first; j <= segment_ids[i].second; ++j)")
text = once(text, "          Eigen::Vector3d ctrl_pts_law(cps_.points.col(j + 1) - cps_.points.col(j - 1)), intersection_point;",
            "          Eigen::Vector3d ctrl_pts_law(cps_.points.col(j + 1) - cps_.points.col(j - 1)), intersection_point;\n"
            "          const int trace_got_before = got_intersection_id;\n"
            "          const size_t trace_pairs_before = cps_.base_point[j].size();\n"
            "          bool trace_crossing = false;\n"
            "          double trace_length = -1.0;")
text = once(text, "              got_intersection_id = j;\n              break;",
            "              got_intersection_id = j;\n              trace_crossing = true;\n              break;")
text = once(text, "            double length = (intersection_point - cps_.points.col(j)).norm();\n            if (length > 1e-5)",
            "            double length = (intersection_point - cps_.points.col(j)).norm();\n"
            "            trace_length = length;\n            if (length > 1e-5)")
text = once(text, "              got_intersection_id = -1;\n            }\n          }\n        }\n\n        //step 3",
            "              got_intersection_id = -1;\n            }\n          }\n"
            "          std::fprintf(stderr, \"[REBOUND-POINT] seg=%zu j=%d got_before=%d crossing=%d length=%.9g \"\n"
            "                       \"got_after=%d flag=%d pairs_before=%zu pairs_after=%zu\\n\", i, j, trace_got_before,\n"
            "                       int(trace_crossing), trace_length, got_intersection_id, int(cps_.flag_temp[j]),\n"
            "                       trace_pairs_before, cps_.base_point[j].size());\n"
            "        }\n\n        //step 3")
for neighbor in ("j - 1", "j + 1"):
    old = f"              cps_.base_point[j].push_back(cps_.base_point[{neighbor}].back());"
    text = once(text, old,
                f"              if (cps_.base_point[{neighbor}].empty())\n"
                f"                std::fprintf(stderr, \"[EMPTY-NEIGHBOR] seg=%zu j=%d neighbor=%d got=%d flag_neighbor=%d\\n\",\n"
                f"                             i, j, {neighbor}, got_intersection_id, int(cps_.flag_temp[{neighbor}]));\n" + old)
OUT.parent.mkdir(exist_ok=True)
OUT.write_bytes(text.encode())
(HERE / "diagnostic_source.json").write_text(json.dumps({
    "parent": str(SOURCE.relative_to(HERE.parents[5])), "parent_sha256": EXPECTED,
    "diagnostic_sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
    "scope": "Adds stderr tracing to the rebound callback's assignment and propagation only; no behavior change intended."}, indent=2) + "\n")
print("diagnostic source written")
