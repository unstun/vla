"""Generate an observer-only copy of the SHA-verified frozen search source."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
parent=HERE.parents[1]/'versions/v240/src/path_searching/src/dyn_a_star.cpp'
text=parent.read_text().replace('using namespace std;','#include "search_trace.h"\nusing namespace std;',1)
needle='    const auto time_1 = std::chrono::steady_clock::now();'
assert text.count(needle)==1
text=text.replace(needle,'    beginSearch(start_pt,end_pt,step_size);\n'+needle)
text=text.replace('grid_map_->collisionFreeSegment(', 'auditSegment(grid_map_.get(),')
import re
text=re.sub(r'return (ASTAR_RET::\w+);',r'return auditReturn(\1,__LINE__);',text)
out=Path('/output/generated');out.mkdir(parents=True,exist_ok=True)
(out/'dyn_a_star.cpp').write_text(text)
(out/'instrumentation.json').write_text(json.dumps(dict(parent_sha256=hashlib.sha256(parent.read_bytes()).hexdigest(),diagnostic_sha256=hashlib.sha256(text.encode()).hexdigest(),semantic_change='none; failed sample requery and counters only'),indent=2)+'\n')
