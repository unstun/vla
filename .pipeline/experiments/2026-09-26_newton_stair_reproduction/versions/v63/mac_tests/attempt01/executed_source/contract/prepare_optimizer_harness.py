"""Script only occupancy/search boundaries around the actual optimizer flow."""
from pathlib import Path
import hashlib,json,sys
from prepare_retry_harness import replace_body

candidate,destination,provenance=map(Path,sys.argv[1:])
header=candidate/'src/plan_env/include/plan_env/grid_map.h'
contents=replace_body(header.read_text(),
    'inline int GridMap::getInflateOccupancy(Eigen::Vector3d pos, double yaw)',
    '  extern int optimizer_fixture_occupancy(Eigen::Vector3d, double);\n'
    '  return optimizer_fixture_occupancy(pos,yaw);')
output=destination/'plan_env/grid_map.h';output.parent.mkdir(parents=True,exist_ok=False)
output.write_text(contents)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
provenance.write_text(json.dumps({'original_header_sha256':sha(header),
    'transformed_header_sha256':sha(output),
    'scope':'Actual optimizer/LBFGS source with scripted occupancy and graph search outcomes',
    'excluded_claims':['collision/support acceptance','dynamics','live max latency','30 Hz']},indent=2)+'\n')
